from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from rasterio.transform import Affine
from scipy import stats

from .polygonize import candidate_feature_collection


@dataclass(frozen=True)
class OlsResult:
    intercept: np.ndarray
    slope: np.ndarray
    r2: np.ndarray
    p_value: np.ndarray
    loo_rmse_tide: float
    loo_rmse_baseline: float


@dataclass(frozen=True)
class RobustZResult:
    median: np.ndarray
    mad: np.ndarray
    sigma_pix: np.ndarray
    sigma_floor: float
    z_maps: np.ndarray
    labels: np.ndarray
    delta_maps: np.ndarray


@dataclass(frozen=True)
class CUSUMResult:
    score: np.ndarray
    flags: list[np.ndarray]


def _loo_rmse(reference: np.ndarray, tide: np.ndarray) -> tuple[float, float]:
    tide_errors: list[float] = []
    baseline_errors: list[float] = []
    for index in range(reference.shape[0]):
        keep = np.ones(reference.shape[0], dtype=bool)
        keep[index] = False
        fitted = pixelwise_ols(reference[keep], tide[keep], calculate_loo=False)
        predicted = fitted.intercept + fitted.slope * tide[index]
        baseline = np.nanmedian(reference[keep], axis=0)
        observed = reference[index]
        valid = np.isfinite(observed) & np.isfinite(predicted) & np.isfinite(baseline)
        if np.any(valid):
            tide_errors.append(float(np.mean((observed[valid] - predicted[valid]) ** 2)))
            baseline_errors.append(float(np.mean((observed[valid] - baseline[valid]) ** 2)))
    if not tide_errors:
        return float("nan"), float("nan")
    return float(np.sqrt(np.mean(tide_errors))), float(np.sqrt(np.mean(baseline_errors)))


def pixelwise_ols(reference: np.ndarray, tide: np.ndarray, *, calculate_loo: bool = True) -> OlsResult:
    values = np.asarray(reference, dtype="float64")
    levels = np.asarray(tide, dtype="float64")
    if values.ndim != 3 or levels.ndim != 1 or values.shape[0] != levels.size:
        raise ValueError("reference must be T,H,W and tide must be T")
    valid_tide = np.isfinite(levels)
    if int(valid_tide.sum()) < 3:
        raise ValueError("at least three tide observations are required")
    values = values[valid_tide]
    levels = levels[valid_tide]
    finite = np.isfinite(values)
    n_valid = finite.sum(axis=0)
    safe_n = np.maximum(n_valid, 1)
    filled = np.where(finite, values, 0.0)
    mean_y = filled.sum(axis=0) / safe_n
    mean_h = float(levels.mean())
    centered_h = levels - mean_h
    centered_y = np.where(finite, filled - mean_y, 0.0)
    denominator = float(np.sum(centered_h ** 2))
    covariance = np.sum(centered_y * centered_h[:, None, None], axis=0) / np.maximum(n_valid - 1, 1)
    variance_h = denominator / max(len(levels) - 1, 1)
    slope = covariance / (variance_h + 1e-12)
    intercept = mean_y - slope * mean_h
    fitted = intercept + slope * levels[:, None, None]
    residual = np.where(finite, values - fitted, 0.0)
    ss_res = np.sum(residual ** 2, axis=0)
    ss_tot = np.sum(np.where(finite, (values - mean_y) ** 2, 0.0), axis=0)
    r2 = 1.0 - ss_res / (ss_tot + 1e-12)
    degrees = np.maximum(n_valid - 2, 1)
    s2 = ss_res / degrees
    standard_error = np.sqrt(s2 / (denominator + 1e-12))
    t_stat = slope / (standard_error + 1e-12)
    p_value = 2 * stats.t.sf(np.abs(t_stat), degrees)
    invalid = n_valid < 3
    for array in (intercept, slope, r2, p_value):
        array[invalid] = np.nan
    loo_tide, loo_baseline = _loo_rmse(values, levels) if calculate_loo else (float("nan"), float("nan"))
    return OlsResult(
        intercept=intercept.astype("float32"),
        slope=slope.astype("float32"),
        r2=r2.astype("float32"),
        p_value=p_value.astype("float32"),
        loo_rmse_tide=loo_tide,
        loo_rmse_baseline=loo_baseline,
    )


def robust_z_labels(
    reference: np.ndarray,
    monitoring: np.ndarray,
    *,
    vegetation_mask: np.ndarray,
    z_thr: float = -3.0,
    z_pos: float = 3.0,
    min_db_drop: float = 1.5,
) -> RobustZResult:
    ref = np.asarray(reference, dtype="float32")
    mon = np.asarray(monitoring, dtype="float32")
    mask = np.asarray(vegetation_mask, dtype=bool)
    if ref.ndim != 3 or mon.ndim != 3 or ref.shape[1:] != mon.shape[1:] or ref.shape[1:] != mask.shape:
        raise ValueError("reference, monitoring and vegetation mask shapes are incompatible")
    median = np.nanmedian(ref, axis=0)
    mad = np.nanmedian(np.abs(ref - median), axis=0)
    n_valid = np.isfinite(ref).sum(axis=0)
    sigma = 1.4826 * mad
    finite_sigma = sigma[np.isfinite(sigma) & (n_valid >= 3)]
    sigma_floor = float(np.percentile(finite_sigma, 25)) if finite_sigma.size else 0.5
    sigma_pix = np.maximum(sigma, sigma_floor)
    z_maps: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    deltas: list[np.ndarray] = []
    for observed in mon:
        delta = observed - median
        z = delta / (sigma_pix + 1e-12)
        z = np.where((n_valid >= 3) & np.isfinite(observed), z, np.nan)
        label = np.zeros(z.shape, dtype=np.int8)
        label[~np.isfinite(z)] = -1
        negative = (z <= z_thr) & (delta <= -min_db_drop) & mask
        positive = (z >= z_pos) & (delta >= min_db_drop) & mask
        label[negative] = 1
        label[positive] = 2
        z_maps.append(z.astype("float32"))
        labels.append(label)
        deltas.append(delta.astype("float32"))
    return RobustZResult(
        median=median.astype("float32"),
        mad=mad.astype("float32"),
        sigma_pix=sigma_pix.astype("float32"),
        sigma_floor=sigma_floor,
        z_maps=np.stack(z_maps),
        labels=np.stack(labels),
        delta_maps=np.stack(deltas),
    )


def cusum_decrease(z_maps: list[np.ndarray] | np.ndarray, *, k: float = 0.5, h: float = 4.0) -> CUSUMResult:
    sequence = [np.asarray(value, dtype="float32") for value in z_maps]
    if not sequence:
        raise ValueError("CUSUM requires at least one z map")
    score = np.zeros_like(sequence[0], dtype="float32")
    flags: list[np.ndarray] = []
    for z in sequence:
        score = np.maximum(0.0, score - z - k)
        flags.append((score > h) & np.isfinite(z))
        score = np.where(np.isfinite(z), score, 0.0)
    return CUSUMResult(score=score, flags=flags)


def _otsu_threshold(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return float("nan")
    if np.allclose(finite.min(), finite.max()):
        return float(finite.min())
    histogram, edges = np.histogram(finite, bins=256)
    centers = (edges[:-1] + edges[1:]) / 2.0
    cumulative = np.cumsum(histogram)
    cumulative_mean = np.cumsum(histogram * centers)
    total = cumulative_mean[-1]
    denominator = cumulative * (cumulative[-1] - cumulative) + 1e-12
    between = (total * cumulative - cumulative_mean) ** 2 / denominator
    return float(centers[int(np.nanargmax(between))])


def provisional_vegetation_mask(median_hv: np.ndarray) -> np.ndarray:
    threshold = _otsu_threshold(np.asarray(median_hv, dtype="float32"))
    return np.isfinite(median_hv) & (median_hv >= threshold)


def run_track_analysis(
    *,
    track: str,
    roles: list[str],
    stacks: dict[str, np.ndarray],
    tide_levels: np.ndarray,
    vegetation_mask: np.ndarray | None = None,
    z_thr: float = -3.0,
    z_pos: float = 3.0,
    min_db_drop: float = 1.5,
    cusum_k: float = 0.5,
    cusum_h: float = 4.0,
    min_patch: int = 3,
    transform: Affine | None = None,
    crs: str = "EPSG:32648",
) -> dict:
    role_array = np.asarray(roles)
    reference_indices = np.where(np.char.startswith(role_array.astype(str), "Reference"))[0]
    monitoring_indices = np.where(np.char.startswith(role_array.astype(str), "Monitoring"))[0]
    if reference_indices.size < 3 or monitoring_indices.size < 1:
        raise ValueError("Track requires at least three Reference and one Monitoring scene")
    levels = np.asarray(tide_levels, dtype="float64")
    if not np.isfinite(levels[reference_indices]).all():
        raise ValueError("Reference tide is incomplete")
    if vegetation_mask is None:
        vegetation_mask = provisional_vegetation_mask(np.nanmedian(stacks["HVHV"][reference_indices], axis=0))
    if transform is None:
        transform = Affine(100.0, 0.0, 0.0, 0.0, -100.0, 0.0)
    monitoring_tide_available = np.isfinite(levels[monitoring_indices]).all()
    warnings: list[str] = []
    if not monitoring_tide_available:
        warnings.append("Missing Monitoring tide")
    bands: dict[str, dict] = {}
    corrected_available = bool(monitoring_tide_available)
    for band, stack in stacks.items():
        values = np.asarray(stack, dtype="float32")
        reference = values[reference_indices]
        monitoring = values[monitoring_indices]
        ols = pixelwise_ols(reference, levels[reference_indices])
        original = robust_z_labels(
            reference,
            monitoring,
            vegetation_mask=vegetation_mask,
            z_thr=z_thr,
            z_pos=z_pos,
            min_db_drop=min_db_drop,
        )
        original_cusum = cusum_decrease(original.z_maps, k=cusum_k, h=cusum_h)
        original_patches = candidate_feature_collection(
            (original.labels[-1] == 1) & vegetation_mask,
            transform,
            crs,
            min_pixels=min_patch,
        )
        band_result = {
            "ols": ols,
            "original": original,
            "original_cusum": original_cusum,
            "original_patches": original_patches,
            "tide_helps": ols.loo_rmse_tide < ols.loo_rmse_baseline,
        }
        if corrected_available:
            correction_mask = (ols.p_value < 0.10) & (ols.r2 >= 0.5) & np.isfinite(ols.slope)
            corrected = monitoring.copy()
            reference_mean_tide = float(np.mean(levels[reference_indices]))
            for index, monitoring_index in enumerate(monitoring_indices):
                expected_change = ols.slope * (levels[monitoring_index] - reference_mean_tide)
                corrected[index] = np.where(correction_mask, corrected[index] - expected_change, corrected[index])
            corrected_result = robust_z_labels(
                reference,
                corrected,
                vegetation_mask=vegetation_mask,
                z_thr=z_thr,
                z_pos=z_pos,
                min_db_drop=min_db_drop,
            )
            band_result["corrected"] = corrected_result
            band_result["corrected_cusum"] = cusum_decrease(corrected_result.z_maps, k=cusum_k, h=cusum_h)
            band_result["corrected_patches"] = candidate_feature_collection(
                (corrected_result.labels[-1] == 1) & vegetation_mask,
                transform,
                crs,
                min_pixels=min_patch,
            )
        bands[band] = band_result
    return {
        "track": track,
        "reference_indices": reference_indices,
        "monitoring_indices": monitoring_indices,
        "vegetation_mask": vegetation_mask,
        "corrected_available": corrected_available,
        "warnings": warnings,
        "bands": bands,
    }

