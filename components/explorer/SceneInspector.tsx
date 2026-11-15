"use client";

import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";

export type SceneInspectorProps = {
  scene?: { id: string; title: string };
  language?: "en" | "vi";
  open: boolean;
  onClose: () => void;
  onResizeStart: (side: "inspector", event: ReactPointerEvent<HTMLButtonElement>) => void;
  closeButton: ReactNode;
  resizeHandle: ReactNode;
  children: ReactNode;
};

export function SceneInspector({ scene, language = "vi", open, onClose, onResizeStart, closeButton, resizeHandle, children }: SceneInspectorProps) {
  void onResizeStart;
  const isEnglish = language === "en";
  return (
    <aside className={`inspector ${open ? "mobile-open" : ""}`} data-scene-id={scene?.id ?? ""}>
      {resizeHandle}
      <div className="inspector-head">
        <div><span className="panel-kicker">{isEnglish ? "SELECTED AREA" : "KHU VỰC ĐANG CHỌN"}</span><h1>{scene?.title ?? (isEnglish ? "Area details" : "Chi tiết khu vực")}</h1></div>
        <span onClick={onClose}>{closeButton}</span>
      </div>
      {children}
    </aside>
  );
}
