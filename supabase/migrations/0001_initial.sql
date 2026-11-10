create schema if not exists extensions;

create extension if not exists postgis with schema extensions;
create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  role text not null default 'manager' check (role in ('manager', 'researcher', 'field_team', 'admin')),
  created_at timestamptz not null default now()
);

create table if not exists public.alerts (
  id uuid primary key default gen_random_uuid(),
  area_name text not null,
  status text not null default 'uncertain' check (status in ('high_priority', 'tide_sensitive', 'uncertain', 'no_significant_change')),
  priority_score numeric(6, 3) not null default 0,
  confidence numeric(5, 4),
  tide_delta_m numeric(8, 3),
  acquisition_before timestamptz,
  acquisition_after timestamptz,
  geometry extensions.geometry(Geometry, 4326),
  evidence_summary text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists alerts_geometry_gist on public.alerts using gist (geometry);
create index if not exists alerts_priority_idx on public.alerts (priority_score desc);
create index if not exists alerts_status_idx on public.alerts (status);

create table if not exists public.evidence (
  id uuid primary key default gen_random_uuid(),
  alert_id uuid not null references public.alerts(id) on delete cascade,
  source_type text not null check (source_type in ('nisar', 'sentinel', 'tide', 'field_observation', 'other')),
  source_uri text,
  observed_at timestamptz,
  notes text,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists evidence_alert_idx on public.evidence (alert_id);

create table if not exists public.missions (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  status text not null default 'draft' check (status in ('draft', 'planned', 'in_progress', 'verified', 'cancelled')),
  assigned_to uuid references auth.users(id) on delete set null,
  budget_units integer,
  notes text,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.alerts enable row level security;
alter table public.evidence enable row level security;
alter table public.missions enable row level security;

drop policy if exists "users can read their profile" on public.profiles;
create policy "users can read their profile"
  on public.profiles for select
  to authenticated
  using (auth.uid() = id);

drop policy if exists "authenticated users can read alerts" on public.alerts;
create policy "authenticated users can read alerts"
  on public.alerts for select
  to authenticated
  using (true);

drop policy if exists "authenticated users can read evidence" on public.evidence;
create policy "authenticated users can read evidence"
  on public.evidence for select
  to authenticated
  using (true);

drop policy if exists "authenticated users can create evidence" on public.evidence;
create policy "authenticated users can create evidence"
  on public.evidence for insert
  to authenticated
  with check (auth.uid() = created_by);

drop policy if exists "authenticated users can read missions" on public.missions;
create policy "authenticated users can read missions"
  on public.missions for select
  to authenticated
  using (true);

drop policy if exists "authenticated users can create missions" on public.missions;
create policy "authenticated users can create missions"
  on public.missions for insert
  to authenticated
  with check (auth.uid() = created_by);
