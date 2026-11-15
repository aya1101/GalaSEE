
"use client";

import { useEffect } from "react";
import { createPortal } from "react-dom";

type RegionSelectorProps = {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (region: string) => void;
};

export default function RegionSelector({
  isOpen,
  onClose,
  onSelect,
}: RegionSelectorProps) {
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);

    return () => {
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen, onClose]);

  if (!isOpen || typeof document === "undefined") {
    return null;
  }

  return createPortal(
    <div
      className="region-overlay"
      onClick={onClose}
    >
      <div
        className="region-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="region-title"
        onClick={(event) => event.stopPropagation()}
      >
        <button
          type="button"
          className="region-close"
          onClick={onClose}
          aria-label="Close region selector"
        >
          ×
        </button>

        <span className="region-eyebrow">
          TIDEAWARE / OBSERVATION NETWORK
        </span>

        <h2 id="region-title">
          SELECT A REGION.
        </h2>

        <p className="region-description">
          Choose a coastal observation area to explore
          satellite radar data and environmental changes.
        </p>

        <button
          type="button"
          className="region-option"
          onClick={() => onSelect("can-gio")}
        >
          <span>
            <strong>CAN GIO, VIETNAM</strong>

            <small>
              Coastal observation area · Pilot region
            </small>
          </span>

          <span className="region-arrow">↗</span>
        </button>

        <div className="region-coming-soon">
          <span>MORE REGIONS</span>
          <span>COMING SOON</span>
        </div>

        <div className="region-bottom">
          NASA SPACE APPS CHALLENGE 2026
        </div>
      </div>
    </div>,
    document.body
  );
}
