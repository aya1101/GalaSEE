import hashlib
import json
from typing import Any

from shapely.geometry import shape


def canonical_geojson(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def aoi_hash(value: dict[str, Any]) -> str:
    digest = hashlib.sha256(canonical_geojson(value).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


class AoiRegistry:
    def __init__(self) -> None:
        self._values: dict[tuple[str, str], dict[str, Any]] = {}

    def register(self, session_id: str, geometry: dict[str, Any], aoi_id: str = "aoi-study") -> tuple[str, str]:
        candidate = shape(geometry)
        if candidate.geom_type != "Polygon" or not candidate.is_valid or candidate.is_empty:
            raise ValueError("AOI must be a valid non-empty Polygon")
        digest = aoi_hash(geometry)
        self._values[(session_id, aoi_id)] = geometry
        return aoi_id, digest

    def resolve(self, session_id: str, aoi_id: str, expected_hash: str) -> dict[str, Any]:
        geometry = self._values.get((session_id, aoi_id))
        if geometry is None:
            raise ValueError("AOI is not registered for this session")
        if aoi_hash(geometry) != expected_hash:
            raise ValueError("AOI hash does not match the registered geometry")
        return geometry
