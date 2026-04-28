"""
db.py — Supabase database layer for CIMS
All Supabase reads/writes go through this module.
Configure SUPABASE_URL and SUPABASE_KEY in .env or Streamlit secrets.
"""

import os
import json
import streamlit as st

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False


def _client() -> "Client | None":
    """Return a cached Supabase client, or None if not configured."""
    if not SUPABASE_AVAILABLE:
        return None
    if "sb_client" in st.session_state:
        return st.session_state.sb_client
    try:
        url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY", "")
        if not url or not url.startswith("https://"):
            return None
        sb = create_client(url, key)
        st.session_state.sb_client = sb
        return sb
    except Exception:
        return None


def is_connected() -> bool:
    return _client() is not None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe(response):
    """Return .data from a Supabase response, or [] on error."""
    try:
        return response.data or []
    except Exception:
        return []


def _perms_to_list(perms):
    """Convert set/list of perms to list for Postgres TEXT[]."""
    if isinstance(perms, set):
        return list(perms)
    return perms or []


def _perms_to_set(perms):
    """Convert Postgres TEXT[] back to Python set."""
    if isinstance(perms, list):
        return set(perms)
    return set(perms or [])


# ── System settings ────────────────────────────────────────────────────────────

def load_settings() -> dict:
    sb = _client()
    if not sb:
        return {"system_name": "Client Interaction Management", "system_logo_b64": None}
    rows = _safe(sb.table("system_settings").select("*").execute())
    return {r["key"]: r["value"] for r in rows}


def save_setting(key: str, value: str):
    sb = _client()
    if not sb:
        return
    sb.table("system_settings").upsert({"key": key, "value": value}).execute()


# ── Roles ──────────────────────────────────────────────────────────────────────

def load_roles() -> list:
    sb = _client()
    if not sb:
        return []
    rows = _safe(sb.table("roles").select("*").execute())
    for r in rows:
        r["perms"] = _perms_to_set(r.get("perms", []))
    return rows


def upsert_role(role: dict):
    sb = _client()
    if not sb:
        return
    payload = {**role, "perms": _perms_to_list(role.get("perms", set()))}
    sb.table("roles").upsert(payload).execute()


def delete_role(role_id: str):
    sb = _client()
    if not sb:
        return
    sb.table("roles").delete().eq("id", role_id).execute()


# ── Users ──────────────────────────────────────────────────────────────────────

def load_users() -> list:
    sb = _client()
    if not sb:
        return []
    rows = _safe(sb.table("users").select("*").execute())
    for r in rows:
        if isinstance(r.get("extra_fields"), str):
            r["extra_fields"] = json.loads(r["extra_fields"])
        r.setdefault("extra_fields", {})
    return rows


def upsert_user(user: dict):
    sb = _client()
    if not sb:
        return
    payload = {k: v for k, v in user.items() if k not in ("notes",)}
    if isinstance(payload.get("extra_fields"), dict):
        payload["extra_fields"] = json.dumps(payload["extra_fields"])
    sb.table("users").upsert(payload).execute()


def delete_user(user_id: str):
    sb = _client()
    if not sb:
        return
    sb.table("users").delete().eq("id", user_id).execute()


def bulk_upsert_users(users: list):
    sb = _client()
    if not sb:
        return 0
    payload = []
    for u in users:
        row = {k: v for k, v in u.items()}
        if isinstance(row.get("extra_fields"), dict):
            row["extra_fields"] = json.dumps(row["extra_fields"])
        payload.append(row)
    sb.table("users").upsert(payload).execute()
    return len(payload)


# ── Call statuses ──────────────────────────────────────────────────────────────

def load_call_statuses() -> list:
    sb = _client()
    if not sb:
        return []
    return _safe(sb.table("call_statuses").select("*").order("sort_order").execute())


def upsert_call_status(status: dict):
    sb = _client()
    if not sb:
        return
    sb.table("call_statuses").upsert(status).execute()


def delete_call_status(status_id: str):
    sb = _client()
    if not sb:
        return
    sb.table("call_statuses").delete().eq("id", status_id).execute()


# ── Custom fields ──────────────────────────────────────────────────────────────

def load_custom_fields() -> list:
    sb = _client()
    if not sb:
        return []
    rows = _safe(sb.table("custom_fields").select("*").order("sort_order").execute())
    for r in rows:
        if isinstance(r.get("options"), list):
            pass  # already a list from Postgres TEXT[]
        else:
            r["options"] = []
    return rows


def upsert_custom_field(field: dict):
    sb = _client()
    if not sb:
        return
    payload = {**field, "options": field.get("options") or []}
    sb.table("custom_fields").upsert(payload).execute()


def delete_custom_field(field_id: str):
    sb = _client()
    if not sb:
        return
    sb.table("custom_fields").delete().eq("id", field_id).execute()


# ── Accounts ───────────────────────────────────────────────────────────────────

def load_accounts() -> list:
    """Load all active accounts with their call logs joined."""
    sb = _client()
    if not sb:
        return []
    rows = _safe(sb.table("accounts").select("*").execute())
    acc_ids = [r["id"] for r in rows]
    if not acc_ids:
        return rows
    # Load call logs for all accounts
    logs = _safe(sb.table("call_logs").select("*").in_("account_id", acc_ids).order("call_date", desc=True).execute())
    logs_by_acc: dict = {}
    for log in logs:
        if isinstance(log.get("extra_fields"), str):
            log["extra_fields"] = json.loads(log["extra_fields"])
        log.setdefault("extra_fields", {})
        # normalise key names for app compatibility
        log["date"] = str(log.get("call_date", ""))
        log["text"] = log.get("notes", "")
        logs_by_acc.setdefault(log["account_id"], []).append(log)

    for r in rows:
        r["notes"] = logs_by_acc.get(r["id"], [])
        if isinstance(r.get("extra_fields"), str):
            r["extra_fields"] = json.loads(r["extra_fields"])
        r.setdefault("extra_fields", {})
        if r.get("last_call_date"):
            r["last_call_date"] = str(r["last_call_date"])
    return rows


def upsert_account(account: dict) -> dict:
    """Insert or update a single account. Returns the saved row."""
    sb = _client()
    if not sb:
        return account
    payload = {k: v for k, v in account.items() if k != "notes"}
    if isinstance(payload.get("extra_fields"), dict):
        payload["extra_fields"] = json.dumps(payload["extra_fields"])
    result = _safe(sb.table("accounts").upsert(payload).execute())
    return result[0] if result else account


def bulk_upsert_accounts(accounts: list) -> tuple[int, int, int]:
    """Upsert a list of accounts. Returns (added, updated, skipped)."""
    sb = _client()
    if not sb:
        return 0, 0, 0

    # Fetch existing IDs
    existing_ids = {
        r["id"] for r in _safe(sb.table("accounts").select("id").execute())
    }

    to_insert, to_update = [], []
    for a in accounts:
        payload = {k: v for k, v in a.items() if k != "notes"}
        if isinstance(payload.get("extra_fields"), dict):
            payload["extra_fields"] = json.dumps(payload["extra_fields"])
        if a["id"] in existing_ids:
            to_update.append(payload)
        else:
            to_insert.append(payload)

    if to_insert:
        sb.table("accounts").insert(to_insert).execute()
    if to_update:
        sb.table("accounts").upsert(to_update).execute()

    return len(to_insert), len(to_update), 0


def delete_account(account: dict, deleted_by_user: dict):
    """
    Soft-delete: move account + all its call logs to deleted_accounts,
    then hard-delete from accounts (cascade deletes call_logs).
    """
    sb = _client()
    if not sb:
        return

    # Snapshot call logs
    logs = _safe(sb.table("call_logs").select("*").eq("account_id", account["id"]).execute())

    archive = {
        "original_id":     account["id"],
        "account_name":    account.get("account_name", ""),
        "brand_name":      account.get("brand_name", ""),
        "branches":        account.get("branches", 0),
        "sector":          account.get("sector", ""),
        "last_call_date":  account.get("last_call_date"),
        "contact_person":  account.get("contact_person", ""),
        "logo_b64":        account.get("logo_b64"),
        "extra_fields":    json.dumps(account.get("extra_fields", {})),
        "call_logs_json":  json.dumps(logs),
        "deleted_by":      deleted_by_user.get("id"),
        "deleted_by_name": deleted_by_user.get("name", ""),
        "is_restored":     False,
    }
    sb.table("deleted_accounts").insert(archive).execute()
    sb.table("accounts").delete().eq("id", account["id"]).execute()


def bulk_delete_accounts(accounts: list, deleted_by_user: dict) -> int:
    """Soft-delete multiple accounts. Returns count deleted."""
    for acc in accounts:
        delete_account(acc, deleted_by_user)
    return len(accounts)


def load_deleted_accounts() -> list:
    sb = _client()
    if not sb:
        return []
    rows = _safe(
        sb.table("deleted_accounts")
          .select("*")
          .eq("is_restored", False)
          .order("deleted_at", desc=True)
          .execute()
    )
    for r in rows:
        if isinstance(r.get("extra_fields"), str):
            r["extra_fields"] = json.loads(r["extra_fields"])
        if isinstance(r.get("call_logs_json"), str):
            r["call_logs_json"] = json.loads(r["call_logs_json"])
    return rows


def restore_account(deleted_row: dict, restored_by_user: dict):
    """Restore an account from deleted_accounts back to accounts."""
    sb = _client()
    if not sb:
        return
    acc = {
        "id":            deleted_row["original_id"],
        "account_name":  deleted_row["account_name"],
        "brand_name":    deleted_row["brand_name"],
        "branches":      deleted_row.get("branches", 0),
        "sector":        deleted_row.get("sector", ""),
        "last_call_date":deleted_row.get("last_call_date"),
        "contact_person":deleted_row.get("contact_person", ""),
        "logo_b64":      deleted_row.get("logo_b64"),
        "extra_fields":  json.dumps(deleted_row.get("extra_fields") or {}),
    }
    sb.table("accounts").insert(acc).execute()

    # Restore call logs if any
    logs = deleted_row.get("call_logs_json") or []
    if isinstance(logs, str):
        logs = json.loads(logs)
    for log in logs:
        log.pop("id", None)
        if isinstance(log.get("extra_fields"), dict):
            log["extra_fields"] = json.dumps(log["extra_fields"])
        sb.table("call_logs").insert(log).execute()

    # Mark as restored
    sb.table("deleted_accounts").update({
        "is_restored":      True,
        "restored_by":      restored_by_user.get("id"),
        "restored_by_name": restored_by_user.get("name", ""),
        "restored_at":      "now()",
    }).eq("id", deleted_row["id"]).execute()


# ── Call logs ──────────────────────────────────────────────────────────────────

def insert_call_log(account_id: str, log: dict):
    sb = _client()
    if not sb:
        return
    payload = {
        "account_id":  account_id,
        "member_id":   log.get("member_id"),
        "status_id":   log.get("status_id"),
        "call_date":   log.get("date", str(__import__("datetime").date.today())),
        "notes":       log.get("text", ""),
        "extra_fields": json.dumps(log.get("extra_fields", {})),
    }
    result = _safe(sb.table("call_logs").insert(payload).execute())
    # Update account last_call_date
    sb.table("accounts").update({"last_call_date": payload["call_date"]}).eq("id", account_id).execute()
    return result[0] if result else None
