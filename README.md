# TideAware

TideAware is an evidence-aware coastal intelligence workspace for monitoring mangrove areas with NISAR GCOV data.

The repository currently contains an integrated local slice:

- Next.js explorer UI with the landing-page theme, English/Vietnamese language switch, map layers, AOI focus, scene timeline, and right-side inspector.
- FastAPI service for Earthdata streaming, GCOV preview/cache, raster analytics, and Copilot SSE responses.
- Demo GeoJSON fallback when live Earthdata is not configured.
- Supabase/PostGIS migration files for the operational data model.

## Architecture

```text
app/                 Next.js routes and web entry points
components/          Explorer, Copilot, map and shared UI components
lib/                 GeoJSON and browser-side configuration helpers
api/                 FastAPI service and Python tests
scripts/dev-api.mjs  Cross-platform API launcher with automatic reload
supabase/            PostGIS migrations
public/              Static assets
```

## Requirements

- Node.js `>=20.9.0`
- npm
- Python `>=3.11`
- Python packages from `api/requirements.txt`

On Windows, the development launcher prefers `api/.venv/Scripts/python.exe` when that environment exists. On macOS/Linux it looks for `api/.venv/bin/python`.

## Local development

### Windows PowerShell

Run these commands from the repository root:

```powershell
npm ci
Copy-Item .env.example .env
py -3 -m venv api/.venv
api/.venv/Scripts/python.exe -m pip install -r api/requirements.txt
npm run dev
```

### macOS/Linux

```bash
npm ci
cp .env.example .env
python3 -m venv api/.venv
api/.venv/bin/python -m pip install -r api/requirements.txt
npm run dev
```

The single `npm run dev` command starts both services:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- API health: `http://localhost:8000/health`

The API reads the shared root `.env` file. Next.js also reads this file, so it is the simplest local setup. `.env.local` is ignored by Git as well, but backend values placed only there will not be loaded by the FastAPI process.

### Development reload

Both sides reload during development:

- Next.js handles frontend changes through its normal dev server.
- On Windows, `scripts/dev-api.mjs` watches `api/**/*.py` and restarts the FastAPI process after a Python change.
- On macOS/Linux, the launcher passes Uvicorn's `--reload` flags.

To disable backend reload temporarily:

```powershell
$env:TIDEAWARE_API_RELOAD = "0"
npm run dev:api
```

For a standalone API process from the repository root:

```bash
python -m uvicorn api.main:app --port 8000
```

If port `8000` already has a healthy TideAware API, the development launcher reuses it. Stop the old process when you need to load a different environment or dependency set.

### Sharing the frontend with ngrok

Expose the Next.js port, not the API port:

```bash
ngrok http 127.0.0.1:3000
```

Use the explicit IPv4 target above instead of `ngrok http 3000`; on Windows, `localhost` may resolve to `[::1]` while the dev server is bound to IPv4. The Next.js config allows `*.ngrok-free.dev` and `*.ngrok.io` for development-only assets. This is required by Next.js 16 so client-only features such as the 3D globe can hydrate through the tunnel. Production builds do not use this dev-origin allowlist.

## Environment configuration

Start with `.env.example`. The most important values are:

```text
# Leave blank for local Next.js proxy routes.
NEXT_PUBLIC_API_URL=

# Used by Next.js server routes to reach FastAPI.
EARTHDATA_API_URL=http://localhost:8000

# Required for live NASA/ASF requests.
EARTHDATA_TOKEN=
EARTHDATA_DATA_URL=
EARTHDATA_ALLOWED_HOSTS=

# Local cached GCOV rasters and analytics.
GCOV_CACHE_DIR=.cache/gcov
GCOV_INSPECTION_TTL_SECONDS=21600

# Optional Copilot provider.
OPENROUTER_API_KEY=
OPENROUTER_MODEL=
```

Without `EARTHDATA_TOKEN` and `EARTHDATA_DATA_URL`, the explorer uses the clearly labeled demo catalog. Live Earthdata URLs must be HTTPS NASA/Earthdata URLs, unless the host is explicitly added to `EARTHDATA_ALLOWED_HOSTS`.

The browser never receives `EARTHDATA_TOKEN`. The FastAPI service adds the bearer token while streaming the upstream response. Large HDF5 files are processed through the backend; the browser receives map-friendly GeoJSON, browse images, previews, and analytics results.

OpenRouter is optional. Copilot streaming requires both `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`; the map and Earthdata features remain usable without Copilot configuration.

## Useful commands

```bash
npm run dev          # Start web + API
npm run dev:web      # Start only Next.js
npm run dev:api      # Start only FastAPI
npm run typecheck    # TypeScript validation
npm test             # Vitest test suite
npm run test:watch   # Vitest watch mode
npm run build        # Production Next.js build
```

Python tests can be run from the repository root with:

```bash
python -m unittest discover -s api -t . -p "test_*.py"
```

## Supabase setup

1. Create a Supabase project.
2. Enable the `postgis` extension in the `extensions` schema.
3. Run `supabase/migrations/0001_initial.sql` in the Supabase SQL Editor.
4. Add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` to the environment when the client integration is enabled.

Large NISAR/HDF5/COG assets should remain in object storage or the backend cache, not in database rows.

## Deployment notes

The frontend can be deployed as a Next.js application and the API as a separate Python service. Configure these values in the frontend environment:

```text
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

Configure the API service with:

```text
WEB_ORIGIN=https://tideaware.example.com
EARTHDATA_TOKEN=...
EARTHDATA_DATA_URL=https://...
```

The API must expose HTTPS and allow the deployed frontend origin through `WEB_ORIGIN`.

## Verification checklist

Before opening a pull request:

```bash
npm run typecheck
npm test -- --run
git diff --check
```

If Python dependencies are available, also run:

```bash
python -m unittest discover -s api -t . -p "test_*.py"
```

Never commit `.env`, `.env.local`, Earthdata tokens, OpenRouter keys, downloaded raster files, or local cache contents.
