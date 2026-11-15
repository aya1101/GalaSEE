from __future__ import annotations

from typing import Any

import numpy as np
from pyproj import Geod
from rasterio.features import shapes
from rasterio.transform import Affine
from scipy.ndimage import label
from shapely.geometry import shape


GEOD = Geod(ellps="WGS84")


def _area_m2(geometry: dict[str, Any], transform: Affine, crs: str) -> float:
    if crs.upper() in {"EPSG:4326", "CRS84"}:
        area, _ = GEOD.geometry_area_perimeter(shape(geometry))
        return abs(float(area))
    return abs(float(shape(geometry).area))


def candidate_feature_collection(
    mask: np.ndarray,
    transform: Affine,
    crs: str,
    *,
    min_pixels: int = 3,
) -> dict[str, Any]:
    candidate = np.asarray(mask, dtype=bool)
    if candidate.ndim != 2:
        raise ValueError("candidate mask must be 2D")
    structure = np.ones((3, 3), dtype=np.int8)
    component_labels, count = label(candidate, structure=structure)
    sizes = np.bincount(component_labels.ravel())
    keep = np.zeros(candidate.shape, dtype=bool)
    for component_id in range(1, count + 1):
        if int(sizes[component_id]) >= min_pixels:
            keep[component_labels == component_id] = True
    pixel_area_m2 = abs(float(transform.a * transform.e)) if crs.upper() not in {"EPSG:4326", "CRS84"} else 0.0
    features: list[dict[str, Any]] = []
    total_area_m2 = 0.0
    for geometry, value in shapes(keep.astype("uint8"), mask=keep, transform=transform):
        if int(value) != 1:
            continue
        area_m2 = _area_m2(geometry, transform, crs)
        pixel_count = max(1, int(round(area_m2 / pixel_area_m2))) if pixel_area_m2 else int(round(area_m2 / 10000))
        total_area_m2 += area_m2
        features.append({
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "areaHa": area_m2 / 10000.0,
                "pixelCount": pixel_count,
                "status": "CANDIDATE",
            },
        })
    return {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "candidateAreaHa": total_area_m2 / 10000.0,
            "minPixels": min_pixels,
            "crs": crs,
        },
    }

