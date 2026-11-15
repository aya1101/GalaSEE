export type CopilotBand = "HHHH" | "HVHV" | "COMPOSITE";
export type CopilotContext = {
  sceneId: string | null;
  sceneDate?: string | null;
  band: CopilotBand;
  collectionId?: string | null;
  aoiId: string;
  aoiHash: string;
  layerState: Record<string, boolean>;
  timelineIndex: number;
  timelineCount: number;
  catalogMode: "earthdata" | "demo" | "error";
  assetMode: "live" | "cached" | "unavailable";
  dataStatus: "ready" | "partial" | "unknown" | "error";
  analytics?: CopilotAnalyticsSnapshot;
  contextVersion: number;
};

export type CopilotAnalyticsSeries = {
  variable: "HHHH" | "HVHV";
  values: number[];
  meanDb: number;
  medianDb?: number;
  p10Db?: number;
  p90Db?: number;
  validPixelCount?: number;
};

export type CopilotAnalyticsSnapshot = {
  radarProfile?: {
    status: "idle" | "loading" | "ready" | "error";
    activeBand?: "HHHH" | "HVHV";
    series: Partial<Record<"HHHH" | "HVHV", CopilotAnalyticsSeries>>;
    source?: string;
  };
  regionStats?: {
    status: "idle" | "loading" | "ready" | "error";
    statistics?: Record<string, unknown>;
    source?: string;
  };
  pixel?: Record<string, unknown> | null;
  raster?: {
    status: "idle" | "loading" | "raster" | "preview" | "error";
    style: { mode: "grayscale" | "heatmap"; opacity: number; lowPercentile: number; highPercentile: number };
  };
};

export type UiAction = {
  action: "set_radar_band" | "toggle_layer" | "select_scene" | "set_timeline_index" | "open_region_stats" | "open_pixel_inspector";
  arguments: Record<string, unknown>;
  requiresConfirmation?: boolean;
  undoable?: boolean;
};

export type CopilotCitation = { sourceDocumentId: string; title: string; canonicalUrl: string; documentVersion: string; sourceAnchor: string };
export type CopilotProvenance = { source?: string; tool?: string; sceneId?: string; band?: string; bands?: string[]; assetMode?: string; [key: string]: unknown };
export type CopilotMessage = { id: string; role: "user" | "assistant"; text: string; status?: string; citations?: CopilotCitation[]; provenance?: CopilotProvenance[]; actions?: UiAction[]; progress?: string };

