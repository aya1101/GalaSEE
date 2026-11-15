"use client";

import type { ReactNode } from "react";

export type TimelineControlProps = {
  selectedSceneId: string;
  children: ReactNode;
};

export function TimelineControl({ selectedSceneId, children }: TimelineControlProps) {
  return <div className="explorer-timeline-control" data-selected-scene={selectedSceneId}>{children}</div>;
}
