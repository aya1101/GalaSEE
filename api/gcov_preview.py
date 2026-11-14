from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from PIL import Image


def _colourize(normalized: np.ndarray, mode: str) -> np.ndarray:
    if mode == "heatmap":
        red = np.clip(normalized * 1.45, 0, 1)
        green = np.clip(1 - np.abs(normalized - 0.55) * 1.8, 0, 1)
        blue = np.clip(1 - normalized * 1.25, 0, 1)
        return np.stack([red, green * 0.86, blue], axis=-1)
    return np.repeat(normalized[..., None], 3, axis=-1)


def render_preview_png(
    raster_path: Path,
    output_path: Path,
    *,
    mode: str = "grayscale",
    low_percentile: float = 2.0,
    high_percentile: float = 98.0,
    max_dimension: int = 1600,
) -> dict:
    """Render a small cached PNG from a georeferenced GCOV GeoTIFF.

    The source raster is read server-side at a reduced resolution. This keeps
    the browser from downloading and decoding the full GeoTIFF just to paint a
    map preview. Invalid and nodata pixels remain transparent.
    """
    if mode not in {"grayscale", "heatmap"}:
        raise ValueError("Unsupported preview mode")
    with rasterio.open(raster_path) as source:
        scale = min(1.0, max_dimension / max(source.width, source.height))
        width = max(1, round(source.width * scale))
        height = max(1, round(source.height * scale))
        values = source.read(1, out_shape=(height, width), masked=True).astype("float32")
        valid = (~np.ma.getmaskarray(values)) & np.isfinite(values.filled(np.nan)) & (values.filled(0) > 0)
        raw = values.filled(np.nan)
        db = np.where(valid, 10.0 * np.log10(np.maximum(raw, np.finfo("float32").tiny)), np.nan)
        valid_values = db[valid]
        if valid_values.size == 0:
            raise ValueError("Raster has no valid positive pixels")
        low = float(np.percentile(valid_values, low_percentile))
        high = float(np.percentile(valid_values, high_percentile))
        if not np.isfinite(high) or high <= low:
            high = low + 1.0
        normalized = np.clip((np.nan_to_num(db, nan=low) - low) / (high - low), 0, 1)
        rgb = (_colourize(normalized, mode) * 255).round().astype("uint8")
        alpha = np.where(valid, 225, 0).astype("uint8")
        rgba = np.concatenate([rgb, alpha[..., None]], axis=-1)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgba, mode="RGBA").save(output_path, format="PNG", optimize=True)
        bounds = source.bounds
        return {
            "width": width,
            "height": height,
            "coordinates": [[bounds.left, bounds.top], [bounds.right, bounds.top], [bounds.right, bounds.bottom], [bounds.left, bounds.bottom]],
            "stretch": {"lowDb": low, "highDb": high, "lowPercentile": low_percentile, "highPercentile": high_percentile},
            "sourceCrs": str(source.crs) if source.crs else None,
        }
