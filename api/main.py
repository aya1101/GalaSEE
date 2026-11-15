import os
import re
import hashlib
import json
import asyncio
import uuid
from typing import Literal
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from shapely.geometry import shape

from .gcov_analytics import AnalyticsError, compare_rasters, raster_metadata, raster_profile, region_statistics, sample_pixel
from .gcov_preview import render_preview_png
from .copilot_models import CatalogResult
from .copilot_context import build_map_context, build_scene_truth
from .aoi_registry import AoiRegistry
from .copilot import CopilotRequest, CopilotService
from .copilot_tools import ToolContext
from .default_aoi import DEFAULT_AOI_GEOMETRY, DEFAULT_AOI_ID


load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GCOV_CACHE_DIR = Path(os.getenv("GCOV_CACHE_DIR", Path(__file__).resolve().parent.parent / ".cache" / "gcov"))
GCOV_CACHE_DIR.mkdir(parents=True, exist_ok=True)
GCOV_CACHE_INDEX = GCOV_CACHE_DIR / "index.json"
GCOV_INSPECTION_DIR = GCOV_CACHE_DIR / "inspection"
GCOV_INSPECTION_DIR.mkdir(parents=True, exist_ok=True)
GCOV_INSPECTION_TTL_SECONDS = max(60, int(os.getenv("GCOV_INSPECTION_TTL_SECONDS", "21600")))
GCOV_COLLECTION_PATH_RE = re.compile(r"^/science/LSAR/GCOV/grids/(?P<frequency>frequency[^/]+)/(?P<name>[^/]+)$")
ANALYTICS_CACHE_DIR = GCOV_CACHE_DIR / "analytics"
COMPARISON_DIR = ANALYTICS_CACHE_DIR / "comparisons"
PREVIEW_DIR = ANALYTICS_CACHE_DIR / "previews"
ANALYTICS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
COMPARISON_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
COMPARISON_TASKS: dict[str, asyncio.Task] = {}
GCOV_INFLIGHT: dict[str, asyncio.Task] = {}
COPILOT_AOIS = AoiRegistry()
COPILOT_AOIS.register("default", DEFAULT_AOI_GEOMETRY, DEFAULT_AOI_ID)
COPILOT_AOIS.register("browser-session", DEFAULT_AOI_GEOMETRY, DEFAULT_AOI_ID)
COPILOT_SERVICE = CopilotService()


def configured_origins() -> list[str]:
    raw_origins = os.getenv("WEB_ORIGIN", "http://localhost:3000")
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


app = FastAPI(
    title="TideAware API",
    version="0.1.0",
    description="Evidence-aware coastal intelligence API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-TideAware-Data-Source", "X-TideAware-Catalog-Mode", "X-TideAware-Asset-Mode", "X-TideAware-Data-Status"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "tideaware-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/api/v1/copilot/chat")
async def copilot_chat(request: CopilotRequest):
    try:
        COPILOT_AOIS.resolve(request.conversationId, request.mapContext.aoiId, request.mapContext.aoiHash)
    except ValueError as error:
        return JSONResponse({"error": "Invalid copilot AOI context", "detail": str(error)}, status_code=400)
    return StreamingResponse(
        COPILOT_SERVICE.stream_sse(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.get("/api/v1/meta")
def metadata() -> dict[str, str]:
    return {
        "name": "TideAware",
        "version": "0.1.0",
        "stage": "earthdata-connected",
        "data_status": "live-asf-nisar-geojson-and-browse",
    }


def is_allowed_earthdata_url(raw_url: str) -> bool:
    parsed = urlparse(raw_url)
    host = (parsed.hostname or "").lower().rstrip(".")
    configured = [item.strip().lower() for item in os.getenv("EARTHDATA_ALLOWED_HOSTS", "").split(",") if item.strip()]
    host_allowed = any(host == item or host.endswith(f".{item}") for item in configured)
    nasa_allowed = host.endswith(".nasa.gov") or host.endswith(".earthdata.nasa.gov")
    return parsed.scheme == "https" and host != "urs.earthdata.nasa.gov" and (nasa_allowed or host_allowed)


async def stream_earthdata_url(data_url: str, accept: str, expected_type: str):
    token = os.getenv("EARTHDATA_TOKEN", "").strip()
    if not token or not data_url:
        return JSONResponse({"error": "Earthdata is not configured", "hint": "Set EARTHDATA_TOKEN and EARTHDATA_DATA_URL."}, status_code=503)
    if not is_allowed_earthdata_url(data_url):
        return JSONResponse({"error": "EARTHDATA_DATA_URL is not an allowed HTTPS NASA URL."}, status_code=400)

    client = httpx.AsyncClient(timeout=None, follow_redirects=True)
    try:
        request = client.build_request("GET", data_url, headers={"Authorization": f"Bearer {token}", "Accept": accept})
        upstream = await client.send(request, stream=True)
    except httpx.HTTPError as error:
        await client.aclose()
        return JSONResponse({"error": "Unable to reach Earthdata", "detail": str(error)}, status_code=502)

    if upstream.status_code >= 400:
        body = await upstream.aread()
        await upstream.aclose()
        await client.aclose()
        return JSONResponse({"error": "Earthdata rejected the request", "upstream_status": upstream.status_code, "detail": body.decode("utf-8", errors="replace")[:500]}, status_code=upstream.status_code)

    async def stream_bytes():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    content_type = upstream.headers.get("content-type", expected_type).split(";", 1)[0]
    if expected_type.startswith("image/") and content_type in {"binary/octet-stream", "application/octet-stream"}:
        content_type = expected_type
    return StreamingResponse(stream_bytes(), status_code=upstream.status_code, media_type=content_type, headers={"X-TideAware-Data-Source": "earthdata", "Cache-Control": "no-store"})


def safe_harmony_id(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+", value))


async def harmony_get(url: str, token: str):
    client = httpx.AsyncClient(timeout=180, follow_redirects=False)
    try:
        response = await client.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        payload = response.json() if response.content else {}
    except (httpx.HTTPError, ValueError) as error:
        await client.aclose()
        return None, JSONResponse({"error": "Unable to reach Harmony", "detail": str(error)}, status_code=502)
    await client.aclose()
    return response, payload


def gcov_label(scene: str, collection: str, variable_path: str) -> str:
    key = f"{collection}:{scene}:{variable_path}".encode("utf-8")
    return f"tideaware-gcov-{hashlib.sha256(key).hexdigest()[:24]}"


def legacy_gcov_label(scene: str, collection: str, variable: str) -> str:
    """Keep reusing GeoTIFF jobs created before variable paths were discovered."""
    key = f"{collection}:{scene}:{variable}".encode("utf-8")
    return f"tideaware-gcov-{hashlib.sha256(key).hexdigest()[:24]}"


def gcov_inspection_path(collection: str) -> Path:
    safe_collection = re.sub(r"[^A-Za-z0-9_.-]+", "_", collection)
    return GCOV_INSPECTION_DIR / f"{safe_collection}.json"


def read_cached_gcov_inspection(collection: str) -> dict | None:
    path = gcov_inspection_path(collection)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        return None
    cached_at = harmony_timestamp(payload.get("cachedAt"))
    if not cached_at or (datetime.now(timezone.utc) - cached_at).total_seconds() > GCOV_INSPECTION_TTL_SECONDS:
        return None
    return payload if isinstance(payload, dict) else None


def write_cached_gcov_inspection(collection: str, payload: dict) -> dict:
    enriched = {**payload, "cachedAt": datetime.now(timezone.utc).isoformat()}
    path = gcov_inspection_path(collection)
    partial_path = path.with_suffix(".part")
    partial_path.write_text(json.dumps(enriched, indent=2), encoding="utf-8")
    os.replace(partial_path, path)
    return enriched


def gcov_path_from_collection_item(item: dict) -> str | None:
    for link in item.get("links", []) if isinstance(item.get("links"), list) else []:
        title = link.get("title") if isinstance(link, dict) else None
        if isinstance(title, str) and title.startswith("Perform rangeset request for "):
            path = title.removeprefix("Perform rangeset request for ").strip()
            if GCOV_COLLECTION_PATH_RE.fullmatch(path):
                return path
    title = item.get("title")
    if isinstance(title, str):
        path = title.split(" NISAR_", 1)[0].strip()
        if GCOV_COLLECTION_PATH_RE.fullmatch(path):
            return path
    return None


def build_gcov_inspection(collection: str, collections_payload: dict, capabilities_payload: dict | None) -> dict:
    variables: list[dict] = []
    for item in collections_payload.get("collections", []) if isinstance(collections_payload.get("collections"), list) else []:
        if not isinstance(item, dict):
            continue
        path = gcov_path_from_collection_item(item)
        if not path:
            continue
        match = GCOV_COLLECTION_PATH_RE.fullmatch(path)
        if not match:
            continue
        variables.append({
            "path": path,
            "name": match.group("name"),
            "frequency": match.group("frequency"),
            "title": item.get("title"),
            "description": item.get("description"),
            "id": item.get("id"),
            "extentCrs": (item.get("extent") or {}).get("spatial", {}).get("crs") if isinstance(item.get("extent"), dict) else None,
        })
    variables.sort(key=lambda item: (item["frequency"], item["name"]))
    frequencies: dict[str, dict] = {}
    for item in variables:
        frequency = item["frequency"]
        group = frequencies.setdefault(frequency, {"bands": [], "paths": []})
        group["paths"].append(item["path"])
        if item["name"] not in {"mask", "numberOfLooks", "rtcGammaToSigmaFactor"}:
            group["bands"].append(item["name"])
    return {
        "collection": collection,
        "source": "Harmony OGC API collection metadata",
        "variables": variables,
        "frequencies": frequencies,
        "metadata": {
            "datasetCrs": "not exposed by Harmony collection metadata",
            "extentCrs": next((item.get("extentCrs") for item in variables if item.get("extentCrs")), None),
            "supportedOutputCrs": [item.get("crs") for item in ((capabilities_payload or {}).get("summary", {}).get("reprojection", {}).get("supportedProjections", [])) if item.get("crs")],
            "units": "not exposed by Harmony collection metadata",
            "validRange": "not exposed by Harmony collection metadata",
        },
    }


async def inspect_gcov_collection(collection: str, token: str, refresh: bool = False) -> dict:
    if not refresh:
        cached = read_cached_gcov_inspection(collection)
        if cached:
            return cached
    collections_url = f"https://harmony.earthdata.nasa.gov/{collection}/ogc-api-coverages/1.0.0/collections"
    capabilities_url = f"https://harmony.earthdata.nasa.gov/capabilities?collectionId={quote(collection, safe='')}"
    collections_result, capabilities_result = await asyncio.gather(
        harmony_get(collections_url, token),
        harmony_get(capabilities_url, token),
    )
    collections_response, collections_payload = collections_result
    capabilities_response, capabilities_payload = capabilities_result
    if collections_response is None:
        raise RuntimeError("Unable to inspect Harmony collection metadata")
    if collections_response.status_code >= 400:
        raise RuntimeError(f"Harmony collection metadata failed with status {collections_response.status_code}")
    if not isinstance(collections_payload, dict):
        raise RuntimeError("Harmony collection metadata was not JSON")
    return write_cached_gcov_inspection(
        collection,
        build_gcov_inspection(collection, collections_payload, capabilities_payload if capabilities_response and capabilities_response.status_code < 400 else None),
    )


def resolve_gcov_variable(manifest: dict, variable: str, frequency: str = "auto") -> dict | None:
    requested = variable.strip()
    variables = manifest.get("variables", [])
    if requested.startswith("/science/"):
        return next((item for item in variables if item.get("path") == requested), None)
    candidates = [item for item in variables if item.get("name", "").upper() == requested.upper()]
    if frequency != "auto":
        candidates = [item for item in candidates if item.get("frequency", "").lower() == frequency.lower()]
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item.get("frequency", ""), item.get("path", "")))
    return candidates[0]


def harmony_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def harmony_job_data_url(payload: dict) -> str | None:
    for link in payload.get("links", []):
        if link.get("rel") == "data" and link.get("href"):
            return str(link["href"])
    return None


def gcov_cache_path(job_id: str) -> Path:
    return GCOV_CACHE_DIR / f"{job_id}.tif"


def read_gcov_cache_index() -> dict:
    try:
        value = json.loads(GCOV_CACHE_INDEX.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, OSError, ValueError):
        return {}


def cached_gcov_job_for_label(label: str) -> str | None:
    for job_id, record in read_gcov_cache_index().items():
        if record.get("label") == label and gcov_cache_path(job_id).is_file():
            return job_id
    return None


def record_gcov_cache(job_id: str, label: str | None) -> None:
    if not label:
        return
    index = read_gcov_cache_index()
    index[job_id] = {"label": label, "cachedAt": datetime.now(timezone.utc).isoformat()}
    partial_index = GCOV_CACHE_INDEX.with_suffix(".part")
    partial_index.write_text(json.dumps(index, indent=2), encoding="utf-8")
    os.replace(partial_index, GCOV_CACHE_INDEX)


def harmony_job_label(payload: dict) -> str | None:
    labels = payload.get("labels", [])
    for label in labels if isinstance(labels, list) else []:
        if isinstance(label, str) and label.startswith("tideaware-gcov-"):
            return label
    request = payload.get("request", "")
    if isinstance(request, str):
        label = parse_qs(urlparse(request).query).get("label", [None])[0]
        if isinstance(label, str) and label.startswith("tideaware-gcov-"):
            return label
    return None


def cached_gcov_file(job_id: str) -> FileResponse | None:
    path = gcov_cache_path(job_id)
    if not path.is_file() or path.stat().st_size == 0:
        return None
    return FileResponse(
        path,
        media_type="image/tiff",
        filename=f"{job_id}.tif",
        headers={
            "X-TideAware-Data-Source": "local-cache",
            "Cache-Control": "public, max-age=86400",
        },
    )


@app.get("/api/v1/earthdata/geojson")
async def earthdata_geojson():
    """Stream authenticated GeoJSON without exposing the Earthdata token to the browser."""
    return await stream_earthdata_url(os.getenv("EARTHDATA_DATA_URL", "").strip(), "application/geo+json, application/json", "application/geo+json")


@app.get("/api/v1/earthdata/browse")
async def earthdata_browse(url: str):
    """Proxy a protected ASF/NASA browse PNG while keeping the Earthdata token server-side."""
    if not url.strip():
        return JSONResponse({"error": "Missing browse URL"}, status_code=400)
    if not is_allowed_earthdata_url(url):
        return JSONResponse({"error": "Browse URL is not an allowed HTTPS NASA URL."}, status_code=400)
    response = await stream_earthdata_url(url, "image/png,image/*", "image/png")
    if isinstance(response, StreamingResponse) and not response.media_type.startswith("image/"):
        return JSONResponse({"error": "Browse endpoint did not return an image."}, status_code=415)
    return response


@app.get("/api/v1/earthdata/kml")
async def earthdata_kml(url: str):
    """Proxy the official KML quad used to georeference a protected browse image."""
    if not url.strip():
        return JSONResponse({"error": "Missing KML URL"}, status_code=400)
    if not is_allowed_earthdata_url(url):
        return JSONResponse({"error": "KML URL is not an allowed HTTPS NASA URL."}, status_code=400)
    return await stream_earthdata_url(url, "application/vnd.google-earth.kml+xml,text/xml,application/xml", "application/vnd.google-earth.kml+xml")


@app.get("/api/v1/earthdata/gcov/inspect")
async def earthdata_gcov_inspect(scene: str = "", collection: str = "C3622241360-ASF", refresh: bool = False):
    """Inspect the collection's real GCOV variables before any raster extraction."""
    token = os.getenv("EARTHDATA_TOKEN", "").strip()
    if not token or not safe_harmony_id(collection) or (scene and not safe_harmony_id(scene)):
        return JSONResponse({"error": "Invalid Earthdata inspection request"}, status_code=400)
    try:
        manifest = await inspect_gcov_collection(collection, token, refresh=refresh)
    except (RuntimeError, httpx.HTTPError) as error:
        return JSONResponse({"error": "Unable to inspect GCOV metadata", "detail": str(error)}, status_code=502)
    return {**manifest, "scene": scene or None}


@app.get("/api/v1/earthdata/gcov")
async def earthdata_gcov(scene: str, collection: str = "C3622241360-ASF", variable: str = "HHHH", frequency: str = "auto"):
    """Start a Harmony extraction of a discovered GCOV variable as a GeoTIFF."""
    token = os.getenv("EARTHDATA_TOKEN", "").strip()
    if not token:
        return JSONResponse({"error": "Earthdata is not configured"}, status_code=503)
    if not safe_harmony_id(scene) or not safe_harmony_id(collection) or not variable.strip() or (frequency != "auto" and not re.fullmatch(r"frequency[A-Za-z0-9]+", frequency, re.IGNORECASE)):
        return JSONResponse({"error": "Invalid scene, collection or GCOV variable"}, status_code=400)
    try:
        manifest = await inspect_gcov_collection(collection, token)
    except (RuntimeError, httpx.HTTPError) as error:
        return JSONResponse({"error": "Unable to inspect GCOV metadata", "detail": str(error)}, status_code=502)
    resolved = resolve_gcov_variable(manifest, variable, frequency)
    if not resolved:
        return JSONResponse({
            "error": "GCOV variable is not published for this collection",
            "requestedVariable": variable,
            "requestedFrequency": frequency,
            "availableVariables": manifest.get("variables", []),
        }, status_code=404)
    variable_path = resolved["path"]
    harmony_url = f"https://harmony.earthdata.nasa.gov/{collection}/ogc-api-coverages/1.0.0/collections/parameter_vars/coverage/rangeset"
    label = gcov_label(scene, collection, variable_path)
    labels = [label, legacy_gcov_label(scene, collection, resolved["name"])]
    for candidate_label in labels:
        cached_job_id = cached_gcov_job_for_label(candidate_label)
        if cached_job_id:
            return {"jobId": cached_job_id, "status": "successful", "variable": resolved["name"], "variablePath": variable_path, "frequency": resolved["frequency"], "cached": True}
        jobs_response, jobs_payload = await harmony_get(
            f"https://harmony.earthdata.nasa.gov/jobs?limit=10&label={quote(candidate_label, safe='')}",
            token,
        )
        if jobs_response is not None and jobs_response.status_code < 400 and isinstance(jobs_payload, dict):
            jobs = sorted(jobs_payload.get("jobs", []), key=lambda job: job.get("createdAt", ""), reverse=True)
            for job in jobs:
                status = job.get("status")
                if status == "successful":
                    return {"jobId": job.get("jobID"), "status": status, "variable": resolved["name"], "variablePath": variable_path, "frequency": resolved["frequency"], "cached": True}
                if status == "running":
                    updated_at = harmony_timestamp(job.get("updatedAt"))
                    if updated_at and (datetime.now(timezone.utc) - updated_at).total_seconds() < 600:
                        return {"jobId": job.get("jobID"), "status": status, "variable": resolved["name"], "variablePath": variable_path, "frequency": resolved["frequency"], "cached": True}
    params = {
        "granuleName": scene,
        "subset": ["lat(10.3686:10.6807)", "lon(106.7603:107.0276)"],
        "outputCrs": "EPSG:4326",
        "format": "image/tiff",
        "variable": variable_path,
        "forceAsync": "true",
        "skipPreview": "true",
        "label": label,
    }
    client = httpx.AsyncClient(timeout=60, follow_redirects=False)
    try:
        response = await client.get(harmony_url, params=params, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
    except httpx.HTTPError as error:
        await client.aclose()
        return JSONResponse({"error": "Unable to start Harmony extraction", "detail": str(error)}, status_code=502)
    body = response.text
    location = response.headers.get("location")
    await client.aclose()
    if response.status_code not in {200, 201, 202, 303} or not location:
        return JSONResponse({"error": "Harmony rejected the extraction", "upstream_status": response.status_code, "detail": body[:800]}, status_code=502 if response.status_code < 500 else response.status_code)
    job_id = location.rstrip("/").split("/")[-1]
    return {"jobId": job_id, "status": "running", "variable": resolved["name"], "variablePath": variable_path, "frequency": resolved["frequency"]}


@app.get("/api/v1/earthdata/gcov/{job_id}/status")
async def earthdata_gcov_status(job_id: str):
    """Return Harmony extraction status without exposing the staging URL to the browser."""
    token = os.getenv("EARTHDATA_TOKEN", "").strip()
    if not token or not safe_harmony_id(job_id):
        return JSONResponse({"error": "Invalid Harmony job"}, status_code=400)
    response, payload = await harmony_get(f"https://harmony.earthdata.nasa.gov/jobs/{job_id}", token)
    if response is None:
        return payload
    if response.status_code >= 400:
        return JSONResponse({"error": "Harmony job lookup failed", "upstream_status": response.status_code, "detail": str(payload)[:800]}, status_code=response.status_code)
    status = payload.get("status", "unknown")
    updated_at = harmony_timestamp(payload.get("updatedAt"))
    if status == "running" and updated_at and (datetime.now(timezone.utc) - updated_at).total_seconds() >= 600:
        status = "stale"
    result = {"jobId": job_id, "status": status, "progress": payload.get("progress", 0), "message": payload.get("message", ""), "updatedAt": payload.get("updatedAt")}
    if result["status"] == "successful":
        result["fileUrl"] = f"/api/v1/earthdata/gcov/{job_id}/file"
    return result


@app.get("/api/v1/earthdata/gcov/{job_id}/file")
async def earthdata_gcov_file(job_id: str):
    """Serve a cached GeoTIFF or stream it once from Harmony while saving it locally."""
    token = os.getenv("EARTHDATA_TOKEN", "").strip()
    if not token or not safe_harmony_id(job_id):
        return JSONResponse({"error": "Invalid Harmony job"}, status_code=400)
    cached = cached_gcov_file(job_id)
    if cached:
        return cached
    response, payload = await harmony_get(f"https://harmony.earthdata.nasa.gov/jobs/{job_id}", token)
    if response is None:
        return payload
    if response.status_code >= 400:
        return JSONResponse({"error": "Harmony job lookup failed", "upstream_status": response.status_code}, status_code=response.status_code)
    data_url = harmony_job_data_url(payload) if payload.get("status") == "successful" else None
    if not data_url:
        return JSONResponse({"error": "Harmony output is not ready", "status": payload.get("status", "unknown")}, status_code=409)
    if not is_allowed_earthdata_url(data_url):
        return JSONResponse({"error": "Harmony returned an invalid output URL"}, status_code=502)

    client = httpx.AsyncClient(timeout=None, follow_redirects=True)
    try:
        upstream = await client.send(
            client.build_request(
                "GET",
                data_url,
                headers={"Authorization": f"Bearer {token}", "Accept": "image/tiff,application/octet-stream"},
            ),
            stream=True,
        )
    except httpx.HTTPError as error:
        await client.aclose()
        return JSONResponse({"error": "Unable to download Harmony output", "detail": str(error)}, status_code=502)

    if upstream.status_code >= 400:
        body = await upstream.aread()
        await upstream.aclose()
        await client.aclose()
        return JSONResponse({"error": "Harmony output download failed", "upstream_status": upstream.status_code, "detail": body.decode("utf-8", errors="replace")[:500]}, status_code=upstream.status_code)

    cache_path = gcov_cache_path(job_id)
    partial_path = cache_path.with_name(f"{cache_path.stem}.{os.getpid()}.{id(upstream)}.part")
    label = harmony_job_label(payload)

    async def stream_and_cache():
        completed = False
        try:
            with partial_path.open("wb") as cache_file:
                async for chunk in upstream.aiter_bytes():
                    cache_file.write(chunk)
                    yield chunk
            os.replace(partial_path, cache_path)
            record_gcov_cache(job_id, label)
            completed = True
        finally:
            await upstream.aclose()
            await client.aclose()
            if not completed:
                partial_path.unlink(missing_ok=True)

    content_type = upstream.headers.get("content-type", "image/tiff").split(";", 1)[0]
    if content_type in {"binary/octet-stream", "application/octet-stream"}:
        content_type = "image/tiff"
    return StreamingResponse(
        stream_and_cache(),
        status_code=upstream.status_code,
        media_type=content_type,
        headers={"X-TideAware-Data-Source": "earthdata-and-local-cache", "Cache-Control": "public, max-age=86400"},
    )


def gcov_preview_id(job_id: str, variable: str, mode: str, low: float, high: float) -> str:
    value = f"{job_id}:{variable}:{mode}:{low:.4f}:{high:.4f}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:32]


def gcov_preview_paths(preview_id: str) -> tuple[Path, Path]:
    if not safe_harmony_id(preview_id):
        raise ValueError("Invalid preview id")
    return PREVIEW_DIR / f"{preview_id}.png", PREVIEW_DIR / f"{preview_id}.json"


@app.get("/api/v1/earthdata/gcov/preview")
async def earthdata_gcov_preview(
    scene: str,
    collection: str = "C3622241360-ASF",
    variable: str = "HHHH",
    mode: str = "grayscale",
    low: float = 2.0,
    high: float = 98.0,
):
    """Materialize a small server-side preview without sending the GeoTIFF to the browser."""
    token = os.getenv("EARTHDATA_TOKEN", "").strip()
    if not token or not safe_harmony_id(scene) or not safe_harmony_id(collection) or variable not in {"HHHH", "HVHV"}:
        return JSONResponse({"error": "Invalid GCOV preview request"}, status_code=400)
    if mode not in {"grayscale", "heatmap"} or not (0 <= low < high <= 100):
        return JSONResponse({"error": "Invalid preview styling"}, status_code=400)
    try:
        raster_path, resolved = await ensure_cached_gcov_raster(scene, collection, variable)
        preview_id = gcov_preview_id(raster_path.stem, variable, mode, low, high)
        image_path, meta_path = gcov_preview_paths(preview_id)
        if image_path.is_file() and meta_path.is_file():
            payload = _read_json(meta_path) or {}
            return {**payload, "status": "ready", "cached": True}
        render = render_preview_png(raster_path, image_path, mode=mode, low_percentile=low, high_percentile=high)
        payload = {
            "status": "ready",
            "cached": False,
            "previewId": preview_id,
            "fileUrl": f"/api/v1/earthdata/gcov/preview/file/{preview_id}",
            "scene": scene,
            "variable": resolved["name"],
            "coordinates": render["coordinates"],
            "width": render["width"],
            "height": render["height"],
            "stretch": render["stretch"],
            "sourceCrs": render["sourceCrs"],
            "source": "server-preview-cache",
        }
        _write_json(meta_path, payload)
        return payload
    except (AnalyticsError, OSError, ValueError) as error:
        return JSONResponse({"error": "Unable to render GCOV preview", "detail": str(error)}, status_code=502)


@app.get("/api/v1/earthdata/gcov/preview/file/{preview_id}")
async def earthdata_gcov_preview_file(preview_id: str):
    try:
        image_path, _ = gcov_preview_paths(preview_id)
    except ValueError:
        return JSONResponse({"error": "Invalid preview id"}, status_code=400)
    if not image_path.is_file():
        return JSONResponse({"error": "Preview is not ready"}, status_code=404)
    return FileResponse(image_path, media_type="image/png", headers={"Cache-Control": "public, max-age=86400", "X-TideAware-Data-Source": "server-preview-cache"})


# ---------------------------------------------------------------------------
# Cached raster analytics
# ---------------------------------------------------------------------------


class PixelRequest(BaseModel):
    scene: str
    collection: str = "C3622241360-ASF"
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)


class RegionStatsRequest(BaseModel):
    scene: str
    collection: str = "C3622241360-ASF"
    geometry: dict
    bands: list[Literal["HHHH", "HVHV"]] = ["HHHH", "HVHV"]


class ProfileRequest(BaseModel):
    scene: str
    collection: str = "C3622241360-ASF"
    bands: list[Literal["HHHH", "HVHV"]] = ["HHHH"]
    width: int = Field(default=96, ge=8, le=256)
    height: int = Field(default=64, ge=8, le=256)


class SceneTruthRequest(BaseModel):
    scene: str
    collection: str = "C3622241360-ASF"
    requestedBands: list[Literal["HHHH", "HVHV"]] = ["HHHH", "HVHV"]


class CopilotContextQuery(BaseModel):
    sceneId: str | None = None
    sceneDate: str | None = None
    band: Literal["HHHH", "HVHV", "COMPOSITE"] = "COMPOSITE"
    aoiId: str = "aoi-study"
    aoiHash: str
    timelineIndex: int = 0
    timelineCount: int = 0
    contextVersion: int = 0


class ComparisonCheckRequest(BaseModel):
    scene_t1: str
    scene_t2: str
    collection: str = "C3622241360-ASF"
    bands: list[Literal["HHHH", "HVHV"]] = ["HHHH", "HVHV"]
    aoi: dict


class ComparisonStartRequest(ComparisonCheckRequest):
    threshold_db: float = Field(default=3.0, ge=0.1, le=30)
    min_component_pixels: int = Field(default=9, ge=1, le=100000)


def _analytics_job_path(comparison_id: str) -> Path:
    if not safe_harmony_id(comparison_id):
        raise ValueError("Invalid comparison id")
    return COMPARISON_DIR / f"{comparison_id}.json"


def _write_json(path: Path, payload: dict) -> None:
    partial = path.with_suffix(f".{os.getpid()}.part")
    partial.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    os.replace(partial, path)


def _read_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def catalog_result_from_payload(status_code: int, payload: object) -> CatalogResult:
    if status_code >= 400:
        return CatalogResult(status="error", errorCode="UPSTREAM_HTTP_ERROR", detail=f"HTTP {status_code}")
    features = payload.get("features", []) if isinstance(payload, dict) else []
    records = [item for item in features if isinstance(item, dict)]
    return CatalogResult(status="ok", records=records)


async def earthdata_scene_catalog_result() -> CatalogResult:
    url = os.getenv("EARTHDATA_DATA_URL", "").strip()
    token = os.getenv("EARTHDATA_TOKEN", "").strip()
    if not url or not token or not is_allowed_earthdata_url(url):
        return CatalogResult(status="disabled", errorCode="EARTHDATA_NOT_CONFIGURED")
    client = httpx.AsyncClient(timeout=45, follow_redirects=True)
    try:
        response = await client.get(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/geo+json,application/json"})
        payload = response.json()
    except (httpx.HTTPError, asyncio.TimeoutError, TimeoutError, ValueError) as error:
        return CatalogResult(status="error", errorCode="UPSTREAM_ERROR", detail=str(error))
    finally:
        await client.aclose()
    return catalog_result_from_payload(response.status_code, payload)


async def earthdata_scene_catalog() -> list[dict]:
    result = await earthdata_scene_catalog_result()
    return result.records if result.status == "ok" else []


def _scene_name(record: dict) -> str:
    properties = record.get("properties") if isinstance(record.get("properties"), dict) else record
    return str(properties.get("fileName") or properties.get("fileID") or properties.get("granuleName") or record.get("id") or "")


async def find_scene_record(scene: str) -> dict | None:
    wanted = scene.removesuffix(".h5")
    for record in await earthdata_scene_catalog():
        name = _scene_name(record).removesuffix(".h5")
        if name == wanted or str(record.get("id", "")).removesuffix(".h5") == wanted:
            return record
    return None


def _scene_metadata(record: dict | None, fallback: str) -> dict:
    properties = record.get("properties") if isinstance(record and record.get("properties"), dict) else (record or {})
    def first(*names: str):
        for name in names:
            value = properties.get(name)
            if value not in (None, ""):
                return value
        return None
    browse_values = properties.get("browse") or properties.get("browseUrls") or properties.get("browseUrl") or []
    if isinstance(browse_values, str):
        browse_values = [browse_values]
    browse_available = any(isinstance(value, str) and value.strip() for value in browse_values) if isinstance(browse_values, list) else False
    if not browse_available and isinstance(record, dict) and isinstance(record.get("links"), list):
        browse_available = any(
            isinstance(link, dict)
            and any(
                isinstance(link.get(field), str)
                and ("browse" in link[field].lower() or link[field].lower().endswith((".png", ".jpg", ".jpeg")))
                for field in ("href", "title", "rel")
            )
            for link in record["links"]
        )
    return {
        "scene": _scene_name(record or {}) or fallback,
        "collection": first("conceptID", "collectionId", "collection") or "C3622241360-ASF",
        "product": first("processingLevel", "scienceProduct", "dataset", "platform") or "NISAR GCOV",
        "processingLevel": first("processingLevel") or "GCOV",
        "orbitDirection": first("flightDirection", "orbitDirection"),
        "track": first("pathNumber", "track", "path"),
        "frame": first("frameNumber", "frame"),
        "frequency": first("frequency", "frequencyA", "frequencyB"),
        "polarization": first("polarization", "polarizations", "mainPolarization", "sidePolarization"),
        "geometry": record.get("geometry") if isinstance(record, dict) else None,
        "startTime": first("startTime", "beginningDateTime"),
        "stopTime": first("stopTime", "endingDateTime"),
        "browseAvailable": browse_available,
    }


async def _resolved_gcov(scene: str, collection: str, variable: str) -> tuple[dict, dict]:
    token = os.getenv("EARTHDATA_TOKEN", "").strip()
    if not token:
        raise AnalyticsError("Earthdata is not configured")
    manifest = await inspect_gcov_collection(collection, token)
    resolved = resolve_gcov_variable(manifest, variable, "auto")
    if not resolved:
        raise AnalyticsError(f"GCOV variable {variable} is not published")
    return manifest, resolved


async def _download_harmony_output(job_id: str, label: str, variable_path: str) -> Path:
    token = os.getenv("EARTHDATA_TOKEN", "").strip()
    response, payload = await harmony_get(f"https://harmony.earthdata.nasa.gov/jobs/{job_id}", token)
    if response is None or response.status_code >= 400:
        raise AnalyticsError("Harmony job lookup failed")
    data_url = harmony_job_data_url(payload) if payload.get("status") == "successful" else None
    if not data_url or not is_allowed_earthdata_url(data_url):
        raise AnalyticsError("Harmony output is not ready")
    cache_path = gcov_cache_path(job_id)
    if cache_path.is_file() and cache_path.stat().st_size > 0:
        return cache_path
    client = httpx.AsyncClient(timeout=None, follow_redirects=True)
    partial_path = cache_path.with_name(f"{cache_path.stem}.{os.getpid()}.{uuid.uuid4().hex}.part")
    try:
        upstream = await client.get(data_url, headers={"Authorization": f"Bearer {token}", "Accept": "image/tiff,application/octet-stream"})
        if upstream.status_code >= 400:
            raise AnalyticsError(f"Harmony output download failed with {upstream.status_code}")
        with partial_path.open("wb") as target:
            target.write(upstream.content)
        os.replace(partial_path, cache_path)
        record_gcov_cache(job_id, label or gcov_label("", "", variable_path))
        return cache_path
    except (httpx.HTTPError, OSError) as error:
        partial_path.unlink(missing_ok=True)
        raise AnalyticsError(str(error)) from error
    finally:
        await client.aclose()


async def _ensure_cached_gcov_raster(scene: str, collection: str, variable: str) -> tuple[Path, dict]:
    manifest, resolved = await _resolved_gcov(scene, collection, variable)
    variable_path = resolved["path"]
    labels = [gcov_label(scene, collection, variable_path), legacy_gcov_label(scene, collection, resolved["name"])]
    for label in labels:
        cached_job_id = cached_gcov_job_for_label(label)
        if cached_job_id:
            return gcov_cache_path(cached_job_id), resolved
    started = await earthdata_gcov(scene=scene, collection=collection, variable=variable, frequency=resolved.get("frequency", "auto"))
    if isinstance(started, JSONResponse):
        raise AnalyticsError(f"GCOV extraction rejected ({started.status_code})")
    job_id = started.get("jobId") if isinstance(started, dict) else None
    if not job_id:
        raise AnalyticsError("GCOV extraction did not return a job id")
    status = started.get("status", "running")
    payload: dict = {}
    for _ in range(90):
        if status == "successful":
            break
        if status in {"failed", "canceled", "stale"}:
            raise AnalyticsError(f"GCOV extraction ended with {status}")
        await asyncio.sleep(2)
        response, payload = await harmony_get(f"https://harmony.earthdata.nasa.gov/jobs/{job_id}", os.getenv("EARTHDATA_TOKEN", "").strip())
        if response is None or response.status_code >= 400:
            raise AnalyticsError("Unable to read GCOV extraction status")
        status = payload.get("status", "unknown")
    if status != "successful":
        raise AnalyticsError("GCOV extraction timed out")
    return await _download_harmony_output(job_id, labels[0], variable_path), resolved


async def ensure_cached_gcov_raster(scene: str, collection: str, variable: str) -> tuple[Path, dict]:
    """Share one extraction/download task among concurrent callers.

    Timeline changes, the map preview and analytics can all ask for the same
    band at nearly the same time. Only the first caller is allowed to start a
    Harmony job; the others await the same task and reuse the disk cache.
    """
    key = f"{collection}:{scene}:{variable}"
    existing = GCOV_INFLIGHT.get(key)
    if existing:
        return await existing
    task = asyncio.create_task(_ensure_cached_gcov_raster(scene, collection, variable))
    GCOV_INFLIGHT[key] = task
    try:
        return await task
    finally:
        if GCOV_INFLIGHT.get(key) is task:
            GCOV_INFLIGHT.pop(key, None)


async def _cached_gcov_raster(scene: str, collection: str, variable: str) -> tuple[Path, dict] | None:
    """Return an existing raster without starting inspection or Harmony work.

    Scene metadata is allowed to answer quickly even when the expensive
    GeoTIFF extraction has not happened yet. This helper is deliberately
    cache-only and is used by the copilot truth tool.
    """
    manifest = read_cached_gcov_inspection(collection)
    if not manifest:
        return None
    resolved = resolve_gcov_variable(manifest, variable, "auto")
    if not resolved:
        return None
    labels = [
        gcov_label(scene, collection, resolved["path"]),
        legacy_gcov_label(scene, collection, resolved["name"]),
        legacy_gcov_label(scene, collection, variable),
    ]
    for label in labels:
        job_id = cached_gcov_job_for_label(label)
        if not job_id:
            continue
        path = gcov_cache_path(job_id)
        if path.is_file() and path.stat().st_size > 0:
            return path, resolved
    return None


def _scene_overlap(record: dict | None, aoi: dict) -> bool:
    if not record or not record.get("geometry"):
        return False
    try:
        return bool(shape(record["geometry"]).intersection(shape(aoi)).area > 0)
    except (TypeError, ValueError):
        return False


def _check(name: str, status: str, t1=None, t2=None, detail: str | None = None, blocking: bool = False) -> dict:
    item = {"name": name, "status": status}
    if t1 is not None:
        item["t1"] = t1
    if t2 is not None:
        item["t2"] = t2
    if detail:
        item["detail"] = detail
    if blocking:
        item["blocking"] = True
    return item


async def compatibility_report(request: ComparisonCheckRequest, require_rasters: bool = False) -> dict:
    first, second = await asyncio.gather(find_scene_record(request.scene_t1), find_scene_record(request.scene_t2))
    first_meta = _scene_metadata(first, request.scene_t1)
    second_meta = _scene_metadata(second, request.scene_t2)
    checks: list[dict] = []
    issues: list[str] = []
    if not first or not second:
        checks.append(_check("scene_exists", "FAIL", first_meta["scene"], second_meta["scene"], "Không tìm thấy một hoặc cả hai scene trong ASF Search API.", True))
        issues.append("scene_not_found")
    else:
        checks.append(_check("scene_exists", "PASS", first_meta["scene"], second_meta["scene"]))
    for name, key in (("collection_product", "collection"), ("orbit_direction", "orbitDirection"), ("track", "track"), ("frame", "frame"), ("frequency", "frequency"), ("polarization", "polarization")):
        left, right = first_meta.get(key), second_meta.get(key)
        status = "PASS" if left is not None and right is not None and str(left).upper() == str(right).upper() else "FAIL"
        if status == "FAIL":
            issues.append(name)
        checks.append(_check(name, status, left, right, "Hai scene không cùng metadata bắt buộc." if status == "FAIL" else None, status == "FAIL"))
    overlap_left = _scene_overlap(first, request.aoi)
    overlap_right = _scene_overlap(second, request.aoi)
    overlap_status = "PASS" if overlap_left and overlap_right else "FAIL"
    if overlap_status == "FAIL":
        issues.append("aoi_overlap")
    checks.append(_check("aoi_overlap", overlap_status, overlap_left, overlap_right, "AOI không giao với cả hai scene." if overlap_status == "FAIL" else None, overlap_status == "FAIL"))
    for band in request.bands:
        try:
            await asyncio.gather(_resolved_gcov(request.scene_t1, request.collection, band), _resolved_gcov(request.scene_t2, request.collection, band))
            checks.append(_check(f"band_{band}", "PASS", band, band))
        except AnalyticsError as error:
            checks.append(_check(f"band_{band}", "FAIL", detail=str(error), blocking=True))
            issues.append(f"band_{band}")
    raster_checks: list[dict] = []
    for band in request.bands:
        left_path = right_path = None
        try:
            left_manifest, left_resolved = await _resolved_gcov(request.scene_t1, request.collection, band)
            right_manifest, right_resolved = await _resolved_gcov(request.scene_t2, request.collection, band)
            for label in (gcov_label(request.scene_t1, request.collection, left_resolved["path"]), legacy_gcov_label(request.scene_t1, request.collection, band)):
                job = cached_gcov_job_for_label(label)
                if job:
                    left_path = gcov_cache_path(job)
            for label in (gcov_label(request.scene_t2, request.collection, right_resolved["path"]), legacy_gcov_label(request.scene_t2, request.collection, band)):
                job = cached_gcov_job_for_label(label)
                if job:
                    right_path = gcov_cache_path(job)
            if not left_path or not right_path:
                raster_checks.append(_check(f"raster_{band}", "PENDING", detail="GeoTIFF chưa có trong cache; sẽ được tạo khi chạy comparison."))
                if require_rasters:
                    issues.append(f"raster_{band}")
                continue
            left_meta = raster_metadata(left_path)
            right_meta = raster_metadata(right_path)
            same = left_meta == right_meta or (
                left_meta.get("crs") == right_meta.get("crs")
                and left_meta.get("width") == right_meta.get("width")
                and left_meta.get("height") == right_meta.get("height")
                and left_meta.get("resolution") == right_meta.get("resolution")
                and all(abs(a - b) < 1e-6 for a, b in zip(left_meta.get("transform", []), right_meta.get("transform", [])))
            )
            raster_checks.append(_check(f"raster_{band}", "PASS" if same else "FAIL", left_meta, right_meta, "CRS/grid/độ phân giải khác nhau." if not same else None, not same))
            if not same:
                issues.append(f"raster_{band}")
        except (AnalyticsError, OSError, ValueError) as error:
            raster_checks.append(_check(f"raster_{band}", "FAIL", detail=str(error), blocking=True))
            issues.append(f"raster_{band}")
    checks.extend(raster_checks)
    checks.append(_check("tide", "UNKNOWN", detail="No validated tide source configured"))
    return {
        "status": "COMPATIBLE" if not issues else "BLOCKED",
        "checks": checks,
        "blockingIssues": issues,
        "tide": {"status": "UNKNOWN", "reason": "No validated tide source configured"},
    }


def _comparison_hash(request: ComparisonStartRequest) -> str:
    canonical = request.model_dump_json(exclude_none=True, by_alias=True, indent=None)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def _run_comparison(comparison_id: str, request: ComparisonStartRequest) -> None:
    path = _analytics_job_path(comparison_id)
    state = _read_json(path) or {}
    state.update({"id": comparison_id, "status": "running", "updatedAt": datetime.now(timezone.utc).isoformat()})
    _write_json(path, state)
    try:
        rasters: dict[str, tuple[Path, Path]] = {}
        extracted = await asyncio.gather(*(
            ensure_cached_gcov_raster(scene, request.collection, band)
            for band in request.bands
            for scene in (request.scene_t1, request.scene_t2)
        ))
        index = 0
        for band in request.bands:
            rasters[band] = (extracted[index][0], extracted[index + 1][0])
            index += 2
        gate = await compatibility_report(request, require_rasters=True)
        state["compatibility"] = gate
        if gate["status"] != "COMPATIBLE":
            state.update({"status": "blocked", "updatedAt": datetime.now(timezone.utc).isoformat()})
            _write_json(path, state)
            return
        outputs = {}
        all_features: list[dict] = []
        for band, (left, right) in rasters.items():
            delta_path = COMPARISON_DIR / f"{comparison_id}_{band.lower()}_delta.tif"
            result = compare_rasters(left, right, threshold_db=request.threshold_db, min_pixels=request.min_component_pixels, geometry=request.aoi, output_path=delta_path)
            outputs[band] = {key: value for key, value in result.items() if key != "candidate"}
            all_features.extend([{**feature, "properties": {**feature.get("properties", {}), "band": band}} for feature in result["candidate"]["features"]])
        state.update({
            "status": "ready",
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "sceneT1": request.scene_t1,
            "sceneT2": request.scene_t2,
            "thresholdDb": request.threshold_db,
            "provenance": {"bands": request.bands, "aoi": request.aoi, "processingVersion": "gcov-analytics-1", "processingHash": _comparison_hash(request), "source": "cached-geotiff"},
            "outputs": outputs,
            "candidate": {"type": "FeatureCollection", "features": all_features, "status": "CANDIDATE", "label": "Candidate change — cần kiểm chứng"},
        })
    except (AnalyticsError, OSError, ValueError) as error:
        state.update({"status": "error", "error": str(error), "updatedAt": datetime.now(timezone.utc).isoformat()})
    _write_json(path, state)


@app.post("/api/v1/analytics/pixel")
async def analytics_pixel(request: PixelRequest):
    try:
        raster_paths = await asyncio.gather(*(ensure_cached_gcov_raster(request.scene, request.collection, band) for band in ("HHHH", "HVHV")))
        values = {}
        for band, (path, _) in zip(("HHHH", "HVHV"), raster_paths):
            sampled = sample_pixel(path, request.longitude, request.latitude)
            values[band] = {"power": sampled.get("rawValue"), "db": sampled.get("db"), "unit": "dB", "valid": sampled["valid"]}
        return {"coordinate": {"longitude": request.longitude, "latitude": request.latitude}, "scene": request.scene, "values": values, "mask": {"valid": all(item["valid"] for item in values.values()), "rawValue": None, "source": "derived-from-valid-power"}, "source": "cached-geotiff"}
    except (AnalyticsError, OSError, ValueError) as error:
        return JSONResponse({"error": "Unable to inspect raster pixel", "detail": str(error)}, status_code=502)


@app.post("/api/v1/analytics/region-stats")
async def analytics_region_stats(request: RegionStatsRequest):
    try:
        cache_key = hashlib.sha256(json.dumps(request.model_dump(mode="json"), sort_keys=True).encode("utf-8")).hexdigest()[:24]
        cached_stats = _read_json(ANALYTICS_CACHE_DIR / f"region-{cache_key}.json")
        if cached_stats:
            return cached_stats
        results = {}
        for band in request.bands:
            path, _ = await ensure_cached_gcov_raster(request.scene, request.collection, band)
            results[band] = region_statistics(path, request.geometry)
        payload = {"scene": request.scene, "statistics": results, "source": "cached-geotiff", "cacheKey": cache_key}
        _write_json(ANALYTICS_CACHE_DIR / f"region-{cache_key}.json", payload)
        return payload
    except (AnalyticsError, OSError, ValueError) as error:
        return JSONResponse({"error": "Unable to calculate region statistics", "detail": str(error)}, status_code=502)


@app.post("/api/v1/analytics/profile")
async def analytics_profile(request: ProfileRequest):
    """Return compact HHHH/HVHV profiles from cached GeoTIFFs for the chart."""
    try:
        cache_key = hashlib.sha256(json.dumps(request.model_dump(mode="json"), sort_keys=True).encode("utf-8")).hexdigest()[:24]
        cache_path = ANALYTICS_CACHE_DIR / f"profile-{cache_key}.json"
        cached_profile = _read_json(cache_path)
        if cached_profile:
            return cached_profile
        results = {}
        for band in request.bands:
            path, _ = await ensure_cached_gcov_raster(request.scene, request.collection, band)
            results[band] = raster_profile(path, request.width, request.height)
        payload = {"scene": request.scene, "series": results, "source": "cached-geotiff", "cacheKey": cache_key}
        _write_json(cache_path, payload)
        return payload
    except (AnalyticsError, OSError, ValueError) as error:
        return JSONResponse({"error": "Unable to calculate radar profile", "detail": str(error)}, status_code=502)


@app.get("/api/v1/copilot/context")
async def copilot_context(query: CopilotContextQuery):
    try:
        geometry = COPILOT_AOIS.resolve("default", query.aoiId, query.aoiHash)
        context = build_map_context(
            query.sceneId or "",
            query.sceneDate,
            query.band,
            query.aoiId,
            geometry,
            {"radar": True},
            query.timelineIndex,
            query.timelineCount,
            "earthdata",
            "cached",
            "ready",
        )
        return context.model_dump(mode="json")
    except ValueError as error:
        return JSONResponse({"error": "Invalid copilot context", "detail": str(error)}, status_code=400)


@app.post("/api/v1/analytics/scene-truth")
async def analytics_scene_truth(request: SceneTruthRequest):
    record = await find_scene_record(request.scene)
    raster_metadata_value: dict = {}
    raster_status = "unavailable"
    for band in request.requestedBands:
        try:
            path, _ = await ensure_cached_gcov_raster(request.scene, request.collection, band)
            raster_metadata_value = raster_metadata(path)
            raster_status = "cached"
            break
        except (AnalyticsError, OSError, ValueError):
            continue
    truth = build_scene_truth(record, raster_metadata_value or None, request.requestedBands)
    payload = truth.model_dump(mode="json")
    payload["rasterStatus"] = raster_status
    payload["catalogStatus"] = "found" if record else "not-found"
    return payload


@app.post("/api/v1/comparisons/check")
async def comparisons_check(request: ComparisonCheckRequest):
    try:
        return await compatibility_report(request)
    except (AnalyticsError, OSError, ValueError) as error:
        return JSONResponse({"error": "Unable to check scene compatibility", "detail": str(error)}, status_code=502)


@app.post("/api/v1/comparisons", status_code=202)
async def comparisons_start(request: ComparisonStartRequest):
    comparison_id = uuid.uuid4().hex
    state = {"id": comparison_id, "status": "queued", "createdAt": datetime.now(timezone.utc).isoformat(), "request": request.model_dump(mode="json")}
    _write_json(_analytics_job_path(comparison_id), state)
    task = asyncio.create_task(_run_comparison(comparison_id, request))
    COMPARISON_TASKS[comparison_id] = task
    task.add_done_callback(lambda _: COMPARISON_TASKS.pop(comparison_id, None))
    return {"id": comparison_id, "status": "queued"}


@app.get("/api/v1/comparisons/{comparison_id}")
async def comparisons_status(comparison_id: str):
    try:
        state = _read_json(_analytics_job_path(comparison_id))
    except ValueError:
        state = None
    if not state:
        return JSONResponse({"error": "Comparison not found"}, status_code=404)
    return state


@app.get("/api/v1/comparisons/{comparison_id}/asset/{asset_name}")
async def comparisons_asset(comparison_id: str, asset_name: str):
    state = _read_json(_analytics_job_path(comparison_id))
    if not state or state.get("status") != "ready":
        return JSONResponse({"error": "Comparison output is not ready"}, status_code=409)
    match = re.fullmatch(r"(hhhh|hvhv)_delta", asset_name.lower())
    if not match:
        return JSONResponse({"error": "Unknown comparison asset"}, status_code=404)
    output = (state.get("outputs") or {}).get(match.group(1).upper(), {})
    target = Path(output.get("deltaPath", ""))
    if not target.is_file() or target.parent.resolve() != COMPARISON_DIR.resolve():
        return JSONResponse({"error": "Comparison asset is missing"}, status_code=404)
    return FileResponse(target, media_type="image/tiff", headers={"Cache-Control": "public, max-age=86400", "X-TideAware-Data-Source": "analytics-cache"})


# ---------------------------------------------------------------------------
# Copilot live-tool wiring
# ---------------------------------------------------------------------------
# The LLM is not allowed to read Earthdata directly. These handlers are the
# single bridge from the assistant to the same catalog/cache/analytics code
# used by the map and analytics endpoints.


async def _copilot_scene_metadata(arguments: dict, context: ToolContext) -> dict:
    map_context = context.map_context
    scene = str(arguments.get("sceneId") or map_context.sceneId or "").strip()
    if not scene:
        return {"_status": "UNKNOWN", "reason": "Chưa có scene được chọn trong map context."}

    # mapContext describes what the user is looking at. It is intentionally
    # kept in the response, but it is not authoritative for ASF/cache facts.
    map_payload = map_context.model_dump(mode="json")
    record = None
    catalog_status = map_context.catalogMode.value
    try:
        if map_context.catalogMode.value == "earthdata":
            record = await find_scene_record(scene)
            catalog_status = "found" if record else "not-found"
    except (AnalyticsError, OSError, RuntimeError, ValueError) as error:
        catalog_status = "unavailable"
        map_payload["catalogWarning"] = str(error)

    metadata = _scene_metadata(record, scene) if record else {}
    collection = str(map_context.collectionId or metadata.get("collection") or "C3622241360-ASF")
    requested_bands = [map_context.band] if map_context.band in {"HHHH", "HVHV"} else ["HHHH", "HVHV"]
    cached_bands: list[str] = []
    raster_metadata_value: dict = {}
    for band in requested_bands:
        try:
            cached = await _cached_gcov_raster(scene, collection, band)
            if cached:
                cached_bands.append(band)
                if not raster_metadata_value:
                    raster_metadata_value = raster_metadata(cached[0])
        except (AnalyticsError, OSError, RuntimeError, ValueError):
            continue

    truth = build_scene_truth(record, raster_metadata_value or None, requested_bands)
    truth_payload = truth.model_dump(mode="json")
    truth_payload["collection"] = collection
    truth_payload["catalogStatus"] = catalog_status
    truth_payload["cachedBands"] = cached_bands
    truth_payload["rasterStatus"] = "cached" if cached_bands else "unavailable"
    truth_payload["dataStatus"] = "ready" if len(cached_bands) == len(requested_bands) else ("partial" if record else "unknown")
    truth_payload["assetMode"] = "cached" if cached_bands else "unavailable"
    browse_available = bool(metadata.get("browseAvailable"))
    truth_payload["dataAvailability"] = {
        "catalog": "available" if record else "unavailable",
        "browse": "available" if browse_available else "unavailable",
        "rasterMeasurement": "available" if cached_bands else "unavailable",
        "canView": browse_available or bool(cached_bands),
        "canMeasure": bool(cached_bands),
        "nextStep": "Có thể xem ảnh browse; cần GeoTIFF cache để đo HHHH/HVHV." if browse_available and not cached_bands else ("Có thể xem và đo các band đã cache." if cached_bands else "Chưa có asset hiển thị hoặc đo được."),
    }
    truth_payload["provenance"] = {
        "source": "ASF catalog + local GeoTIFF cache",
        "sceneId": scene,
        "collection": collection,
        "authoritativeFor": ["catalogMetadata", "rasterAvailability", "rasterMetadata"],
    }
    return {
        "mapContext": map_payload,
        "sceneTruth": truth_payload,
        "hasScene": bool(record) or map_context.catalogMode.value != "earthdata",
        "hasRasterData": bool(cached_bands),
        "timeline": {"index": map_context.timelineIndex, "count": map_context.timelineCount},
        "_status": "KNOWN" if record or map_context.catalogMode.value != "earthdata" else "UNKNOWN",
        "_provenance": [{
            "source": "ASF catalog + local GeoTIFF cache",
            "tool": "get_scene_metadata",
            "sceneId": scene,
            "collection": collection,
            "cachedBands": cached_bands,
            "mapContextVersion": map_context.contextVersion,
        }],
    }


async def _copilot_search_scenes(arguments: dict, context: ToolContext) -> dict:
    query = str(arguments.get("query") or "").strip().lower()
    result = await earthdata_scene_catalog_result()
    if result.status != "ok":
        return {
            "_status": "UNKNOWN",
            "catalogStatus": result.status,
            "reason": result.detail or result.errorCode or "ASF catalog không khả dụng.",
        }
    records = []
    for record in result.records:
        name = _scene_name(record)
        if query and query not in name.lower():
            continue
        records.append(_scene_metadata(record, name))
    return {"catalogStatus": "ok", "query": query, "count": len(records), "scenes": records[:20]}


async def _copilot_profile(arguments: dict, context: ToolContext) -> dict:
    scene = str(context.map_context.sceneId or "").strip()
    band = str(arguments.get("band") or context.map_context.band).upper()
    if band not in {"HHHH", "HVHV"} or not scene:
        return {"_status": "UNKNOWN", "reason": "Cần scene và band HHHH hoặc HVHV."}
    try:
        cached = await _cached_gcov_raster(scene, context.map_context.collectionId or "C3622241360-ASF", band)
        if not cached:
            return {"_status": "UNKNOWN", "reason": "GeoTIFF chưa có trong cache; hãy chuẩn bị lớp radar trước.", "scene": scene, "band": band}
        path, resolved = cached
        return {
            "scene": scene,
            "band": band,
            "profile": raster_profile(path, 96, 64),
            "source": "cached-geotiff",
            "variablePath": resolved.get("path"),
            "_provenance": [{"source": "local GeoTIFF cache", "sceneId": scene, "band": band, "variablePath": resolved.get("path"), "assetMode": "cached"}],
        }
    except (AnalyticsError, OSError, RuntimeError, ValueError) as error:
        return {"_status": "UNKNOWN", "reason": str(error), "scene": scene, "band": band}


async def _copilot_region_stats(arguments: dict, context: ToolContext) -> dict:
    scene = str(context.map_context.sceneId or "").strip()
    if not scene:
        return {"_status": "UNKNOWN", "reason": "Chưa có scene được chọn trong map context."}
    try:
        geometry = COPILOT_AOIS.resolve(context.session_id, context.map_context.aoiId, context.map_context.aoiHash)
        requested = str(arguments.get("band") or "").upper()
        bands = [requested] if requested in {"HHHH", "HVHV"} else ["HHHH", "HVHV"]
        results = {}
        for band in bands:
            cached = await _cached_gcov_raster(scene, context.map_context.collectionId or "C3622241360-ASF", band)
            if not cached:
                return {"_status": "UNKNOWN", "reason": f"GeoTIFF {band} chưa có trong cache; hãy chuẩn bị lớp radar trước.", "scene": scene, "band": band}
            path, _ = cached
            results[band] = region_statistics(path, geometry)
        return {
            "scene": scene,
            "aoiId": context.map_context.aoiId,
            "statistics": results,
            "source": "cached-geotiff",
            "_provenance": [{"source": "local GeoTIFF cache", "sceneId": scene, "bands": bands, "aoiId": context.map_context.aoiId, "assetMode": "cached"}],
        }
    except (AnalyticsError, OSError, RuntimeError, ValueError) as error:
        return {"_status": "UNKNOWN", "reason": str(error), "scene": scene}


async def _copilot_pixel(arguments: dict, context: ToolContext) -> dict:
    scene = str(context.map_context.sceneId or "").strip()
    try:
        longitude = float(arguments["longitude"])
        latitude = float(arguments["latitude"])
    except (KeyError, TypeError, ValueError):
        return {"_status": "UNKNOWN", "reason": "Cần longitude và latitude hợp lệ."}
    if not scene:
        return {"_status": "UNKNOWN", "reason": "Chưa có scene được chọn trong map context."}
    try:
        values = {}
        for band in ("HHHH", "HVHV"):
            cached = await _cached_gcov_raster(scene, context.map_context.collectionId or "C3622241360-ASF", band)
            if not cached:
                return {"_status": "UNKNOWN", "reason": f"GeoTIFF {band} chưa có trong cache; hãy chuẩn bị lớp radar trước.", "scene": scene, "band": band}
            path, _ = cached
            sampled = sample_pixel(path, longitude, latitude)
            values[band] = {"power": sampled.get("rawValue"), "db": sampled.get("db"), "unit": "dB", "valid": sampled["valid"]}
        return {
            "coordinate": {"longitude": longitude, "latitude": latitude},
            "scene": scene,
            "values": values,
            "mask": {"valid": all(item["valid"] for item in values.values())},
            "source": "cached-geotiff",
            "_provenance": [{"source": "local GeoTIFF cache", "sceneId": scene, "bands": ["HHHH", "HVHV"], "coordinate": {"longitude": longitude, "latitude": latitude}, "assetMode": "cached"}],
        }
    except (AnalyticsError, OSError, RuntimeError, ValueError) as error:
        return {"_status": "UNKNOWN", "reason": str(error), "scene": scene}


COPILOT_SERVICE.tools.register("get_scene_metadata", _copilot_scene_metadata)
COPILOT_SERVICE.tools.register("search_scenes", _copilot_search_scenes)
COPILOT_SERVICE.tools.register("get_radar_profile", _copilot_profile)
COPILOT_SERVICE.tools.register("get_region_stats", _copilot_region_stats)
COPILOT_SERVICE.tools.register("get_pixel_values", _copilot_pixel)
