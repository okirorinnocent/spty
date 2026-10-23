-- Run this once in Supabase: SQL Editor -> New query -> paste -> Run.
create table if not exists public.reports (
  id             bigint generated always as identity primary key,
  received_at    timestamptz not null default now(),
  device_id      text        not null check (char_length(device_id) between 1 and 64),
  local_id       integer,
  recorded_at    timestamptz not null,
  cpu_percent    real check (cpu_percent    between 0 and 100),
  memory_percent real check (memory_percent between 0 and 100),
  disk_free_gb   real check (disk_free_gb  >= 0),
  disk_total_gb  real check (disk_total_gb >= 0),
  health_status  text        not null check (health_status in ('ok','warn','critical')),
  unique (device_id, recorded_at)      -- makes agent retries idempotent
);

-- Lock the table: with RLS on and no policies, only the server's service_role key can touch it.
alter table public.reports enable row level security;

-- Optional retention (30 days). Needs the pg_cron extension (Database -> Extensions).
-- select cron.schedule('opendiag-retention', '0 3 * * *',
--   $$ delete from public.reports where received_at < now() - interval '30 days' $$);
