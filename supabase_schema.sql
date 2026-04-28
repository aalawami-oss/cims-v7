-- ============================================================
-- CIMS — Supabase PostgreSQL Schema
-- Run this in Supabase SQL Editor (Project → SQL Editor → New query)
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── roles ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roles (
  id          TEXT PRIMARY KEY,
  label       TEXT NOT NULL,
  color       TEXT DEFAULT '#6C3FC5',
  bg          TEXT DEFAULT '#EDE9FC',
  perms       TEXT[] DEFAULT '{}',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── users ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id          TEXT PRIMARY KEY DEFAULT ('u' || substr(uuid_generate_v4()::text, 1, 8)),
  name        TEXT NOT NULL,
  email       TEXT UNIQUE NOT NULL,
  role        TEXT REFERENCES roles(id) ON DELETE SET NULL,
  color       TEXT DEFAULT '#6C3FC5',
  bg          TEXT DEFAULT '#EDE9FC',
  extra_fields JSONB DEFAULT '{}',
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── call_statuses ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS call_statuses (
  id          TEXT PRIMARY KEY DEFAULT ('cs' || substr(uuid_generate_v4()::text, 1, 8)),
  label       TEXT NOT NULL,
  color       TEXT DEFAULT '#6C3FC5',
  sort_order  INT  DEFAULT 0,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── custom_fields ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS custom_fields (
  id          TEXT PRIMARY KEY DEFAULT ('f' || substr(uuid_generate_v4()::text, 1, 8)),
  label       TEXT NOT NULL,
  field_type  TEXT NOT NULL CHECK (field_type IN ('text','number','date','select')),
  entity      TEXT NOT NULL CHECK (entity IN ('account','user','call')),
  options     TEXT[] DEFAULT '{}',
  sort_order  INT  DEFAULT 0,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── accounts ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS accounts (
  id             TEXT PRIMARY KEY DEFAULT ('ACC-' || LPAD(nextval('acc_seq')::text, 4, '0')),
  account_name   TEXT NOT NULL,
  brand_name     TEXT NOT NULL,
  branches       INT  DEFAULT 0,
  sector         TEXT,
  last_call_date DATE,
  contact_person TEXT,
  logo_b64       TEXT,
  extra_fields   JSONB DEFAULT '{}',
  created_at     TIMESTAMPTZ DEFAULT NOW(),
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);
CREATE SEQUENCE IF NOT EXISTS acc_seq START 1;

-- ── call_logs ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS call_logs (
  id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  account_id  TEXT REFERENCES accounts(id) ON DELETE CASCADE,
  member_id   TEXT REFERENCES users(id)    ON DELETE SET NULL,
  status_id   TEXT REFERENCES call_statuses(id) ON DELETE SET NULL,
  call_date   DATE NOT NULL DEFAULT CURRENT_DATE,
  notes       TEXT,
  extra_fields JSONB DEFAULT '{}',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── deleted_accounts ───────────────────────────────────────
-- Soft-delete archive with full snapshot + audit fields
CREATE TABLE IF NOT EXISTS deleted_accounts (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  original_id     TEXT NOT NULL,
  account_name    TEXT NOT NULL,
  brand_name      TEXT NOT NULL,
  branches        INT,
  sector          TEXT,
  last_call_date  DATE,
  contact_person  TEXT,
  logo_b64        TEXT,
  extra_fields    JSONB DEFAULT '{}',
  call_logs_json  JSONB DEFAULT '[]',   -- full call history snapshot
  deleted_by      TEXT REFERENCES users(id) ON DELETE SET NULL,
  deleted_by_name TEXT,
  deleted_at      TIMESTAMPTZ DEFAULT NOW(),
  restored_at     TIMESTAMPTZ,
  restored_by     TEXT REFERENCES users(id) ON DELETE SET NULL,
  restored_by_name TEXT,
  is_restored     BOOLEAN DEFAULT FALSE
);

-- ── system_settings ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS system_settings (
  key        TEXT PRIMARY KEY,
  value      TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes ─────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_accounts_sector       ON accounts(sector);
CREATE INDEX IF NOT EXISTS idx_accounts_last_call    ON accounts(last_call_date);
CREATE INDEX IF NOT EXISTS idx_call_logs_account     ON call_logs(account_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_member      ON call_logs(member_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_date        ON call_logs(call_date);
CREATE INDEX IF NOT EXISTS idx_deleted_accounts_date ON deleted_accounts(deleted_at);

-- ── Updated_at trigger ──────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_accounts_updated
  BEFORE UPDATE ON accounts
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_users_updated
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ── Seed default data ────────────────────────────────────────
INSERT INTO roles(id,label,color,bg,perms) VALUES
  ('admin',  'Admin',   '#6C3FC5','#EDE9FC', ARRAY['view','log','add_account','import','manage_users','export','manage_schema']),
  ('manager','Manager', '#085041','#E1F5EE', ARRAY['view','log','add_account','import','export']),
  ('rep',    'Rep',     '#633806','#FAEEDA', ARRAY['view','log']),
  ('viewer', 'Viewer',  '#444441','#F1EFE8', ARRAY['view'])
ON CONFLICT(id) DO NOTHING;

INSERT INTO users(id,name,email,role,color,bg) VALUES
  ('u1','Alawi Alawami',    'a.alawami@foodics.com','admin',  '#6C3FC5','#EDE9FC'),
  ('u2','Sara Al-Zahrani',  'sara@corp.com',        'manager','#0F6E56','#E1F5EE'),
  ('u3','Mohammed Al-Ghamdi','mohammed@corp.com',   'rep',    '#993C1D','#FAECE7'),
  ('u4','Fatima Al-Otaibi', 'fatima@corp.com',      'rep',    '#993556','#FBEAF0'),
  ('u5','Khalid Al-Qahtani','khalid@corp.com',      'viewer', '#854F0B','#FAEEDA')
ON CONFLICT(id) DO NOTHING;

INSERT INTO call_statuses(id,label,color,sort_order) VALUES
  ('cs1','Completed',         '#1D9E75',1),
  ('cs2','No Answer',         '#BA7517',2),
  ('cs3','Follow-up Required','#6C3FC5',3),
  ('cs4','Meeting Scheduled', '#534AB7',4),
  ('cs5','Not Interested',    '#A32D2D',5),
  ('cs6','Voicemail Left',    '#5F5E5A',6)
ON CONFLICT(id) DO NOTHING;

INSERT INTO custom_fields(id,label,field_type,entity,options,sort_order) VALUES
  ('ef1','Region',  'text',  'account','{}',1),
  ('ef2','Priority','select','account',ARRAY['High','Medium','Low'],2),
  ('uf1','Phone',   'text',  'user',   '{}',1),
  ('uf2','Territory','text', 'user',   '{}',2),
  ('cf1','Deal Size','text', 'call',   '{}',1),
  ('cf2','Next Step','text', 'call',   '{}',2)
ON CONFLICT(id) DO NOTHING;

INSERT INTO system_settings(key,value) VALUES
  ('system_name','Client Interaction Management'),
  ('system_logo_b64',NULL)
ON CONFLICT(key) DO NOTHING;

-- ── Row-Level Security (enable after setup) ──────────────────
-- ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE call_logs ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE deleted_accounts ENABLE ROW LEVEL SECURITY;
-- (Add policies per your auth setup)
