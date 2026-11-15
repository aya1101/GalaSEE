# Map Analysis Copilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a session-scoped Vietnamese map chatbot that explains approved NISAR/ASF knowledge, reads live TideAware analytics, and executes safe reversible map actions without treating demo data or candidate change as scientific truth.

**Architecture:** Add a typed Copilot API to the FastAPI backend. The API combines an approved filesystem knowledge base, read-only live tools, and an OpenRouter adapter behind a small provider interface, then streams validated answer events over SSE. The Next frontend sends one canonical `MapContext`, renders citations and progress, and executes only allowlisted UI commands with an undo stack. Comparison/change-detection actions are explicitly deferred from this chatbot MVP.

**Tech Stack:** FastAPI, Pydantic, httpx, rasterio/numpy existing analytics, Next.js 16, React 19, TypeScript, SSE over `fetch()` streams, OpenRouter Chat Completions, JSON Schema-style Pydantic validation, filesystem cache, Vitest/React Testing Library. Playwright/E2E is intentionally deferred.

**Spec:** `docs/superpowers/specs/2026-11-15-map-analysis-copilot-design.md`

## Global Constraints

- MVP is for one internal user/session at a time. No login, multi-user permissions, or shared conversation store.
- Earthdata and LLM credentials remain server-side. They must never enter browser state, citations, logs, or LLM context.
- Knowledge retrieval may use only approved NASA/JPL, ASF, and CMR sources in the source registry.
- Scene values come from ASF/CMR metadata or cached HDF5/GeoTIFF analytics, never from LLM generation or raster colors.
- Catalog and asset truth must be separate: `catalogMode` is `earthdata|demo|error`, `assetMode` is `live|cached|unavailable`, and `dataStatus` is `ready|partial|unknown|error`.
- `contextVersion` invalidates tool results after scene, band, AOI, or layer changes.
- Safe UI actions execute immediately and are undoable. Comparison/change-detection actions are not exposed by the chatbot MVP; downloads and other expensive operations are also outside its action allowlist.
- Candidate change is always labeled as a candidate requiring verification, never as mangrove loss, deforestation, or legal violation.
- Nodata and invalid pixels must not be converted to zero.
- TypeScript typecheck, Python unit tests, and production build must pass before handoff.

## Review Focus

- Earthdata upstream failure versus an empty search result must remain distinguishable; test the `demo-fallback` regression in the Next proxy.
- A scene catalog record without a cached raster must return `PARTIAL` or `UNKNOWN`, never fabricated raster statistics.
- A stale response from an earlier scene/band must not update the current map; test `contextVersion` rejection.
- An LLM-produced action must be rejected if it is not in the allowlist or lacks valid arguments; test malformed and expensive actions.
- A document or metadata chunk containing instruction-like text must be treated as data, not as an instruction to the agent.
- A catalog record with a cached raster must report both truths, not collapse `earthdata` and `cached` into one mode.
- Missing `OPENROUTER_API_KEY` must disable only the copilot; map and analytics continue to work.
- The copilot must not expose comparison tools or actions until a later scope decision.

---

### Task 0: Add the frontend test harness before implementing the copilot UI

**Files:**
- Modify: `package.json`
- Create: `vitest.config.ts`
- Create: `tests/setup.ts`

**Interfaces:**
- `npm.cmd test` runs Vitest with jsdom and React Testing Library.

- [ ] **Step 1: Add test dependencies and scripts**

  Add `vitest`, `@vitejs/plugin-react`, `jsdom`, `@testing-library/react`, and `@testing-library/jest-dom` as development dependencies. Add `test` and `test:watch` scripts without changing the existing `dev`, `build`, or `typecheck` scripts.

- [ ] **Step 2: Configure deterministic test setup**

  Configure jsdom, React JSX transformation, and jest-dom matchers. Frontend tests use the mock provider and must not require an OpenRouter key.

- [ ] **Step 3: Verify the harness**

  ```powershell
  npm.cmd test -- --run
  npm.cmd run typecheck
  ```

  Expected: the empty test suite starts successfully and existing TypeScript checks remain green.

- [ ] **Step 4: Commit**

  ```powershell
  git add package.json vitest.config.ts tests/setup.ts
  git commit -m "test: add frontend copilot test harness"
  ```

---

### Task 1: Establish data truth contracts and remove silent demo fallback

**Files:**
- Create: `api/copilot_models.py`
- Modify: `api/main.py:350-379,676-730`
- Modify: `app/api/earthdata/geojson/route.ts`
- Modify: `app/page.tsx:434-498,731-733`
- Test: `api/test_copilot_models.py`
- Test: `api/test_earthdata_truth.py`
- Test: `app/api/earthdata/geojson/route.test.ts` or the repository's chosen route-test location

**Interfaces:**
- Produces `CatalogMode = Literal["earthdata", "demo", "error"]`, `AssetMode = Literal["live", "cached", "unavailable"]`, and `DataStatus = Literal["ready", "partial", "unknown", "error"]`.
- Produces `MapContext`, `SourceProvenance`, `ToolStatus`, `CopilotStatus` Pydantic models.
- Produces `EarthdataTruthResponse` with `catalogMode`, `assetMode`, `dataStatus`, `source`, `freshness`, `errorCode`, and payload.
- Frontend `dataSource` is replaced or extended with the three explicit fields; it must not infer catalog truth from cache status.

- [ ] **Step 1: Write failing tests for source classification**

  Add tests that assert:

  - successful Earthdata response is `earthdata`;
  - a successful Earthdata catalog record with a local cached raster is `catalogMode=earthdata`, `assetMode=cached`;
  - missing API configuration is `demo` only when the response explicitly says demo;
  - upstream timeout/error is `catalogMode=error`, not `demo` and not `earthdata`;
  - an empty successful catalog is distinguishable from an upstream error.

- [ ] **Step 2: Run the tests and verify the current fallback fails**

  Run:

  ```powershell
  python -m unittest api.test_earthdata_truth -v
  ```

  Expected: failure showing the current `demo-fallback` header can be interpreted as Earthdata and the backend returns an indistinguishable empty list on errors.

- [ ] **Step 3: Implement typed truth models and explicit source headers**

  Define the models in `api/copilot_models.py`. Update `earthdata_scene_catalog()` and Earthdata proxy responses so upstream errors return an explicit error payload/status, while a successful empty result remains a valid empty result.

  Change the Next proxy to emit one of the exact `DataMode` values. Remove the frontend rule that maps every non-`demo` value to Earthdata.

- [ ] **Step 4: Update topbar and initial map state**

  Make `app/page.tsx` show separate catalog/asset badges such as `Earthdata · cache sẵn`, `Earthdata · chưa cache`, `Dữ liệu mô phỏng`, or `Nguồn dữ liệu lỗi`. The map may still render demo data for visual continuity, but the status and copilot context must say it is demo.

- [ ] **Step 5: Run the focused tests**

  Run:

  ```powershell
  python -m unittest api.test_earthdata_truth api.test_copilot_models -v
  npm.cmd run typecheck
  ```

  Expected: all tests pass and no source mode is represented by an unrecognized string.

- [ ] **Step 6: Commit**

  ```powershell
  git add api/copilot_models.py api/main.py app/api/earthdata/geojson/route.ts app/page.tsx api/test_copilot_models.py api/test_earthdata_truth.py app/api/earthdata/geojson/route.test.ts
  git commit -m "feat: make data provenance explicit"
  ```

### Task 2: Create canonical MapContext and SceneTruth endpoints

**Files:**
- Create: `api/copilot_context.py`
- Create: `api/aoi_registry.py`
- Modify: `api/main.py:709-730,969-1018`
- Modify: `app/page.tsx:13-35,434-478,570-609`
- Create: `app/api/copilot/context/route.ts`
- Test: `api/test_copilot_context.py`

**Interfaces:**
- `build_map_context(...) -> MapContext`.
- `GET /api/v1/copilot/context` returns the current backend-safe context when supplied with scene/band/AOI/layer query parameters.
- `POST /api/v1/analytics/scene-truth` accepts `{scene, collection, requestedBands}` and returns catalog metadata merged with raster/cache metadata.
- `SceneTruth` includes `catalogMode`, `assetMode`, `dataStatus`, scene ID, acquisition time, collection, product, orbit, track, frame, geometry, bands, frequency, CRS, resolution, nodata, cache status, freshness, and source provenance.
- `AoiRegistry` resolves a session-scoped `aoiId`/`aoiHash` to validated server-side GeoJSON; raw geometry is never put into the system prompt.

- [ ] **Step 1: Write failing tests for context versioning**

  Add tests that assert:

  - identical context inputs produce the same `contextVersion`/hash;
  - changing scene, band, AOI, or layer state changes the version;
  - AOI is represented by a stable ID/hash rather than copied into every downstream prompt;
  - context never contains Earthdata or LLM credentials.

- [ ] **Step 2: Write failing tests for SceneTruth merging**

  Use a fake catalog record and a small temporary GeoTIFF. Assert that catalog metadata and raster metadata are merged, that `catalogMode=earthdata` can coexist with `assetMode=cached`, and that missing raster cache returns `assetMode=unavailable`/`PARTIAL` with no fabricated statistics.

- [ ] **Step 3: Implement `build_map_context` and `SceneTruth`**

  Use canonical JSON serialization and SHA-256 for AOI/context hashes. Add `api/aoi_registry.py` to validate and resolve the configured study-area AOI or a session-owned AOI. Store only `aoiId` and `aoiHash` in the LLM-facing context. Keep geometry server-side for analytics calls and reject unknown/mismatched hashes.

- [ ] **Step 4: Implement the scene-truth endpoint**

  Reuse `find_scene_record`, `_scene_metadata`, `raster_metadata`, and cache lookup. Make the endpoint report `catalogStatus`, `rasterStatus`, `catalogMode`, `assetMode`, and `dataStatus` separately so the agent can distinguish “scene exists” from “raster is ready”.

- [ ] **Step 5: Wire the frontend context**

  Add a single `mapContext` memo/state object in `app/page.tsx`. Increment it when scene, band, AOI, layer visibility, or timeline changes. Include `catalogMode`, `assetMode`, `dataStatus`, `aoiId`, and `aoiHash` in copilot requests and use it to reject stale tool results.

- [ ] **Step 6: Run tests**

  ```powershell
  python -m unittest api.test_copilot_context api.test_gcov_analytics api.test_gcov_inspection -v
  npm.cmd run typecheck
  ```

  Expected: SceneTruth tests pass and context contains no credentials.

- [ ] **Step 7: Commit**

  ```powershell
  git add api/copilot_context.py api/main.py app/page.tsx app/api/copilot/context/route.ts api/test_copilot_context.py
  git commit -m "feat: add canonical map context and scene truth"
  ```

### Task 3: Build the approved knowledge base and claim registry

**Files:**
- Create: `api/knowledge_base.py`
- Create: `api/knowledge_models.py`
- Create: `knowledge/sources.json`
- Create: `knowledge/claims.json`
- Create: `knowledge/snapshots/README.md`
- Create: `knowledge/documents/README.md`
- Create: `scripts/snapshot_knowledge.py`
- Create: `scripts/index_knowledge.py`
- Test: `api/test_knowledge_base.py`

**Interfaces:**
- `SourceRecord`, `DocumentRecord`, `ClaimRecord` Pydantic models.
- `KnowledgeBase.search(query, topics, limit) -> list[KnowledgeChunk]`.
- `KnowledgeBase.get_claim(claim_id) -> ClaimRecord | None`.
- `snapshot_knowledge.py` supports `--check`, `--fetch-approved`, and `--verify` and never accepts a URL from the LLM.
- `index_knowledge.py` supports `--check`, `--rebuild`, and writes a versioned local index.

- [ ] **Step 1: Add source registry fixtures**

  Register only the approved NASA/JPL GCOV specification, ASF GCOV guide, ASF HDF5 format guide, ASF search API guide, and NASA CMR API documentation. Each record must contain canonical URL, authority, version/retrieved date, status, content hash, and snapshot path.

- [ ] **Step 2: Write failing retrieval and approval tests**

  Assert that:

  - approved sources are searchable;
  - deprecated/unapproved sources are excluded;
  - every returned chunk has URL, authority, version, anchor, and source ID;
  - claims about HHHH/HVHV retrieve the ASF/NASA source;
  - instruction-like text inside a chunk is returned as data and cannot alter tool policy.

- [ ] **Step 3: Implement filesystem index**

  Implement the snapshot gate first: fetch only canonical allowlisted URLs, save immutable snapshots, verify SHA-256, and require `status=approved` before indexing. Keep MVP retrieval filesystem-based and versioned. Use deterministic chunk IDs based on document hash and anchor. Do not add a vector database until retrieval tests show full-text search is insufficient.

- [ ] **Step 4: Add claim registry**

  Store approved claims for HHHH/HVHV, gamma-naught, mask, nodata, pixel spacing, dB display, candidate change, AOI, and footprint. Each claim must specify allowed answer types and its source anchor.

- [ ] **Step 5: Run indexing and tests**

  ```powershell
  python scripts/index_knowledge.py --check
  python -m unittest api.test_knowledge_base -v
  ```

  Expected: index is deterministic, all sources are approved, and no unapproved URL is returned.

- [ ] **Step 6: Commit**

  ```powershell
  git add api/knowledge_base.py api/knowledge_models.py knowledge scripts/index_knowledge.py api/test_knowledge_base.py
  git commit -m "feat: add approved NISAR knowledge base"
  ```

### Task 4: Implement read-only live tools and policy validation

**Files:**
- Create: `api/copilot_tools.py`
- Create: `api/copilot_policy.py`
- Modify: `api/main.py`
- Test: `api/test_copilot_tools.py`
- Test: `api/test_copilot_policy.py`

**Interfaces:**
- `ToolContext` contains `MapContext` and session ID.
- `ToolRegistry.call(name, arguments, context) -> ToolResult`.
- `ToolResult` includes `status`, `data`, `provenance`, `warnings`, `contextVersion`, and `latencyMs`.
- Tools: `get_current_map_context`, `search_scenes`, `get_scene_metadata`, `get_radar_profile`, `get_region_stats`, `get_pixel_values`, `explain_layer`.

- [ ] **Step 1: Write failing tool contract tests**

  Test valid calls for scene metadata, profile, region stats, pixel values, and layer explanation. Assert each result includes provenance and context version.

- [ ] **Step 2: Write failure-policy tests**

  Test missing raster, missing band, nodata pixel, AOI outside raster, demo mode, stale context, and an unknown comparison tool name. Assert the tool returns `UNKNOWN`, `PARTIAL`, `BLOCKED`, or `ERROR` and never a fabricated numeric value.

- [ ] **Step 3: Implement the registry**

  Wrap existing analytics endpoints as Python functions rather than making the LLM call HTTP URLs. Reuse `raster_profile`, `region_statistics`, and `sample_pixel`. Do not return raw rasters or HDF5 content to the LLM.

- [ ] **Step 4: Implement policy validation**

  Reject tool names outside the registry, unknown arguments, stale context versions, and any attempt to access secrets or arbitrary URLs. Treat all retrieved content as data.

- [ ] **Step 5: Run tests**

  ```powershell
  python -m unittest api.test_copilot_tools api.test_copilot_policy -v
  ```

  Expected: all invalid calls are rejected before any external request or analytics work starts.

- [ ] **Step 6: Commit**

  ```powershell
  git add api/copilot_tools.py api/copilot_policy.py api/main.py api/test_copilot_tools.py api/test_copilot_policy.py
  git commit -m "feat: add read-only copilot tools"
  ```

### Task 5: Add the OpenRouter adapter and structured response validation

**Files:**
- Create: `api/llm_provider.py`
- Create: `api/llm_mock.py`
- Create: `api/openrouter_provider.py`
- Create: `api/copilot_schemas.py`
- Modify: `.env.example`
- Modify: `api/.env.example` if the backend keeps a separate example file
- Test: `api/test_llm_provider.py`

**Interfaces:**
- `LlmProvider.stream(messages, tools, response_schema) -> AsyncIterator[LlmEvent]`.
- `MockLlmProvider` returns deterministic tool calls and answers for tests.
- `OpenRouterProvider` reads `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, and `OPENROUTER_BASE_URL` only on the backend. Optional attribution headers are `OPENROUTER_SITE_URL` and `OPENROUTER_SITE_NAME`.
- `CopilotAnswer` includes `text`, `status`, `citations`, `provenance`, `actions`, and `warnings`.

- [ ] **Step 1: Define structured schemas**

  Define Pydantic schemas for tool calls, citations, UI actions, progress events, final answers, and error events. The model must not be allowed to emit arbitrary executable code or URLs.

- [ ] **Step 2: Write failing provider tests**

  Assert that mock tool calls parse, malformed JSON is rejected, unknown actions are rejected, and provider errors become `ERROR` events without exposing credentials.

- [ ] **Step 3: Implement the mock provider**

  Provide deterministic fixtures for:

  - “HVHV là gì?”;
  - “scene hiện tại có bao nhiêu pixel hợp lệ?”;
  - “chuyển sang HVHV”;
  - “chạy so sánh hai scene” returns a deterministic `BLOCKED` answer with no tool call or action.

- [ ] **Step 4: Implement the OpenRouter provider**

  Call `POST https://openrouter.ai/api/v1/chat/completions` with Bearer authentication, `model`, `messages`, `tools`, `tool_choice`, `parallel_tool_calls=false`, and `stream=true`. Implement the standard tool loop: parse a model `tool_call`, execute the registered local tool, append the validated tool result, then request the next model event. OpenRouter never executes TideAware tools itself. Do not use OpenRouter server tools/web search in this MVP. Use explicit timeout, request ID, cancellation and response-size limits. The adapter is disabled when `OPENROUTER_API_KEY` is absent and the map/analytics remain available.

  Use a model capability configuration for structured output: prefer validated tool-call JSON; use `response_format` only for models/providers that advertise support. Pydantic validation remains mandatory for every model event.

- [ ] **Step 5: Add prompt policy**

  The system prompt must state that live tools are authoritative for scene values, approved sources are authoritative for concepts, candidate change is not forest loss, and comparison is not an available chatbot action in this MVP. Include the current `MapContext` as data, not instructions.

- [ ] **Step 6: Run tests**

  ```powershell
  python -m unittest api.test_llm_provider -v
  ```

  Expected: provider tests pass without a real LLM key.

- [ ] **Step 7: Commit**

  ```powershell
  git add api/llm_provider.py api/llm_mock.py api/openrouter_provider.py api/copilot_schemas.py .env.example api/.env.example api/test_llm_provider.py
  git commit -m "feat: add OpenRouter copilot provider"
  ```

### Task 6: Implement Copilot SSE API and audit logging

**Files:**
- Create: `api/copilot.py`
- Create: `api/copilot_audit.py`
- Modify: `api/main.py`
- Create: `app/api/copilot/chat/route.ts`
- Test: `api/test_copilot_api.py`

**Interfaces:**
- `POST /api/v1/copilot/chat` accepts `conversationId`, `message`, `mapContext`, and optional `clientRequestId`.
- Response is `text/event-stream` with `status`, `tool`, `token`, `citation`, `action`, `warning`, `done`, and `error` events.
- Audit records contain session ID, source IDs, tool names, latency, answer status, context version, and provider/model version, but never prompt secrets or tokens.
- The endpoint enforces `maxToolRounds=4`, `maxToolsPerRequest=6`, bounded message/answer sizes, and a total request timeout. `conversationId` is server-generated or bound to the current short-lived session; clients cannot read another session's history.

- [ ] **Step 1: Write failing SSE tests**

  Assert event order for a knowledge-only answer and a tool-backed answer. Assert `done` includes answer ID and status. Assert stale context and provider failure emit `error` and close the stream.

- [ ] **Step 2: Implement the orchestration loop**

  The endpoint should:

  1. validate request and context;
  2. emit `status`;
  3. retrieve approved knowledge chunks;
  4. let the LLM select only registered read-only tools;
  5. run tools with policy checks;
  6. validate final answer, citations, and the absence of comparison actions;
  7. emit tokens/actions/citations;
  8. write audit record;
  9. emit `done`.

- [ ] **Step 3: Add cancellation and timeout handling**

  Cancel in-flight tool/provider work when the request disconnects. Enforce a bounded total request time and return a request ID for support/debugging.

- [ ] **Step 4: Add the Next proxy**

  Proxy the SSE body without buffering, keep credentials server-side, and preserve `Content-Type`, `Cache-Control: no-cache`, and connection headers.

- [ ] **Step 5: Run tests**

  ```powershell
  python -m unittest api.test_copilot_api -v
  npm.cmd run typecheck
  ```

  Expected: the mock provider streams events and the proxy does not convert them into a buffered JSON response.

- [ ] **Step 6: Commit**

  ```powershell
  git add api/copilot.py api/copilot_audit.py api/main.py app/api/copilot/chat/route.ts api/test_copilot_api.py
  git commit -m "feat: stream copilot answers over sse"
  ```

### Task 7: Add chatbot UI, citations, progress, safe actions, and undo

**Files:**
- Create: `components/copilot/CopilotPanel.tsx`
- Create: `components/copilot/CopilotMessage.tsx`
- Create: `components/copilot/CopilotAction.tsx`
- Create: `components/copilot/copilot-types.ts`
- Modify: `app/page.tsx`
- Modify: `app/globals.css`
- Test: `components/copilot/CopilotPanel.test.tsx` or the repository's chosen frontend test location

**Interfaces:**
- `CopilotPanel` receives `mapContext`, `onAction`, and `onUndo` callbacks.
- `CopilotAction` accepts only the typed `UiAction` union from `copilot-types.ts`.
- `useCopilotStream()` consumes SSE events and exposes `messages`, `status`, `cancel`, `send`, and `undoLastAction`.

- [ ] **Step 1: Write frontend tests for stream states**

  Test progress messages, token accumulation, citation rendering, error state, cancel state, and empty/no-data answers.

- [ ] **Step 2: Write frontend tests for action safety**

  Test that `set_radar_band`, `toggle_layer`, `select_scene`, and panel-open actions execute immediately and create undo entries. Test that comparison/change-detection/download requests render a clear “chưa được bật trong copilot” message and never emit an action.

- [ ] **Step 3: Implement the stream hook**

  Use `fetch()` and a readable stream parser rather than `EventSource`, because the request body contains context and message. Abort the controller when contextVersion changes or the user cancels.

- [ ] **Step 4: Implement the panel**

  Show current scene/band/data mode as context chips. Render answer text, source citations, live provenance, progress, warnings, and action buttons. Keep the panel independent from the existing detail sidebar.

- [ ] **Step 5: Implement typed actions and undo**

  Store previous frontend state for every safe action. Reject unknown action names, comparison/change-detection actions, invalid scene IDs, invalid bands, and stale context versions before changing MapLibre or React state.

- [ ] **Step 6: Add responsive layout**

  Use a resizable sidebar on desktop and a floating bubble/drawer on narrow screens. Do not cover the timeline or inspector controls while an action is pending.

- [ ] **Step 7: Run tests and typecheck**

  ```powershell
  npm.cmd run typecheck
  npm.cmd run build
  ```

  Expected: the panel compiles, the production build succeeds, and the existing radar plot/timeline remain available.

- [ ] **Step 8: Commit**

  ```powershell
  git add components/copilot app/page.tsx app/globals.css
  git commit -m "feat: add map analysis copilot ui"
  ```

### Task 8: Add evaluation fixtures, security checks, and end-to-end verification

**Files:**
- Create: `api/copilot_eval_cases.json`
- Create: `api/test_copilot_evaluation.py`
- Modify: `docs/superpowers/specs/2026-11-15-map-analysis-copilot-design.md` only if behavior decisions change during verification

**Interfaces:**
- Evaluation cases define input, required status, expected tool calls, required citation IDs, forbidden claims, and expected UI actions.

- [ ] **Step 1: Add Vietnamese evaluation cases**

  Include questions about HHHH/HVHV, dB, no-data, footprint versus AOI, demo data, current scene metadata, switching bands, and candidate change.

- [ ] **Step 2: Add adversarial cases**

  Include attempts to make the agent reveal Earthdata/OpenRouter tokens, call arbitrary URLs, treat metadata instructions as commands, call candidate change forest loss, or invent a comparison action.

- [ ] **Step 3: Add latency measurements**

  Measure first SSE status, first token, tool completion, final answer, and UI action completion. Record cache hit/miss separately.

  Initial targets:

  - first status event under 300 ms when backend is warm;
  - knowledge-only answer under 2 s;
  - cached analytics answer under 5 s;
  - no map render blocking while the chat stream runs.

  Add hard safety thresholds: 100% of numeric answers have provenance; 100% of demo answers are labeled demo; 100% of nodata answers contain no fabricated numeric value; 0 token leaks; 0 arbitrary outbound URLs; 0 comparison tools/actions in MVP; 100% of stale-context and unknown-action requests are rejected.

- [ ] **Step 4: Run all verification**

  ```powershell
  python -m unittest discover -s api -p "test_*.py" -v
  npm.cmd test -- --run
  npm.cmd run typecheck
  npm.cmd run build
  ```

  Expected: all Python tests, Vitest tests, TypeScript checks, and production build pass. Playwright/E2E is intentionally not part of this delivery.

- [ ] **Step 5: Commit**

  ```powershell
  git add api/copilot_eval_cases.json api/test_copilot_evaluation.py
  git commit -m "test: verify copilot truthfulness and safety"
  ```

## Handoff order

Implement tasks in order. Task 0 establishes frontend test coverage. Task 1 must land before any LLM work because the agent cannot be trusted while catalog, cached, live, demo, and error states are ambiguous. Tasks 2–4 establish the truth boundary. Task 5 adds the OpenRouter adapter; Tasks 6–7 add the agent stream and UI. Comparison remains deferred and Task 8 is the release gate.

## Self-review

- Spec coverage: source registry, live tools, map context, data modes, citations, SSE, action policy, undo, session scope, audit, cache, guardrails, and evaluation each map to a task.
- Type consistency: `MapContext`, `DataMode`, `SceneTruth`, `ToolResult`, `UiAction`, `CopilotAnswer`, and SSE event names are introduced before consumers.
- Main uncovered risks are pinned in Review Focus and assigned to Tasks 1, 2, 4, 5, and 7.
- No vector database, multi-user auth, or model classification is included in this MVP.
