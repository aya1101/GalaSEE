"""Small, reproducible analytics primitives for cached Harmony GeoTIFFs."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from pyproj import Geod
from rasterio.features import geometry_mask, shapes
from rasterio.mask import mask as raster_mask
from rasterio.enums import Resampling
from rasterio.warp import transform, transform_geom
from shapely.geometry import shape


class AnalyticsError(RuntimeError):
    pass


GEOD = Geod(ellps="WGS84")


def power_to_db(power: np.ndarray) -> np.ndarray:
    values = np.asarray(power, dtype="float32")
    result = np.full(values.shape, np.nan, dtype="float32")
    valid = np.isfinite(values) & (values > 0)
    result[valid] = 10.0 * np.log10(values[valid])
    return result


def raster_metadata(path: Path) -> dict[str, Any]:
    with rasterio.open(path) as source:
        return {
            "crs": source.crs.to_string() if source.crs else None,
            "width": source.width,
            "height": source.height,
            "count": source.count,
            "dtype": source.dtypes[0],
            "nodata": source.nodata,
            "resolution": [float(source.res[0]), float(source.res[1])],
            "transform": [float(value) for value in source.transform.to_gdal()],
            "bounds": [float(value) for value in source.bounds],
        }


def _valid_values(array: np.ndarray, nodata: float | None = None) -> np.ndarray:
    masked = np.ma.asarray(array, dtype="float32")
    values = masked.compressed() if np.ma.isMaskedArray(masked) else np.asarray(masked, dtype="float32")
    valid = np.isfinite(values) & (values > 0)
    if nodata is not None and np.isfinite(nodata):
        valid &= values != nodata
    return values[valid]


def _stats(values: np.ndarray, histogram_bins: int = 12) -> dict[str, Any]:
    if values.size == 0:
        return {
            "validPixelCount": 0,
            "minDb": None,
            "maxDb": None,
            "meanDb": None,
            "medianDb": None,
            "p10Db": None,
            "p90Db": None,
            "histogram": {"edgesDb": [], "counts": []},
        }
    db = power_to_db(values)
    db = db[np.isfinite(db)]
    low = float(np.percentile(db, 2))
    high = float(np.percentile(db, 98))
    if math.isclose(low, high):
        edges = np.array([low - 0.5, high + 0.5], dtype="float32")
    else:
        edges = np.linspace(low, high, histogram_bins + 1, dtype="float32")
    counts, edges = np.histogram(db, bins=edges)
    return {
        "validPixelCount": int(db.size),
        "minDb": float(np.min(db)),
        "maxDb": float(np.max(db)),
        "meanDb": float(np.mean(db)),
        "medianDb": float(np.median(db)),
        "p10Db": float(np.percentile(db, 10)),
        "p90Db": float(np.percentile(db, 90)),
        "histogram": {"edgesDb": [float(value) for value in edges], "counts": [int(value) for value in counts]},
    }


def _db_stats(db: np.ndarray, histogram_bins: int = 12) -> dict[str, Any]:
    values = np.asarray(db, dtype="float32")
    values = values[np.isfinite(values)]
    if values.size == 0:
        return _stats(np.array([], dtype="float32"), histogram_bins)
    low = float(np.percentile(values, 2))
    high = float(np.percentile(values, 98))
    edges = np.array([low - 0.5, high + 0.5], dtype="float32") if math.isclose(low, high) else np.linspace(low, high, histogram_bins + 1, dtype="float32")
    counts, edges = np.histogram(values, bins=edges)
    return {
        "validPixelCount": int(values.size),
        "minDb": float(np.min(values)),
        "maxDb": float(np.max(values)),
        "meanDb": float(np.mean(values)),
        "medianDb": float(np.median(values)),
        "p10Db": float(np.percentile(values, 10)),
        "p90Db": float(np.percentile(values, 90)),
        "histogram": {"edgesDb": [float(value) for value in edges], "counts": [int(value) for value in counts]},
    }


def region_values(path: Path, geometry: dict[str, Any] | None = None) -> tuple[np.ndarray, Any, dict[str, Any]]:
    with rasterio.open(path) as source:
        if geometry is None:
            values = source.read(1)
            return values, source.transform, raster_metadata(path)
        if not source.crs:
            raise AnalyticsError("Raster has no CRS")
        projected = transform_geom("EPSG:4326", source.crs, geometry, precision=6)
        values, out_transform = raster_mask(source, [projected], crop=True, filled=False)
        return values[0], out_transform, raster_metadata(path)


def region_statistics(path: Path, geometry: dict[str, Any] | None = None) -> dict[str, Any]:
    values, transform_value, metadata = region_values(path, geometry)
    raw = _valid_values(values, metadata.get("nodata"))
    stats = _stats(raw)
    total = int(np.ma.count(values)) if np.ma.isMaskedArray(values) else int(np.asarray(values).size)
    stats.update({
        "totalPixelCount": total,
        "validCoveragePercent": float(stats["validPixelCount"] / total * 100) if total else 0.0,
        "pixelAreaM2": _pixel_area_m2(transform_value, metadata.get("crs")),
        "validAreaHa": float(stats["validPixelCount"] * _pixel_area_m2(transform_value, metadata.get("crs")) / 10000) if total else 0.0,
        "unit": "dB",
        "source": "cached-geotiff",
        "raster": metadata,
    })
    return stats


def raster_profile(path: Path, width: int = 96, height: int = 64) -> dict[str, Any]:
    """Return a compact across-image backscatter profile for the sidebar chart.

    The profile is computed from the cached GeoTIFF on the backend. Values are
    averaged in dB per downsampled image column, so the browser never has to
    download or decode the full GeoTIFF just to draw the chart.
    """
    width = max(8, min(int(width), 256))
    height = max(8, min(int(height), 256))
    with rasterio.open(path) as source:
        sampled = source.read(
            1,
            out_shape=(height, width),
            masked=True,
            resampling=Resampling.average,
        )
        raw = np.ma.asarray(sampled, dtype="float32")
        invalid = np.ma.getmaskarray(raw) | ~np.isfinite(np.ma.getdata(raw)) | (np.ma.getdata(raw) <= 0)
        db = power_to_db(np.ma.getdata(raw))
        db = np.ma.array(db, mask=invalid | ~np.isfinite(db))
        column_values: list[float] = []
        for column in range(width):
            values = db[:, column].compressed()
            if values.size:
                column_values.append(float(np.mean(values)))
        stats = _db_stats(np.asarray(column_values, dtype="float32"))
        stats.update({
            "values": column_values,
            "columns": len(column_values),
            "sampleWidth": width,
            "sampleHeight": height,
            "unit": "dB",
            "source": "cached-geotiff",
        })
        return stats


def sample_pixel(path: Path, longitude: float, latitude: float) -> dict[str, Any]:
    with rasterio.open(path) as source:
        if not source.crs:
            raise AnalyticsError("Raster has no CRS")
        x_values, y_values = transform("EPSG:4326", source.crs, [longitude], [latitude])
        row, column = source.index(x_values[0], y_values[0])
        if row < 0 or column < 0 or row >= source.height or column >= source.width:
            return {"valid": False, "reason": "outside-raster", "row": row, "column": column}
        value = float(source.read(1, window=((row, row + 1), (column, column + 1)))[0, 0])
        valid = np.isfinite(value) and value > 0 and (source.nodata is None or value != source.nodata)
        return {
            "valid": bool(valid),
            "rawValue": value if valid else None,
            "db": float(10 * math.log10(value)) if valid else None,
            "row": row,
            "column": column,
        }


def _same_grid(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left.get("crs") == right.get("crs")
        and left.get("width") == right.get("width")
        and left.get("height") == right.get("height")
        and np.allclose(left.get("resolution", []), right.get("resolution", []), rtol=0, atol=1e-6)
        and np.allclose(left.get("transform", []), right.get("transform", []), rtol=0, atol=1e-6)
    )


def _geodesic_area(geometry: dict[str, Any]) -> float:
    polygon = shape(geometry)
    if polygon.is_empty:
        return 0.0
    area, _ = GEOD.geometry_area_perimeter(polygon)
    return abs(float(area))


def _pixel_area_m2(transform_value: Any, crs: str | None) -> float:
    """Estimate one pixel's area in square metres for geographic or projected grids."""
    if crs and crs.upper() in {"EPSG:4326", "CRS84"}:
        lon, lat = transform_value @ (0.5, 0.5)
        corners = [
            (lon - abs(transform_value.a) / 2, lat - abs(transform_value.e) / 2),
            (lon + abs(transform_value.a) / 2, lat - abs(transform_value.e) / 2),
            (lon + abs(transform_value.a) / 2, lat + abs(transform_value.e) / 2),
            (lon - abs(transform_value.a) / 2, lat + abs(transform_value.e) / 2),
        ]
        area, _ = GEOD.polygon_area_perimeter(*zip(*corners))
        return max(abs(float(area)), 1e-9)
    return max(abs(float(transform_value.a * transform_value.e)), 1e-9)


def candidate_polygons(mask: np.ndarray, transform_value: Any, crs: str | None, min_pixels: int = 9) -> tuple[list[dict[str, Any]], float]:
    if crs is None:
        raise AnalyticsError("Candidate raster has no CRS")
    output: list[dict[str, Any]] = []
    total_area = 0.0
    pixel_area_m2 = _pixel_area_m2(transform_value, crs)
    for geometry, value in shapes(mask.astype("uint8"), mask=mask, transform=transform_value):
        if int(value) != 1:
            continue
        area_m2 = _geodesic_area(geometry) if crs.upper() in {"EPSG:4326", "CRS84"} else abs(float(shape(geometry).area))
        pixel_count = max(1, int(round(area_m2 / pixel_area_m2)))
        if pixel_count < min_pixels:
            continue
        total_area += area_m2
        output.append({"type": "Feature", "properties": {"areaHa": area_m2 / 10000, "pixelCount": pixel_count, "status": "CANDIDATE"}, "geometry": geometry})
    return output, total_area


def compare_rasters(
    left_path: Path,
    right_path: Path,
    threshold_db: float = 3.0,
    min_pixels: int = 9,
    geometry: dict[str, Any] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    left_meta = raster_metadata(left_path)
    right_meta = raster_metadata(right_path)
    if not _same_grid(left_meta, right_meta):
        raise AnalyticsError("Raster grids are not compatible")
    with rasterio.open(left_path) as left, rasterio.open(right_path) as right:
        left_values = left.read(1)
        right_values = right.read(1)
        left_valid = np.isfinite(left_values) & (left_values > 0)
        right_valid = np.isfinite(right_values) & (right_values > 0)
        if left.nodata is not None:
            left_valid &= left_values != left.nodata
        if right.nodata is not None:
            right_valid &= right_values != right.nodata
        analysis_mask = np.ones(left_values.shape, dtype=bool)
        if geometry is not None:
            if not left.crs:
                raise AnalyticsError("Raster has no CRS")
            projected = transform_geom("EPSG:4326", left.crs, geometry, precision=6)
            analysis_mask = geometry_mask([projected], out_shape=left_values.shape, transform=left.transform, invert=True)
        valid = left_valid & right_valid & analysis_mask
        left_db = power_to_db(left_values)
        right_db = power_to_db(right_values)
        delta = right_db - left_db
        candidate = valid & np.isfinite(delta) & (np.abs(delta) >= threshold_db)
        features, area_m2 = candidate_polygons(candidate, left.transform, left_meta.get("crs"), min_pixels=min_pixels)
        profile = left.profile.copy()
        profile.update(dtype="float32", count=1, compress="deflate", nodata=np.nan)
    delta_path = output_path or left_path.with_name(f"{left_path.stem}__delta__{right_path.stem}.tif")
    with rasterio.open(delta_path, "w", **profile) as output:
        output.write(np.where(valid, delta, np.nan).astype("float32"), 1)
    return {
        "deltaPath": str(delta_path),
        "candidate": {"type": "FeatureCollection", "features": features},
        "candidateAreaHa": area_m2 / 10000,
        "validCoveragePercent": float(np.count_nonzero(valid) / np.count_nonzero(analysis_mask) * 100) if np.count_nonzero(analysis_mask) else 0.0,
        "statistics": _db_stats(delta[valid]),
        "thresholdDb": threshold_db,
        "minComponentPixels": min_pixels,
        "source": "cached-geotiff",
    }
