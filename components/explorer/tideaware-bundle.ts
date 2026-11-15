export type TideAwareBundlePoint = {
  date: string;
  role: "Reference" | "Monitoring";
  levelM: number | null;
};

export type TideAwareBundleTrack = {
  track: "047" | "155";
  sceneCount: number;
  tideMatchedCount: number;
  patchCount: number;
  patchAreaHa: number;
  tideMinM: number;
  tideMaxM: number;
  tideMeanM: number;
  points: TideAwareBundlePoint[];
};

// Summary extracted from tideaware_delivery_bundle/app_bundle and layer4.
// The source plot is the bundle's figures/F12_tide_vs_date.png.
export const TIDEAWARE_BUNDLE_TRACKS: TideAwareBundleTrack[] = [
  {
    track: "047",
    sceneCount: 6,
    tideMatchedCount: 5,
    patchCount: 1631,
    patchAreaHa: 1679,
    tideMinM: 0.664,
    tideMaxM: 2.031,
    tideMeanM: 1.245,
    points: [
      { date: "2026-06-17", role: "Reference", levelM: 1.534 },
      { date: "2026-06-29", role: "Reference", levelM: 0.773 },
      { date: "2026-07-23", role: "Reference", levelM: 2.031 },
      { date: "2026-08-28", role: "Reference", levelM: 1.221 },
      { date: "2026-09-09", role: "Monitoring", levelM: 0.664 },
      { date: "2026-10-27", role: "Monitoring", levelM: null },
    ],
  },
  {
    track: "155",
    sceneCount: 6,
    tideMatchedCount: 5,
    patchCount: 466,
    patchAreaHa: 490,
    tideMinM: 2.761,
    tideMaxM: 3.541,
    tideMeanM: 3.144,
    points: [
      { date: "2026-06-24", role: "Reference", levelM: 2.761 },
      { date: "2026-07-06", role: "Reference", levelM: 3.324 },
      { date: "2026-08-11", role: "Reference", levelM: 3.037 },
      { date: "2026-08-23", role: "Reference", levelM: 3.056 },
      { date: "2026-09-16", role: "Monitoring", levelM: 3.541 },
      { date: "2026-10-22", role: "Monitoring", levelM: null },
    ],
  },
];

export const TIDEAWARE_BUNDLE_PLOT_SRC = "/tideaware/F12_tide_vs_date.png";
