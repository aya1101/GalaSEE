from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class CatalogMode(str, Enum):
    earthdata = "earthdata"
    demo = "demo"
    error = "error"


class AssetMode(str, Enum):
    live = "live"
    cached = "cached"
    unavailable = "unavailable"


class DataStatus(str, Enum):
    ready = "ready"
    partial = "partial"
    unknown = "unknown"
    error = "error"


class CatalogResult(BaseModel):
    status: str = Field(pattern=r"^(ok|error|disabled)$")
    records: list[dict[str, Any]] = Field(default_factory=list)
    errorCode: str | None = None
    detail: str | None = None


class EarthdataTruthResponse(BaseModel):
    catalogMode: CatalogMode
    assetMode: AssetMode
    dataStatus: DataStatus
    source: str
    freshness: str | None = None
    errorCode: str | None = None
    payload: Any


class MapContext(BaseModel):
    sceneId: str | None = None
    sceneDate: str | None = None
    band: Literal["HHHH", "HVHV", "COMPOSITE"]
    collectionId: str | None = None
    aoiId: str
    aoiHash: str
    layerState: dict[str, bool] = Field(default_factory=dict)
    timelineIndex: int = 0
    timelineCount: int = 0
    catalogMode: CatalogMode
    assetMode: AssetMode
    dataStatus: DataStatus
    analytics: dict[str, Any] = Field(default_factory=dict)
    contextVersion: int


class SceneTruth(BaseModel):
    sceneId: str
    acquisitionTime: str | None = None
    collection: str | None = None
    product: str | None = None
    orbitDirection: str | None = None
    track: str | int | None = None
    frame: str | int | None = None
    geometry: dict[str, Any] | None = None
    bands: list[str] = Field(default_factory=list)
    frequency: str | None = None
    polarization: str | None = None
    catalogMode: CatalogMode
    assetMode: AssetMode
    dataStatus: DataStatus
    raster: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Any] = Field(default_factory=dict)
