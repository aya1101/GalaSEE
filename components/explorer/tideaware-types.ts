export type TideAwareTrack = "047" | "155" | "both";
export type TideAwareBand = "HHHH" | "HVHV";
export type TideAwareRunStatusName = "queued" | "resolving" | "fetching" | "processing" | "ready" | "blocked" | "error";
export type TideCoverageStatus = "AVAILABLE" | "PARTIAL" | "UNAVAILABLE";
export type TideAwareValidationStatus = "NOT VALIDATED" | "PARTIALLY VALIDATED" | "VALIDATED";

export type TideAwareRunRequest = {
  aoi: Record<string, unknown>;
  track?: TideAwareTrack;
  frame?: string;
  reference_count?: number;
  monitoring_count?: number;
  bands?: TideAwareBand[];
  z_thr?: number;
  z_pos?: number;
  min_db_drop?: number;
  cusum_k?: number;
  cusum_h?: number;
  min_patch?: number;
  use_corrected?: boolean;
};

export type TideAwareSceneRole = {
  scene_id: string;
  file_name: string;
  track: string;
  frame?: string | null;
  orbit_direction?: string | null;
  acquisition_time: string;
  role: string;
  tide_level_m?: number | null;
  tide_covered: boolean;
};

export type TideAwareLayer = {
  id: string;
  track: string;
  branch: "Original" | "Corrected";
  polarization: TideAwareBand;
  kind: string;
  url: string;
  media_type: string;
  status: "OK" | "UNAVAILABLE";
};

export type TideAwareTideCoverage = {
  status: TideCoverageStatus;
  source: string;
  station: string;
  covered_count: number;
  total_count: number;
  missing_scene_ids: string[];
  max_gap_minutes?: number | null;
  reason?: string | null;
};

export type TideAwareTrackSummary = {
  track: "047" | "155";
  status: "ready" | "blocked" | "error";
  scene_roles: TideAwareSceneRole[];
  tide?: TideAwareTideCoverage | null;
  layers: TideAwareLayer[];
  candidate_area_ha: number;
  repeated_anomaly_area_ha: number;
  validation_status: TideAwareValidationStatus;
  warnings: string[];
};

export type TideAwareRunStatus = {
  id: string;
  status: TideAwareRunStatusName;
  stage?: string | null;
  progress: number;
  tracks: TideAwareTrackSummary[];
  validation_status: TideAwareValidationStatus;
  report_url?: string | null;
  report_html_url?: string | null;
  error?: string | null;
};
