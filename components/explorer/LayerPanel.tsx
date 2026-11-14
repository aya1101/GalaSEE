"use client";

import type { ReactNode } from "react";

export type LayerPanelProps = {
  layerState: Record<string, boolean>;
  onLayerChange: (layer: string) => void;
  children: ReactNode;
};

export function LayerPanel({ layerState, onLayerChange, children }: LayerPanelProps) {
  void onLayerChange;
  const activeLayers = Object.entries(layerState).filter(([, enabled]) => enabled).map(([layer]) => layer).join(",");
  return <div className="explorer-layer-panel" data-active-layers={activeLayers}>{children}</div>;
}
