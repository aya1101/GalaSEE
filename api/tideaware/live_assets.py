from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import rasterio


class AssetCompatibilityError(ValueError):
    pass


@dataclass(frozen=True)
class SceneAsset:
    scene_id: str
    band: str
    path: Path
    unit: str


def ensure_live_scene_assets(
    scene_ids: list[str],
    bands: list[str],
    resolver: Callable[[str, str], tuple[Path, dict]],
) -> list[SceneAsset]:
    assets: list[SceneAsset] = []
    for scene_id in scene_ids:
        for band in bands:
            path, metadata = resolver(scene_id, band)
            unit = str(metadata.get("unit", "")).strip().lower()
            if unit not in {"power", "db"}:
                raise AssetCompatibilityError(f"Raster unit is missing or unsupported for {scene_id}/{band}")
            assets.append(SceneAsset(scene_id=scene_id, band=band, path=Path(path), unit=unit))
    validate_asset_set(assets)
    return assets


def _signature(path: Path) -> tuple:
    with rasterio.open(path) as source:
        return (
            source.crs.to_string() if source.crs else None,
            source.width,
            source.height,
            tuple(float(value) for value in source.transform),
            tuple(float(value) for value in source.res),
        )


def validate_asset_set(assets: list[SceneAsset]) -> None:
    if not assets:
        raise AssetCompatibilityError("No raster assets were resolved")
    signatures = {_signature(asset.path) for asset in assets}
    if len(signatures) != 1:
        raise AssetCompatibilityError("Live rasters do not share the same CRS, grid or resolution")
    for asset in assets:
        if asset.unit.lower() not in {"power", "db"}:
            raise AssetCompatibilityError(f"Unsupported raster unit: {asset.unit}")


def _read_as_db(asset: SceneAsset) -> np.ndarray:
    with rasterio.open(asset.path) as source:
        values = source.read(1).astype("float32")
        nodata = source.nodata
    if nodata is not None and np.isfinite(nodata):
        values[values == nodata] = np.nan
    if asset.unit.lower() == "power":
        values[(~np.isfinite(values)) | (values <= 0)] = np.nan
        with np.errstate(divide="ignore", invalid="ignore"):
            values = 10.0 * np.log10(values)
    else:
        values[~np.isfinite(values)] = np.nan
    return values.astype("float32")


def read_common_stack(assets: list[SceneAsset]) -> dict[str, np.ndarray]:
    validate_asset_set(assets)
    output: dict[str, list[np.ndarray]] = {}
    for asset in assets:
        output.setdefault(asset.band, []).append(_read_as_db(asset))
    return {band: np.stack(values, axis=0) for band, values in output.items()}

