
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function ExplorerDashboard() {
  const router = useRouter();
  const [scene, setScene] = useState(0);
  const [polarization, setPolarization] = useState("HHHH");

  const [layers, setLayers] = useState({
    sar: true,
    mangrove: true,
    changes: false,
    alerts: false,
  });

  const layerOptions = [
    { key: "sar", label: "NISAR Radar Imagery" },
    { key: "mangrove", label: "Mangrove Boundary" },
    { key: "changes", label: "Detected Changes" },
    { key: "alerts", label: "Threat Alerts" },
  ] as const;

  return (
    <main className="min-h-screen bg-[#030810] text-white">
      <header className="flex items-center justify-between border-b border-white/10 px-8 py-5">
        <div>
          <h1 className="text-xl tracking-[0.3em] font-semibold">
            TIDEAWARE<span className="text-cyan-400">.</span>
          </h1>
          <p className="mt-1 text-[10px] tracking-[0.2em] text-slate-500">
            COASTAL CHANGE EXPLORER
          </p>
        </div>

        <button
          onClick={() => router.push("/")}
          className="border border-white/20 px-4 py-2 text-xs text-slate-300 hover:border-cyan-400"
        >
          ← BACK TO EARTH
        </button>
      </header>

      <div className="flex min-h-[calc(100vh-85px)] flex-col lg:flex-row">
        <aside className="w-full border-r border-white/10 bg-[#07111d] p-6 lg:w-[300px]">
          <p className="text-[10px] tracking-[0.2em] text-cyan-400">
            OBSERVATION CONTROL
          </p>

          <h2 className="mt-4 text-2xl font-medium">
            Coastal Layers
          </h2>

          <div className="mt-8 space-y-5">
            {layerOptions.map((layer) => (
              <label
                key={layer.key}
                className="flex cursor-pointer items-center gap-3 text-sm text-slate-300"
              >
                <input
                  type="checkbox"
                  checked={layers[layer.key]}
                  onChange={() =>
                    setLayers((prev) => ({
                      ...prev,
                      [layer.key]: !prev[layer.key],
                    }))
                  }
                  className="accent-cyan-400"
                />
                {layer.label}
              </label>
            ))}
          </div>

          <div className="mt-10 border-t border-white/10 pt-6">
            <p className="text-xs tracking-widest text-slate-400">
              POLARIZATION
            </p>

            <div className="mt-4 flex gap-2">
              {["HHHH", "HVHV"].map((mode) => (
                <button
                  key={mode}
                  onClick={() => setPolarization(mode)}
                  className={`border px-4 py-2 text-xs ${
                    polarization === mode
                      ? "border-cyan-400 bg-cyan-400/10 text-cyan-300"
                      : "border-white/20 text-slate-400"
                  }`}
                >
                  {mode}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-10 border-t border-white/10 pt-6">
            <p className="text-xs tracking-widest text-slate-400">
              DATA STATUS
            </p>
            <p className="mt-3 text-sm text-amber-300">
              Preview Mode
            </p>
            <p className="mt-2 text-xs leading-6 text-slate-500">
              Awaiting integration with NISAR scene data.
            </p>
          </div>
        </aside>

        <section className="relative flex min-h-[550px] flex-1 flex-col">
          <div className="relative flex-1 bg-[#091722]">
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <div className="mb-5 text-5xl text-cyan-500/60">
                ◎
              </div>
              <h3 className="text-lg tracking-[0.2em]">
                SATELLITE OBSERVATION MAP
              </h3>
              <p className="mt-3 text-sm text-slate-500">
                Interactive map will be integrated next
              </p>
            </div>

            <div className="absolute top-6 left-6 border border-cyan-500/20 bg-black/50 px-4 py-3 text-xs text-cyan-300">
              SCENE {String(scene + 1).padStart(2, "0")} / 21
            </div>
          </div>

          <div className="border-t border-white/10 bg-[#07111d] px-8 py-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs tracking-[0.2em] text-cyan-400">
                  OBSERVATION TIMELINE
                </p>
                <p className="mt-2 text-sm text-slate-400">
                  Scene {scene + 1} of 21
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setScene((s) => Math.max(0, s - 1))}
                  className="border border-white/20 px-4 py-2 hover:border-cyan-400"
                >
                  ←
                </button>
                <button
                  onClick={() => setScene((s) => Math.min(20, s + 1))}
                  className="border border-white/20 px-4 py-2 hover:border-cyan-400"
                >
                  →
                </button>
              </div>
            </div>

            <input
              type="range"
              min="0"
              max="20"
              value={scene}
              onChange={(e) => setScene(Number(e.target.value))}
              className="mt-6 w-full accent-cyan-400"
            />
          </div>
        </section>
      </div>
    </main>
  );
}
