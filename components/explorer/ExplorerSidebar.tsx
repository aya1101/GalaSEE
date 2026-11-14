"use client";

import type { PointerEvent as ReactPointerEvent } from "react";

export type ExplorerSceneSummary = {
  id: string;
  title: string;
  dataMode: "earthdata" | "cached" | "demo" | "error";
  assetMode: "live" | "cached" | "unavailable";
  dataStatus: "ready" | "partial" | "unknown" | "error";
};

export type ExplorerSidebarProps = {
  scene?: ExplorerSceneSummary;
  layerState: Record<string, boolean>;
  onLayerChange: (layer: string) => void;
  activeSection: "map" | "layers";
  onSectionChange: (section: "map" | "layers") => void;
  onResizeStart: (side: "sidebar", event: ReactPointerEvent<HTMLButtonElement>) => void;
};

function sourceLabel(scene?: ExplorerSceneSummary) {
  if (!scene || scene.dataMode === "earthdata") return "Earthdata live";
  if (scene.dataMode === "cached" || scene.assetMode === "cached") return "Earthdata · cache sẵn";
  if (scene.dataMode === "demo") return "Dữ liệu mô phỏng";
  return "Nguồn dữ liệu lỗi";
}

export function ExplorerSidebar({ scene, layerState, onLayerChange, activeSection, onSectionChange, onResizeStart }: ExplorerSidebarProps) {
  const activeLayerCount = Object.values(layerState).filter(Boolean).length;

  return (
    <aside className="sidebar" aria-label="Thanh điều hướng explorer">
      <div className="side-nav">
        <button className={`nav-item ${activeSection === "map" ? "active" : ""}`} onClick={() => onSectionChange("map")}>
          <span aria-hidden="true">◈</span><span>Bản đồ</span>
        </button>
        <button className={`nav-item ${activeSection === "layers" ? "active" : ""}`} onClick={() => onSectionChange("layers")}>
          <span aria-hidden="true">▱</span><span>Lớp dữ liệu</span><span className="nav-count">{activeLayerCount}</span>
        </button>
        <button className="nav-item" onClick={() => onLayerChange("anomalies")}>
          <span aria-hidden="true">⌁</span><span>Bất thường</span><span className="nav-count">08</span>
        </button>
        <button className="nav-item"><span aria-hidden="true">⌖</span><span>Khu vực nghiên cứu</span></button>
        <button className="nav-item"><span aria-hidden="true">⇩</span><span>Xuất dữ liệu</span></button>
      </div>
      <div className="side-bottom">
        <div className="explorer-data-status" role="status" aria-label="Trạng thái dữ liệu">
          <strong>{sourceLabel(scene)}</strong>
          <span>{scene?.title ?? "Đang tải scene"}</span>
          {scene?.dataStatus === "error" && <small>Không có raster hợp lệ; không dùng số giả.</small>}
        </div>
        <button className="nav-item"><span aria-hidden="true">⚙</span><span>Cài đặt</span></button>
        <button type="button" className="panel-resize-handle sidebar" aria-label="Kéo để đổi độ rộng thanh bên trái" onPointerDown={(event) => onResizeStart("sidebar", event)}><span aria-hidden="true" /></button>
      </div>
    </aside>
  );
}
