# TideAware Engine Website Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the TideAware multi-scene mangrove anomaly pipeline into the existing Next.js + FastAPI website without presenting unvalidated results as confirmed loss.

**Architecture:** Keep the existing two-scene comparison flow unchanged as a fallback. Add a separate persistent TideAware analysis-run flow: scene grouping and tide retrieval feed a Python processing engine; a background worker writes manifests, GeoJSON and raster layers to durable storage; FastAPI exposes status and assets; the explorer renders candidate, temporal, CUSUM and uncertainty layers. The first production scope is deterministic OLS + Robust Z + mask + CUSUM; L-TAE remains an explicitly experimental optional stage.

**Tech Stack:** Next.js 16 / React 19 / TypeScript, FastAPI / Pydantic, NumPy / SciPy / Rasterio / Shapely / PyProj / h5py, Supabase/PostGIS for run metadata, Supabase Storage or S3-compatible object storage for raster/vector assets, Render web service plus background worker.

**Spec:** `TideAware_AI_Engine.ipynb` and the current website implementation in `api/main.py`, `api/gcov_analytics.py`, `components/explorer/ExplorerShell.tsx`, and `supabase/migrations/0001_initial.sql`.

## Global Constraints

- Process Track `047` and Track `155` independently; never merge them before grid/statistical comparison.
- Use NISAR `xCoordinates` / `yCoordinates` or a verified raster transform; do not create synthetic coordinate grids.
- Use HH/HV from the NISAR `frequencyA` products and preserve an explicit power-vs-dB unit contract.
- Default validation status is `NOT VALIDATED`; never emit `Confirmed Loss`, F1, Accuracy, Precision, Recall or Kappa without independent reference data.
- Labels are `Potential Loss`, `Potential Gain`, `Negative Anomaly`, `Uncertain` and `Insufficient Temporal Evidence`.
- Missing or low-quality tide data blocks the corrected branch; it must not silently produce corrected values from `NaN` tide.
- Earthdata credentials remain backend/worker-only and must never enter browser payloads, logs, manifests or generated assets.
- The existing pairwise comparison endpoint remains available and is not silently changed to use TideAware semantics.
- `uncertainty` is ordinal (`Insufficient`, `Low`, `Medium`, `High`), not a calibrated probability or confidence percentage.
- Production results must include processing version, input scene IDs, thresholds, tide status, source and validation status.

## Review Focus

- A six-scene sequence with one missing tide value must be blocked or run as Original-only, never partially corrected; test in Task 2 and Task 3.
- Scenes from different tracks, frames, CRS or grids must be rejected before processing; test in Task 2.
- A run restarted during download or processing must remain queryable and retryable; test in Task 5.
- A result with no independent validation must render as Potential/Unvalidated, not as confirmed loss or percentage confidence; test in Task 6 and Task 7.
- Large raster assets must not be stored in database rows or sent wholesale to the browser; test in Task 4 and Task 5.

---

### Task 1: Freeze the TideAware analysis contract

**Files:**
- Create: `api/tideaware/__init__.py`
- Create: `api/tideaware/contracts.py`
- Create: `api/test_tideaware_contracts.py`
- Create: `components/explorer/tideaware-types.ts`
- Test: `api/test_tideaware_contracts.py`, existing TypeScript typecheck

**Interfaces:**
- Consumes: scene IDs, AOI GeoJSON, track selection, thresholds and optional `runLtae` flag.
- Produces: Pydantic/TypeScript-compatible `TideAwareAnalysisRequest`, `AnalysisRunStatus`, `AnalysisLayer`, `AnalysisPatch` and `TideAwareManifest` contracts.

- [ ] **Step 1: Write contract tests** for valid request serialization, default thresholds (`Z_THR=-3`, `Z_POS=3`, `MIN_DB_DROP=1.5`, `MIN_PATCH=3`), invalid threshold ranges and allowed status/label values.
- [ ] **Step 2: Implement the contracts** with explicit nullable tide status, validation status, branch (`Original`/`Corrected`), polarization (`HH`/`HV`) and asset URLs.
- [ ] **Step 3: Add matching frontend types in `components/explorer/tideaware-types.ts`** without using `confidence: number` for uncertainty.
- [ ] **Step 4: Run `python -m unittest api.test_tideaware_contracts` and `npm run typecheck`; expect both to pass.**

### Task 2: Add scene grouping, compatibility and tide services

**Files:**
- Create: `api/tideaware/scenes.py`
- Create: `api/tideaware/tide.py`
- Create: `api/test_tideaware_scenes.py`
- Create: `api/test_tideaware_tide.py`
- Modify: `api/main.py` only to reuse catalog metadata helpers where appropriate
- Modify: `.env.example` with `TIDE_PROVIDER`, `TIDE_CACHE_DIR` and station configuration

**Interfaces:**
- `group_analysis_scenes(records, requested_track, requested_frame) -> SceneGroupReport`
- `validate_scene_group(group) -> CompatibilityReport`
- `TideProvider.get_level(acquisition_time) -> TideSample`
- `TideProvider.coverage(start, end) -> TideCoverage`

- [ ] **Step 1: Write deterministic tests** for six scenes becoming four Reference plus two Monitoring, separate grouping for 047/155, rejection of mixed track/frame, and rejection of incompatible grid metadata.
- [ ] **Step 2: Write tide tests** for interpolation inside coverage, missing/out-of-range observations, nearest-observation gap and `PARTIAL` aggregate status.
- [ ] **Step 3: Implement scene grouping** from ASF metadata, sorting by acquisition time and requiring a minimum of four Reference scenes plus one Monitoring scene.
- [ ] **Step 4: Implement UHSLC station 383 retrieval/cache** with explicit UTC timestamps and no forecasting fallback. Return `AVAILABLE`, `PARTIAL` or `UNAVAILABLE`.
- [ ] **Step 5: Run the two test modules and verify that a missing final tide marks the corrected branch unavailable.**

### Task 3: Productionize the deterministic processing engine

**Files:**
- Create: `api/tideaware/engine.py`
- Create: `api/tideaware/raster_adapter.py`
- Create: `api/tideaware/polygonize.py`
- Create: `api/test_tideaware_engine.py`
- Modify: `api/requirements.txt` to add only required runtime dependencies (`scipy`, `h5py`, `pandas` if needed, `scikit-image`, `tqdm`); keep PyTorch out of the base API image initially

**Interfaces:**
- `load_scene_stack(scene_group) -> SceneStack`
- `run_tide_ols(stack, tide) -> TideCorrectionResult`
- `run_robust_z(stack, vegetation_mask, thresholds) -> AnomalyResult`
- `run_temporal_cusum(anomaly_result, config) -> TemporalResult`
- `build_uncertainty(anomaly_result, temporal_result, correction_result) -> UncertaintyResult`
- `run_tideaware_deterministic(request, assets) -> TideAwareProcessingResult`

- [ ] **Step 1: Write tests** for robust median/MAD, sigma floor, negative/positive labels, one/two-monitor temporal counts, CUSUM, patch filtering and ordinal uncertainty.
- [ ] **Step 2: Write adapter tests** that reject ambiguous power/dB units and verify CRS, dimensions, transform and common grid before stacking.
- [ ] **Step 3: Implement the adapter** over the current cached GeoTIFF path first, while preserving the option to read raw HDF5. The adapter must record `source_format`, `unit`, `crs`, `transform`, `width`, `height` and `resolution`.
- [ ] **Step 4: Implement per-track OLS and LOO evaluation**. If tide is incomplete, produce `Original` only and a structured reason for omitting `Corrected`.
- [ ] **Step 5: Implement vegetation mask** with a pluggable external GMW mask and provisional Otsu fallback; record the mask status in the manifest.
- [ ] **Step 6: Implement Robust Z, CUSUM, temporal evidence, connected components and patch GeoJSON. Use 1 ha only when the actual raster transform proves a 100 m × 100 m pixel; otherwise calculate geodesic/projected area from the transform.
- [ ] **Step 7: Run engine tests and add a small deterministic fixture-based integration test covering both tracks and both polarizations.**

### Task 4: Add durable result export and storage abstraction

**Files:**
- Create: `api/tideaware/export.py`
- Create: `api/tideaware/storage.py`
- Create: `api/test_tideaware_export.py`
- Modify: `.env.example` with local/object-storage settings

**Interfaces:**
- `write_analysis_outputs(result, destination) -> TideAwareManifest`
- `put_asset(local_path, key) -> AssetRef`
- `get_asset_path(asset_ref) -> Path | URL`

- [ ] **Step 1: Write export tests** for GeoJSON labels, GeoTIFF CRS/nodata, manifest contents and path traversal rejection.
- [ ] **Step 2: Implement local development storage** under `GCOV_CACHE_DIR/analyses/{run_id}`.
- [ ] **Step 3: Implement production object storage** using Supabase Storage or an S3-compatible bucket; store only metadata and URLs in the database.
- [ ] **Step 4: Export per-track/per-branch/per-polarization layers:** `z`, `label`, `temporal`, `cusum`, `uncertainty`, vegetation mask, patches and optional corrected outputs.
- [ ] **Step 5: Ensure the manifest includes thresholds, source scenes, tide coverage, mask status, validation status, processing version and model status.**
- [ ] **Step 6: Run export tests and verify that no Earthdata token appears in any generated text asset.**

### Task 5: Add persistent analysis runs and worker execution

**Files:**
- Create: `supabase/migrations/0002_tideaware_analysis.sql`
- Create: `api/tideaware/jobs.py`
- Create: `api/worker.py`
- Create: `api/test_tideaware_jobs.py`
- Modify: `render.yaml` to add a background worker
- Modify: `api/requirements.txt` for the selected storage/database client if not already available

**Interfaces:**
- `create_analysis_run(request) -> run_id`
- `claim_next_analysis_run() -> AnalysisRun | None`
- `execute_analysis_run(run_id) -> None`
- `get_analysis_run(run_id) -> AnalysisRunStatus`

- [ ] **Step 1: Write migration tests/documented SQL checks** for `analysis_runs`, `analysis_scenes`, `analysis_layers`, `analysis_patches` and row-level access policies.
- [ ] **Step 2: Implement run state transitions**: `queued → running → ready`, with `blocked`, `failed` and retry metadata.
- [ ] **Step 3: Implement worker claim/retry semantics** so service restart does not lose a run and only one worker claims a run.
- [ ] **Step 4: Connect the worker to scene resolution, tide service, deterministic engine and export/storage.
- [ ] **Step 5: Add progress stages** such as `resolving_scenes`, `fetching_assets`, `processing_track_047`, `processing_track_155`, `exporting`, `ready`.
- [ ] **Step 6: Run job tests including restart/retry simulation and missing-tide blocking.**

### Task 6: Add TideAware FastAPI endpoints without changing pairwise comparison

**Files:**
- Create: `api/tideaware_routes.py`
- Modify: `api/main.py` to mount/include the router
- Create: `api/test_tideaware_routes.py`

**Interfaces:**
- `POST /api/v1/tideaware/compatibility` → compatibility report.
- `POST /api/v1/tideaware/runs` → `{ id, status: "queued" }`.
- `GET /api/v1/tideaware/runs/{run_id}` → status, progress, manifest summary and blocking/error reason.
- `GET /api/v1/tideaware/runs/{run_id}/geojson` → candidate patch FeatureCollection.
- `GET /api/v1/tideaware/runs/{run_id}/manifest` → full provenance manifest.
- `GET /api/v1/tideaware/runs/{run_id}/asset/{asset_id}` → authorized raster/vector asset.

- [ ] **Step 1: Write route tests** for valid requests, incompatible scenes, missing tide, unknown run, blocked run and ready asset access.
- [ ] **Step 2: Implement compatibility endpoint** and return explicit checks rather than a generic 500.
- [ ] **Step 3: Implement run creation/status routes** backed by persistent run records.
- [ ] **Step 4: Implement GeoJSON and asset streaming** with content types, cache headers and no full-raster browser payload.
- [ ] **Step 5: Run route tests plus the existing Python test suite.**

### Task 7: Integrate the explorer UI and map layers

**Files:**
- Modify: `components/explorer/ExplorerShell.tsx`
- Modify: `components/explorer/ExplorerSidebar.tsx`
- Modify: `components/explorer/SceneInspector.tsx`
- Modify: `components/explorer/explorer.css`
- Modify: existing API proxy routes under `app/api/earthdata/analytics/[...path]/route.ts` or add `app/api/earthdata/tideaware/[...path]/route.ts`
- Create: `components/explorer/TideAwareAnalysisPanel.tsx`
- Create: `components/explorer/TideAwareAnalysisPanel.test.tsx`

**Interfaces:**
- `startTideAwareAnalysis(request) -> runId`
- `pollTideAwareAnalysis(runId) -> AnalysisRunStatus`
- `loadTideAwareGeoJson(runId) -> FeatureCollection`

- [ ] **Step 1: Write UI tests** for idle/queued/running/blocked/ready/error states, missing tide messaging and unvalidated labels.
- [ ] **Step 2: Add an analysis panel** allowing track selection (`047`, `155`, `Both`), scene group preview, threshold display and explicit `Run analysis` action.
- [ ] **Step 3: Add polling with cancellation and cleanup**; do not poll forever after route change or unmount.
- [ ] **Step 4: Add map sources/layers** for Potential Loss, Potential Gain, repeated anomaly, uncertainty and optional raster overlays.
- [ ] **Step 5: Replace hard-coded tide sparkline with the returned tide status/series and show missing coverage.
- [ ] **Step 6: Replace percentage confidence for TideAware results with ordinal uncertainty and `NOT VALIDATED` status.
- [ ] **Step 7: Keep the existing pairwise `Compare` button and candidate layer behavior unchanged.
- [ ] **Step 8: Run component tests, `npm run typecheck` and a browser smoke test.**

### Task 8: Persist alerts/evidence from TideAware patches

**Files:**
- Create: `supabase/migrations/0003_tideaware_alerts.sql`
- Modify: `api/tideaware_routes.py`
- Modify: `components/explorer/SceneInspector.tsx`
- Create: `api/test_tideaware_alerts.py`

**Interfaces:**
- `POST /api/v1/tideaware/runs/{run_id}/promote-patch/{patch_id}` → creates an `uncertain`/`tide_sensitive` alert with provenance.
- `POST /api/v1/alerts/{alert_id}/evidence` → records field or external evidence.

- [ ] **Step 1: Write tests** ensuring a patch cannot be promoted as confirmed loss and that run/scene/layer provenance is attached.
- [ ] **Step 2: Add alert fields** for `run_id`, `track`, `label`, `uncertainty_level`, `validation_status`, `area_ha` and `source_layer`.
- [ ] **Step 3: Add a UI action** for field verification that creates evidence rather than changing the detection label.
- [ ] **Step 4: Run database/API tests and verify RLS behavior.**

### Task 9: Add L-TAE as an experimental, isolated stage

**Files:**
- Create: `api/tideaware/ltae.py`
- Create: `api/tideaware/ltae_worker.py` or worker stage in `api/worker.py`
- Create: `api/test_tideaware_ltae.py`
- Modify: `api/requirements-ml.txt` or worker-only dependency definition
- Modify: `TideAware_AI_Engine.ipynb` only if the production implementation changes the reference algorithm

**Interfaces:**
- `train_ltae(reference_stack, config) -> LtaeTrainingReport`
- `predict_monitoring_residuals(model, reference_stack, monitoring_stack) -> ResidualResult`

- [ ] **Step 1: Write tests** for deterministic seed/device reporting, train/validation/test separation and no prediction when reference scenes are insufficient.
- [ ] **Step 2: Implement L-TAE in a worker-only environment**; do not add PyTorch to the web API image.
- [ ] **Step 3: Fix the notebook’s current limitation by generating Monitoring residuals, not only held-out Reference predictions.
- [ ] **Step 4: Report L-TAE metrics separately from anomaly labels and require an explicit feature flag before using them in production decisions.
- [ ] **Step 5: Run ML tests on CPU fixture data and record model artifact/version in the manifest.**

### Task 10: End-to-end verification and operational handoff

**Files:**
- Create: `api/test_tideaware_e2e.py`
- Create: `docs/tideaware-operations.md`
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `render.yaml`

- [ ] **Step 1: Add a fixture-backed end-to-end test** from six scenes through status, manifest and GeoJSON output.
- [ ] **Step 2: Add a failure test** for partial tide, incompatible grid, missing band, worker retry and storage failure.
- [ ] **Step 3: Run `python -m unittest discover -s api -t . -p "test_*.py"`.
- [ ] **Step 4: Run `npm run typecheck` and `npm test -- --run`.
- [ ] **Step 5: Run `npm run build` and a deployed/staging smoke test.
- [ ] **Step 6: Document local setup, worker setup, object storage, retention, cleanup, thresholds and validation limitations.
- [ ] **Step 7: Verify that the current pairwise comparison still works after TideAware integration.

## Required decisions before implementation

The plan assumes the following defaults, but these need your confirmation before code work begins:

1. **Production data path:** use a background worker and durable object storage; do not run six-scene TideAware processing inside a FastAPI request or browser.
2. **Initial algorithm scope:** ship OLS + Robust Z + mask + CUSUM + uncertainty first; keep L-TAE experimental until its Monitoring residual path and validation are implemented.
3. **Raster source:** prefer the existing Harmony GeoTIFF pipeline for the first integration only if the unit/grid compatibility gate passes; otherwise add a raw HDF5 ingestion worker for notebook parity.
4. **Track UX:** default to “Both tracks, independently” with per-track results, while allowing a single-track run for debugging.
5. **Storage:** use Supabase/PostGIS for metadata and Supabase Storage or an S3-compatible bucket for GeoTIFF/GeoJSON/model assets.
6. **Validation language:** keep all website copy as “Potential/Unvalidated” until independent GMW or field reference data is supplied.

## Not included in the first implementation

- Automatic “confirmed loss” decisions.
- F1/Accuracy/Kappa or any supervised performance score without reference truth.
- Automated field verification workflow beyond creating evidence records.
- Training L-TAE on every user request.
- Replacing the existing two-scene comparison flow.
