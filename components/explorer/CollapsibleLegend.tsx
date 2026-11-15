import type { ReactNode } from "react";

export type CollapsibleLegendProps = {
  open: boolean;
  title: string;
  closeLabel: string;
  openLabel: string;
  onToggle: () => void;
  children: ReactNode;
};

export function CollapsibleLegend({ open, title, closeLabel, openLabel, onToggle, children }: CollapsibleLegendProps) {
  if (!open) {
    return (
      <button type="button" className="layer-legend-toggle map-overlay" aria-expanded="false" aria-label={openLabel} onClick={onToggle}>
        <span aria-hidden="true">◈</span>{openLabel}
      </button>
    );
  }

  return (
    <div className="layer-legend map-overlay" aria-label={title}>
      <div className="legend-panel-head">
        <div className="legend-title">{title}</div>
        <button type="button" className="legend-collapse-button" aria-expanded="true" aria-label={closeLabel} onClick={onToggle}>−</button>
      </div>
      {children}
    </div>
  );
}
