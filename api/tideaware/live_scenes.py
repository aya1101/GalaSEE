from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .contracts import SceneRole


class SceneCompatibilityError(ValueError):
    """Raised when a live scene sequence cannot be analysed together."""


def _properties(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("properties")
    return value if isinstance(value, dict) else record


def _first(properties: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = properties.get(name)
        if value not in (None, ""):
            return value
    return None


def _code(value: Any, width: int) -> str | None:
    if value in (None, ""):
        return None
    text = str(value)
    return text.zfill(width) if text.isdigit() else text


def _parse_time(value: Any) -> datetime:
    if not value:
        raise SceneCompatibilityError("Scene is missing acquisition time")
    if isinstance(value, datetime):
        result = value
    else:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def normalize_scene_record(record: dict[str, Any]) -> dict[str, Any]:
    properties = _properties(record)
    scene_id = str(_first(properties, "fileName", "fileID", "granuleName") or record.get("id") or "").removesuffix(".h5")
    track = _code(_first(properties, "pathNumber", "track", "path"), 3)
    frame = _code(_first(properties, "frameNumber", "frame"), 3)
    direction = _first(properties, "flightDirection", "orbitDirection")
    collection = _first(properties, "conceptID", "collectionId", "collection")
    if not scene_id or not track:
        raise SceneCompatibilityError("Scene is missing a stable ID or track")
    return {
        "scene_id": scene_id,
        "file_name": scene_id,
        "track": track,
        "frame": frame,
        "orbit_direction": str(direction) if direction else None,
        "collection": str(collection) if collection else None,
        "acquisition_time": _parse_time(_first(properties, "startTime", "acquisitionTime", "datetime")),
        "geometry": record.get("geometry"),
    }


def validate_scene_group(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        raise SceneCompatibilityError("Scene group is empty")
    normalized = [normalize_scene_record(record) for record in records]
    ids = [item["scene_id"] for item in normalized]
    if len(set(ids)) != len(ids):
        raise SceneCompatibilityError("Scene group contains duplicate scenes")
    for field in ("track", "frame", "orbit_direction", "collection"):
        values = {item[field] for item in normalized}
        if len(values) > 1:
            raise SceneCompatibilityError(f"Scene group has mixed {field}")
    return {
        "track": normalized[0]["track"],
        "frame": normalized[0]["frame"],
        "orbit_direction": normalized[0]["orbit_direction"],
        "collection": normalized[0]["collection"],
        "scene_ids": ids,
        "count": len(normalized),
    }


def filter_scene_records(records: list[dict[str, Any]], collection: str | None) -> list[dict[str, Any]]:
    """Keep one product family before enforcing scene-group compatibility."""
    if not collection:
        return records
    wanted = str(collection).strip().upper()
    filtered: list[dict[str, Any]] = []
    for record in records:
        try:
            normalized = normalize_scene_record(record)
        except SceneCompatibilityError:
            continue
        if str(normalized.get("collection") or "").strip().upper() == wanted:
            filtered.append(record)
    return filtered


def select_scene_roles(
    records: list[dict[str, Any]],
    *,
    track: str,
    frame: str | None = None,
    reference_count: int = 4,
    monitoring_count: int = 2,
) -> list[SceneRole]:
    if reference_count < 3 or monitoring_count < 1:
        raise SceneCompatibilityError("Reference/Monitoring counts are too small")
    wanted_track = _code(track, 3)
    wanted_frame = _code(frame, 3) if frame else None
    normalized = [normalize_scene_record(record) for record in records]
    candidates = [
        item for item in normalized
        if item["track"] == wanted_track and (wanted_frame is None or item["frame"] == wanted_frame)
    ]
    if len(candidates) < reference_count + monitoring_count:
        raise SceneCompatibilityError(
            f"Need at least {reference_count + monitoring_count} scenes for track {wanted_track}, found {len(candidates)}"
        )
    selected = sorted(candidates, key=lambda item: item["acquisition_time"])[-(reference_count + monitoring_count):]
    validate_scene_group([
        {
            "id": item["scene_id"],
            "properties": {
                "fileName": item["file_name"],
                "pathNumber": item["track"],
                "frameNumber": item["frame"],
                "flightDirection": item["orbit_direction"],
                "conceptID": item["collection"],
                "startTime": item["acquisition_time"].isoformat(),
            },
        }
        for item in selected
    ])
    roles: list[SceneRole] = []
    for index, item in enumerate(selected):
        role = f"Reference_{index + 1}" if index < reference_count else f"Monitoring_{index - reference_count + 1}"
        roles.append(SceneRole(
            scene_id=item["scene_id"],
            file_name=item["file_name"],
            track=item["track"],
            frame=item["frame"],
            orbit_direction=item["orbit_direction"],
            acquisition_time=item["acquisition_time"],
            role=role,
        ))
    return roles

