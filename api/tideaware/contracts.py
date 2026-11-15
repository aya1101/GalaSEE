from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TrackCode = Literal["047", "155", "both"]
Band = Literal["HHHH", "HVHV"]
RunStatus = Literal["queued", "resolving", "fetching", "processing", "ready", "blocked", "error"]
TideStatus = Literal["AVAILABLE", "PARTIAL", "UNAVAILABLE"]
ValidationStatus = Literal["NOT VALIDATED", "PARTIALLY VALIDATED", "VALIDATED"]
AnomalyLabel = Literal[
    "Stable",
    "Potential Loss",
    "Potential Gain",
    "Negative Anomaly",
    "Uncertain",
    "Insufficient Temporal Evidence",
]


def validate_thresholds(
    *,
    z_thr: float,
    z_pos: float,
    min_db_drop: float,
    cusum_k: float,
    cusum_h: float,
    min_patch: int,
) -> None:
    if z_thr >= 0:
        raise ValueError("z_thr must be negative")
    if z_pos <= 0:
        raise ValueError("z_pos must be positive")
    if min_db_drop <= 0:
        raise ValueError("min_db_drop must be positive")
    if cusum_k <= 0 or cusum_h <= 0:
        raise ValueError("CUSUM parameters must be positive")
    if min_patch < 1:
        raise ValueError("min_patch must be at least 1")


class TideAwareRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    aoi: dict[str, Any]
    track: TrackCode = "both"
    frame: str | None = None
    reference_count: int = Field(default=4, ge=3, le=12)
    monitoring_count: int = Field(default=2, ge=1, le=12)
    bands: list[Band] = Field(default_factory=lambda: ["HHHH", "HVHV"])
    z_thr: float = -3.0
    z_pos: float = 3.0
    min_db_drop: float = 1.5
    cusum_k: float = 0.5
    cusum_h: float = 4.0
    min_patch: int = Field(default=3, ge=1, le=10000)
    use_corrected: bool = True

    @field_validator("bands")
    @classmethod
    def validate_bands(cls, value: list[Band]) -> list[Band]:
        if not value or len(set(value)) != len(value):
            raise ValueError("bands must contain one or more unique polarizations")
        return value

    @model_validator(mode="after")
    def validate_processing_parameters(self) -> "TideAwareRunRequest":
        validate_thresholds(
            z_thr=self.z_thr,
            z_pos=self.z_pos,
            min_db_drop=self.min_db_drop,
            cusum_k=self.cusum_k,
            cusum_h=self.cusum_h,
            min_patch=self.min_patch,
        )
        if self.monitoring_count > self.reference_count:
            raise ValueError("monitoring_count cannot exceed reference_count")
        return self


class SceneRole(BaseModel):
    scene_id: str
    file_name: str
    track: str
    frame: str | None = None
    orbit_direction: str | None = None
    acquisition_time: datetime
    role: str
    tide_level_m: float | None = None
    tide_covered: bool = False


class LayerReference(BaseModel):
    id: str
    track: str
    branch: Literal["Original", "Corrected"]
    polarization: Band
    kind: str
    url: str
    media_type: str
    status: Literal["OK", "UNAVAILABLE"] = "OK"


class TideCoverage(BaseModel):
    status: TideStatus
    source: str
    station: str
    covered_count: int
    total_count: int
    missing_scene_ids: list[str] = Field(default_factory=list)
    max_gap_minutes: float | None = None
    reason: str | None = None


class TrackAnalysisSummary(BaseModel):
    track: Literal["047", "155"]
    status: Literal["ready", "blocked", "error"]
    scene_roles: list[SceneRole] = Field(default_factory=list)
    tide: TideCoverage | None = None
    layers: list[LayerReference] = Field(default_factory=list)
    candidate_area_ha: float = 0.0
    repeated_anomaly_area_ha: float = 0.0
    validation_status: ValidationStatus = "NOT VALIDATED"
    warnings: list[str] = Field(default_factory=list)


class TideAwareRunStatus(BaseModel):
    id: str
    status: RunStatus
    stage: str | None = None
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    tracks: list[TrackAnalysisSummary] = Field(default_factory=list)
    validation_status: ValidationStatus = "NOT VALIDATED"
    report_url: str | None = None
    report_html_url: str | None = None
    error: str | None = None

