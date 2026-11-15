"use client";

import type { PointerEvent as ReactPointerEvent } from "react";

export type ExplorerSidebarProps = {
  language?: "en" | "vi";
  layerState: Record<string, boolean>;
  onLayerChange: (layer: string) => void;
  activeSection: "map" | "layers";
  onSectionChange: (section: "map" | "layers") => void;
  onStudyAreaFocus?: () => void;
  onResizeStart: (side: "sidebar", event: ReactPointerEvent<HTMLButtonElement>) => void;
};

export function ExplorerSidebar({ language = "vi", layerState, onLayerChange, activeSection, onSectionChange, onStudyAreaFocus, onResizeStart }: ExplorerSidebarProps) {
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
        <button className="nav-item" onClick={() => onLayerChange("anomalies")}>
          <span aria-hidden="true">⌁</span><span>{isEnglish ? "Anomalies" : "Bất thường"}</span><span className="nav-count">08</span>
        </button>
        <button className={`nav-item ${activeSection === "map" ? "active" : ""}`} onClick={() => { onSectionChange("map"); onStudyAreaFocus?.(); }}>
          <span className="nav-study-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"><path d="M4 9V5h4M20 9V5h-4M4 15v4h4M20 15v4h-4M8 12h8M12 8v8" /></svg></span>
          <span>{isEnglish ? "Study area" : "Khu vực nghiên cứu"}</span>
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
