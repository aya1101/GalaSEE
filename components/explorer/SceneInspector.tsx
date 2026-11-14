"use client";

import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";

export type SceneInspectorProps = {
  scene?: { id: string; title: string };
  open: boolean;
  onClose: () => void;
  onResizeStart: (side: "inspector", event: ReactPointerEvent<HTMLButtonElement>) => void;
  closeButton: ReactNode;
  resizeHandle: ReactNode;
  children: ReactNode;
};

export function SceneInspector({ scene, open, onClose, onResizeStart, closeButton, resizeHandle, children }: SceneInspectorProps) {
  void onResizeStart;
  return (
    <aside className={`inspector ${open ? "mobile-open" : ""}`} data-scene-id={scene?.id ?? ""}>
      {resizeHandle}
      <div className="inspector-head">
        <div><span className="panel-kicker">KHU VỰC ĐANG CHỌN</span><h1>{scene?.title ?? "Chi tiết khu vực"}</h1></div>
        <span onClick={onClose}>{closeButton}</span>
      </div>
      {children}
    </aside>
  );
}
