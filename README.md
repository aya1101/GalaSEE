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

Open `http://localhost:3000`.

### API

```bash
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API health check is available at `http://localhost:8000/health`.

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
