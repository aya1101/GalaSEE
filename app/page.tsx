
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { useRouter } from "next/navigation";

import LandingHero from "../components/LandingHero";
import Starfield from "../components/Starfield";
import RegionSelector from "../components/RegionSelector";

const EarthGlobe = dynamic(
  () => import("../components/EarthGlobe"),
  {
    ssr: false,
  }
);

const FLIGHT_FALLBACK_MS = 4600;

export default function Home() {
  const router = useRouter();

  const [isRegionOpen, setIsRegionOpen] = useState(false);
  const [flyToRegion, setFlyToRegion] = useState(false);
  const [selectedRegion, setSelectedRegion] = useState("");
  const navigationTimerRef = useRef<number | null>(null);
  const navigationStartedRef = useRef(false);

  const navigateToExplorer = useCallback((region: string) => {
    if (!region || navigationStartedRef.current) return;
    navigationStartedRef.current = true;
    if (navigationTimerRef.current !== null) {
      window.clearTimeout(navigationTimerRef.current);
      navigationTimerRef.current = null;
    }
    router.push(`/explorer?region=${encodeURIComponent(region)}`);
  }, [router]);

  useEffect(() => () => {
    if (navigationTimerRef.current !== null) window.clearTimeout(navigationTimerRef.current);
  }, []);

  // Click Earth -> open region selector
  const handleEarthClick = useCallback(() => {
    if (flyToRegion) return;

    console.log("OPENING REGION SELECTOR");
    setIsRegionOpen(true);
  }, [flyToRegion]);

  // Choose region -> start camera animation
  const handleSelectRegion = useCallback((region: string) => {
    console.log("SELECTED REGION:", region);

    setIsRegionOpen(false);
    setSelectedRegion(region);
    setFlyToRegion(true);
    navigationTimerRef.current = window.setTimeout(() => navigateToExplorer(region), FLIGHT_FALLBACK_MS);
  }, [navigateToExplorer]);

  // Camera animation completed -> open Explorer
  const handleFlightComplete = useCallback(() => {
    if (!selectedRegion) return;

    navigateToExplorer(selectedRegion);
  }, [navigateToExplorer, selectedRegion]);

  return (
    <main
      className="welcome-page"
      style={{
        position: "relative",
        width: "100%",
        height: "100dvh",
        minHeight: "600px",
        overflow: "hidden",
        background: "#03060d",
      }}
    >
      {/* Animated star background */}
      <Starfield />

      {/* Rotating interactive Earth */}
      <EarthGlobe
        onEarthClick={handleEarthClick}
        flyToRegion={flyToRegion}
        onFlightComplete={handleFlightComplete}
      />

      {/* Welcome text */}
      <LandingHero />

      {/* Camera flight indicator */}
      {flyToRegion && (
        <div className="flight-status">
          <span className="flight-status-dot" />
          LOCATING COASTAL OBSERVATION AREA...
        </div>
      )}

      {/* Region selection modal */}
      <RegionSelector
        isOpen={isRegionOpen}
        onClose={() => setIsRegionOpen(false)}
        onSelect={handleSelectRegion}
      />
    </main>
  );
}
