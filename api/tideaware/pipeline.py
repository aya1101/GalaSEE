from __future__ import annotations

from typing import Any, Callable


def _candidate_area(feature_collection: dict[str, Any]) -> float:
    return float(feature_collection.get("candidateAreaHa") or 0.0)


def build_track_summary(
    *,
    track: str,
    roles: list[Any],
    tide: dict[str, Any],
    result: dict[str, Any],
    layer_url_factory: Callable[[str, str], str],
) -> tuple[dict[str, Any], list[tuple[str, str, dict[str, Any]]]]:
    bands = result.get("bands") or {}
    layers: list[dict[str, Any]] = []
    artifacts: list[tuple[str, str, dict[str, Any]]] = []
    candidate_area = 0.0
    for band, band_result in bands.items():
        for branch, key in (("Original", "original_patches"), ("Corrected", "corrected_patches")):
            feature_collection = band_result.get(key)
            if not feature_collection:
                continue
            candidate_area = max(candidate_area, _candidate_area(feature_collection))
            artifacts.append((branch, band, feature_collection))
            layers.append({
                "id": f"{track}-{branch.lower()}-{band.lower()}-candidate",
                "track": track,
                "branch": branch,
                "polarization": band,
                "kind": "candidate",
                "url": layer_url_factory(branch, band),
                "media_type": "application/geo+json",
                "status": "OK",
            })
    scene_roles = [role.model_dump(mode="json") if hasattr(role, "model_dump") else role for role in roles]
    return {
        "track": track,
        "status": "ready",
        "scene_roles": scene_roles,
        "tide": tide,
        "layers": layers,
        "candidate_area_ha": candidate_area,
        "repeated_anomaly_area_ha": 0.0,
        "validation_status": "NOT VALIDATED",
        "warnings": list(result.get("warnings") or []),
        "corrected_available": bool(result.get("corrected_available")),
    }, artifacts
