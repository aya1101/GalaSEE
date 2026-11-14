
"use client";

import { useCallback, useState } from "react";
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

export default function Home() {
  const router = useRouter();

  const [isRegionOpen, setIsRegionOpen] = useState(false);
  const [flyToRegion, setFlyToRegion] = useState(false);
  const [selectedRegion, setSelectedRegion] = useState("");

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
  }, []);

  // Camera animation completed -> open Explorer
  const handleFlightComplete = useCallback(() => {
    if (!selectedRegion) return;

    router.push(
      `/explorer?region=${encodeURIComponent(selectedRegion)}`
    );
  }, [router, selectedRegion]);

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
