# TideAware

Evidence-aware coastal intelligence for mangrove protection.

> Status: initial scaffold. Demo data and Supabase integration are not connected yet.

This repository contains the first deployable slice:

- `app/`: Next.js web app for Vercel.
- `api/`: FastAPI service for Render or another Docker host.
- `supabase/migrations/`: PostgreSQL/PostGIS schema for alerts, evidence and missions.
- Heavy NISAR/GDAL/ML processing stays outside request handlers until the data pipeline is ready.

## Local development

### Web

```bash
npm ci
Copy-Item .env.example .env.local
npm run dev
```

`npm run dev` starts both the Next.js web app and the FastAPI Earthdata proxy. Open `http://localhost:3000`.

For a standalone API process, run `python -m uvicorn api.main:app --port 8000` from the repository root.

The API health check is available at `http://localhost:8000/health`.

### Earthdata streaming

The browser never receives the Earthdata token. Configure the FastAPI service with a protected HTTPS NASA/DAAC URL that returns GeoJSON features using the TideAware properties (`id`, `kind`, `title`, and optional detail fields):

```text
EARTHDATA_TOKEN=your-earthdata-bearer-token
EARTHDATA_DATA_URL=https://your-nasa-data-endpoint.example/regions.geojson
EARTHDATA_ALLOWED_HOSTS=
```

The web app calls `/api/v1/earthdata/geojson`; FastAPI adds `Authorization: Bearer ...` and streams the response. If `EARTHDATA_API_URL` is not configured, the map uses clearly labeled demo GeoJSON so the UI remains usable during setup. NISAR HDF5 scenes should be converted to a small GeoJSON/COG-derived layer before serving to the map; streaming a multi-gigabyte HDF5 file directly into the browser is not suitable for map interaction.

## Supabase setup

1. Create a Supabase project.
2. Enable the `postgis` extension in the `extensions` schema.
3. Run `supabase/migrations/0001_initial.sql` in the Supabase SQL Editor.
4. Copy the project URL and anon key into `.env.local`.

The initial schema stores vector metadata and operational records in PostGIS. The migration is safe to run again in the SQL Editor. Large NISAR/HDF5/COG assets should be stored in object storage, not in database rows.

## Deployment

### Vercel

Import this repository as a Next.js project. Set:

```text
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

Attach the public domain, for example `tideaware.vn`, in Vercel Domains.

### Render API

Create a Render Web Service with `api/` as the root directory, or create it from the root `render.yaml` Blueprint:

```text
Build command: pip install -r requirements.txt
Start command: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Set:

```text
WEB_ORIGIN=https://tideaware.vn
```

Attach `api.tideaware.vn` as the API custom domain. Render will provision HTTPS automatically.

## Verification

```bash
npm run typecheck
npm run build
```

Before opening a pull request, also confirm that no `.env.local` or service credentials are included in the diff.
