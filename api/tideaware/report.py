from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any


def _track_for_report(track: dict[str, Any]) -> dict[str, Any]:
    return {
        "track": track.get("track"),
        "status": track.get("status"),
        "candidateAreaHa": track.get("candidate_area_ha", track.get("candidateAreaHa", 0.0)),
        "repeatedAnomalyAreaHa": track.get("repeated_anomaly_area_ha", track.get("repeatedAnomalyAreaHa", 0.0)),
        "validationStatus": track.get("validation_status", track.get("validationStatus", "NOT VALIDATED")),
        "warnings": list(track.get("warnings") or []),
        "tide": track.get("tide"),
        "layers": track.get("layers") or [],
    }


def build_report_payload(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": state.get("id"),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "status": state.get("status"),
        "validationStatus": state.get("validation_status", state.get("validationStatus", "NOT VALIDATED")),
        "title": "TideAware coastal change report",
        "summary": "Potential findings from live Earthdata scenes and tide-aware analysis. Findings require analyst validation.",
        "tracks": [_track_for_report(track) for track in state.get("tracks") or []],
        "provenance": state.get("provenance") or {},
        "method": {
            "sceneSource": "Live ASF/Earthdata catalog",
            "rasterSource": "Live Harmony GeoTIFF cache",
            "tideSource": "UHSLC hourly observations",
            "detectors": ["OLS tide relationship", "Robust Z", "CUSUM decrease"],
            "labels": "Potential / Not Validated",
        },
    }


def render_report_html(payload: dict[str, Any]) -> str:
    title = html.escape(str(payload.get("title") or "TideAware report"))
    run_id = html.escape(str(payload.get("id") or ""))
    validation = html.escape(str(payload.get("validationStatus") or "NOT VALIDATED"))
    summary = html.escape(str(payload.get("summary") or ""))
    rows = []
    for track in payload.get("tracks") or []:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(track.get('track') or ''))}</td>"
            f"<td>{html.escape(str(track.get('status') or ''))}</td>"
            f"<td>{float(track.get('candidateAreaHa') or 0):.2f}</td>"
            f"<td>{html.escape(str(track.get('validationStatus') or validation))}</td>"
            "</tr>"
        )
    provenance = html.escape(json.dumps(payload.get("provenance") or {}, ensure_ascii=False, indent=2))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:40px auto;padding:0 24px;color:#17212b}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ccd6dd;padding:8px;text-align:left}}.badge{{display:inline-block;padding:4px 8px;background:#f4e4a8;border-radius:999px}}pre{{white-space:pre-wrap;background:#f5f7f9;padding:16px}}</style>
</head><body><h1>{title}</h1><p>Run: <code>{run_id}</code></p><p><span class="badge">{validation}</span></p>
<p>{summary}</p><h2>Potential findings</h2><table><thead><tr><th>Track</th><th>Status</th><th>Candidate area (ha)</th><th>Validation</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Provenance</h2><pre>{provenance}</pre></body></html>"""
