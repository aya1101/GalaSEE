"use client";

import { useEffect, useMemo, useRef, useState, type CSSProperties, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";
import Image from "next/image";
import * as maplibregl from "maplibre-gl";
import { type Map as MapLibreMap, type MapMouseEvent } from "maplibre-gl";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { apiBaseUrl } from "@/lib/config";
import { demoGeoJson, studyAreaGeoJson, type RegionProperties } from "@/lib/geojson";
import { CopilotPanel } from "@/components/copilot/CopilotPanel";
import chatbotLogo from "@/chatbot-logo.png";
import type { CopilotAnalyticsSnapshot, CopilotContext, UiAction } from "@/components/copilot/copilot-types";

maplibregl.setWorkerUrl(new URL("maplibre-gl/dist/maplibre-gl-worker.mjs", import.meta.url).toString());

type RegionFeature = Feature<Geometry, RegionProperties>;
type RadarBand = "COMPOSITE" | "HHHH" | "HVHV";
type SidebarSection = "map" | "layers";
type RadarSeries = { variable: "HHHH" | "HVHV"; values: number[]; meanDb: number; medianDb?: number; p10Db?: number; p90Db?: number; validPixelCount?: number };
type RadarMetric = { values: number[]; meanDb: number; variable: "HHHH" | "HVHV"; series?: Partial<Record<"HHHH" | "HVHV", RadarSeries>>; source?: string };
type RadarMetricState = { status: "idle" | "loading" | "ready" | "error"; metric?: RadarMetric; variable?: "HHHH" | "HVHV" };
type ComparisonState = { status: "idle" | "checking" | "queued" | "running" | "ready" | "blocked" | "error"; id?: string; report?: { checks?: Array<{ name: string; status: string; detail?: string }>; blockingIssues?: string[] }; candidate?: FeatureCollection<Geometry, Record<string, unknown>>; error?: string };
type PixelInspection = { coordinate: { longitude: number; latitude: number }; values: Record<string, { power: number | null; db: number | null; unit: string; valid: boolean }>; mask: { valid: boolean; source?: string }; source: string };
type RegionStats = { validPixelCount: number; totalPixelCount: number; validCoveragePercent: number; validAreaHa?: number; minDb: number | null; maxDb: number | null; meanDb: number | null; medianDb: number | null; p10Db: number | null; p90Db: number | null; histogram?: { edgesDb: number[]; counts: number[] } };
type RegionStatsState = { status: "idle" | "loading" | "ready" | "error"; statistics?: Record<string, RegionStats> };
type RasterStyle = { mode: "grayscale" | "heatmap"; opacity: number; lowPercentile: number; highPercentile: number };
type LayerState = {
  mangrove: boolean;
  anomalies: boolean;
  aoi: boolean;
  sceneImage: boolean;
  basemap: boolean;
};
type UndoSnapshot = { selectedId: string; layers: LayerState; radarBand: RadarBand; activeSection: SidebarSection; mobilePanelOpen: boolean };
type GcovStatus = "idle" | "loading" | "raster" | "preview" | "error";
type CatalogMode = "earthdata" | "demo" | "error";
type AssetMode = "live" | "cached" | "unavailable";
type DataStatus = "ready" | "partial" | "unknown" | "error";
type DataTruth = { catalogMode: CatalogMode; assetMode: AssetMode; dataStatus: DataStatus };

const gcovPreviewCache = new Map<string, Promise<PreviewAsset>>();

function contextVersionFor(value: unknown): number {
  const input = JSON.stringify(value);
  let hash = 2166136261;
  for (let index = 0; index < input.length; index += 1) {
    hash ^= input.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function analyticsUrl(path: string) {
  return apiBaseUrl ? `${apiBaseUrl}/api/v1/${path}` : `/api/earthdata/analytics/${path}`;
}

async function postAnalytics<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(analyticsUrl(path), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body), cache: "no-store" });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(String((payload as { detail?: string; error?: string }).detail ?? (payload as { error?: string }).error ?? `Analytics request failed: ${response.status}`));
  return payload as T;
}

const INITIAL_LAYERS: LayerState = {
  mangrove: false,
  anomalies: false,
  aoi: true,
  sceneImage: true,
  basemap: true,
};
const INTERACTIVE_LAYERS = ["selected-scene-line", "mangrove-fill", "anomaly-fill", "anomaly-points", "candidate-change-fill"];

const mapStyle: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    basemap: {
      type: "raster",
      tileSize: 256,
      maxzoom: 8,
      tiles: ["https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg"],
      attribution: "NASA GIBS Blue Marble",
    },
  },
  layers: [
    { id: "background", type: "background", paint: { "background-color": "#e5efee" } },
    { id: "basemap", type: "raster", source: "basemap", layout: { visibility: "visible" }, paint: { "raster-opacity": 0.72, "raster-saturation": -0.08, "raster-contrast": -0.04 } },
  ],
};

const icons = {
  map: "M4 5.5 8.5 3l7 3.5L20 4v14.5l-4.5 2.5-7-3.5L4 20.5V5.5Zm4.5-2v12.5m7-9.5v12.5",
  layers: "M12 3 3 8l9 5 9-5-9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5",
  anomaly: "m4 17 4.5-5 3 2 5.5-8M16 6h3v3",
  focus: "M4 9V5h4M20 9V5h-4M4 15v4h4M20 15v4h-4M8 12h8M12 8v8",
  download: "M12 3v11m0 0 4-4m-4 4-4-4M4 17v3h16v-3",
  settings: "M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Zm0-5.5v2m0 14v2M3 12h2m14 0h2M5.6 5.6 7 7m10 10 1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4",
  bell: "M18 9a6 6 0 1 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9Zm-8 12h4",
  close: "m6 6 12 12M18 6 6 18",
  menu: "M4 6h16M4 12h16M4 18h16",
};

function Icon({ name, size = 18 }: { name: keyof typeof icons; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={icons[name]} />
    </svg>
  );
}

function formatNumber(value: number | undefined, suffix = "") {
  if (value === undefined) return "—";
  return `${value.toLocaleString("vi-VN")}${suffix}`;
}

function formatSceneTimestamp(value: string | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return value;
  return `${date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" })} · ${date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })}`;
}

function sceneShortId(details: RegionProperties) {
  const source = details.sceneName ?? details.id;
  const match = source.match(/NISAR_L2_[^_]+_[^_]+_(\d{3})_(\d{3})_([A-Z])_(\d{3})/);
  return match ? `${match[1]}/${match[2]} · ${match[3]}${match[4]}` : source.slice(0, 18);
}

function sceneDisplayTitle(details: RegionProperties) {
  if (details.kind !== "study") return details.title;
  return details.location && !details.location.includes("ASF DAAC") ? details.location : "Cửa Dinh – Cồn Ba Lá";
}

function formatSceneDate(value: string | undefined) {
  if (!value) return "Không rõ ngày";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function getFeatureCollection(value: unknown): FeatureCollection<Geometry, RegionProperties> | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as FeatureCollection<Geometry, RegionProperties>;
  if (candidate.type !== "FeatureCollection" || !Array.isArray(candidate.features)) return null;
  return candidate;
}

function normalizeEarthdataFeatures(value: unknown): FeatureCollection<Geometry, RegionProperties> | null {
  const candidate = getFeatureCollection(value);
  if (!candidate) return null;
  const hasTideAwareProperties = candidate.features.some((feature) => feature.properties?.kind);
  if (hasTideAwareProperties) return candidate;
  return {
    ...candidate,
    features: candidate.features.map((feature, index) => {
      const raw = (feature.properties ?? {}) as Record<string, unknown>;
      const id = String(feature.id ?? raw.fileID ?? raw.granuleName ?? `ASF-${index + 1}`);
      const title = String(raw.sceneName ?? raw.fileID ?? raw.granuleName ?? `NISAR GCOV scene ${index + 1}`);
      const browse = Array.isArray(raw.browse) ? raw.browse : [];
      const additionalUrls = Array.isArray(raw.additionalUrls) ? raw.additionalUrls : [];
      const browseCompositeUrl = String(browse.find((url) => typeof url === "string" && url.includes("_NATIVE.png")) ?? "");
      const browseHHHHUrl = String(browse.find((url) => typeof url === "string" && url.includes("_NATIVE_A_HHHH.png")) ?? "");
      const browseHVHVUrl = String(browse.find((url) => typeof url === "string" && url.includes("_NATIVE_A_HVHV.png")) ?? "");
      const nativeKmlUrl = String(additionalUrls.find((url) => typeof url === "string" && url.includes("_NATIVE.kml")) ?? "");
      const browseUrl = browseCompositeUrl || String(browse.find((url) => typeof url === "string" && url.includes("_LATLON.png")) ?? browse.find((url) => typeof url === "string" && url.endsWith(".png")) ?? "");
      return {
        ...feature,
        id,
        properties: {
          id,
          kind: "study",
          title,
          location: "ASF DAAC · NISAR GCOV",
          description: "Scene NISAR lấy từ ASF Search API. Đây là dữ liệu quan sát, chưa phải kết quả phân loại rừng ngập mặn.",
          browseUrl: browseUrl || undefined,
          browseCompositeUrl: browseCompositeUrl || undefined,
          browseHHHHUrl: browseHHHHUrl || undefined,
          browseHVHVUrl: browseHVHVUrl || undefined,
          nativeKmlUrl: nativeKmlUrl || undefined,
          sceneName: title,
          startTime: typeof raw.startTime === "string" ? raw.startTime : undefined,
          stopTime: typeof raw.stopTime === "string" ? raw.stopTime : undefined,
          processingLevel: typeof raw.processingLevel === "string" ? raw.processingLevel : "GCOV",
          collectionId: typeof raw.conceptID === "string" ? raw.conceptID : undefined,
          fileName: typeof raw.fileName === "string" ? raw.fileName.replace(/\.h5$/, "") : typeof raw.fileID === "string" ? raw.fileID : undefined,
        },
      };
    }),
  };
}

function imageCoordinates(feature: RegionFeature): [[number, number], [number, number], [number, number], [number, number]] | null {
  if (feature.geometry.type !== "Polygon") return null;
  const ring = feature.geometry.coordinates[0];
  if (!ring || ring.length < 4) return null;
  const points = ring.slice(0, -1);
  if (points.length === 4) {
    const withScore = points.map(([longitude, latitude]) => ({ longitude, latitude, score: longitude - latitude }));
    const topLeft = withScore.reduce((best, point) => point.score < best.score ? point : best);
    const bottomRight = withScore.reduce((best, point) => point.score > best.score ? point : best);
    const remaining = withScore.filter((point) => point !== topLeft && point !== bottomRight);
    const topRight = remaining[0].latitude >= remaining[1].latitude ? remaining[0] : remaining[1];
    const bottomLeft = remaining[0].latitude >= remaining[1].latitude ? remaining[1] : remaining[0];
    return [[topLeft.longitude, topLeft.latitude], [topRight.longitude, topRight.latitude], [bottomRight.longitude, bottomRight.latitude], [bottomLeft.longitude, bottomLeft.latitude]];
  }
  const xs = points.map(([longitude]) => longitude);
  const ys = points.map(([, latitude]) => latitude);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  return [[minX, maxY], [maxX, maxY], [maxX, minY], [minX, minY]];
}

function featureBounds(feature: RegionFeature | undefined): [[number, number], [number, number]] | null {
  if (!feature || feature.geometry.type !== "Polygon") return null;
  const ring = feature.geometry.coordinates[0];
  if (!ring?.length) return null;
  const longitudes = ring.map(([longitude]) => longitude);
  const latitudes = ring.map(([, latitude]) => latitude);
  return [[Math.min(...longitudes), Math.min(...latitudes)], [Math.max(...longitudes), Math.max(...latitudes)]];
}

type RasterImage = { url: string; coordinates: [[number, number], [number, number], [number, number], [number, number]] };
type PreviewAsset = { blob: Blob; coordinates: RasterImage["coordinates"] };

function browseProxyUrl(url: string, cacheKey?: string) {
  const endpoint = apiBaseUrl ? `${apiBaseUrl}/api/v1/earthdata/browse` : "/api/earthdata/browse";
  const suffix = cacheKey ? `&scene=${encodeURIComponent(cacheKey)}` : "";
  return `${endpoint}?url=${encodeURIComponent(url)}${suffix}`;
}

function kmlProxyUrl(url: string) {
  const endpoint = apiBaseUrl ? `${apiBaseUrl}/api/v1/earthdata/kml` : "/api/earthdata/kml";
  return `${endpoint}?url=${encodeURIComponent(url)}`;
}

function parseKmlImageCoordinates(kml: string): RasterImage["coordinates"] | null {
  const document = new DOMParser().parseFromString(kml, "application/xml");
  if (document.querySelector("parsererror")) return null;
  const coordinatesText = document.querySelector("LatLonQuad coordinates")?.textContent?.trim();
  if (!coordinatesText) return null;
  const points = coordinatesText
    .split(/\s+/)
    .map((value) => value.split(",").slice(0, 2).map(Number))
    .filter((point): point is [number, number] => point.length === 2 && point.every(Number.isFinite));
  if (points.length !== 4) return null;
  const withScore = points.map(([longitude, latitude]) => ({ longitude, latitude, score: longitude - latitude }));
  const topLeft = withScore.reduce((best, point) => point.score < best.score ? point : best);
  const bottomRight = withScore.reduce((best, point) => point.score > best.score ? point : best);
  const remaining = withScore.filter((point) => point !== topLeft && point !== bottomRight);
  const topRight = remaining[0].latitude >= remaining[1].latitude ? remaining[0] : remaining[1];
  const bottomLeft = remaining[0].latitude >= remaining[1].latitude ? remaining[1] : remaining[0];
  return [[topLeft.longitude, topLeft.latitude], [topRight.longitude, topRight.latitude], [bottomRight.longitude, bottomRight.latitude], [bottomLeft.longitude, bottomLeft.latitude]];
}

function setRasterImage(map: MapLibreMap, raster: RasterImage, opacity = 0.72) {
  const sourceId = "scene-image";
  const source = map.getSource(sourceId) as maplibregl.ImageSource | undefined;
  if (!source) {
    map.addSource(sourceId, { type: "image", url: raster.url, coordinates: raster.coordinates });
    map.addLayer({ id: sourceId, type: "raster", source: sourceId, paint: { "raster-opacity": opacity, "raster-fade-duration": 0 } }, "aoi-fill");
  } else {
    source.updateImage({ url: raster.url, coordinates: raster.coordinates });
    map.setPaintProperty(sourceId, "raster-opacity", opacity);
    map.setLayoutProperty(sourceId, "visibility", "visible");
  }
}

function setBrowseImage(map: MapLibreMap, raster: RasterImage, opacity = 0.72) {
  const sourceId = "scene-browse";
  const source = map.getSource(sourceId) as maplibregl.ImageSource | undefined;
  if (!source) {
    map.addSource(sourceId, { type: "image", url: raster.url, coordinates: raster.coordinates });
    map.addLayer({ id: sourceId, type: "raster", source: sourceId, paint: { "raster-opacity": opacity, "raster-fade-duration": 0 } }, "aoi-fill");
  } else {
    source.updateImage({ url: raster.url, coordinates: raster.coordinates });
    map.setPaintProperty(sourceId, "raster-opacity", opacity);
    map.setLayoutProperty(sourceId, "visibility", "visible");
  }
}

function replaceRasterImage(map: MapLibreMap, raster: RasterImage, objectUrlRef: { current: string | null }, opacity = 0.72) {
  const previousObjectUrl = objectUrlRef.current;
  setRasterImage(map, raster, opacity);
  if (previousObjectUrl && previousObjectUrl !== raster.url) URL.revokeObjectURL(previousObjectUrl);
  objectUrlRef.current = raster.url.startsWith("blob:") ? raster.url : null;
}

function gcovRequestKey(feature: RegionFeature, variable: "HHHH" | "HVHV") {
  const properties = feature.properties;
  return `${properties.collectionId ?? "C3622241360-ASF"}:${properties.fileName}:${variable}`;
}

function gcovPreviewKey(feature: RegionFeature, variable: "HHHH" | "HVHV", style: RasterStyle) {
  return `${gcovRequestKey(feature, variable)}:${style.mode}:${style.lowPercentile}:${style.highPercentile}`;
}

async function requestGcovPreview(feature: RegionFeature, variable: "HHHH" | "HVHV", style: RasterStyle, signal?: AbortSignal) {
  const properties = feature.properties;
  if (!properties.fileName) throw new Error("Scene has no HDF5 filename");
  const key = gcovPreviewKey(feature, variable, style);
  const cached = gcovPreviewCache.get(key);
  if (cached) return cached;
  const apiRoot = apiBaseUrl ? `${apiBaseUrl}/api/v1/earthdata/gcov` : "/api/earthdata/gcov";
  const request = (async () => {
    const query = new URLSearchParams({
      scene: properties.fileName as string,
      collection: properties.collectionId ?? "C3622241360-ASF",
      variable,
      mode: style.mode,
      low: String(style.lowPercentile * 100),
      high: String(style.highPercentile * 100),
    });
    const metadataResponse = await fetch(`${apiRoot}/preview?${query.toString()}`, { cache: "no-store", signal });
    if (!metadataResponse.ok) throw new Error(`GCOV preview failed: ${metadataResponse.status}`);
    const metadata = await metadataResponse.json() as { previewId?: string; coordinates?: RasterImage["coordinates"] };
    if (!metadata.previewId || !metadata.coordinates) throw new Error("GCOV preview has no georeference");
    const imageResponse = await fetch(`${apiRoot}/preview/file/${encodeURIComponent(metadata.previewId)}`, { cache: "force-cache", signal });
    if (!imageResponse.ok) throw new Error(`GCOV preview file failed: ${imageResponse.status}`);
    return { blob: await imageResponse.blob(), coordinates: metadata.coordinates };
  })();
  gcovPreviewCache.set(key, request);
  void request.catch(() => { if (gcovPreviewCache.get(key) === request) gcovPreviewCache.delete(key); });
  return request;
}

function percentile(values: number[], fraction: number) {
  if (!values.length) return 0;
  const sorted = [...values].sort((left, right) => left - right);
  return sorted[Math.min(sorted.length - 1, Math.max(0, Math.floor((sorted.length - 1) * fraction)))];
}

function applyLayerVisibility(map: MapLibreMap, layers: LayerState) {
  if (!map.isStyleLoaded()) return;
  map.setLayoutProperty("mangrove-fill", "visibility", layers.mangrove ? "visible" : "none");
  map.setLayoutProperty("mangrove-line", "visibility", layers.mangrove ? "visible" : "none");
  ["anomaly-fill", "anomaly-line", "anomaly-points"].forEach((layer) => map.setLayoutProperty(layer, "visibility", layers.anomalies ? "visible" : "none"));
  map.setLayoutProperty("selected-scene-line", "visibility", "visible");
  map.setLayoutProperty("aoi-fill", "visibility", layers.aoi ? "visible" : "none");
  map.setLayoutProperty("aoi-line", "visibility", layers.aoi ? "visible" : "none");
  if (map.getLayer("scene-image")) map.setLayoutProperty("scene-image", "visibility", layers.sceneImage ? "visible" : "none");
  if (map.getLayer("scene-browse")) map.setLayoutProperty("scene-browse", "visibility", layers.sceneImage ? "visible" : "none");
  map.setLayoutProperty("basemap", "visibility", layers.basemap ? "visible" : "none");
}

async function syncGcovImage(
  map: MapLibreMap,
  feature: RegionFeature | undefined,
  visible: boolean,
  variable: RadarBand,
  requestRef: { current: number },
  setStatus: (status: GcovStatus) => void,
  objectUrlRef: { current: string | null },
  style: RasterStyle,
  signal?: AbortSignal,
) {
  const sourceId = "scene-image";
  const requestId = ++requestRef.current;
  if (!visible || !feature?.properties?.fileName) {
    if (map.getLayer(sourceId)) map.setLayoutProperty(sourceId, "visibility", "none");
    if (map.getLayer("scene-browse")) map.setLayoutProperty("scene-browse", "visibility", "none");
    setStatus("idle");
    return;
  }
  const previewCoordinates = imageCoordinates(feature);
  const browseUrl = variable === "HVHV"
    ? feature.properties.browseHVHVUrl ?? feature.properties.browseUrl
    : variable === "HHHH"
      ? feature.properties.browseHHHHUrl ?? feature.properties.browseUrl
      : feature.properties.browseCompositeUrl ?? feature.properties.browseUrl;
  setStatus("loading");
  if (map.getLayer("scene-image")) map.setLayoutProperty("scene-image", "visibility", "none");
  if (!previewCoordinates || !browseUrl) {
    if (variable === "COMPOSITE") {
      setStatus("error");
      return;
    }
  } else {
    // Browse imagery is intentionally shown first. It is small and georeferenced
    // by the ASF KML, so the user gets an immediate visual while GCOV is decoded.
    setBrowseImage(map, { url: browseProxyUrl(browseUrl, `${feature.properties.id}-${variable}`), coordinates: previewCoordinates }, style.opacity);
    setStatus("preview");
  }
  const nativeKmlUrl = feature.properties.nativeKmlUrl;
  if (nativeKmlUrl && previewCoordinates && browseUrl) {
    void fetch(kmlProxyUrl(nativeKmlUrl), { cache: "force-cache", signal }).then(async (response) => response.ok ? parseKmlImageCoordinates(await response.text()) : null).then((coordinates) => {
      if (requestId !== requestRef.current || !coordinates || !browseUrl) return;
      setBrowseImage(map, { url: browseProxyUrl(browseUrl, `${feature.properties.id}-${variable}`), coordinates }, style.opacity);
    }).catch(() => undefined);
  }
  if (variable !== "COMPOSITE") {
    try {
      const preview = await requestGcovPreview(feature, variable, style, signal);
      if (requestId !== requestRef.current) {
        return;
      }
      const raster = { url: URL.createObjectURL(preview.blob), coordinates: preview.coordinates };
      replaceRasterImage(map, raster, objectUrlRef, style.opacity);
      if (map.getLayer("scene-image")) map.setLayoutProperty("scene-image", "visibility", "visible");
      setStatus("raster");
    } catch {
      // Keep the immediate ASF browse preview if extraction is slow or unavailable.
      if (requestId === requestRef.current && browseUrl) setStatus("preview");
    }
  }
}

async function syncGcovMetric(
  feature: RegionFeature | undefined,
  variable: RadarBand,
  requestRef: { current: number },
  setMetric: (state: RadarMetricState) => void,
) {
  const properties = feature?.properties;
  if (!feature || !properties?.fileName) {
    setMetric({ status: "idle" });
    return;
  }
  const requestId = ++requestRef.current;
  setMetric({ status: "loading", variable: variable === "COMPOSITE" ? undefined : variable });
  try {
    const bands: Array<"HHHH" | "HVHV"> = variable === "COMPOSITE" ? ["HHHH", "HVHV"] : [variable];
    const payload = await postAnalytics<{ series: Record<"HHHH" | "HVHV", { values: number[]; meanDb: number; medianDb?: number; p10Db?: number; p90Db?: number; validPixelCount?: number }> }>("analytics/profile", {
      scene: properties.fileName,
      collection: properties.collectionId ?? "C3622241360-ASF",
      bands,
      width: 96,
      height: 64,
    });
    if (requestId !== requestRef.current) return;
    const seriesMap = Object.fromEntries(Object.entries(payload.series).map(([band, item]) => [band, { variable: band as "HHHH" | "HVHV", ...item }])) as Partial<Record<"HHHH" | "HVHV", RadarSeries>>;
    const active = seriesMap[variable === "COMPOSITE" ? "HHHH" : variable];
    if (!active?.values.length) throw new Error("Radar profile is empty");
    setMetric({ status: "ready", variable: variable === "COMPOSITE" ? undefined : variable, metric: { ...active, series: seriesMap, source: "cached-geotiff" } });
  } catch {
    if (requestId === requestRef.current) setMetric({ status: "error", variable: variable === "COMPOSITE" ? undefined : variable });
  }
}

export default function Home() {
  const mapNode = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const selectedRef = useRef<string | null>(null);
  const regionsRef = useRef<FeatureCollection<Geometry, RegionProperties>>(demoGeoJson);
  const selectedIdRef = useRef("MNG-047");
  const layersRef = useRef<LayerState>(INITIAL_LAYERS);
  const fittedSceneIdRef = useRef<string | null>(null);
  const gcovRequestRef = useRef(0);
  const metricRequestRef = useRef(0);
  const gcovAbortRef = useRef<AbortController | null>(null);
  const rasterObjectUrlRef = useRef<string | null>(null);
  const [regions, setRegions] = useState<FeatureCollection<Geometry, RegionProperties>>(demoGeoJson);
  const [selectedId, setSelectedId] = useState("MNG-047");
  const [loading, setLoading] = useState(true);
  const [dataTruth, setDataTruth] = useState<DataTruth>({ catalogMode: "demo", assetMode: "unavailable", dataStatus: "unknown" });
  const [layers, setLayers] = useState<LayerState>(INITIAL_LAYERS);
  const [mobilePanelOpen, setMobilePanelOpen] = useState(false);
  const [gcovStatus, setGcovStatus] = useState<GcovStatus>("idle");
  const [radarBand, setRadarBand] = useState<RadarBand>("COMPOSITE");
  const [rasterStyle, setRasterStyle] = useState<RasterStyle>({ mode: "grayscale", opacity: 0.72, lowPercentile: .02, highPercentile: .98 });
  const [timelinePlaying, setTimelinePlaying] = useState(false);
  const [comparisonSceneSelection, setComparisonSceneSelection] = useState<string | undefined>(undefined);
  const [radarMetric, setRadarMetric] = useState<RadarMetricState>({ status: "idle" });
  const [comparison, setComparison] = useState<ComparisonState>({ status: "idle" });
  const [pixelInspection, setPixelInspection] = useState<PixelInspection | null>(null);
  const [regionStats, setRegionStats] = useState<RegionStatsState>({ status: "idle" });
  const [activeSection, setActiveSection] = useState<SidebarSection>("map");
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [copilotDockPosition, setCopilotDockPosition] = useState<{ left: number; top: number } | null>(null);
  const [undoStack, setUndoStack] = useState<UndoSnapshot[]>([]);
  const undoStackRef = useRef<UndoSnapshot[]>([]);
  const [sidebarWidth, setSidebarWidth] = useState(140);
  const [inspectorWidth, setInspectorWidth] = useState(365);
  const [isResizing, setIsResizing] = useState(false);
  const resizeRef = useRef<{ side: "sidebar" | "inspector"; startX: number; startWidth: number } | null>(null);
  const mapWorkspaceRef = useRef<HTMLDivElement | null>(null);
  const copilotDragRef = useRef<{
    startX: number;
    startY: number;
    startLeft: number;
    startTop: number;
    width: number;
    height: number;
  } | null>(null);

  const selectedFeature = useMemo<RegionFeature | undefined>(() => regions.features.find((feature) => feature.properties?.id === selectedId), [regions, selectedId]);
  const studyScenes = useMemo(
    () => regions.features
      .filter((feature): feature is RegionFeature => feature.properties?.kind === "study" && Boolean(feature.properties.id))
      .sort((left, right) => new Date(left.properties.startTime ?? 0).valueOf() - new Date(right.properties.startTime ?? 0).valueOf()),
    [regions],
  );
  const comparisonSceneId = useMemo(() => {
    if (comparisonSceneSelection && comparisonSceneSelection !== selectedId && studyScenes.some((scene) => scene.properties.id === comparisonSceneSelection)) return comparisonSceneSelection;
    const index = studyScenes.findIndex((scene) => scene.properties.id === selectedId);
    return studyScenes[index > 0 ? index - 1 : index + 1]?.properties.id;
  }, [studyScenes, selectedId, comparisonSceneSelection]);

  useEffect(() => { regionsRef.current = regions; }, [regions]);
  useEffect(() => { selectedIdRef.current = selectedId; }, [selectedId]);
  useEffect(() => { layersRef.current = layers; }, [layers]);
  useEffect(() => () => {
    if (rasterObjectUrlRef.current) URL.revokeObjectURL(rasterObjectUrlRef.current);
  }, []);

  useEffect(() => {
    let active = true;
    const endpoint = apiBaseUrl ? `${apiBaseUrl}/api/v1/earthdata/geojson` : "/api/earthdata/geojson";
    fetch(endpoint, { headers: { Accept: "application/geo+json, application/json" } })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Earthdata responded with ${response.status}`);
        return {
          data: normalizeEarthdataFeatures(await response.json()),
          truth: {
            catalogMode: (response.headers.get("X-TideAware-Catalog-Mode") ?? response.headers.get("X-TideAware-Data-Source") ?? "error") as CatalogMode,
            assetMode: (response.headers.get("X-TideAware-Asset-Mode") ?? "unavailable") as AssetMode,
            dataStatus: (response.headers.get("X-TideAware-Data-Status") ?? "unknown") as DataStatus,
          },
        };
      })
      .then(({ data, truth }) => {
        if (!active) return;
        setDataTruth(truth);
        if (!data || data.features.length === 0) return;
        setRegions(data);
        const first = data.features.find((feature) => feature.properties?.kind === "study") ?? data.features[0];
        if (first.properties?.id) setSelectedId(first.properties.id);
      })
      .catch(() => { if (active) setDataTruth({ catalogMode: "error", assetMode: "unavailable", dataStatus: "error" }); })
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (dataTruth.catalogMode !== "earthdata") return;
    if (gcovStatus === "raster") {
      setDataTruth((current) => ({ ...current, assetMode: "cached", dataStatus: "ready" }));
    } else if (gcovStatus === "preview") {
      setDataTruth((current) => ({ ...current, assetMode: "unavailable", dataStatus: "partial" }));
    }
  }, [dataTruth.catalogMode, gcovStatus]);

  useEffect(() => {
    if (!mapNode.current || mapRef.current) return;
    const map = new maplibregl.Map({ container: mapNode.current, style: mapStyle, center: [106.9, 10.53], zoom: 10.5, minZoom: 7, maxZoom: 16, attributionControl: false });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    mapRef.current = map;
    map.on("load", () => {
      map.addSource("aoi", { type: "geojson", data: studyAreaGeoJson });
      map.addLayer({ id: "aoi-fill", type: "fill", source: "aoi", paint: { "fill-color": "#f4b23b", "fill-opacity": 0.06 } });
      map.addLayer({ id: "aoi-line", type: "line", source: "aoi", paint: { "line-color": "#f4b23b", "line-width": 2.2, "line-opacity": 0.95 } });
      map.addSource("regions", { type: "geojson", data: demoGeoJson, promoteId: "id" });
      map.addSource("candidate-change", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({ id: "selected-scene-line", type: "line", source: "regions", filter: ["all", ["==", ["get", "kind"], "study"], ["==", ["get", "id"], selectedIdRef.current]], paint: { "line-color": "#ef5b4a", "line-width": 2.7, "line-opacity": 0.98 } });
      map.addLayer({ id: "mangrove-fill", type: "fill", source: "regions", filter: ["==", ["get", "kind"], "mangrove"], paint: { "fill-color": ["case", ["boolean", ["feature-state", "selected"], false], "#f4b23b", "#0cb6a7"], "fill-opacity": ["case", ["boolean", ["feature-state", "selected"], false], 0.58, 0.3] } });
      map.addLayer({ id: "mangrove-line", type: "line", source: "regions", filter: ["==", ["get", "kind"], "mangrove"], paint: { "line-color": ["case", ["boolean", ["feature-state", "selected"], false], "#ffd36b", "#26d6c7"], "line-width": ["case", ["boolean", ["feature-state", "selected"], false], 2.3, 1.1], "line-opacity": 0.92 } });
      map.addLayer({ id: "anomaly-fill", type: "fill", source: "regions", filter: ["==", ["get", "kind"], "anomaly"], paint: { "fill-color": "#ef6b5b", "fill-opacity": 0.13 } });
      map.addLayer({ id: "anomaly-line", type: "line", source: "regions", filter: ["==", ["get", "kind"], "anomaly"], paint: { "line-color": "#ef786b", "line-width": 2.4 } });
      map.addLayer({ id: "anomaly-points", type: "circle", source: "regions", filter: ["==", ["get", "kind"], "anomaly"], paint: { "circle-color": "#ef6b5b", "circle-radius": 5, "circle-stroke-color": "#ffc6bc", "circle-stroke-width": 1.5 } });
      map.addLayer({ id: "candidate-change-fill", type: "fill", source: "candidate-change", paint: { "fill-color": "#ed7f57", "fill-opacity": 0.25 } });
      map.addLayer({ id: "candidate-change-line", type: "line", source: "candidate-change", paint: { "line-color": "#d84f38", "line-width": 2.3, "line-dasharray": [2, 1] } });
      map.setLayoutProperty("candidate-change-fill", "visibility", "none");
      map.setLayoutProperty("candidate-change-line", "visibility", "none");
      applyLayerVisibility(map, layersRef.current);
      (map.getSource("regions") as maplibregl.GeoJSONSource).setData(regionsRef.current);
      map.setFeatureState({ source: "regions", id: selectedIdRef.current }, { selected: true });
      const initialScene = regionsRef.current.features.find((feature) => feature.properties?.id === selectedIdRef.current && feature.properties?.kind === "study") as RegionFeature | undefined;
      const initialBounds = featureBounds(initialScene);
      if (initialBounds) {
        map.fitBounds(initialBounds, { padding: { top: 88, right: 72, bottom: 72, left: 72 }, duration: 0, maxZoom: 9.8 });
      } else {
        map.fitBounds([[106.7603, 10.3686], [107.0276, 10.6807]], { padding: { top: 96, right: 72, bottom: 72, left: 72 }, duration: 0 });
      }
      void syncGcovImage(map, regionsRef.current.features.find((feature) => feature.properties?.id === selectedIdRef.current) as RegionFeature | undefined, false, radarBand, gcovRequestRef, setGcovStatus, rasterObjectUrlRef, rasterStyle);
      map.on("click", INTERACTIVE_LAYERS, (event: MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) => {
        const id = (event.features?.[0]?.properties as RegionProperties | undefined)?.id;
        if (!id) return;
        setSelectedId(id);
        setMobilePanelOpen(true);
      });
      map.on("click", async (event) => {
        const scene = regionsRef.current.features.find((feature) => feature.properties?.id === selectedIdRef.current && feature.properties?.kind === "study") as RegionFeature | undefined;
        if (!scene?.properties.fileName || event.defaultPrevented) return;
        try {
      const payload = await postAnalytics<PixelInspection>("analytics/pixel", { scene: scene.properties.fileName, collection: scene.properties.collectionId ?? "C3622241360-ASF", longitude: event.lngLat.lng, latitude: event.lngLat.lat });
          setPixelInspection(payload);
          setMobilePanelOpen(true);
        } catch {
          setPixelInspection(null);
        }
      });
      map.on("mouseenter", INTERACTIVE_LAYERS, () => { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", INTERACTIVE_LAYERS, () => { map.getCanvas().style.cursor = ""; });
    });
    return () => { map.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const source = map.getSource("regions") as maplibregl.GeoJSONSource | undefined;
    if (!source) return;
    source?.setData(regions);
    if (selectedRef.current) map.setFeatureState({ source: "regions", id: selectedRef.current }, { selected: false });
    map.setFeatureState({ source: "regions", id: selectedId }, { selected: true });
    if (map.getLayer("selected-scene-line")) {
      map.setFilter("selected-scene-line", ["all", ["==", ["get", "kind"], "study"], ["==", ["get", "id"], selectedId]]);
    }
    selectedRef.current = selectedId;
    const selectedScene = regions.features.find((feature) => feature.properties?.id === selectedId && feature.properties?.kind === "study") as RegionFeature | undefined;
    if (dataTruth.catalogMode === "earthdata" && selectedScene && fittedSceneIdRef.current !== selectedId) {
      const bounds = featureBounds(selectedScene);
      const fitScene = () => {
        if (fittedSceneIdRef.current === selectedId || !bounds) return;
        map.fitBounds(bounds, { padding: { top: 88, right: 72, bottom: 72, left: 72 }, duration: 500, maxZoom: 9.8 });
        fittedSceneIdRef.current = selectedId;
      };
      if (map.isStyleLoaded()) fitScene();
      else map.once("idle", fitScene);
    }
    gcovAbortRef.current?.abort();
    const controller = new AbortController();
    gcovAbortRef.current = controller;
    const timer = window.setTimeout(() => {
      const scene = regions.features.find((feature) => feature.properties?.id === selectedId) as RegionFeature | undefined;
      void syncGcovImage(map, scene, layers.sceneImage, radarBand, gcovRequestRef, setGcovStatus, rasterObjectUrlRef, rasterStyle, controller.signal);
      void syncGcovMetric(scene, radarBand, metricRequestRef, setRadarMetric);
    }, 220);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
      gcovRequestRef.current += 1;
      metricRequestRef.current += 1;
    };
  }, [regions, selectedId, dataTruth.catalogMode, layers.sceneImage, radarBand, rasterStyle]);

  useEffect(() => {
    const scene = regions.features.find((feature) => feature.properties?.id === selectedId && feature.properties?.kind === "study") as RegionFeature | undefined;
    if (!scene?.properties.fileName || gcovStatus !== "raster") {
      setRegionStats({ status: "idle" });
      return;
    }
    let active = true;
    setRegionStats({ status: "loading" });
    postAnalytics<{ statistics: Record<string, RegionStats> }>("analytics/region-stats", { scene: scene.properties.fileName, collection: scene.properties.collectionId ?? "C3622241360-ASF", bands: ["HHHH", "HVHV"], geometry: studyAreaGeoJson.features[0].geometry })
      .then((payload) => { if (active) setRegionStats({ status: "ready", statistics: payload.statistics }); })
      .catch(() => { if (active) setRegionStats({ status: "error" }); });
    return () => { active = false; };
  }, [regions, selectedId, gcovStatus]);

  useEffect(() => {
    if (!timelinePlaying || studyScenes.length < 2) return;
    const timer = window.setInterval(() => {
      setSelectedId((currentId) => {
        const currentIndex = studyScenes.findIndex((scene) => scene.properties.id === currentId);
        return studyScenes[(currentIndex + 1 + studyScenes.length) % studyScenes.length]?.properties.id ?? currentId;
      });
    }, 3200);
    return () => window.clearInterval(timer);
  }, [studyScenes, timelinePlaying]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    applyLayerVisibility(map, layers);
  }, [layers]);

  useEffect(() => {
    setComparison({ status: "idle" });
    const map = mapRef.current;
    if (map?.getLayer("candidate-change-fill")) map.setLayoutProperty("candidate-change-fill", "visibility", "none");
    if (map?.getLayer("candidate-change-line")) map.setLayoutProperty("candidate-change-line", "visibility", "none");
  }, [selectedId]);

  useEffect(() => {
    const clamp = (value: number, minimum: number, maximum: number) => Math.max(minimum, Math.min(maximum, value));
    const handlePointerMove = (event: PointerEvent) => {
      const copilotDrag = copilotDragRef.current;
      if (copilotDrag && mapWorkspaceRef.current) {
        const bounds = mapWorkspaceRef.current.getBoundingClientRect();
        const left = clamp(copilotDrag.startLeft + event.clientX - copilotDrag.startX, 8, Math.max(8, bounds.width - copilotDrag.width - 8));
        const top = clamp(copilotDrag.startTop + event.clientY - copilotDrag.startY, 8, Math.max(8, bounds.height - copilotDrag.height - 8));
        setCopilotDockPosition({ left, top });
        event.preventDefault();
        return;
      }
      const resize = resizeRef.current;
      if (!resize) return;
      event.preventDefault();
      if (resize.side === "sidebar") {
        setSidebarWidth(clamp(resize.startWidth + event.clientX - resize.startX, 112, 280));
      } else {
        const available = Math.max(300, window.innerWidth - sidebarWidth - 320);
        setInspectorWidth(clamp(resize.startWidth - event.clientX + resize.startX, 300, Math.min(520, available)));
      }
    };
    const finishResize = () => {
      if (copilotDragRef.current) {
        copilotDragRef.current = null;
        setIsResizing(false);
        return;
      }
      if (!resizeRef.current) return;
      resizeRef.current = null;
      setIsResizing(false);
    };
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", finishResize);
    window.addEventListener("pointercancel", finishResize);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", finishResize);
      window.removeEventListener("pointercancel", finishResize);
    };
  }, [sidebarWidth]);

  const startResize = (side: "sidebar" | "inspector", event: ReactPointerEvent<HTMLButtonElement>) => {
    if (window.innerWidth <= 820) return;
    resizeRef.current = { side, startX: event.clientX, startWidth: side === "sidebar" ? sidebarWidth : inspectorWidth };
    setIsResizing(true);
    event.preventDefault();
  };

  const startCopilotDrag = (event: ReactPointerEvent<HTMLElement>) => {
    if (window.innerWidth <= 820 || !mapWorkspaceRef.current) return;
    const element = event.currentTarget.closest(".copilot-dock") as HTMLElement | null;
    if (!element) return;
    const workspaceRect = mapWorkspaceRef.current.getBoundingClientRect();
    const elementRect = element.getBoundingClientRect();
    copilotDragRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      startLeft: elementRect.left - workspaceRect.left,
      startTop: elementRect.top - workspaceRect.top,
      width: elementRect.width,
      height: elementRect.height,
    };
    event.preventDefault();
  };

  const toggleLayer = (key: keyof typeof layers) => setLayers((current) => ({ ...current, [key]: !current[key] }));
  const rememberUndo = () => {
    const snapshot = { selectedId, layers, radarBand, activeSection, mobilePanelOpen };
    undoStackRef.current = [...undoStackRef.current, snapshot].slice(-20);
    setUndoStack(undoStackRef.current);
  };
  const handleUndo = () => {
    const previous = undoStackRef.current.at(-1);
    if (!previous) return;
    undoStackRef.current = undoStackRef.current.slice(0, -1);
    setUndoStack(undoStackRef.current);
    setSelectedId(previous.selectedId);
    setLayers(previous.layers);
    setRadarBand(previous.radarBand);
    setActiveSection(previous.activeSection);
    setMobilePanelOpen(previous.mobilePanelOpen);
  };
  const runComparison = async () => {
    const current = selectedFeature?.properties.fileName;
    const previous = studyScenes.find((scene) => scene.properties.id === comparisonSceneId)?.properties.fileName;
    if (!current || !previous || current === previous) return;
    const request = { scene_t1: previous, scene_t2: current, collection: selectedFeature.properties.collectionId ?? "C3622241360-ASF", bands: ["HHHH", "HVHV"], aoi: studyAreaGeoJson.features[0].geometry } as const;
    setComparison({ status: "checking" });
    try {
      const report = await postAnalytics<{ status: "COMPATIBLE" | "BLOCKED"; checks?: Array<{ name: string; status: string; detail?: string }>; blockingIssues?: string[] }>("comparisons/check", request);
      setComparison({ status: report.status === "COMPATIBLE" ? "queued" : "blocked", report });
      if (report.status !== "COMPATIBLE") return;
      const started = await postAnalytics<{ id: string }>("comparisons", request);
      setComparison({ status: "queued", id: started.id, report });
      for (let attempt = 0; attempt < 180; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 2000));
        const statusResponse = await fetch(analyticsUrl(`comparisons/${encodeURIComponent(started.id)}`), { cache: "no-store" });
        const status = await statusResponse.json() as { status: ComparisonState["status"]; candidate?: ComparisonState["candidate"]; error?: string; compatibility?: ComparisonState["report"] };
        if (status.status === "ready") {
          setComparison({ status: "ready", id: started.id, report, candidate: status.candidate });
          const map = mapRef.current;
          const source = map?.getSource("candidate-change") as maplibregl.GeoJSONSource | undefined;
          if (source && status.candidate) source.setData(status.candidate);
          if (map?.getLayer("candidate-change-fill")) map.setLayoutProperty("candidate-change-fill", "visibility", "visible");
          if (map?.getLayer("candidate-change-line")) map.setLayoutProperty("candidate-change-line", "visibility", "visible");
          return;
        }
        if (status.status === "blocked" || status.status === "error") {
          setComparison({ status: status.status, id: started.id, report: status.compatibility, error: status.error });
          return;
        }
        setComparison((currentState) => ({ ...currentState, status: "running", id: started.id }));
      }
      setComparison((currentState) => ({ ...currentState, status: "error", error: "Comparison timed out" }));
    } catch (error) {
      setComparison({ status: "error", error: error instanceof Error ? error.message : "Comparison failed" });
    }
  };
  const radarLayerStatus = gcovStatus === "loading" ? "(đang chuẩn bị preview…)" : gcovStatus === "raster" ? "(browse toàn cảnh + preview GeoTIFF cache)" : gcovStatus === "preview" ? "(browse toàn cảnh)" : gcovStatus === "error" ? "(không có ảnh)" : "";
  const analyticsSnapshot: CopilotAnalyticsSnapshot = {
    radarProfile: {
      status: radarMetric.status,
      activeBand: radarMetric.variable,
      series: radarMetric.metric?.series ?? (radarMetric.metric ? { [radarMetric.metric.variable]: radarMetric.metric } : {}),
      source: radarMetric.metric?.source,
    },
    regionStats: {
      status: regionStats.status,
      statistics: regionStats.statistics,
      source: regionStats.statistics ? "cached-geotiff" : undefined,
    },
    pixel: pixelInspection,
    raster: { status: gcovStatus, style: rasterStyle },
  };
  const copilotContext: CopilotContext = {
    // Use the ASF granule/file identifier for backend truth lookups. The
    // display title is presentation-only and may not match the granule name.
    sceneId: selectedFeature?.properties.fileName ?? selectedFeature?.properties.sceneName ?? selectedId,
    sceneDate: selectedFeature?.properties.startTime ?? null,
    band: radarBand,
    collectionId: selectedFeature?.properties.collectionId ?? "C3622241360-ASF",
    aoiId: "aoi-study",
    aoiHash: "sha256:502a9fd90c9cdb68b3a698dccecbd3f3eb234785e04709c62d8519ca3c00c4e0",
    layerState: { ...layers, radar: layers.sceneImage },
    timelineIndex: Math.max(0, studyScenes.findIndex((scene) => scene.properties.id === selectedId)),
    timelineCount: studyScenes.length,
    catalogMode: dataTruth.catalogMode,
    assetMode: dataTruth.assetMode,
    dataStatus: dataTruth.dataStatus,
    analytics: analyticsSnapshot,
    contextVersion: contextVersionFor({
      sceneId: selectedFeature?.properties.fileName ?? selectedFeature?.properties.sceneName ?? selectedId,
      sceneDate: selectedFeature?.properties.startTime ?? null,
      collectionId: selectedFeature?.properties.collectionId ?? "C3622241360-ASF",
      band: radarBand,
      aoiId: "aoi-study",
      aoiHash: "sha256:502a9fd90c9cdb68b3a698dccecbd3f3eb234785e04709c62d8519ca3c00c4e0",
      layerState: Object.fromEntries(Object.entries(layers).sort()),
      timelineIndex: Math.max(0, studyScenes.findIndex((scene) => scene.properties.id === selectedId)),
      timelineCount: studyScenes.length,
      catalogMode: dataTruth.catalogMode,
      assetMode: dataTruth.assetMode,
      dataStatus: dataTruth.dataStatus,
      rasterStyle,
      analytics: analyticsSnapshot,
    }),
  };
  const handleCopilotAction = (action: UiAction) => {
    switch (action.action) {
      case "set_radar_band":
        if (action.arguments.band === "HHHH" || action.arguments.band === "HVHV" || action.arguments.band === "COMPOSITE") {
          rememberUndo();
          setRadarBand(action.arguments.band);
        }
        break;
      case "toggle_layer": {
        const layer = action.arguments.layer;
        if (layer === "radar" || layer === "basemap" || layer === "aoi" || layer === "mangrove" || layer === "anomalies") {
          rememberUndo();
          toggleLayer(layer === "radar" ? "sceneImage" : layer);
        }
        break;
      }
      case "select_scene":
        if (typeof action.arguments.sceneId === "string" && studyScenes.some((scene) => scene.properties.id === action.arguments.sceneId)) {
          rememberUndo();
          setSelectedId(action.arguments.sceneId);
        }
        break;
      case "set_timeline_index":
        if (typeof action.arguments.index === "number" && studyScenes[action.arguments.index]) {
          rememberUndo();
          setSelectedId(studyScenes[action.arguments.index].properties.id);
        }
        break;
      case "open_region_stats":
      case "open_pixel_inspector":
        setMobilePanelOpen(true);
        break;
    }
  };

  return (
    <main className="app-shell">
      <Topbar loading={loading} dataTruth={dataTruth} />
      <div
        ref={mapWorkspaceRef}
        className={`workspace ${isResizing ? "is-resizing" : ""}`}
        style={{ "--sidebar-width": `${sidebarWidth}px`, "--inspector-width": `${inspectorWidth}px` } as CSSProperties}
      >
        <Sidebar activeSection={activeSection} onSelect={setActiveSection} onResizeStart={startResize} />
        <section className="map-workspace">
          <div ref={mapNode} className="map-canvas" aria-label="Bản đồ giám sát rừng ngập mặn" />
          <MapHeader />
          <SceneTimeline scenes={studyScenes} selectedId={selectedId} comparisonId={comparisonSceneId} comparison={comparison} playing={timelinePlaying} onSelect={(id) => { setSelectedId(id); setComparisonSceneSelection(undefined); }} onComparisonSelect={setComparisonSceneSelection} onRunComparison={runComparison} onTogglePlay={() => setTimelinePlaying((value) => !value)} />
          {activeSection === "map" ? <LayerLegend layers={layers} radarBand={radarBand} rasterStyle={rasterStyle} status={radarLayerStatus} onToggle={toggleLayer} onRadarBandChange={setRadarBand} onRasterStyleChange={setRasterStyle} /> : <DataLayersPanel layers={layers} radarBand={radarBand} status={radarLayerStatus} onToggle={toggleLayer} onRadarBandChange={setRadarBand} onClose={() => setActiveSection("map")} />}
          <ScaleBar />
        </section>
        <Inspector feature={selectedFeature} radarMetric={radarMetric} pixelInspection={pixelInspection} regionStats={regionStats} comparison={comparison} open={mobilePanelOpen} onClose={() => setMobilePanelOpen(false)} onResizeStart={startResize} />
        <button className="mobile-panel-trigger" onClick={() => setMobilePanelOpen(true)}><Icon name="menu" /> Chi tiết khu vực</button>
        <div className="copilot-dock" style={copilotDockPosition ? { left: copilotDockPosition.left, top: copilotDockPosition.top, right: "auto", bottom: "auto" } : undefined}>
          <button type="button" className="copilot-bubble" aria-label="Mở GalaSEE Assistant" onPointerDown={startCopilotDrag} onClick={() => setCopilotOpen(true)}><Image src={chatbotLogo} alt="" aria-hidden="true" priority /></button>
          <CopilotPanel open={copilotOpen} context={copilotContext} onPanelDragStart={startCopilotDrag} onClose={() => setCopilotOpen(false)} onAction={handleCopilotAction} onUndo={handleUndo} canUndo={undoStack.length > 0} />
        </div>
      </div>
    </main>
  );
}

function Topbar({ loading, dataTruth }: { loading: boolean; dataTruth: DataTruth }) {
  const status = loading
    ? "Đang đồng bộ"
    : dataTruth.catalogMode === "error"
      ? "Nguồn dữ liệu lỗi"
      : dataTruth.catalogMode === "demo"
        ? "Dữ liệu mô phỏng"
        : dataTruth.assetMode === "cached"
          ? "Earthdata · cache sẵn"
          : "Earthdata live";

  return (
    <header className="topbar">
      <div className="brand-lockup">
        <div className="brand-mark" aria-hidden="true"><span /></div>
        <div><strong>TideAware</strong><span>Giám sát rừng ngập mặn ven biển</span></div>
      </div>
      <div className="topbar-actions">
        <span className="sync-status"><span className="status-dot" /> {status}</span>
        <span className="updated">Cập nhật: 14/11/2026 · 08:42 (UTC+7)</span>
        <button className="icon-button" aria-label="Thông báo"><Icon name="bell" /></button>
        <button className="team-button"><span className="avatar">BT</span><span>Đội bảo tồn</span><span className="caret">⌄</span></button>
      </div>
    </header>
  );
}

function Sidebar({ activeSection, onSelect, onResizeStart }: { activeSection: SidebarSection; onSelect: (section: SidebarSection) => void; onResizeStart: (side: "sidebar" | "inspector", event: ReactPointerEvent<HTMLButtonElement>) => void }) {
  return (
    <aside className="sidebar">
      <div className="side-nav">
        <button className={`nav-item ${activeSection === "map" ? "active" : ""}`} onClick={() => onSelect("map")}><Icon name="map" /><span>Bản đồ</span></button>
        <button className={`nav-item ${activeSection === "layers" ? "active" : ""}`} onClick={() => onSelect("layers")}><Icon name="layers" /><span>Lớp dữ liệu</span></button>
        <button className="nav-item"><Icon name="anomaly" /><span>Bất thường</span><span className="nav-count">08</span></button>
        <button className="nav-item"><Icon name="focus" /><span>Khu vực nghiên cứu</span></button>
        <button className="nav-item"><Icon name="download" /><span>Xuất dữ liệu</span></button>
      </div>
      <div className="side-bottom"><button className="nav-item"><Icon name="settings" /><span>Cài đặt</span></button></div>
      <PanelResizeHandle side="sidebar" onPointerDown={(event) => onResizeStart("sidebar", event)} />
    </aside>
  );
}

function DataLayersPanel({
  layers,
  radarBand,
  status,
  onToggle,
  onRadarBandChange,
  onClose,
}: {
  layers: LayerState;
  radarBand: RadarBand;
  status: string;
  onToggle: (key: keyof LayerState) => void;
  onRadarBandChange: (variable: RadarBand) => void;
  onClose: () => void;
}) {
  const radarLabel = radarBand === "COMPOSITE" ? "RGB composite" : radarBand;
  return (
    <section className="data-layers-panel map-overlay" aria-label="Các lớp dữ liệu">
      <div className="data-layers-head">
        <div><span className="panel-kicker">QUẢN LÝ HIỂN THỊ</span><h2>Lớp dữ liệu</h2></div>
        <button className="icon-button" aria-label="Đóng lớp dữ liệu" onClick={onClose}><Icon name="close" /></button>
      </div>
      <p className="data-layers-intro">Mỗi lớp trả lời một câu hỏi khác nhau: ảnh radar cho biết vệ tinh quan sát gì, còn các lớp phân tích cho biết hệ thống diễn giải quan sát đó ra sao.</p>
      <div className="data-layer-group">
        <span className="data-layer-group-title">DỮ LIỆU QUAN SÁT</span>
        <div className="data-layer-card">
          <LayerToggle checked={layers.sceneImage} onChange={() => onToggle("sceneImage")} swatch="legend-swatch swatch-radar">Ảnh radar NISAR · {radarLabel} {status}</LayerToggle>
          <div className="layer-explanation">
            <p><b>Ý nghĩa:</b> browse ASF toàn cảnh được hiển thị ngay; preview PNG được tạo từ GeoTIFF thật ở backend rồi phủ lên AOI sau khi cache xong.</p>
            <p><b>Cách đọc:</b> vùng sáng/tối là khác biệt về phản xạ; không nên đọc trực tiếp như ảnh màu tự nhiên.</p>
            <p><b>Nguồn:</b> NISAR L2 GCOV từ ASF DAAC. Đây là ảnh browse để quan sát nhanh, không thay thế giá trị đo trong HDF5.</p>
          </div>
          <div className="radar-band-picker panel-band-picker">
            <button type="button" className={radarBand === "COMPOSITE" ? "active" : ""} onClick={() => onRadarBandChange("COMPOSITE")}>RGB</button>
            <button type="button" className={radarBand === "HHHH" ? "active" : ""} onClick={() => onRadarBandChange("HHHH")}>HHHH</button>
            <button type="button" className={radarBand === "HVHV" ? "active" : ""} onClick={() => onRadarBandChange("HVHV")}>HVHV</button>
          </div>
        </div>
        <div className="data-layer-card">
          <LayerToggle checked={layers.basemap} onChange={() => onToggle("basemap")} swatch="legend-swatch swatch-basemap">Bản đồ nền</LayerToggle>
          <div className="layer-explanation">
            <p><b>Ý nghĩa:</b> nền địa lý giúp định hướng sông, bờ biển và khu vực xung quanh.</p>
            <p><b>Lưu ý:</b> không phải dữ liệu NISAR và không được dùng để kết luận rừng ngập mặn hay bất thường.</p>
            <p><b>Nguồn:</b> NASA GIBS Blue Marble.</p>
          </div>
        </div>
      </div>
      <div className="data-layer-group">
        <span className="data-layer-group-title">LỚP PHÂN TÍCH</span>
        <div className="data-layer-card">
          <LayerToggle checked={layers.aoi} onChange={() => onToggle("aoi")} swatch="legend-outline swatch-aoi">AOI nghiên cứu</LayerToggle>
          <div className="layer-explanation">
            <p><b>Ý nghĩa:</b> đường biên của khu vực Cửa Dinh – Cồn Ba Lá được dùng để tập trung quan sát.</p>
            <p><b>Cách đọc:</b> chỉ là ranh giới phạm vi nghiên cứu, không phải kết quả phân loại phủ bề mặt.</p>
          </div>
        </div>
        <div className="data-layer-card is-disabled">
          <LayerToggle checked={layers.mangrove} onChange={() => onToggle("mangrove")} swatch="legend-swatch swatch-mangrove">Rừng ngập mặn</LayerToggle>
          <div className="layer-explanation"><p><b>Ý nghĩa dự kiến:</b> mask các pixel được mô hình xác định là rừng ngập mặn.</p><p><b>Trạng thái:</b> chưa có model phân loại đã xác nhận nên hiện đang tắt.</p></div>
        </div>
        <div className="data-layer-card is-disabled">
          <LayerToggle checked={layers.anomalies} onChange={() => onToggle("anomalies")} swatch="legend-dot swatch-anomaly">Bất thường</LayerToggle>
          <div className="layer-explanation"><p><b>Ý nghĩa dự kiến:</b> vùng hoặc điểm có thay đổi tín hiệu đáng chú ý giữa các scene.</p><p><b>Trạng thái:</b> chưa có model phát hiện bất thường nên hiện đang tắt.</p></div>
        </div>
      </div>
    </section>
  );
}

function MapHeader() {
  return <div className="map-overlay map-header-control"><span className="select-label">KHU VỰC NGHIÊN CỨU</span><button className="area-select">Cửa Dinh – Cồn Ba Lá <span>⌄</span></button></div>;
}

function SceneTimeline({
  scenes,
  selectedId,
  comparisonId,
  comparison,
  playing,
  onSelect,
  onComparisonSelect,
  onRunComparison,
  onTogglePlay,
}: {
  scenes: RegionFeature[];
  selectedId: string;
  comparisonId?: string;
  comparison: ComparisonState;
  playing: boolean;
  onSelect: (id: string) => void;
  onComparisonSelect: (id: string) => void;
  onRunComparison: () => void;
  onTogglePlay: () => void;
}) {
  if (scenes.length === 0) return null;
  const selectedIndex = Math.max(0, scenes.findIndex((scene) => scene.properties.id === selectedId));
  const selectedScene = scenes[selectedIndex];
  const selectRelative = (offset: number) => {
    const nextIndex = (selectedIndex + offset + scenes.length) % scenes.length;
    onSelect(scenes[nextIndex].properties.id);
  };
  return (
    <div className="timeline-control map-overlay">
      <div className="timeline-head">
        <div>
          <span className="timeline-kicker">DÒNG THỜI GIAN QUAN SÁT</span>
          <strong>{formatSceneDate(selectedScene.properties.startTime)}</strong>
        </div>
        <span className="timeline-count">Scene {selectedIndex + 1} / {scenes.length}</span>
      </div>
      <div className="timeline-actions">
        <button type="button" aria-label="Scene trước" onClick={() => selectRelative(-1)}>‹</button>
        <button type="button" className="timeline-play" aria-label={playing ? "Tạm dừng timeline" : "Phát timeline"} onClick={onTogglePlay}>{playing ? "Ⅱ" : "▶"}</button>
        <button type="button" aria-label="Scene sau" onClick={() => selectRelative(1)}>›</button>
      </div>
      <input
        className="timeline-range"
        type="range"
        min="0"
        max={scenes.length - 1}
        step="1"
        value={selectedIndex}
        aria-label="Chọn scene theo thời gian"
        onChange={(event) => onSelect(scenes[Number(event.target.value)].properties.id)}
      />
      <div className="timeline-ticks" style={{ gridTemplateColumns: `repeat(${scenes.length}, 1fr)` }} aria-hidden="true">
        {scenes.map((scene, index) => <span key={scene.properties.id} className={index === selectedIndex ? "active" : ""} title={formatSceneDate(scene.properties.startTime)} />)}
      </div>
      <div className="timeline-endpoints"><span>{formatSceneDate(scenes[0].properties.startTime)}</span><span>{formatSceneDate(scenes[scenes.length - 1].properties.startTime)}</span></div>
      {scenes.length > 1 && <div className="comparison-controls">
        <label><span>So sánh với</span><select value={comparisonId ?? ""} onChange={(event) => onComparisonSelect(event.target.value)}>{scenes.filter((scene) => scene.properties.id !== selectedId).map((scene) => <option key={scene.properties.id} value={scene.properties.id}>{formatSceneDate(scene.properties.startTime)} · {sceneShortId(scene.properties)}</option>)}</select></label>
        <button type="button" className="comparison-button" disabled={!comparisonId || ["checking", "queued", "running"].includes(comparison.status)} onClick={onRunComparison}>{comparison.status === "checking" || comparison.status === "queued" || comparison.status === "running" ? "Đang phân tích…" : "So sánh"}</button>
        {comparison.status === "blocked" && <p className="comparison-warning">Bị khóa: {(comparison.report?.blockingIssues ?? []).join(", ") || "metadata chưa tương thích"}.</p>}
        {comparison.status === "ready" && <p className="comparison-success">Candidate change đã sẵn sàng · cần kiểm chứng.</p>}
      </div>}
    </div>
  );
}

function LayerLegend({
  layers,
  radarBand,
  rasterStyle,
  status,
  onToggle,
  onRadarBandChange,
  onRasterStyleChange,
}: {
  layers: LayerState;
  radarBand: RadarBand;
  rasterStyle: RasterStyle;
  status: string;
  onToggle: (key: keyof LayerState) => void;
  onRadarBandChange: (variable: RadarBand) => void;
  onRasterStyleChange: (style: RasterStyle) => void;
}) {
  const radarLabel = radarBand === "COMPOSITE" ? "RGB composite" : radarBand;
  return (
    <div className="layer-legend map-overlay">
      <div className="legend-title">Lớp bản đồ</div>
      <LayerToggle checked={layers.mangrove} onChange={() => onToggle("mangrove")} swatch="legend-swatch swatch-mangrove">Rừng ngập mặn</LayerToggle>
      <LayerToggle checked={layers.anomalies} onChange={() => onToggle("anomalies")} swatch="legend-dot swatch-anomaly">Bất thường</LayerToggle>
      <LayerToggle checked={layers.aoi} onChange={() => onToggle("aoi")} swatch="legend-outline swatch-aoi">AOI nghiên cứu</LayerToggle>
      <LayerToggle checked={layers.sceneImage} onChange={() => onToggle("sceneImage")} swatch="legend-swatch swatch-radar">Ảnh radar NISAR · {radarLabel} {status}</LayerToggle>
      <div className="radar-band-picker">
        <button type="button" className={radarBand === "COMPOSITE" ? "active" : ""} onClick={() => onRadarBandChange("COMPOSITE")}>RGB</button>
        <button type="button" className={radarBand === "HHHH" ? "active" : ""} onClick={() => onRadarBandChange("HHHH")}>HHHH</button>
        <button type="button" className={radarBand === "HVHV" ? "active" : ""} onClick={() => onRadarBandChange("HVHV")}>HVHV</button>
      </div>
      {layers.sceneImage && <div className="raster-style-controls"><label>Hiển thị <select value={rasterStyle.mode} onChange={(event) => onRasterStyleChange({ ...rasterStyle, mode: event.target.value as RasterStyle["mode"] })}><option value="grayscale">Grayscale</option><option value="heatmap">Heatmap</option></select></label><label>Opacity <input type="range" min="0.2" max="1" step="0.05" value={rasterStyle.opacity} onChange={(event) => onRasterStyleChange({ ...rasterStyle, opacity: Number(event.target.value) })} /></label><small>P{Math.round(rasterStyle.lowPercentile * 100)}–P{Math.round(rasterStyle.highPercentile * 100)} stretch · dB</small></div>}
      <LayerToggle checked={layers.basemap} onChange={() => onToggle("basemap")} swatch="legend-swatch swatch-basemap">Bản đồ nền</LayerToggle>
      <div className="legend-divider" />
      <div className="legend-title">Chú giải</div>
      <div className="key-row"><i className="legend-swatch swatch-mangrove" />Rừng ngập mặn</div>
      <div className="key-row"><i className="legend-swatch swatch-selected" />Khu vực đang chọn</div>
      <div className="key-row"><i className="legend-swatch swatch-anomaly-area" />Vùng bất thường</div>
      <div className="key-row"><i className="legend-dot swatch-anomaly" />Điểm bất thường</div>
      <div className="key-row"><i className="legend-outline swatch-candidate" />Candidate change · cần kiểm chứng</div>
      <div className="key-row"><i className="legend-outline swatch-selected-scene" />Scene đang chọn</div>
      <div className="key-row"><i className="legend-outline swatch-aoi" />AOI nghiên cứu</div>
    </div>
  );
}

function LayerToggle({ checked, onChange, swatch, children }: { checked: boolean; onChange: () => void; swatch: string; children: ReactNode }) {
  return <label><input type="checkbox" checked={checked} onChange={onChange} /><span className="checkmark">✓</span><i className={swatch} />{children}</label>;
}

function ScaleBar() {
  return <><div className="scale-bar map-overlay"><div><span /><span /><span /><span /></div><p><b>0</b><b>2,5</b><b>5 km</b></p></div><div className="map-brand">NASA GIBS · Earthdata</div></>;
}

function Inspector({ feature, radarMetric, pixelInspection, regionStats, comparison, open, onClose, onResizeStart }: { feature?: RegionFeature; radarMetric: RadarMetricState; pixelInspection: PixelInspection | null; regionStats: RegionStatsState; comparison: ComparisonState; open: boolean; onClose: () => void; onResizeStart: (side: "sidebar" | "inspector", event: ReactPointerEvent<HTMLButtonElement>) => void }) {
  return (
    <aside className={`inspector ${open ? "mobile-open" : ""}`}>
      <PanelResizeHandle side="inspector" onPointerDown={(event) => onResizeStart("inspector", event)} />
      <div className="inspector-head">
        <div><span className="panel-kicker">KHU VỰC ĐANG CHỌN</span><h1>Chi tiết khu vực</h1></div>
        <button className="icon-button close-panel" aria-label="Đóng chi tiết" onClick={onClose}><Icon name="close" /></button>
      </div>
      {feature ? <RegionDetails feature={feature} radarMetric={radarMetric} pixelInspection={pixelInspection} regionStats={regionStats} comparison={comparison} /> : <div className="empty-detail">Chọn một vùng trên bản đồ để xem thông tin.</div>}
    </aside>
  );
}

function PanelResizeHandle({ side, onPointerDown }: { side: "sidebar" | "inspector"; onPointerDown: (event: ReactPointerEvent<HTMLButtonElement>) => void }) {
  return <button type="button" className={`panel-resize-handle ${side}`} aria-label={side === "sidebar" ? "Kéo để đổi độ rộng thanh bên trái" : "Kéo để đổi độ rộng bảng chi tiết"} onPointerDown={onPointerDown}><span aria-hidden="true" /></button>;
}

function RegionDetails({ feature, radarMetric, pixelInspection, regionStats, comparison }: { feature: RegionFeature; radarMetric: RadarMetricState; pixelInspection: PixelInspection | null; regionStats: RegionStatsState; comparison: ComparisonState }) {
  const details = feature.properties;
  const isAnomaly = details.kind === "anomaly";
  const label = details.kind === "mangrove" ? "Rừng ngập mặn" : isAnomaly ? "Vùng bất thường" : "Scene NISAR";
  const status = isAnomaly ? "Bất thường" : details.kind === "study" ? "Đã đồng bộ" : "Ổn định";
  return (
    <div className="detail-content">
      <div className="selected-preview">
        <div className={`preview-shape ${isAnomaly ? "anomaly-preview" : ""}`}><span /></div>
        <div className="selected-preview-copy">
          <span className="preview-eyebrow">{details.kind === "study" ? "NISAR · GCOV" : "KHU VỰC"}</span>
          <h2>{sceneDisplayTitle(details)}</h2>
          <p>{label}{details.kind === "study" ? ` · ${sceneShortId(details)}` : ""}</p>
        </div>
      </div>

      <div className="detail-grid">
        <div><span>Vị trí</span><strong>{sceneDisplayTitle(details)}</strong><b>{details.kind === "study" ? "ASF DAAC · NISAR GCOV" : "Khu vực nghiên cứu"}</b></div>
        <div><span>Diện tích</span><strong>{formatNumber(details.areaHa, " ha")}</strong></div>
        <div><span>Độ tin cậy</span><strong className="accent">{details.confidence ? `${Math.round(details.confidence * 100)}%` : "—"}</strong></div>
      </div>

      {details.kind === "study" && (
        <div className="scene-meta">
          <div><span>Thu nhận</span><strong>{formatSceneTimestamp(details.startTime)}</strong></div>
          <div><span>Mã cảnh</span><strong>{sceneShortId(details)}</strong></div>
          <div><span>Mức xử lý</span><strong>{details.processingLevel ?? "GCOV"}</strong></div>
        </div>
      )}

      <div className="detail-rule" />
      <section className="status-section">
        <div className="section-title"><h3>Tình trạng</h3><span className={`status-tag ${isAnomaly ? "danger" : "good"}`}>{status}</span></div>
        <p>{details.description}</p>
      </section>

      <MetricSection title={`Tín hiệu radar${radarMetric.metric?.series && Object.keys(radarMetric.metric.series).length > 1 ? " · HH/HV" : radarMetric.variable ? ` · ${radarMetric.variable}` : ""}`} value={radarMetric.status === "loading" ? "Đang đọc…" : radarMetric.metric ? `${radarMetric.metric.meanDb.toFixed(1)} dB` : "Chưa có dữ liệu"}>
        <RadarSparkline metric={radarMetric.metric} status={radarMetric.status} />
      </MetricSection>
      {pixelInspection && <section className="pixel-inspection"><div className="metric-title"><h3>Pixel đang xem</h3><span>{pixelInspection.coordinate.longitude.toFixed(5)}, {pixelInspection.coordinate.latitude.toFixed(5)}</span></div><div className="pixel-values">{Object.entries(pixelInspection.values).map(([band, value]) => <div key={band}><span>{band}</span><b>{value.valid && value.db !== null ? `${value.db.toFixed(2)} dB` : "Không có dữ liệu"}</b></div>)}</div><small>Mask: {pixelInspection.mask.valid ? "hợp lệ" : "nodata"} · {pixelInspection.source}</small></section>}
      {regionStats.status !== "idle" && <section className="region-stats"><div className="metric-title"><h3>Thống kê trong AOI</h3><span>{regionStats.status === "loading" ? "Đang tính…" : regionStats.status === "error" ? "Không đọc được" : "GeoTIFF cache"}</span></div>{regionStats.statistics && Object.entries(regionStats.statistics).map(([band, stats]) => <div className="stats-band" key={band}><b>{band}</b><span>Coverage {stats.validCoveragePercent.toFixed(1)}%</span><span>Median {(stats.medianDb ?? 0).toFixed(2)} dB</span><span>Diện tích hợp lệ {(stats.validAreaHa ?? 0).toFixed(2)} ha</span><span>P10/P90 {(stats.p10Db ?? 0).toFixed(1)} / {(stats.p90Db ?? 0).toFixed(1)} dB</span><div className="stats-histogram" aria-label={`Histogram ${band}`}>{(stats.histogram?.counts ?? []).map((count, index) => <i key={`${band}-${index}`} style={{ height: `${Math.max(4, Math.min(100, count / Math.max(...(stats.histogram?.counts ?? [1])) * 100))}%` }} />)}</div></div>)}</section>}
      {comparison.status === "ready" && <section className="candidate-note"><b>Candidate change</b><p>Vùng vượt ngưỡng sàng lọc 3 dB. Đây chưa phải kết luận mất rừng hay bất thường đã xác nhận.</p></section>}
      <MetricSection title="Mực triều" value={details.tideM ? `Hiện tại: ${details.tideM} m` : "Chưa có dữ liệu"} className="tide-section">
        <TideSparkline />
      </MetricSection>

      <button className="field-action"><Icon name="focus" size={16} /> Mở phiếu kiểm tra thực địa <span>↗</span></button>
    </div>
  );
}

function MetricSection({ title, value, className = "", children }: { title: string; value: string; className?: string; children: ReactNode }) {
  return (
    <section className={`metric-section ${className}`}>
      <div className="metric-title"><h3>{title}</h3><span className="info-dot">i</span><strong>{value}</strong></div>
      {children}
    </section>
  );
}

function RadarSparkline({ metric, status }: { metric?: RadarMetric; status: RadarMetricState["status"] }) {
  if (!metric?.values.length) return <div className="chart-empty">{status === "loading" ? "Đang đọc giá trị thật từ GCOV…" : "Chưa có chuỗi số liệu radar cho scene này."}</div>;
  const series = metric.series && Object.values(metric.series).filter((item): item is RadarSeries => Boolean(item?.values.length));
  const plottedSeries = series && series.length > 1 ? series : [{ variable: metric.variable, values: metric.values, meanDb: metric.meanDb } as RadarSeries];
  const allValues = plottedSeries.flatMap((item) => item.values);
  const minimum = Math.min(...allValues);
  const maximum = Math.max(...allValues);
  const range = maximum - minimum || 1;
  const chartLeft = 12;
  const chartWidth = 336;
  const chartTop = 15;
  const chartHeight = 106;
  const makePath = (values: number[]) => values.map((value, index) => {
    const x = chartLeft + (index / Math.max(values.length - 1, 1)) * chartWidth;
    const y = chartTop + ((maximum - value) / range) * chartHeight;
    return `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
  return (
    <div className="radar-chart-card">
      <div className="radar-chart-caption">
        <span>{plottedSeries.length > 1 ? "HH/HV profile · dB" : `Backscatter ${metric.variable}`}</span>
        <span>{plottedSeries.map((item) => `${item.variable}: ${item.values.length}`).join(" · ")} cột ảnh</span>
      </div>
      <div className="radar-plot-shell">
        <div className="radar-y-labels" aria-hidden="true"><span>{maximum.toFixed(1)}</span><span>{(maximum - range / 2).toFixed(1)}</span><span>{minimum.toFixed(1)}</span></div>
        <svg className="sparkline radar-chart" viewBox="0 0 360 136" preserveAspectRatio="none" role="img" aria-label={`Biểu đồ backscatter ${metric.variable} theo vị trí trong ảnh`}>
          <defs><linearGradient id="radar-area-gradient" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#0b9d91" stopOpacity=".22" /><stop offset="100%" stopColor="#0b9d91" stopOpacity=".02" /></linearGradient></defs>
          <path className="spark-grid" d="M12 15H348M12 68H348M12 121H348M12 15V121M96 15V121M180 15V121M264 15V121M348 15V121" />
          {plottedSeries.map((item, index) => {
            const path = makePath(item.values);
            const color = index === 0 ? "#0b9d91" : "#e98b45";
            return <g key={item.variable}><path className="radar-mean" stroke={color} strokeDasharray="4 4" d={`M12 ${(chartTop + ((maximum - item.meanDb) / range) * chartHeight).toFixed(1)}H348`} /><path className={index === 0 ? "radar-area" : "radar-area radar-area-secondary"} fill={color} d={`${path} L348 121 L12 121 Z`} /><path className="spark-path" stroke={color} d={path} /><circle cx="12" cy={Number((chartTop + ((maximum - item.values[0]) / range) * chartHeight).toFixed(1))} r="3" fill={color} className="radar-point" /><circle cx="348" cy={Number((chartTop + ((maximum - item.values[item.values.length - 1]) / range) * chartHeight).toFixed(1))} r="3" fill={color} className="radar-point" /></g>;
          })}
        </svg>
      </div>
      <div className="radar-axis-labels"><span>Vị trí tương đối trong ảnh · 0%</span><span>100%</span></div>
      <div className="radar-stats"><span>P10 <b>{(plottedSeries[0].p10Db ?? minimum).toFixed(1)} dB</b></span><span>Median <b>{(plottedSeries[0].medianDb ?? plottedSeries[0].meanDb).toFixed(1)} dB</b></span><span>P90 <b>{(plottedSeries[0].p90Db ?? maximum).toFixed(1)} dB</b></span></div>
      {plottedSeries.length > 1 && <div className="radar-series-legend"><span><i className="series-dot hh" /> HHHH</span><span><i className="series-dot hv" /> HVHV</span></div>}
      <p className="chart-note">Mỗi điểm là trung bình theo một cột ảnh. Giá trị phân tích lấy từ GeoTIFF cache; RGB chỉ là cách hiển thị, không phải một band mới.</p>
    </div>
  );
}

function TideSparkline() {
  return (
    <svg className="sparkline tide-chart" viewBox="0 0 340 118" preserveAspectRatio="none" aria-label="Biểu đồ mực triều">
      <path className="spark-grid" d="M0 18H340M0 50H340M0 82H340M0 114H340M0 18V114M85 18V114M170 18V114M255 18V114M340 18V114" />
      <path className="tide-area" d="M0 78 C42 24 82 24 126 68 S214 105 256 64 S314 28 340 40 V118 H0 Z" />
      <path className="tide-path" d="M0 78 C42 24 82 24 126 68 S214 105 256 64 S314 28 340 40" />
      <circle cx="340" cy="40" r="5" className="tide-point" />
    </svg>
  );
}
