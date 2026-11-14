
"use client";

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import dynamic from "next/dynamic";
import type { GlobeMethods } from "react-globe.gl";

const Globe = dynamic(() => import("react-globe.gl"), {
  ssr: false,
});

type EarthGlobeProps = {
  onEarthClick?: () => void;
  flyToRegion?: boolean;
  onFlightComplete?: () => void;
};

export default function EarthGlobe({
  onEarthClick,
  flyToRegion = false,
  onFlightComplete,
}: EarthGlobeProps) {
  const globeRef = useRef<GlobeMethods | undefined>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);

  const [dimensions, setDimensions] = useState({
    width: 600,
    height: 600,
  });

  const [ready, setReady] = useState(false);

  const flightStartedRef = useRef(false);
  const onFlightCompleteRef = useRef(onFlightComplete);

  useEffect(() => {
    onFlightCompleteRef.current = onFlightComplete;
  }, [onFlightComplete]);

  // Keep canvas size synchronized with its container
  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const updateSize = () => {
      setDimensions({
        width: element.clientWidth,
        height: element.clientHeight,
      });
    };

    updateSize();

    const observer = new ResizeObserver(updateSize);
    observer.observe(element);

    return () => observer.disconnect();
  }, []);

  // Initialize Earth rotation
  const handleReady = useCallback(() => {
    const globe = globeRef.current;
    if (!globe) return;

    const controls = globe.controls();

    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35;
    controls.enableDamping = true;

    globe.pointOfView({
      lat: 12,
      lng: 108,
      altitude: 2.1,
    });

    setReady(true);
  }, []);

  // Fly to Vietnam, then Can Gio
  useEffect(() => {
    if (!flyToRegion || !ready || flightStartedRef.current) {
      return;
    }

    const globe = globeRef.current;
    if (!globe) return;

    flightStartedRef.current = true;

    const controls = globe.controls();
    controls.autoRotate = false;
    controls.enabled = false;

    // First: approach Vietnam
    globe.pointOfView(
      {
        lat: 16,
        lng: 107,
        altitude: 1.1,
      },
      1800
    );

    // Second: zoom towards Can Gio
    const zoomTimer = window.setTimeout(() => {
      globe.pointOfView(
        {
          lat: 10.52,
          lng: 106.91,
          altitude: 0.28,
        },
        2200
      );
    }, 1900);

    // Finally: navigate to Explorer
    const finishTimer = window.setTimeout(() => {
      onFlightCompleteRef.current?.();
    }, 4400);

    return () => {
      window.clearTimeout(zoomTimer);
      window.clearTimeout(finishTimer);
    };
  }, [flyToRegion, ready]);

  // Reset if flight is cancelled
  useEffect(() => {
    if (!flyToRegion) {
      flightStartedRef.current = false;

      const globe = globeRef.current;
      if (globe && ready) {
        const controls = globe.controls();
        controls.enabled = true;
        controls.autoRotate = true;
      }
    }
  }, [flyToRegion, ready]);

  const handleEarthClick = useCallback(() => {
    if (flyToRegion) return;

    console.log("EARTH CLICK DETECTED");
    onEarthClick?.();
  }, [flyToRegion, onEarthClick]);

  return (
    <div
      ref={containerRef}
      className="earth-stage"
      onClick={handleEarthClick}
      style={{
        cursor: flyToRegion ? "default" : "pointer",
        pointerEvents: "auto",
      }}
    >
      <Globe
        ref={globeRef}
        width={dimensions.width}
        height={dimensions.height}
        onGlobeReady={handleReady}
        globeImageUrl="https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg"
        bumpImageUrl="https://unpkg.com/three-globe/example/img/earth-topology.png"
        backgroundColor="rgba(0,0,0,0)"
        showAtmosphere
        atmosphereColor="#6eb7dc"
        atmosphereAltitude={0.13}
        animateIn
      />
    </div>
  );
}
