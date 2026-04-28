# CIMS — Technical Documentation

---

## Version history

### v1 — Foundation (HTML/React)
**Stack:** Single-file React (CDN), Chart.js, PapaParse, Tailwind-like inline CSS  
**Storage:** In-memory only (resets on refresh)

**What was built:**
- Account data model: ID, Account Name, Brand Name, # of Branches, Last Call Date
- Dashboard with Coverage Rate (30d), Branch Coverage, Overdue count
- Urgency list — accounts with Last Call Date > 14 days
- Searchable, sortable accounts table
- Log Call modal with date and notes
- Team member dropdown on log call (tracks who made each call)
- Weekly calls bar chart (stacked by team member)
- Mock data generator (20 accounts, 90 days of call history)
- Activity Log tab

**Limitations at v1:**
- No persistence; data resets on page refresh
- No roles or permissions
- No CSV import
- Chart had no granularity switching

---

### v2 — Roles, CSV Import, Chart Enhancement (HTML/React)
**Stack:** React (CDN), Chart.js, PapaParse  
**Storage:** In-memory

**What was added:**
- **Role system** — Admin, Manager, Rep, Viewer with 7 permission flags
- **User switcher** — simulate any user's view from the top-right chip
- **CSV / Excel import** — Add new or Update existing by Account ID; preview before import; template download
- **Chart granularity** — Daily (14 periods), Weekly (8), Monthly (12), Yearly (4)
- **Chart navigation** — "← Older / Newer →" pagination for any time range
- Rep role dashboard filter — Reps only see their own calls and accounts
- Call status dropdown — Completed, No Answer, Follow-up Required, Meeting Scheduled, Not Interested, Voicemail Left
- Status badge in Activity Log and account detail view

**Key design decisions:**
- `session_state`-equivalent pattern using React `useState` hooks
- All data kept as flat arrays with JSONB-style note arrays per account

---

### v3 — Field Builder, Chart Types, Settings (HTML/React → Python/Streamlit)
**Stack:** Python 3.11, Streamlit ≥1.32, Plotly, Pandas, PapaParse (moved to Pandas)  
**Storage:** Streamlit `session_state` (in-memory, persists within session)

**Migration rationale:** Streamlit provides native form components, better data table handling, and straightforward deployment via Streamlit Community Cloud.

**What was added:**
- **8 chart types:** Bar, Stacked Bar, Line, Area, Horizontal Bar, Pie, Donut, Scatter
- **Field Builder (admin only):** custom fields for Accounts, Users, and Calls; types: text, number, date, select
- **Custom call statuses** with color picker — add/edit/remove
- **Role manager** — create new roles, set custom label, badge colors, tick any permission
- **System settings tab** — upload system logo, rename app
- **Brand logo per account** — PNG/JPG upload, shown as thumbnail
- **Column visibility** — admin toggles which account table columns are visible
- **Violet theme** — `#6C3FC5` primary color throughout
- Bulk user import via CSV (Name, Email, Role columns)
- Admin: inline Add, Edit, Delete for accounts and users
- Admin changed to Alawi Alawami / a.alawami@foodics.com

**Streamlit architecture notes:**
- All mutable state in `st.session_state`
- `init_state()` runs once and populates defaults + mock data
- Each tab is a separate render function (`render_dashboard`, `render_accounts`, etc.)
- Forms use `st.form` + `form_submit_button` to batch inputs and avoid re-runs on every keypress

---

### v7 — Supabase Backend, Bulk Delete, Deletion Log, Filters (current)
**Stack:** Python 3.11, Streamlit ≥1.32, Plotly, Pandas, supabase-py ≥2.3  
**Storage:** Supabase (Postgres) as primary; `session_state` as in-memory cache; graceful fallback to mock data

**What was added:**

#### Supabase integration
- `get_supabase()` — cached Supabase client, reads credentials from `.streamlit/secrets.toml`
- `sb_available()` — feature flag; all Supabase calls are no-ops if credentials are missing
- Sidebar shows 🟢 connected / 🟡 mock-mode indicator
- All writes go to Supabase immediately after updating local `session_state`
- On startup, data is loaded from Supabase if connected; mock data is used as fallback

#### Database tables (`schema.sql`)
| Table | Primary key | Notes |
|---|---|---|
| `accounts` | `id` (text, e.g. ACC-0001) | `is_deleted` boolean for soft-delete; `notes` and `extra_fields` as JSONB |
| `account_deletions` | `uuid` | Audit log: `account_id`, `deleted_by_id`, `deleted_by_name`, `deleted_at`, `restored` |
| `call_logs` | `uuid` | Individual call entries mirrored from `accounts.notes` for analytics |
| `users` | `id` (text) | `extra_fields` as JSONB, `perms` as JSON array |

#### Soft delete + restore
- `sb_soft_delete_account(account_id, deleted_by_id, deleted_by_name)` — sets `is_deleted=True` on `accounts`, inserts row into `account_deletions`
- `sb_restore_account(account_id)` — sets `is_deleted=False`, marks deletion record as `restored=True`
- Accounts tab: `sb_fetch_accounts()` filters `is_deleted=False` automatically
- **Deleted Accounts tab** — shows full deletion log with restorer button; only visible when Supabase is connected

#### Bulk delete (admin only)
- "Select all N accounts" master checkbox at top of filtered list
- Per-row checkbox inside each account expander
- Selected IDs held in `st.session_state.selected_accounts` (a `set`)
- "Delete N selected" button triggers confirmation dialog
- On confirm: removes from local state, calls `sb_soft_delete_account` for each

#### Filters (Accounts tab)
Six filter controls in a collapsible expander:

| Filter | Type | Logic |
|---|---|---|
| Search | Text | Case-insensitive match on account name, brand name, ID |
| Sector | Multi-select | `account.sector in selected` |
| Urgency | Select | All / Overdue >14d / Critical >30d / Recent ≤14d |
| Contact person | Multi-select | `account.contact_person in selected` |
| Last called by | Multi-select | Matches user name of the first note's `member_id` |
| Branches | Range slider | `min ≤ branches ≤ max` |
| Priority | Multi-select | Shown only if a "Priority" select field exists in account_extra_fields |

All filters are composable (AND logic). "Clear filters" button resets all filter keys from `session_state`.

#### Bulk CSV import → Supabase
- After in-memory update, calls `sb_upsert_accounts_bulk(all_to_write)` to write all added/updated rows in one Supabase upsert call
- `logo_b64` is stripped before writing (binary not stored in Supabase — store in Supabase Storage separately for production)

#### Call log mirroring
- Every `Save log` action calls both `sb_upsert_account(a)` (updates JSONB notes) and `sb_upsert_call_log(account_id, note)` (inserts separate row to `call_logs`)
- `call_logs` enables SQL-level analytics without parsing JSONB

---

## Architecture overview

```
┌─────────────────────────────────────────────────────┐
│                  Streamlit Frontend                 │
│  render_sidebar()  render_dashboard()               │
│  render_accounts() render_log()  render_users()     │
│  render_schema()   render_deleted_accounts()        │
└────────────────────────┬────────────────────────────┘
                         │ read/write
                         ▼
┌─────────────────────────────────────────────────────┐
│              st.session_state (cache)               │
│  accounts[]  users[]  roles[]  call_statuses[]      │
│  account_extra_fields[]  call_extra_fields[]        │
│  visible_columns  selected_accounts  settings{}     │
└────────────────────────┬────────────────────────────┘
                         │ sync on every mutation
                         ▼
┌─────────────────────────────────────────────────────┐
│                    Supabase (Postgres)               │
│  accounts  account_deletions  call_logs  users      │
└─────────────────────────────────────────────────────┘
```

**Write path:** UI action → update `session_state` → call `sb_*` helper → Supabase upsert/insert/update  
**Read path (startup):** `init_state()` → `sb_fetch_accounts()` + `sb_fetch_users()` → populate `session_state`  
**Fallback:** if `SUPABASE_URL`/`SUPABASE_KEY` missing or Supabase unreachable, `sb_available()` returns `False`, all `sb_*` calls are no-ops, mock data is used

---

## Supabase helper functions

| Function | Table | Operation | Called when |
|---|---|---|---|
| `sb_fetch_accounts()` | accounts | SELECT WHERE is_deleted=false | App startup |
| `sb_upsert_account(acc)` | accounts | UPSERT | Add, Edit, Log call |
| `sb_upsert_accounts_bulk(accs)` | accounts | UPSERT (batch) | CSV import |
| `sb_soft_delete_account(id,by_id,by_name)` | accounts + account_deletions | UPDATE + INSERT | Single or bulk delete |
| `sb_restore_account(id)` | accounts + account_deletions | UPDATE both | Restore from deletion log |
| `sb_fetch_deleted_accounts()` | account_deletions | SELECT WHERE restored=false | Deleted Accounts tab |
| `sb_fetch_users()` | users | SELECT * | App startup |
| `sb_upsert_user(user)` | users | UPSERT | Add, Edit user |
| `sb_delete_user(uid)` | users | DELETE | Remove user |
| `sb_upsert_call_log(account_id, note)` | call_logs | INSERT | Log call |

---

## Permission flags

| Flag | Who uses it |
|---|---|
| `view` | Can see accounts, urgency, activity log |
| `log` | Can log calls |
| `add_account` | Can add, edit, delete accounts; bulk delete; restore |
| `import` | Can import CSV |
| `manage_users` | Can add, edit, delete, bulk-import users |
| `export` | Can download activity log CSV |
| `manage_schema` | Can access Field Builder & Roles tab (fields, statuses, roles, settings) |

---

## Known limitations and next steps

| Item | Notes |
|---|---|
| Logo storage | `logo_b64` is kept in `session_state` only, not written to Supabase. For production, upload to Supabase Storage and store the URL instead. |
| Authentication | Current user switcher is demo-only. For production, add Streamlit-Authenticator or Supabase Auth. |
| Real-time sync | Multiple users editing simultaneously will not see each other's changes without a page refresh. Add `st.rerun()` on a timer or Supabase Realtime subscriptions. |
| Custom field schema persistence | Custom fields, roles, and call statuses are in `session_state` only and reset on restart. Persist them to a `settings` table in Supabase. |
| Row Level Security | RLS is defined but commented out in `schema.sql`. Enable for production after configuring auth. |
| Audit trail | Deletion is logged. Edits and call logs are not separately audited — add an `audit_log` table if needed. |
