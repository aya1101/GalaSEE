from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
from .contracts import TideAwareRunRequest
from .deterministic_engine import run_track_analysis
from .jobs import SAFE_ID, read_run_state, run_state_path, write_run_state
from .live_assets import AssetCompatibilityError, ensure_live_scene_assets, read_common_stack
from .live_scenes import SceneCompatibilityError, filter_scene_records, select_scene_roles
from .live_tide import DEFAULT_UHSLC_URL, evaluate_tide_coverage, fetch_uhslc_hourly, interpolate_tide, tide_window
from .pipeline import build_track_summary
from .report import build_report_payload, render_report_html


router = APIRouter(prefix="/api/v1/tideaware", tags=["tideaware"])
RUN_TASKS: dict[str, asyncio.Task] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _root() -> Path:
    from .. import main
    return main.ANALYTICS_CACHE_DIR / "tideaware"


def _run_dir(run_id: str) -> Path:
    if not SAFE_ID.fullmatch(run_id):
        raise ValueError("Invalid TideAware run id")
    root = _root()
    path = root / run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_path(run_id: str) -> Path:
    return run_state_path(_root(), run_id)


def _write_state(run_id: str, state: dict) -> None:
    write_run_state(_state_path(run_id), state)


def _read_state(run_id: str) -> dict | None:
    return read_run_state(_state_path(run_id))


def _default_frame(track: str) -> str | None:
    return os.getenv(f"TIDEAWARE_FRAME_{track}", {"047": "083", "155": "007"}.get(track, "")) or None


def _json_file(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _blocked_track(track: str, warning: str) -> dict:
    return {
        "track": track,
        "status": "blocked",
        "scene_roles": [],
        "tide": {"status": "UNAVAILABLE", "source": "UHSLC", "station": os.getenv("TIDEAWARE_TIDE_STATION", "383"), "covered_count": 0, "total_count": 0, "missing_scene_ids": [], "reason": warning},
        "layers": [],
        "candidate_area_ha": 0.0,
        "repeated_anomaly_area_ha": 0.0,
        "validation_status": "NOT VALIDATED",
        "warnings": [warning],
    }


async def _run_tideaware(run_id: str, request: TideAwareRunRequest) -> None:
    state = _read_state(run_id) or {}
    state.update({"status": "resolving", "stage": "Loading live ASF scene catalog", "progress": 0.05, "updatedAt": _now()})
    _write_state(run_id, state)
    try:
        from .. import main

        records = await main.earthdata_scene_catalog()
        if not records:
            raise RuntimeError("Live ASF scene catalog is unavailable or returned no scenes")
        tracks = [request.track] if request.track != "both" else ["047", "155"]
        collection = os.getenv("TIDEAWARE_COLLECTION", "C3622241360-ASF")
        filtered_records = filter_scene_records(records, collection)
        catalog_records = filtered_records or records
        frame_map = {track: request.frame or _default_frame(track) for track in tracks}

        state.update({"stage": "Fetching UHSLC tide observations", "progress": 0.12, "updatedAt": _now()})
        _write_state(run_id, state)
        station = os.getenv("TIDEAWARE_TIDE_STATION", "383")
        tide_url = os.getenv("TIDEAWARE_UHSLC_URL", DEFAULT_UHSLC_URL)
        tide_path = _root() / "tide" / f"station-{station}.csv"
        tide_series = await asyncio.to_thread(fetch_uhslc_hourly, tide_url, cache_path=tide_path)

        summaries: list[dict] = []
        for track_index, track in enumerate(tracks):
            frame = frame_map[track]
            state.update({"stage": f"Processing Track {track}", "progress": 0.18 + (track_index / max(len(tracks), 1)) * 0.72, "updatedAt": _now()})
            _write_state(run_id, state)
            try:
                roles = select_scene_roles(catalog_records, track=track, frame=frame, reference_count=request.reference_count, monitoring_count=request.monitoring_count)
                samples = [interpolate_tide(tide_series, role.acquisition_time) for role in roles]
                coverage = evaluate_tide_coverage(samples, scene_ids=[role.scene_id for role in roles], source=f"UHSLC station {station}", station=station)
                roles = [role.model_copy(update={"tide_level_m": sample.level_m, "tide_covered": sample.covered}) for role, sample in zip(roles, samples)]
                scene_ids = [role.scene_id for role in roles]
                extracted = await asyncio.gather(*(
                    main.ensure_cached_gcov_raster(scene_id, collection, band)
                    for scene_id in scene_ids
                    for band in request.bands
                ))
                resolved: dict[tuple[str, str], tuple[Path, dict]] = {}
                cursor = 0
                for scene_id in scene_ids:
                    for band in request.bands:
                        path, metadata = extracted[cursor]
                        resolved[(scene_id, band)] = (path, {**metadata, "unit": metadata.get("unit") or os.getenv("TIDEAWARE_RASTER_UNIT", "power")})
                        cursor += 1
                assets = ensure_live_scene_assets(scene_ids, list(request.bands), lambda scene_id, band: resolved[(scene_id, band)])
                stacks = read_common_stack(assets)
                first_asset = assets[0]
                with rasterio.open(first_asset.path) as source:
                    transform = source.transform
                    crs = source.crs.to_string() if source.crs else "EPSG:4326"
                result = run_track_analysis(
                    track=track,
                    roles=[role.role for role in roles],
                    stacks=stacks,
                    tide_levels=np.asarray([role.tide_level_m if role.tide_level_m is not None else np.nan for role in roles], dtype="float64"),
                    z_thr=request.z_thr,
                    z_pos=request.z_pos,
                    min_db_drop=request.min_db_drop,
                    cusum_k=request.cusum_k,
                    cusum_h=request.cusum_h,
                    min_patch=request.min_patch,
                    transform=transform,
                    crs=crs,
                )
                summary, artifacts = build_track_summary(
                    track=track,
                    roles=roles,
                    tide=coverage.model_dump(mode="json"),
                    result=result,
                    layer_url_factory=lambda branch, band, track=track: f"/api/v1/tideaware/runs/{run_id}/layer/{track}/{branch.lower()}/{band.lower()}",
                )
                for branch, band, feature_collection in artifacts:
                    _json_file(_run_dir(run_id) / f"{track}_{branch.lower()}_{band.lower()}.geojson", feature_collection)
                summaries.append(summary)
            except (SceneCompatibilityError, AssetCompatibilityError, ValueError, OSError, RuntimeError) as error:
                summaries.append(_blocked_track(track, str(error)))

        if not summaries or all(item["status"] == "blocked" for item in summaries):
            state.update({"status": "blocked", "stage": "No track completed", "progress": 1.0, "tracks": summaries, "error": "No track could be processed", "updatedAt": _now()})
        else:
            state.update({"status": "ready", "stage": "Report ready", "progress": 1.0, "tracks": summaries, "updatedAt": _now()})
        state["validation_status"] = "NOT VALIDATED"
        state["provenance"] = {"sceneSource": "Live ASF/Earthdata catalog", "rasterSource": "Live Harmony GeoTIFF cache", "tideSource": tide_series.source, "tideStation": station, "tracks": tracks, "frames": frame_map}
        report = build_report_payload(state)
        report_json = _run_dir(run_id) / "report.json"
        report_html = _run_dir(run_id) / "report.html"
        _json_file(report_json, report)
        report_html.write_text(render_report_html(report), encoding="utf-8")
        state.update({"report_url": f"/api/v1/tideaware/runs/{run_id}/report.json", "report_html_url": f"/api/v1/tideaware/runs/{run_id}/report.html"})
    except Exception as error:
        state.update({"status": "error", "stage": "Run failed", "progress": 1.0, "error": str(error), "updatedAt": _now(), "validation_status": "NOT VALIDATED"})
    _write_state(run_id, state)


@router.post("/runs", status_code=202)
async def tideaware_start(request: TideAwareRunRequest):
    run_id = uuid.uuid4().hex
    state = {"id": run_id, "status": "queued", "stage": "Queued", "progress": 0.0, "tracks": [], "validation_status": "NOT VALIDATED", "request": request.model_dump(mode="json"), "createdAt": _now()}
    _write_state(run_id, state)
    task = asyncio.create_task(_run_tideaware(run_id, request))
    RUN_TASKS[run_id] = task
    task.add_done_callback(lambda _: RUN_TASKS.pop(run_id, None))
    return {"id": run_id, "status": "queued"}


@router.get("/tide")
async def tideaware_tide(center: str | None = None, hours: int = 72):
    try:
        center_time = datetime.fromisoformat(center.replace("Z", "+00:00")) if center else None
        station = os.getenv("TIDEAWARE_TIDE_STATION", "383")
        url = os.getenv("TIDEAWARE_UHSLC_URL", DEFAULT_UHSLC_URL)
        series = await asyncio.to_thread(fetch_uhslc_hourly, url, cache_path=_root() / "tide" / f"station-{station}.csv")
        observations = tide_window(series, center_time, hours=hours)
        target = interpolate_tide(series, center_time or series.end)
        return {
            "status": "AVAILABLE" if observations else "UNAVAILABLE",
            "source": series.source,
            "station": station,
            "center": center_time.isoformat() if center_time else None,
            "targetLevelM": target.level_m if target and target.covered else None,
            "observations": [{"timestamp": item.timestamp.isoformat(), "levelM": item.level_m} for item in observations],
        }
    except (OSError, ValueError, RuntimeError) as error:
        return JSONResponse({"error": "Unable to load tide observations", "detail": str(error)}, status_code=502)


@router.get("/runs/{run_id}")
async def tideaware_status(run_id: str):
    try:
        state = _read_state(run_id)
    except ValueError:
        state = None
    if not state:
        return JSONResponse({"error": "TideAware run not found"}, status_code=404)
    return state


@router.get("/runs/{run_id}/layer/{track}/{branch}/{band}")
async def tideaware_layer(run_id: str, track: str, branch: str, band: str):
    if track not in {"047", "155"} or branch not in {"original", "corrected"} or band not in {"hhhh", "hvhv"}:
        return JSONResponse({"error": "Unknown TideAware layer"}, status_code=404)
    try:
        path = _run_dir(run_id) / f"{track}_{branch}_{band}.geojson"
    except ValueError:
        return JSONResponse({"error": "TideAware run not found"}, status_code=404)
    if not path.is_file():
        return JSONResponse({"error": "TideAware layer is not ready"}, status_code=404)
    return FileResponse(path, media_type="application/geo+json", headers={"Cache-Control": "no-store", "X-TideAware-Data-Source": "live-analysis"})


@router.get("/runs/{run_id}/report.json")
async def tideaware_report_json(run_id: str):
    try:
        path = _run_dir(run_id) / "report.json"
    except ValueError:
        return JSONResponse({"error": "TideAware run not found"}, status_code=404)
    if not path.is_file():
        return JSONResponse({"error": "TideAware report is not ready"}, status_code=409)
    return FileResponse(path, media_type="application/json", headers={"Cache-Control": "no-store"})


@router.get("/runs/{run_id}/report.html")
async def tideaware_report_html(run_id: str):
    try:
        path = _run_dir(run_id) / "report.html"
    except ValueError:
        return JSONResponse({"error": "TideAware run not found"}, status_code=404)
    if not path.is_file():
        return JSONResponse({"error": "TideAware report is not ready"}, status_code=409)
    return FileResponse(path, media_type="text/html", headers={"Cache-Control": "no-store"})
