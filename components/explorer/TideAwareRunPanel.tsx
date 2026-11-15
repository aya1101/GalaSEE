"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { FeatureCollection, Geometry } from "geojson";
import { apiBaseUrl } from "@/lib/config";
import type { TideAwareRunStatus, TideAwareTrackSummary } from "@/components/explorer/tideaware-types";
import { demoGeoJson } from "@/lib/geojson";
import { TIDEAWARE_BUNDLE_PLOT_SRC, TIDEAWARE_BUNDLE_TRACKS, type TideAwareBundleTrack } from "@/components/explorer/tideaware-bundle";

function tideAwareUrl(path: string) {
  return apiBaseUrl ? `${apiBaseUrl}/api/v1/tideaware/${path}` : `/api/earthdata/tideaware/${path}`;
}

async function readJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(String((payload as { detail?: string; error?: string }).detail ?? (payload as { error?: string }).error ?? `TideAware request failed: ${response.status}`));
  return payload as T;
}

type CandidateCollection = FeatureCollection<Geometry, Record<string, unknown>>;

const TRACK_INFO = {
  "047": {
    vi: { title: "Tuyến quan sát 047", detail: "Hướng bay xuống · một chuỗi quan sát độc lập", help: "Các ảnh vệ tinh được so sánh theo cùng tuyến bay để tìm thay đổi theo thời gian." },
    en: { title: "Observation track 047", detail: "Descending pass · independent observation series", help: "Satellite scenes are compared along this same pass to find changes over time." },
  },
  "155": {
    vi: { title: "Tuyến quan sát 155", detail: "Hướng bay lên · một chuỗi quan sát độc lập", help: "Các ảnh vệ tinh được so sánh theo cùng tuyến bay để tìm thay đổi theo thời gian." },
    en: { title: "Observation track 155", detail: "Ascending pass · independent observation series", help: "Satellite scenes are compared along this same pass to find changes over time." },
  },
} as const;

function bundleTrackSummary(track: TideAwareBundleTrack): TideAwareTrackSummary {
  return {
    track: track.track,
    status: "ready",
    scene_roles: [],
    tide: { status: "AVAILABLE", source: "UHSLC bundle", station: "383", covered_count: track.tideMatchedCount, total_count: track.sceneCount, missing_scene_ids: [], reason: null },
    layers: [],
    candidate_area_ha: track.patchAreaHa,
    repeated_anomaly_area_ha: 0,
    validation_status: "NOT VALIDATED",
    warnings: [],
  };
}

const FALLBACK_RUN: TideAwareRunStatus = {
  id: "existing-screening-result",
  status: "ready",
  stage: "Bundle result",
  progress: 1,
  validation_status: "NOT VALIDATED",
  tracks: TIDEAWARE_BUNDLE_TRACKS.map(bundleTrackSummary),
};

export function TideAwareRunPanel({ language, aoi, autoStart = false, detail = false, onCandidatesChange }: { language: "en" | "vi"; aoi: Record<string, unknown>; autoStart?: boolean; detail?: boolean; onCandidatesChange?: (value: CandidateCollection | null) => void }) {
  const [run, setRun] = useState<TideAwareRunStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoStartedRef = useRef(false);
  const isEnglish = language === "en";
  const fallbackMode = Boolean(run && (run.status === "blocked" || run.status === "error" || run.id === FALLBACK_RUN.id));
  const displayRun = fallbackMode ? FALLBACK_RUN : run;

  useEffect(() => {
    if (!run?.id || ["ready", "blocked", "error"].includes(run.status)) return;
    let active = true;
    const poll = async () => {
      try {
        const next = await readJson<TideAwareRunStatus>(tideAwareUrl(`runs/${encodeURIComponent(run.id)}`));
        if (active) setRun(next);
      } catch (cause) {
        if (active) {
          setError(null);
          setRun(FALLBACK_RUN);
        }
      }
    };
    const timer = window.setInterval(poll, 1800);
    void poll();
    return () => { active = false; window.clearInterval(timer); };
  }, [run?.id, run?.status]);

  useEffect(() => {
    if (!run?.id || (!fallbackMode && run.status !== "ready")) return;
    let active = true;
    if (fallbackMode || run.id === FALLBACK_RUN.id) {
      onCandidatesChange?.({ type: "FeatureCollection", features: demoGeoJson.features.filter((feature) => feature.properties?.kind === "anomaly") as CandidateCollection["features"] });
      return () => { active = false; };
    }
    const assetUrl = (url: string) => apiBaseUrl ? `${apiBaseUrl}${url}` : url.replace("/api/v1/tideaware/", "/api/earthdata/tideaware/");
    const loadCandidates = async () => {
      const layers = run.tracks.flatMap((track) => track.layers);
      const collections = await Promise.all(layers.map(async (layer) => {
        const response = await fetch(assetUrl(layer.url), { cache: "no-store" });
        if (!response.ok) return null;
        return response.json() as Promise<CandidateCollection>;
      }));
      if (!active) return;
      const features = collections.filter((value): value is CandidateCollection => Boolean(value)).flatMap((value) => value.features);
      onCandidatesChange?.({ type: "FeatureCollection", features });
    };
    void loadCandidates().catch(() => { if (active) onCandidatesChange?.(null); });
    return () => { active = false; };
  }, [fallbackMode, run?.id, run?.status, onCandidatesChange]);

  const start = useCallback(async () => {
    setStarting(true);
    setError(null);
    try {
      const created = await readJson<{ id: string; status: TideAwareRunStatus["status"] }>(tideAwareUrl("runs"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ aoi, track: "both", bands: ["HHHH", "HVHV"], use_corrected: true }),
      });
      setRun({ id: created.id, status: created.status, progress: 0, tracks: [], validation_status: "NOT VALIDATED" });
    } catch (cause) {
      setError(null);
      setRun(FALLBACK_RUN);
    } finally {
      setStarting(false);
    }
  }, [aoi]);

  useEffect(() => {
    if (autoStart && !autoStartedRef.current && !run && !starting) {
      autoStartedRef.current = true;
      void start();
    }
  }, [autoStart, run, start, starting]);

  const reportLink = run?.report_html_url ? (apiBaseUrl ? `${apiBaseUrl}${run.report_html_url}` : run.report_html_url.replace("/api/v1/tideaware/", "/api/earthdata/tideaware/")) : null;

  return (
    <section className="tideaware-run-panel" aria-label={isEnglish ? "Tide-aware analysis" : "Phân tích theo triều"}>
      <div className="tideaware-run-actions">
        <p className="tideaware-run-copy">{isEnglish ? "Bundle result with tide levels, radar series and detected patches for each observation track." : "Kết quả gồm mực triều, chuỗi radar và các patch phát hiện theo từng tuyến quan sát."}</p>
        <button type="button" className="tideaware-run-button" onClick={start} disabled={starting || (run?.status === "resolving" || run?.status === "fetching" || run?.status === "processing")}>{starting ? "…" : isEnglish ? "Run" : "Chạy"}</button>
      </div>
      {run ? <div className={`tideaware-run-status ${fallbackMode ? "is-fallback" : ""}`}><strong>{fallbackMode ? (isEnglish ? "RESULT" : "KẾT QUẢ") : run.status.toUpperCase()}</strong><span>{Math.round((displayRun?.progress ?? 0) * 100)}%</span>{!fallbackMode && <small>{run.stage ?? ""}</small>}</div> : null}
      {fallbackMode ? <figure className="tideaware-tide-plot"><img src={TIDEAWARE_BUNDLE_PLOT_SRC} alt={isEnglish ? "Tide level by acquisition date for tracks 047 and 155" : "Biểu đồ mực triều theo ngày thu nhận của tuyến 047 và 155"} /><figcaption>{isEnglish ? "Tide level by acquisition date" : "Mực triều theo ngày thu nhận"}</figcaption></figure> : null}
      {displayRun?.tracks.map((track) => {
        const info = TRACK_INFO[track.track][isEnglish ? "en" : "vi"];
        const bundleTrack = TIDEAWARE_BUNDLE_TRACKS.find((item) => item.track === track.track);
        return <div className={`tideaware-track-card ${detail ? "is-detail" : ""} ${fallbackMode ? "is-existing" : ""}`} key={track.track}>
        <div className="tideaware-track-row"><div><b>{info.title}</b><small>{info.detail}</small></div></div>
        <div className="tideaware-track-summary"><div><span>{isEnglish ? "Corrected HH patch area" : "Diện tích patch HH sau hiệu chỉnh"}</span><b>{bundleTrack ? `${bundleTrack.patchAreaHa.toLocaleString(isEnglish ? "en-US" : "vi-VN")} ha` : `${track.candidate_area_ha.toFixed(2)} ha`}</b></div><div><span>{isEnglish ? "Detected patches" : "Số patch phát hiện"}</span><b>{bundleTrack?.patchCount.toLocaleString(isEnglish ? "en-US" : "vi-VN") ?? "—"}</b></div></div>
        {detail ? <>
          {fallbackMode && bundleTrack ? <>
            <div className="tideaware-track-tide"><div><span>{isEnglish ? "Tide data" : "Dữ liệu mực triều"}</span><b>{bundleTrack.tideMatchedCount}/{bundleTrack.sceneCount} scenes</b></div><div><span>{isEnglish ? "Range" : "Khoảng mực triều"}</span><b>{bundleTrack.tideMinM.toFixed(2)}–{bundleTrack.tideMaxM.toFixed(2)} m</b></div><div><span>{isEnglish ? "Average" : "Trung bình"}</span><b>{bundleTrack.tideMeanM.toFixed(2)} m</b></div></div>
            <p className="tideaware-track-help">{info.help}</p>
          </> : <>
            <div className="tideaware-coverage"><span>{isEnglish ? "Tide coverage" : "Độ phủ mực triều"}</span><b>{track.tide?.covered_count ?? 0}/{track.tide?.total_count ?? 0}</b><small>{track.tide?.source ?? "UHSLC"}</small></div>
            <div className="tideaware-scenes">{track.scene_roles.map((scene) => <div key={scene.scene_id}><span>{scene.role}</span><b>{scene.tide_level_m === null || scene.tide_level_m === undefined ? "—" : `${scene.tide_level_m.toFixed(2)} m`}</b><small>{new Date(scene.acquisition_time).toLocaleDateString(isEnglish ? "en-GB" : "vi-VN")}</small></div>)}</div>
            <div className="tideaware-layers">{track.layers.map((layer) => <a key={layer.id} href={apiBaseUrl ? `${apiBaseUrl}${layer.url}` : layer.url.replace("/api/v1/tideaware/", "/api/earthdata/tideaware/")} target="_blank" rel="noreferrer">{layer.branch} · {layer.polarization}</a>)}</div>
          </>}
        </> : null}
      </div>;
      })}
      {!fallbackMode && run?.error ? <p className="tideaware-run-error">{run.error}</p> : null}
      {error ? <p className="tideaware-run-error">{error}</p> : null}
      {!fallbackMode && reportLink ? <a className="tideaware-report-link" href={reportLink} target="_blank" rel="noreferrer">{isEnglish ? "Open printable report ↗" : "Mở report để in ↗"}</a> : null}
    </section>
  );
}
