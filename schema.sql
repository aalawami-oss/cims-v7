-- ═══════════════════════════════════════════════════════════════════════════
-- CIMS v7 — Supabase Schema
-- Run this entire file in the Supabase SQL editor (Dashboard → SQL Editor)
-- ═══════════════════════════════════════════════════════════════════════════

-- ── Accounts ─────────────────────────────────────────────────────────────────
create table if not exists accounts (
  id               text primary key,
  account_name     text not null,
  brand_name       text not null,
  branches         integer default 0,
  sector           text,
  last_call_date   date,
  contact_person   text,
  notes            jsonb  default '[]'::jsonb,
  extra_fields     jsonb  default '{}'::jsonb,
  is_deleted       boolean default false,
  created_at       timestamptz default now(),
  updated_at       timestamptz default now()
);

-- Auto-update updated_at
create or replace function update_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end; $$;

drop trigger if exists accounts_updated_at on accounts;
create trigger accounts_updated_at
  before update on accounts
  for each row execute function update_updated_at();

-- ── Account deletions log ─────────────────────────────────────────────────────
create table if not exists account_deletions (
  id               uuid primary key default gen_random_uuid(),
  account_id       text not null references accounts(id),
  deleted_by_id    text,
  deleted_by_name  text,
  deleted_at       timestamptz default now(),
  restored         boolean default false,
  restored_at      timestamptz
);

-- ── Call logs (separate table for analytics) ─────────────────────────────────
create table if not exists call_logs (
  id           uuid primary key default gen_random_uuid(),
  account_id   text references accounts(id),
  date         date not null,
  text         text,
  member_id    text,
  status_id    text,
  extra_fields jsonb default '{}'::jsonb,
  created_at   timestamptz default now()
);

-- ── Users ─────────────────────────────────────────────────────────────────────
create table if not exists users (
  id           text primary key,
  name         text not null,
  email        text unique,
  role         text default 'viewer',
  color        text default '#6C3FC5',
  bg           text default '#EDE9FC',
  extra_fields jsonb default '{}'::jsonb,
  created_at   timestamptz default now()
);

-- ── Indexes for performance ───────────────────────────────────────────────────
create index if not exists idx_accounts_is_deleted    on accounts(is_deleted);
create index if not exists idx_accounts_last_call     on accounts(last_call_date);
create index if not exists idx_accounts_sector        on accounts(sector);
create index if not exists idx_call_logs_account_id   on call_logs(account_id);
create index if not exists idx_call_logs_date         on call_logs(date);
create index if not exists idx_call_logs_member_id    on call_logs(member_id);
create index if not exists idx_deletions_account_id   on account_deletions(account_id);
create index if not exists idx_deletions_restored     on account_deletions(restored);

-- ── Row Level Security (enable for production) ────────────────────────────────
-- Uncomment to enable RLS after confirming your auth setup:
-- alter table accounts          enable row level security;
-- alter table account_deletions enable row level security;
-- alter table call_logs         enable row level security;
-- alter table users             enable row level security;

-- Example policy (allow all authenticated users to read):
-- create policy "allow_read" on accounts for select using (auth.role() = 'authenticated');
-- create policy "allow_write" on accounts for all using (auth.role() = 'authenticated');
