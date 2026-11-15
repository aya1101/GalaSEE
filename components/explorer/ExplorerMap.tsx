"use client";

import type { ReactNode } from "react";

export type ExplorerMapContext = {
  region: string;
  sceneId: string | null;
  dataMode: "earthdata" | "cached" | "demo" | "error";
};

export type ExplorerMapProps = {
  mapContext: ExplorerMapContext;
  onPixelSelect: (coordinate: { longitude: number; latitude: number }) => void;
  children: ReactNode;
};

export function ExplorerMap({ mapContext, onPixelSelect, children }: ExplorerMapProps) {
  void onPixelSelect;
  return (
    <section className="map-workspace" data-region={mapContext.region} data-scene-id={mapContext.sceneId ?? ""}>
      {children}
    </section>
  );
}
