from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

from .contracts import TideCoverage


@dataclass(frozen=True)
class TideObservation:
    timestamp: datetime
    level_m: float


@dataclass(frozen=True)
class TideSeries:
    observations: list[TideObservation]
    source: str
    station: str = "383"

    @property
    def start(self) -> datetime:
        return self.observations[0].timestamp

    @property
    def end(self) -> datetime:
        return self.observations[-1].timestamp


@dataclass(frozen=True)
class TideSample:
    timestamp: datetime
    level_m: float | None
    gap_to_nearest_obs_minutes: float | None
    covered: bool


DEFAULT_UHSLC_URL = "https://uhslc.soest.hawaii.edu/data/csv/fast/hourly/h383.csv"


def _parse_timestamp(year: str, month: str, day: str, hour: str) -> datetime:
    return datetime(int(year), int(month), int(day), int(hour), tzinfo=timezone.utc)


def _read_csv(text: str, source: str) -> TideSeries:
    rows = list(csv.reader(text.splitlines()))
    observations: dict[datetime, TideObservation] = {}
    for row in rows:
        if len(row) < 5:
            continue
        try:
            timestamp = _parse_timestamp(row[0], row[1], row[2], row[3])
            sea_level_mm = float(row[4])
        except (TypeError, ValueError):
            continue
        if sea_level_mm <= -30000:
            continue
        observations[timestamp] = TideObservation(timestamp=timestamp, level_m=sea_level_mm / 1000.0)
    ordered = [observations[key] for key in sorted(observations)]
    if not ordered:
        raise ValueError("Tide source contains no valid observations")
    return TideSeries(observations=ordered, source=source)


def fetch_uhslc_hourly(
    url: str = DEFAULT_UHSLC_URL,
    *,
    cache_path: Path | None = None,
    timeout_seconds: float = 60.0,
) -> TideSeries:
    source = url
    if url.startswith("http://") or url.startswith("https://"):
        if cache_path and cache_path.is_file():
            text = cache_path.read_text(encoding="utf-8")
        else:
            response = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
            response.raise_for_status()
            text = response.text
            if cache_path:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                partial = cache_path.with_suffix(cache_path.suffix + ".part")
                partial.write_text(text, encoding="utf-8")
                os.replace(partial, cache_path)
    else:
        source_path = Path(url)
        text = source_path.read_text(encoding="utf-8")
        source = str(source_path)
    return _read_csv(text, source)


def interpolate_tide(series: TideSeries, acquisition_time: datetime) -> TideSample:
    timestamp = acquisition_time if acquisition_time.tzinfo else acquisition_time.replace(tzinfo=timezone.utc)
    timestamp = timestamp.astimezone(timezone.utc)
    if timestamp < series.start or timestamp > series.end:
        return TideSample(timestamp=timestamp, level_m=None, gap_to_nearest_obs_minutes=None, covered=False)

    seconds = [(item.timestamp - series.start).total_seconds() for item in series.observations]
    target_seconds = (timestamp - series.start).total_seconds()
    nearest_index = min(range(len(seconds)), key=lambda index: abs(seconds[index] - target_seconds))
    nearest_gap = abs(seconds[nearest_index] - target_seconds) / 60.0
    if target_seconds <= seconds[0]:
        level = series.observations[0].level_m
    elif target_seconds >= seconds[-1]:
        level = series.observations[-1].level_m
    else:
        right = next(index for index, value in enumerate(seconds) if value >= target_seconds)
        left = right - 1
        fraction = (target_seconds - seconds[left]) / (seconds[right] - seconds[left])
        level = series.observations[left].level_m + fraction * (series.observations[right].level_m - series.observations[left].level_m)
    return TideSample(timestamp=timestamp, level_m=float(level), gap_to_nearest_obs_minutes=nearest_gap, covered=True)


def tide_window(series: TideSeries, center_time: datetime | None = None, *, hours: int = 72) -> list[TideObservation]:
    """Return the observed tide values around a scene, without forecasting."""
    if hours < 1:
        raise ValueError("hours must be positive")
    center = center_time or series.end
    if center.tzinfo is None:
        center = center.replace(tzinfo=timezone.utc)
    center = center.astimezone(timezone.utc)
    from datetime import timedelta
    lower = center - timedelta(hours=hours)
    upper = center + timedelta(hours=hours)
    return [item for item in series.observations if lower <= item.timestamp <= upper]


def evaluate_tide_coverage(
    samples: list[TideSample],
    *,
    scene_ids: list[str] | None = None,
    source: str = "UHSLC station 383",
    station: str = "383",
) -> TideCoverage:
    total = len(samples)
    covered = sum(1 for sample in samples if sample.covered)
    missing = [scene_ids[index] for index, sample in enumerate(samples) if not sample.covered] if scene_ids else []
    gaps = [sample.gap_to_nearest_obs_minutes for sample in samples if sample.gap_to_nearest_obs_minutes is not None]
    if total == 0 or covered == 0:
        status = "UNAVAILABLE"
    elif covered < total:
        status = "PARTIAL"
    else:
        status = "AVAILABLE"
    reason = None if status == "AVAILABLE" else "One or more acquisition times are outside tide coverage"
    return TideCoverage(
        status=status,
        source=source,
        station=station,
        covered_count=covered,
        total_count=total,
        missing_scene_ids=missing,
        max_gap_minutes=max(gaps) if gaps else None,
        reason=reason,
    )

