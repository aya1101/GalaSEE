import hashlib
import json
from typing import Any, Literal

from .aoi_registry import aoi_hash
from .copilot_models import AssetMode, CatalogMode, DataStatus, MapContext, SceneTruth


def _context_hash(payload: dict[str, Any]) -> int:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return int(hashlib.sha256(encoded).hexdigest()[:12], 16)


def build_map_context(
    scene_id: str,
    scene_date: str | None,
    band: Literal["HHHH", "HVHV", "COMPOSITE"],
    aoi_id: str,
    aoi: dict[str, Any],
    layer_state: dict[str, bool],
    timeline_index: int,
    timeline_count: int,
    catalog_mode: CatalogMode | str,
    asset_mode: AssetMode | str,
    data_status: DataStatus | str,
    collection_id: str | None = None,
) -> MapContext:
    geometry_hash = aoi_hash(aoi)
    stable = {
        "sceneId": scene_id,
        "sceneDate": scene_date,
        "band": band,
        "collectionId": collection_id,
        "aoiId": aoi_id,
        "aoiHash": geometry_hash,
        "layerState": dict(sorted(layer_state.items())),
        "timelineIndex": timeline_index,
        "timelineCount": timeline_count,
        "catalogMode": str(catalog_mode.value if hasattr(catalog_mode, "value") else catalog_mode),
        "assetMode": str(asset_mode.value if hasattr(asset_mode, "value") else asset_mode),
        "dataStatus": str(data_status.value if hasattr(data_status, "value") else data_status),
    }
    return MapContext(
        sceneId=scene_id,
        sceneDate=scene_date,
        band=band,
        collectionId=collection_id,
        aoiId=aoi_id,
        aoiHash=geometry_hash,
        layerState=layer_state,
        timelineIndex=timeline_index,
        timelineCount=timeline_count,
        catalogMode=catalog_mode,
        assetMode=asset_mode,
        dataStatus=data_status,
        contextVersion=_context_hash(stable),
    )


def build_scene_truth(record: dict[str, Any] | None, raster: dict[str, Any] | None, bands: list[str]) -> SceneTruth:
    properties = record.get("properties") if isinstance(record and record.get("properties"), dict) else (record or {})
    scene_id = str(properties.get("fileName") or properties.get("fileID") or properties.get("granuleName") or (record or {}).get("id") or "unknown")
    raster_metadata = raster or {}
    has_raster = bool(raster)
    return SceneTruth(
        sceneId=scene_id,
        acquisitionTime=properties.get("startTime") or properties.get("beginningDateTime"),
        collection=properties.get("conceptID") or properties.get("collectionId"),
        product=properties.get("processingLevel") or properties.get("scienceProduct") or "NISAR GCOV",
        orbitDirection=properties.get("flightDirection") or properties.get("orbitDirection"),
        track=properties.get("pathNumber") or properties.get("track") or properties.get("path"),
        frame=properties.get("frameNumber") or properties.get("frame"),
        geometry=record.get("geometry") if isinstance(record, dict) else None,
        bands=bands,
        frequency=properties.get("frequency") or properties.get("frequencyA") or properties.get("frequencyB"),
        polarization=properties.get("polarization") or properties.get("polarizations"),
        catalogMode=CatalogMode.earthdata if record else CatalogMode.error,
        assetMode=AssetMode.cached if has_raster else AssetMode.unavailable,
        dataStatus=DataStatus.ready if has_raster else DataStatus.partial,
        raster=raster_metadata,
        provenance={"source": "ASF catalog + cached GeoTIFF" if has_raster else "ASF catalog"},
    )
