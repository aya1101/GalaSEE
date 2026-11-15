"use client";

import type { PointerEvent as ReactPointerEvent } from "react";

export type ExplorerSidebarProps = {
  language?: "en" | "vi";
  layerState: Record<string, boolean>;
  onLayerChange: (layer: string) => void;
  activeSection: "map" | "layers" | "engine";
  onSectionChange: (section: "map" | "layers" | "engine") => void;
  onResizeStart: (side: "sidebar", event: ReactPointerEvent<HTMLButtonElement>) => void;
};

export function ExplorerSidebar({ language = "vi", layerState, onLayerChange, activeSection, onSectionChange, onResizeStart }: ExplorerSidebarProps) {
  const isEnglish = language === "en";
  const activeLayerCount = Object.values(layerState).filter(Boolean).length;

  return (
    <aside className="sidebar" aria-label={isEnglish ? "Explorer navigation" : "Thanh điều hướng explorer"}>
      <div className="side-nav">
        <button className={`nav-item ${activeSection === "map" ? "active" : ""}`} onClick={() => onSectionChange("map")}>
          <span aria-hidden="true">◈</span><span>{isEnglish ? "Map" : "Bản đồ"}</span>
        </button>
        <button className={`nav-item ${activeSection === "layers" ? "active" : ""}`} onClick={() => onSectionChange("layers")}>
          <span aria-hidden="true">▱</span><span>{isEnglish ? "Data layers" : "Lớp dữ liệu"}</span><span className="nav-count">{activeLayerCount}</span>
        </button>
        <button className={`nav-item engine-nav-item ${activeSection === "engine" ? "active" : ""}`} onClick={() => onSectionChange("engine")}>
          <span className="nav-engine-icon" aria-hidden="true">≈</span><span>{isEnglish ? "Tide-aware" : "Theo triều"}</span>
        </button>
        <button className="nav-item" onClick={() => onLayerChange("anomalies")}>
          <span aria-hidden="true">⌁</span><span>{isEnglish ? "Anomalies" : "Bất thường"}</span><span className="nav-count">08</span>
        </button>
        <button className="nav-item"><span aria-hidden="true">⇩</span><span>{isEnglish ? "Export data" : "Xuất dữ liệu"}</span></button>
      </div>
      <div className="side-bottom">
        <button className="nav-item"><span aria-hidden="true">⚙</span><span>{isEnglish ? "Settings" : "Cài đặt"}</span></button>
        <button type="button" className="panel-resize-handle sidebar" aria-label={isEnglish ? "Resize left sidebar" : "Kéo để đổi độ rộng thanh bên trái"} onPointerDown={(event) => onResizeStart("sidebar", event)}><span aria-hidden="true" /></button>
      </div>
    </aside>
  );
}
