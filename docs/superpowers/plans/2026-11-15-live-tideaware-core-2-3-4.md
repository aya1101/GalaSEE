# Live TideAware Core Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run TideAware from live Earthdata and live tide inputs on the website, without using the H5 files from the delivery ZIP at runtime, and implement the tide source, scene role assignment and OLS + Robust Z + CUSUM core.

**Architecture:** The browser only starts and monitors a run. FastAPI resolves current ASF scene metadata and uses the server-side `EARTHDATA_TOKEN` through the existing Harmony/GeoTIFF cache path; the token never reaches the browser. A background job builds two independent time series (Track 047 and Track 155), attaches UHSLC tide observations, runs deterministic anomaly analysis, and exposes GeoJSON/raster/manifest results.

**Tech Stack:** Next.js 16 / React 19 / TypeScript, FastAPI / Pydantic, httpx, NumPy, SciPy, scikit-image, Rasterio, Shapely, PyProj, Supabase/PostGIS metadata and object/file storage.

**Spec:** `TideAware_AI_Engine.ipynb`, the live Earthdata path in `api/main.py`, and the existing explorer comparison flow in `components/explorer/ExplorerShell.tsx`.

## Global Constraints

- Runtime scene input comes from live Earthdata using the backend `EARTHDATA_TOKEN`; `tideaware_delivery_bundle.zip` and its H5 files are offline fixtures only.
- The browser must never receive or log `EARTHDATA_TOKEN`.
- Prefer the existing Harmony GeoTIFF path for live input; verify unit, CRS, transform, resolution and common grid before analysis.
- Process Track `047` and Track `155` independently.
- Use live ASF metadata to assign scenes; do not use `metadata.csv` from the bundle at runtime.
- Fetch UHSLC station 383 at runtime with a server cache; use the bundle CSV only as a deterministic test fixture.
- Missing tide data must produce `PARTIAL`/`UNAVAILABLE` status and must not create fake corrected values.
- Default thresholds: `Z_THR=-3`, `Z_POS=3`, `MIN_DB_DROP=1.5`, `CUSUM_K=0.5`, `CUSUM_H=4`, `MIN_PATCH=3`.
- Results are `Potential`/`Not Validated`; do not expose confirmed-loss or calibrated-confidence language.
- Keep the existing pairwise `/api/v1/comparisons` flow unchanged.

## Review Focus

- Token stays server-side while live scene downloads are in progress; test request logs and browser payloads.
- A live catalog with mixed tracks/frames or incompatible grids is blocked before any model calculation; test in Task 2.
- A tide series ending before a Monitoring scene produces `PARTIAL` and Original-only output, never NaN-corrected output; test in Task 3 and Task 4.
- Harmony rasters with ambiguous units are rejected rather than double-converted to dB; test in Task 4.
- Browser receives compact status/GeoJSON/asset URLs, not raw H5 or full raster arrays; test in Task 5.

---

### Task 1: Define the live TideAware request and result contracts

**Files:**
- Create: `api/tideaware/__init__.py`
- Create: `api/tideaware/contracts.py`
- Create: `components/explorer/tideaware-types.ts`
- Create: `api/test_tideaware_contracts.py`

**Interfaces:**
- `TideAwareRunRequest`: `aoi`, `track: "047" | "155" | "both"`, optional `frame`, `referenceCount=4`, `monitoringCount=2`, `bands=["HHHH","HVHV"]`, thresholds and `useCorrected`.
- `SceneRole`: live scene ID, track, frame, direction, acquisition time and `Reference_n`/`Monitoring_n` role.
- `AnalysisRunStatus`: `queued | resolving | fetching | processing | ready | blocked | error`.
- `TideAwareResult`: per-track status, tide status, validation status, layer refs, patch GeoJSON URL and provenance.

- [ ] **Step 1: Write contract tests** for defaults, allowed tracks/bands, threshold validation and status serialization.
- [ ] **Step 2: Implement Pydantic contracts** with no token fields.
- [ ] **Step 3: Add matching TypeScript types** for the future UI and API proxy.
- [ ] **Step 4: Run `python -m unittest api.test_tideaware_contracts` and `npm run typecheck`.**

### Task 2: Resolve live scenes and assign Reference/Monitoring roles

**Files:**
- Create: `api/tideaware/live_scenes.py`
- Create: `api/test_tideaware_live_scenes.py`
- Modify: `api/main.py` only to expose existing catalog/metadata helpers through a stable internal interface

**Interfaces:**
- `resolve_live_scene_groups(request: TideAwareRunRequest) -> SceneGroupReport`
- `select_scene_roles(records, reference_count: int, monitoring_count: int) -> list[SceneRole]`
- `validate_scene_group(group: SceneGroup) -> CompatibilityReport`

- [ ] **Step 1: Write tests** using catalog-like metadata fixtures for Track 047 frame 083 and Track 155 frame 007, asserting chronological roles `Reference_1..4` and `Monitoring_1..2`.
- [ ] **Step 2: Write rejection tests** for mixed track/frame/direction, fewer than four Reference scenes, AOI non-overlap and incompatible scene metadata.
- [ ] **Step 3: Implement live catalog resolution** using the existing ASF catalog functions; do not read bundle `metadata.csv` in this path.
- [ ] **Step 4: Implement grouping by track + frame + orbit direction**, sorting by acquisition timestamp and keeping the two most recent scenes as Monitoring.
- [ ] **Step 5: Add a compatibility check** for scene collection, band availability, AOI overlap and expected common raster grid.
- [ ] **Step 6: Run tests and verify that the result contains live scene IDs/file names suitable for Harmony extraction.**

### Task 3: Add live tide provider and tide coverage policy

**Files:**
- Create: `api/tideaware/live_tide.py`
- Create: `api/test_tideaware_live_tide.py`
- Modify: `.env.example` with `TIDE_UHSLC_URL`, `TIDE_STATION`, `TIDE_CACHE_DIR` and `TIDE_MAX_GAP_MINUTES`

**Interfaces:**
- `fetch_uhslc_hourly(url: str) -> TideSeries`
- `interpolate_tide(series: TideSeries, acquisition_time: datetime) -> TideSample`
- `evaluate_tide_coverage(samples: list[TideSample]) -> TideCoverage`

- [ ] **Step 1: Write tests** from a small fixture with valid rows, sentinel missing rows and an acquisition outside coverage; assert millimetres become metres and timestamps are UTC.
- [ ] **Step 2: Implement server-side UHSLC fetching and atomic cache writes** using httpx; the bundle CSV is copied into tests only, never used by production code.
- [ ] **Step 3: Implement interpolation and nearest-observation gap reporting** without forecasting.
- [ ] **Step 4: Implement policy:** Reference tide must be available for OLS; if Monitoring tide is missing, mark corrected output unavailable and preserve Original output.
- [ ] **Step 5: Run tests and verify the current October 2026 scenes would report `PARTIAL` until a newer tide source is configured.**

### Task 4: Implement live GeoTIFF stack and OLS + Robust Z + CUSUM

**Files:**
- Create: `api/tideaware/live_assets.py`
- Create: `api/tideaware/deterministic_engine.py`
- Create: `api/tideaware/polygonize.py`
- Create: `api/test_tideaware_deterministic_engine.py`
- Modify: `api/requirements.txt` with `scipy`, `scikit-image` and any raster dependency missing from the API image

**Interfaces:**
- `ensure_live_scene_assets(scene_roles, bands) -> SceneAssetSet`
- `read_common_stack(asset_set) -> SceneStack`
- `run_pixelwise_ols(reference_stack, reference_tide) -> OlsResult`
- `run_robust_z(stack, reference_mask, thresholds) -> RobustZResult`
- `run_temporal_cusum(z_maps, labels, config) -> TemporalResult`
- `run_deterministic_tideaware(group, tide_series, config) -> TrackAnalysisResult`

- [ ] **Step 1: Write tests** for live asset retrieval delegation to `ensure_cached_gcov_raster`, no raw H5 response to clients, common-grid validation and explicit power/dB handling.
- [ ] **Step 2: Implement live asset resolution** by reusing the current Harmony GeoTIFF cache path and backend token. Do not duplicate the browser-facing token proxy.
- [ ] **Step 3: Implement stack loading** for HHHH/HVHV, converting power to dB exactly once and recording the unit in provenance.
- [ ] **Step 4: Implement per-track OLS and LOO evaluation** on Reference scenes only. Disable Corrected for any Monitoring scene without tide.
- [ ] **Step 5: Implement provisional Otsu vegetation mask** with a status field, then Robust Z labels using the fixed thresholds.
- [ ] **Step 6: Implement CUSUM, temporal count, connected-component filtering and patch properties. Calculate area from raster transform rather than hard-coding 1 ha.
- [ ] **Step 7: Export per-track HH/HV results as GeoJSON plus GeoTIFF/COG references and a manifest.
- [ ] **Step 8: Run deterministic engine tests and compare a fixture run against the bundle’s audit values only as a regression check, not as runtime input.

### Task 5: Expose live analysis as a website job

**Files:**
- Create: `api/tideaware/routes.py`
- Create: `api/tideaware/jobs.py`
- Create: `api/test_tideaware_routes.py`
- Modify: `api/main.py` to include the router
- Modify: `components/explorer/ExplorerShell.tsx`
- Create: `components/explorer/TideAwareRunPanel.tsx`
- Modify: `components/explorer/explorer.css`
- Create or modify: `app/api/earthdata/tideaware/[...path]/route.ts`

**Interfaces:**
- `POST /api/v1/tideaware/compatibility`
- `POST /api/v1/tideaware/runs`
- `GET /api/v1/tideaware/runs/{run_id}`
- `GET /api/v1/tideaware/runs/{run_id}/geojson`
- `GET /api/v1/tideaware/runs/{run_id}/asset/{asset_id}`

- [ ] **Step 1: Write route tests** for queueing, blocked compatibility, partial tide, ready result and unknown run.
- [ ] **Step 2: Implement a persistent run record/status path**; local development may use the existing cache directory, production must use database/object storage.
- [ ] **Step 3: Implement worker execution** with progress stages: `resolving_scenes`, `fetching_assets`, `fetching_tide`, `processing_047`, `processing_155`, `exporting`, `ready`.
- [ ] **Step 4: Add the UI action** to start a live run using the selected AOI/track, then poll status with cancellation on unmount.
- [ ] **Step 5: Display results in four UI areas:** progress/status panel; per-track summary cards for 047/155; map layer toggles for Potential Loss/Gain, Repeated Anomaly and Uncertainty; and a selected-patch inspector with area, monitoring date, polarization, Z-score, dB delta, tide status and validation status.
- [ ] **Step 6: Add a report action** beside the completed run: `View report` opens the report page and `Download report` downloads the generated HTML/JSON artifacts.
- [ ] **Step 7: Display tide coverage and `NOT VALIDATED`; do not display a confidence percentage.
- [ ] **Step 8: Run route tests, component tests, `npm run typecheck`, `npm test -- --run` and Python test discovery.

### Task 6: Generate and display a reproducible analysis report

**Files:**
- Create: `api/tideaware/report.py`
- Create: `api/test_tideaware_report.py`
- Create: `app/explorer/report/[runId]/page.tsx`
- Create: `components/explorer/TideAwareReport.tsx`
- Modify: `api/tideaware/routes.py`
- Modify: `components/explorer/TideAwareRunPanel.tsx`
- Modify: `components/explorer/explorer.css`

**Interfaces:**
- `build_report_json(result: TideAwareResult, manifest: TideAwareManifest) -> TideAwareReport`
- `render_report_html(report: TideAwareReport) -> str`
- `GET /api/v1/tideaware/runs/{run_id}/report` → report JSON and artifact URLs.
- `GET /api/v1/tideaware/runs/{run_id}/report.html` → printable/downloadable HTML report.

- [ ] **Step 1: Write report tests** asserting that the report includes run ID, AOI, scene roles, per-track results, tide coverage, thresholds, layer URLs, validation status and limitations.
- [ ] **Step 2: Implement a canonical JSON report** generated only from the processing result and manifest; it must not recalculate metrics or invent confidence values.
- [ ] **Step 3: Implement an HTML report** with sections: Executive Summary, Input Scenes, Tide Coverage, Processing Parameters, Results by Track, Map Layers, Uncertainty, Validation Status, Limitations and Provenance.
- [ ] **Step 4: Include explicit warnings** for `PARTIAL` tide, provisional Otsu mask, insufficient temporal evidence and `NOT VALIDATED` status.
- [ ] **Step 5: Add report URLs to the run status response** and store report files in the same run asset namespace as GeoJSON/GeoTIFF outputs.
- [ ] **Step 6: Add the report page** with Vietnamese/English labels, links to interactive map layers and print/download actions.
- [ ] **Step 7: Run report tests and verify a fixture report never contains `Confirmed Loss` or a percentage confidence.**

## What the ZIP is used for

- `scenes/*.h5`: test fixture only; never read by the live run.
- `audit/uhslc_h383.csv`: tide fixture only; live code fetches `TIDE_UHSLC_URL`.
- `metadata.csv`: role-assignment regression fixture only; live code uses ASF catalog metadata.
- `audit/*.csv`: expected-value/regression checks only.

## Required configuration before implementation

- Keep `EARTHDATA_TOKEN` only in the FastAPI/worker environment.
- Confirm the production `EARTHDATA_DATA_URL`/ASF catalog endpoint returns the target Cần Giờ scenes and their track/frame metadata.
- Configure a tide URL that covers the actual Monitoring dates; UHSLC h383 currently ends before the bundle’s October 2026 Monitoring scenes.
- Decide where generated GeoTIFF/GeoJSON assets live in production: Supabase Storage or S3-compatible object storage.
- Confirm whether Track 047, Track 155 or both should be the default run selection; the plan defaults to both independently.

## Not included in this scope

- L-TAE training/inference.
- Raw H5 download from the browser.
- Using ZIP H5 files as production data.
- Independent validation metrics.
- Replacing the existing two-scene comparison endpoint.
- PDF rendering in the first iteration; the first report format is printable HTML plus canonical JSON.
