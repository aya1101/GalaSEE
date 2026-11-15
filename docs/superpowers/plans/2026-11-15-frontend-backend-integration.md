# Frontend/Backend Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tích hợp UI landing của branch frontend với explorer, API, chatbot và sidebar của branch `fix-be-fe` mà không làm thay đổi hiệu ứng landing hoặc theme frontend.

**Architecture:** Dùng `fix-be-fe` làm nền tích hợp vì branch này chứa backend/API. Tạo branch riêng `codex/integrate-frontend-into-fix-be`, giữ nguyên landing ở `/`, chuyển explorer thật vào `/explorer?region=can-gio`, và dùng lớp adapter để kết nối UI frontend với logic/backend hiện có. CSS explorer được scope riêng dưới `.explorer-shell` để không ghi đè landing.

**Tech Stack:** Next.js 16 App Router, React, TypeScript, Tailwind CSS 4, MapLibre, Python/FastAPI, OpenRouter, Earthdata/ASF APIs, Vitest.

**Spec:** `C:\Users\Admin\Downloads\TideAware_Product_Technical_Spec.md` và yêu cầu tích hợp hiện tại.

## Global Constraints

- Landing page `/` phải giữ nguyên animation, Earth, starfield, typography và interaction của branch `feature/tideaware-frontend`.
- Explorer thật chỉ bắt đầu áp dụng ở `/explorer?region=can-gio`.
- API, token Earthdata và OpenRouter key chỉ được dùng phía server/backend.
- Không copy nguyên `app/globals.css` của backend lên landing.
- Không gọi dữ liệu demo như dữ liệu thật; phải phân biệt `earthdata`, `cached`, `demo` và `error`.
- Candidate change chỉ được gọi là candidate change, không được gọi là mất rừng hay phá rừng.
- Không commit `.cache/`, `.gstack/`, `.history/`, `.superpowers/` hoặc secret local.
- Không merge trực tiếp vào branch gốc trước khi integration branch build và smoke test đạt.

## Review Focus

- Landing bị đổi theme hoặc mất animation sau khi thêm CSS explorer; test bằng route `/` trước và sau merge.
- Backend `app/page.tsx` ghi đè landing; test rằng file này không còn là route root sau integration.
- Query `region` bị bỏ qua; test `/explorer?region=can-gio` tạo đúng AOI/map context.
- MapLibre/Globe chạy trong SSR; test production build và mở route explorer trong browser.
- API lỗi hoặc thiếu raster bị fallback thành demo; test trạng thái loading/error/empty rõ ràng.

### Ma trận sở hữu file

| Nhóm | Nguồn chính | Cách xử lý |
|---|---|---|
| Landing route và hiệu ứng | `feature/tideaware-frontend` | Giữ nguyên `app/page.tsx`, `LandingHero`, `EarthGlobe`, `Starfield`, `RegionSelector` |
| API/backend/analytics | `fix-be-fe` | Giữ `api/**`, `app/api/**`, `lib/**`, `scripts/**` |
| Chatbot và nội dung sidebar | `fix-be-fe` | Giữ logic, chuyển vào explorer components, áp theme frontend bằng props/CSS adapter |
| Explorer map | `fix-be-fe` | Đưa vào `ExplorerShell`, không dùng làm root page |
| Theme landing | `feature/tideaware-frontend` | Giữ token màu, font, spacing và animation |
| Explorer CSS | Hai branch | Merge thủ công, scope dưới `.explorer-shell` |
| Dependencies/scripts | Hai branch | Giữ script API/test của BE, bổ sung dependency frontend, regenerate lockfile |

### Task 1: Tạo integration branch và bảo vệ worktree

**Files:**
- Modify: không sửa source trong task này
- Test: trạng thái Git và danh sách branch

**Interfaces:**
- Produces: branch `codex/integrate-frontend-into-fix-be` được tạo từ `fix-be-fe`; các thay đổi local hiện tại được bảo toàn.

- [ ] **Step 1: Ghi nhận trạng thái hiện tại**

Run:

```powershell
git status --short --branch
git diff -- postcss.config.mjs package.json package-lock.json next-env.d.ts
```

Expected: xác định rõ thay đổi cần giữ, đặc biệt `postcss.config.mjs`.

- [ ] **Step 2: Bảo toàn thay đổi local**

Dùng stash tạm có message rõ ràng hoặc cơ chế backup tương đương; không dùng `reset --hard`, `checkout --` hoặc xoá file chưa xác minh.

- [ ] **Step 3: Tạo branch tích hợp từ BE**

```powershell
git switch fix-be-fe
git switch -c codex/integrate-frontend-into-fix-be
```

- [ ] **Step 4: Kiểm tra điểm xuất phát**

```powershell
git log --oneline --decorate -5
git status --short --branch
```

Expected: branch mới trỏ tới commit của `fix-be-fe`, không có thay đổi ngoài phần đã bảo toàn.

### Task 2: Merge frontend theo ma trận, giữ backend làm nền

**Files:**
- Modify: các file conflict do merge
- Keep from frontend: `app/page.tsx`, landing components, landing assets/styles
- Keep from backend: `api/**`, `app/api/**`, `lib/**`, `scripts/**`, backend components
- Test: `git diff --check`, route/file inventory

**Interfaces:**
- Consumes: `feature/tideaware-frontend` và branch tích hợp từ Task 1.
- Produces: toàn bộ backend vẫn tồn tại; landing frontend vẫn là root route.

- [ ] **Step 1: Merge không commit tự động**

```powershell
git merge --no-commit --no-ff feature/tideaware-frontend
```

- [ ] **Step 2: Resolve conflict theo ma trận**

Quy tắc bắt buộc:

- `app/page.tsx`: chọn frontend.
- `components/LandingHero.tsx`, `EarthGlobe.tsx`, `Starfield.tsx`, `RegionSelector.tsx`: chọn frontend.
- `api/**`, `app/api/**`, `lib/**`, backend scripts: chọn backend.
- `package.json`: merge thủ công, không chọn nguyên một phía.
- `package-lock.json`: regenerate sau khi `package.json` ổn định.
- `app/globals.css`: merge thủ công ở Task 5.

- [ ] **Step 3: Kiểm tra file bị xoá ngoài ý muốn**

```powershell
git diff --name-status --cached
git diff --check
```

Expected: không mất API, Copilot, analytics, knowledge source hoặc script dev-api.

- [ ] **Step 4: Commit checkpoint merge**

Chỉ commit sau khi danh sách conflict đã được kiểm tra và không còn marker `<<<<<<<`.

### Task 3: Đưa explorer backend vào route riêng

**Files:**
- Create/modify: `components/explorer/ExplorerShell.tsx`
- Create/modify: `components/explorer/ExplorerMap.tsx`
- Create/modify: `components/explorer/ExplorerSidebar.tsx`
- Create/modify: `components/explorer/SceneInspector.tsx`
- Create/modify: `components/explorer/LayerPanel.tsx`
- Create/modify: `components/explorer/TimelineControl.tsx`
- Modify: `app/explorer/page.tsx`
- Avoid using as route: backend `app/page.tsx`
- Test: `app/explorer/page.test.tsx` hoặc test component tương đương

**Interfaces:**
- `ExplorerShell({ region }: { region: string }): JSX.Element`
- `ExplorerMap({ mapContext, onPixelSelect }: ExplorerMapProps): JSX.Element`
- `ExplorerSidebar({ scene, layerState, onLayerChange }: ExplorerSidebarProps): JSX.Element`
- `TimelineControl({ scenes, selectedSceneId, onSceneChange }: TimelineControlProps): JSX.Element`
- `app/explorer/page.tsx` nhận `searchParams: Promise<{ [key: string]: string | string[] | undefined }>` theo Next 16 và truyền region chuẩn hoá vào `ExplorerShell`.

- [ ] **Step 1: Viết test route**

Test kiểm tra `/explorer?region=can-gio` truyền `can-gio`, còn thiếu region dùng default region hợp lệ; không đọc từ hard-code trong component.

- [ ] **Step 2: Tách phần render explorer khỏi backend root page**

Giữ nguyên data fetching/analytics đã ổn định trước; chỉ chuyển phần UI cần thiết vào `ExplorerShell`, tránh rewrite logic bản đồ trong cùng task.

- [ ] **Step 3: Thêm client boundary đúng chỗ**

Các phần sử dụng MapLibre, browser API hoặc event map phải nằm trong client component; page server chỉ đọc query và truyền props.

- [ ] **Step 4: Chạy test route và typecheck**

```powershell
npm run typecheck
npm test -- --run
```

### Task 4: Giữ design chatbot và nội dung hai sidebar của BE

**Files:**
- Modify/create: `components/copilot/CopilotPanel.tsx`
- Modify/create: `components/explorer/ExplorerSidebar.tsx`
- Modify/create: `components/explorer/SceneInspector.tsx`
- Modify/create: `components/explorer/LayerPanel.tsx`
- Test: `components/copilot/CopilotPanel.test.tsx`, explorer sidebar tests

**Interfaces:**
- `CopilotPanel({ mapContext, onUiAction }: CopilotPanelProps): JSX.Element`
- `mapContext` là object thống nhất gồm scene, band, AOI, layer state, data mode và context version.
- Chatbot không tự gọi URL/token; live analytics đi qua backend contract hiện có.

- [ ] **Step 1: Giữ các section UI người dùng đã thích**

Giữ nội dung scene detail, radar signal, layer explanation, provenance và chatbot từ BE; chỉ thay wrapper/theme, không thay đổi ý nghĩa dữ liệu.

- [ ] **Step 2: Chuẩn hoá dữ liệu qua props**

Không để sidebar tự đọc state rải rác hoặc hard-code scene. Tạo adapter từ state explorer sang props của sidebar/chatbot.

- [ ] **Step 3: Test data mode và lỗi**

Test các trạng thái `earthdata`, `cached`, `error`, thiếu raster và nodata; UI phải nói rõ trạng thái thay vì tự hiện số giả.

### Task 5: Merge theme frontend với explorer CSS có scope

**Files:**
- Modify: `app/globals.css`
- Modify: `postcss.config.mjs`
- Possibly modify: `components/explorer/*.tsx` class names
- Test: visual smoke check `/` và `/explorer`

**Interfaces:**
- `.explorer-shell` là namespace CSS của explorer.
- `postcss.config.mjs` tiếp tục dùng `@tailwindcss/postcss`.

- [ ] **Step 1: Giữ nguyên phần CSS landing**

Không thay đổi selector animation, hero, globe, starfield và region modal nếu không cần thiết.

- [ ] **Step 2: Thêm MapLibre CSS và explorer CSS**

Import MapLibre một lần; chuyển selector global của explorer thành selector có tiền tố `.explorer-shell` khi có thể.

- [ ] **Step 3: Dùng theme adapter**

Định nghĩa biến explorer trong `.explorer-shell`, lấy palette/typography từ theme frontend thay vì đổi `body` toàn cục.

- [ ] **Step 4: Kiểm tra Tailwind/PostCSS**

```powershell
npx postcss app/globals.css --no-map
```

Expected: không còn cảnh báo `Unknown at rule: @theme`.

### Task 6: Hợp nhất dependencies, scripts và môi trường

**Files:**
- Modify: `package.json`
- Modify: `package-lock.json`
- Review: `scripts/dev-api.mjs`, `.env.example`, `api/.env.example`, `next.config.ts`
- Test: startup và environment validation

**Interfaces:**
- `npm run dev` chạy web và API qua script backend hiện có.
- `npm run dev:web` chạy Next.
- `npm run dev:api` chạy API.
- Frontend dependencies của landing và backend dependencies cùng tồn tại.

- [ ] **Step 1: Merge scripts, không đổi tên tuỳ ý**

Giữ `dev`, `dev:web`, `dev:api`, `typecheck`, `test`, `build` của BE; thêm dependency frontend còn thiếu.

- [ ] **Step 2: Regenerate lockfile**

Chạy `npm install` sau khi `package.json` ổn định; review lockfile diff, không commit thay đổi không liên quan.

- [ ] **Step 3: Kiểm tra env server-only**

Đảm bảo OpenRouter/Earthdata keys không có prefix `NEXT_PUBLIC_` và không được import vào client component.

- [ ] **Step 4: Smoke test dev**

```powershell
npm run dev
```

Expected: web và API cùng khởi động; nếu port 8000 đã được dùng thì script phải báo lỗi rõ, không làm web chết âm thầm.

### Task 7: Kiểm thử tích hợp và visual regression thủ công

**Files:**
- Test: `tests/integration/` hoặc test hiện có
- Review: `/`, `/explorer?region=can-gio`

**Interfaces:**
- Produces: integration branch có thể review và merge vào `fix-be-fe`.

- [ ] **Step 1: Kiểm tra landing**

Mở `/`; xác nhận animation, Earth, starfield, region selector, font, spacing và CTA không đổi đáng kể.

- [ ] **Step 2: Kiểm tra explorer**

Mở `/explorer?region=can-gio`; xác nhận map, timeline, hai sidebar, chatbot, layer controls và scene detail render được.

- [ ] **Step 3: Kiểm tra API thật/cache**

Xác nhận scene metadata/raster/analytics lấy đúng nguồn; backend lỗi phải hiện error state, không giả lập thành dữ liệu thật.

- [ ] **Step 4: Chạy verification**

```powershell
npm run typecheck
npm test -- --run
npm run build
```

Nếu Windows còn lỗi `EPERM` ở `.next-build`, dừng dev server và xoá/chuyển riêng đúng thư mục build sau khi xác nhận không có process đang giữ file; không dùng lệnh xoá rộng.

- [ ] **Step 5: Review diff cuối**

```powershell
git diff --stat fix-be-fe...HEAD
git diff --check
git status --short
```

Chỉ khi các kiểm tra đạt mới merge branch integration vào `fix-be-fe`; chưa push nếu chưa có yêu cầu.

### Task 8: Merge integration branch vào `fix-be-fe`

**Files:**
- Git history only
- Test: final branch verification

- [ ] **Step 1: Chuyển về branch đích**

```powershell
git switch fix-be-fe
```

- [ ] **Step 2: Merge integration branch**

```powershell
git merge --no-ff codex/integrate-frontend-into-fix-be
```

- [ ] **Step 3: Chạy lại typecheck/build trên branch đích**

Không coi integration branch là đủ; kiểm tra lại sau merge để chắc chắn branch đích nhận đúng commit và không bị conflict resolution mới.

- [ ] **Step 4: Chỉ push khi người dùng yêu cầu**

Không tự động push hoặc force-push.

## Kết quả mong đợi

- `/` là landing frontend nguyên bản.
- `/explorer?region=can-gio` là explorer backend có UI hybrid.
- Chatbot và nội dung hai sidebar được giữ từ BE.
- Palette, typography và cảm giác tổng thể của frontend được giữ.
- Backend/API/analytics vẫn chạy qua `npm run dev`.
- Mọi thay đổi có thể review theo từng checkpoint, không làm bẩn branch gốc.
