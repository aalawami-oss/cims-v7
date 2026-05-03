"""
Client Interaction Management System (CIMS) — v7
Supabase backend · Streamlit frontend
Run: streamlit run app.py
Set .streamlit/secrets.toml with SUPABASE_URL and SUPABASE_KEY
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import random, uuid, base64, json, os
import bcrypt
from supabase import create_client, Client

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="CIMS",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .main .block-container{padding-top:1.2rem;padding-bottom:2rem;max-width:1200px}
  .stTabs [data-baseweb="tab-list"]{gap:4px}
  .stTabs [data-baseweb="tab"]{border-radius:8px;padding:5px 13px}
  .stButton>button[kind="primary"]{background:#6C3FC5!important;border-color:#6C3FC5!important;color:#fff!important}
  .stButton>button[kind="primary"]:hover{background:#5530A8!important}
  .stButton>button{border-radius:8px!important}
  div[data-testid="stMetricValue"]>div{font-size:1.45rem!important}
  .stDataFrame{border-radius:10px;overflow:hidden}
  .badge-ok{background:#EDE9FC;color:#6C3FC5;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:500}
  .badge-warn{background:#EDE9FC;color:#6C3FC5;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:500}
  .badge-danger{background:#6C3FC5;color:#ffffff;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:500}
  .badge-info{background:#EDE9FC;color:#6C3FC5;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:500}
  .rep-banner{background:#EDE9FC;color:#6C3FC5;padding:10px 14px;border-radius:8px;margin-bottom:1rem;font-size:13px}
  .acc-logo{width:40px;height:40px;border-radius:8px;object-fit:contain;background:#f3f0ff;padding:4px}
  .sys-logo{max-height:38px;max-width:140px;object-fit:contain}
  .filter-bar{background:#faf9fe;border:1px solid #e0daf5;border-radius:10px;padding:12px 16px;margin-bottom:1rem}
  .deleted-banner{background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:10px 14px;margin-bottom:8px;font-size:13px}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
VIOLET       = "#6C3FC5"
VIOLET_LIGHT = "#EDE9FC"
VIOLET_TEXT  = "#6C3FC5"

PERM_MODULES = {
    "Accounts": [
        ("view",           "View accounts"),
        ("acc_add",        "Add new accounts"),
        ("acc_edit",       "Edit accounts (general)"),
        ("acc_edit_name",  "Edit account name"),
        ("acc_edit_brand", "Edit brand name"),
        ("acc_edit_f5",    "Edit F5 number"),
        ("acc_delete",     "Delete accounts"),
        ("import",         "Import accounts (CSV)"),
    ],
    "Calls": [
        ("log",            "Log interactions"),
    ],
    "Data": [
        ("export",         "Export data"),
    ],
    "Users": [
        ("manage_users",   "Manage users"),
    ],
    "Settings": [
        ("manage_schema",  "Manage fields, roles & settings"),
    ],
}
ALL_PERMS = [(pk, pl) for perms in PERM_MODULES.values() for pk, pl in perms]

DEFAULT_BUTTON_LABELS = {
    "log_call":    "Log call",
    "add_account": "+ Account",
    "import_csv":  "Import CSV",
    "edit":        "Edit",
    "delete":      "Delete",
    "restore":     "Restore",
    "save":        "Save",
    "cancel":      "Cancel",
    "add_user":    "+ Add user",
    "export_csv":  "Export as CSV",
    "sign_in":     "Sign in",
    "logout":      "Logout",
}
TEAM_COLORS = [
    {"color":"#6C3FC5","bg":"#EDE9FC"},{"color":"#6C3FC5","bg":"#EDE9FC"},
    {"color":"#6C3FC5","bg":"#EDE9FC"},{"color":"#6C3FC5","bg":"#EDE9FC"},
    {"color":"#6C3FC5","bg":"#EDE9FC"},{"color":"#6C3FC5","bg":"#EDE9FC"},
    {"color":"#6C3FC5","bg":"#EDE9FC"},{"color":"#6C3FC5","bg":"#EDE9FC"},
]
SECTORS  = ["Retail","F&B","Finance","Healthcare","Logistics","Tech","Education","Real Estate"]
CHART_TYPES = ["Bar","Stacked Bar","Line","Area","Horizontal Bar","Pie","Donut","Scatter"]
CORE_COLUMNS = ["ID","Account Name","Brand Name","Branches","Sector","Last Call","Contact","Account Owner","F5 Number"]
SECTION_AFFECT_OPTIONS = ["Accounts", "Calls", "Users"]

# Ordered list of main-nav tabs.  key=internal id, label=display name, removable=can admin hide it
TAB_DEFS = [
    ("dashboard",    "Dashboard",        True),
    ("accounts",     "Accounts",         False),
    ("urgency",      "Urgency",          True),
    ("activity_log", "Activity Log",     True),
    ("users",        "Users",            True),
    ("deleted",      "Deleted Accounts", True),
]
BRANDS = [
    ("Al Futtaim Group","ACE Hardware"),("Alshaya Group","Starbucks ME"),
    ("Majid Al Futtaim","Mall of the Emirates"),("Jarir Bookstore","Jarir"),
    ("Extra Stores","Extra"),("Nahdi Medical","Nahdi"),("Tamimi Markets","Tamimi"),
    ("Abdul Latif Jameel","ALJ Auto"),("Gulf Union Foods","Sunbulah"),("Sadafco","Saudia Dairy"),
    ("National Water Company","NWC"),("Saudi Airlines Catering","SAC"),
    ("Binzagr Company","Binzagr"),("Leejam Sports","Fitness Time"),
    ("BinDawood Holding","Danube"),("United Electronics","eXtra"),
    ("Cenomi Retail","Cenomi"),("Arabian Food Industries","Domty"),
    ("SASCO","SASCO Energy"),("Nana Direct","Nana"),
]

# ══════════════════════════════════════════════════════════════════════════════
# SUPABASE CONNECTION
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_supabase() -> Client:
    try:
        url = st.secrets.get("SUPABASE_URL", "") or os.getenv("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "") or os.getenv("SUPABASE_KEY", "")
    except Exception:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        st.sidebar.error(f"Supabase error: {e}")
        return None

def sb_available():
    return get_supabase() is not None

# ══════════════════════════════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════════════════════════════

def verify_login(email: str, password: str):
    """Return user dict if credentials are valid, else None. Raises on unexpected errors."""
    sb = get_supabase()
    if not sb:
        raise RuntimeError("Supabase not connected.")
    # Fetch all users and match email case-insensitively in Python
    # (avoids supabase-py version differences with ilike)
    rows = sb.table("users").select("*").execute().data or []
    user = next((u for u in rows if (u.get("email") or "").lower() == email.strip().lower()), None)
    if not user:
        return None
    ef = user.get("extra_fields") or {}
    if isinstance(ef, str):
        try: ef = json.loads(ef)
        except: ef = {}
    pw_hash = user.get("password_hash") or ef.get("_pw", "")
    if not pw_hash:
        raise RuntimeError(f"No password set for this account. Contact your admin.")
    if bcrypt.checkpw(password.encode("utf-8"), pw_hash.encode("utf-8")):
        return user
    return None

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

def render_login_page():
    """Full-screen login page. Sets session state on success."""
    st.markdown("""
    <style>
      section[data-testid="stSidebar"]{display:none}
      .login-wrap{max-width:400px;margin:60px auto}
    </style>
    """, unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("## 📋 CIMS")
        st.markdown("##### Client Interaction Management System")
        st.markdown("---")
        with st.form("login_form", clear_on_submit=False):
            email    = st.text_input("Email address", placeholder="you@company.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button(get_btn("sign_in"), type="primary", use_container_width=True)
        if submitted:
            if not email or not password:
                st.error("Enter your email and password.")
            else:
                try:
                    user = verify_login(email, password)
                    if user:
                        st.session_state.logged_in_user_id = user["id"]
                        st.session_state.pop("initialized", None)
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
                except RuntimeError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Login error: {type(e).__name__}: {e}")

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

def save_layout():
    """Persist section/field layout to admin user's extra_fields._layout in Supabase."""
    sb = get_supabase()
    if not sb:
        return
    admin = next((u for u in st.session_state.get("users", []) if u.get("role") == "admin"), None)
    if not admin:
        return
    ef = admin.get("extra_fields") or {}
    if isinstance(ef, str):
        try: ef = json.loads(ef)
        except: ef = {}
    # Strip internal _pw from layout copy
    ef["_layout"] = {
        "sections": st.session_state.get("account_sections", []),
        "account_extra_fields": st.session_state.get("account_extra_fields", []),
        "call_extra_fields": st.session_state.get("call_extra_fields", []),
    }
    for i, u in enumerate(st.session_state.users):
        if u["id"] == admin["id"]:
            st.session_state.users[i]["extra_fields"] = ef
            break
    try:
        sb.table("users").update({"extra_fields": json.dumps(ef)}).eq("id", admin["id"]).execute()
    except Exception as e:
        st.warning(f"Layout save failed: {e}")

def get_btn(key: str) -> str:
    """Return a potentially-customized button label, falling back to DEFAULT_BUTTON_LABELS."""
    labels = st.session_state.get("settings", {}).get("button_labels", {})
    return labels.get(key) or DEFAULT_BUTTON_LABELS.get(key, key)

def apply_theme():
    """Inject dynamic CSS overrides using the stored primary/light colors."""
    s  = st.session_state.get("settings", {})
    pc = s.get("primary_color", VIOLET)
    lc = s.get("light_color",   VIOLET_LIGHT)
    st.markdown(f"""
    <style>
      :root{{--pc:{pc};--lc:{lc}}}
      .stButton>button[kind="primary"]{{background:{pc}!important;border-color:{pc}!important;color:#fff!important}}
      .stButton>button[kind="primary"]:hover{{background:{pc}cc!important}}
      .badge-ok,.badge-warn,.badge-info{{background:{lc}!important;color:{pc}!important}}
      .badge-danger{{background:{pc}!important;color:#fff!important}}
      .rep-banner{{background:{lc}!important;color:{pc}!important}}
      .stTabs [data-baseweb="tab"][aria-selected="true"]{{color:{pc}!important;border-bottom-color:{pc}!important}}
    </style>
    """, unsafe_allow_html=True)

def save_settings():
    """Persist system settings to admin user's extra_fields._settings in Supabase."""
    sb = get_supabase()
    if not sb: return
    admin = next((u for u in st.session_state.get("users", []) if u.get("role") == "admin"), None)
    if not admin: return
    ef = admin.get("extra_fields") or {}
    if isinstance(ef, str):
        try: ef = json.loads(ef)
        except: ef = {}
    s = st.session_state.get("settings", {})
    ef["_settings"] = {
        "system_name":   s.get("system_name", "Client Interaction Management"),
        "primary_color": s.get("primary_color", VIOLET),
        "light_color":   s.get("light_color",   VIOLET_LIGHT),
        "button_labels": s.get("button_labels", dict(DEFAULT_BUTTON_LABELS)),
    }
    for i, u in enumerate(st.session_state.users):
        if u["id"] == admin["id"]:
            st.session_state.users[i]["extra_fields"] = ef
            break
    try:
        sb.table("users").update({"extra_fields": json.dumps(ef)}).eq("id", admin["id"]).execute()
    except Exception as e:
        st.warning(f"Settings save failed: {e}")

# ══ Supabase CRUD helpers ══════════════════════════════════════════════════════

def sb_fetch_accounts():
    """Fetch all active accounts from Supabase."""
    sb = get_supabase()
    if not sb: return []
    try:
        r = sb.table("accounts").select("*").eq("is_deleted", False).execute()
        rows = r.data or []
        for row in rows:
            # decode JSONB fields
            for jf in ("extra_fields","notes"):
                if isinstance(row.get(jf), str):
                    try: row[jf] = json.loads(row[jf])
                    except: row[jf] = {} if jf=="extra_fields" else []
            if not isinstance(row.get("notes"), list): row["notes"] = []
            if not isinstance(row.get("extra_fields"), dict): row["extra_fields"] = {}
        return rows
    except Exception as e:
        st.sidebar.warning(f"Supabase fetch failed: {e}")
        return []

def sb_upsert_account(acc: dict):
    """Insert or update a single account in Supabase."""
    sb = get_supabase()
    if not sb: return
    try:
        payload = {k: (json.dumps(v) if isinstance(v,(dict,list)) else v) for k,v in acc.items()}
        payload.pop("logo_b64", None)           # never store base64 in main table
        payload["is_deleted"] = False
        sb.table("accounts").upsert(payload).execute()
    except Exception as e:
        st.warning(f"Supabase upsert failed: {e}")

def sb_upsert_accounts_bulk(accs: list):
    """Bulk upsert a list of accounts."""
    sb = get_supabase()
    if not sb: return
    try:
        payloads = []
        for acc in accs:
            p = {k: (json.dumps(v) if isinstance(v,(dict,list)) else v) for k,v in acc.items()}
            p.pop("logo_b64", None)
            p["is_deleted"] = False
            payloads.append(p)
        sb.table("accounts").upsert(payloads).execute()
    except Exception as e:
        st.warning(f"Supabase bulk upsert failed: {e}")

def sb_soft_delete_account(account_id: str, deleted_by_id: str, deleted_by_name: str):
    """Soft-delete: mark is_deleted=True and log to account_deletions."""
    sb = get_supabase()
    if not sb: return
    try:
        sb.table("accounts").update({"is_deleted": True}).eq("id", account_id).execute()
        sb.table("account_deletions").insert({
            "id": str(uuid.uuid4()),
            "account_id": account_id,
            "deleted_by_id": deleted_by_id,
            "deleted_by_name": deleted_by_name,
            "deleted_at": datetime.utcnow().isoformat(),
            "restored": False,
        }).execute()
    except Exception as e:
        st.warning(f"Supabase delete log failed: {e}")

def sb_restore_account(account_id: str):
    """Restore a soft-deleted account."""
    sb = get_supabase()
    if not sb: return
    try:
        sb.table("accounts").update({"is_deleted": False}).eq("id", account_id).execute()
        sb.table("account_deletions").update({"restored": True}).eq("account_id", account_id).eq("restored", False).execute()
    except Exception as e:
        st.warning(f"Supabase restore failed: {e}")

def sb_fetch_deleted_accounts():
    """Fetch deletion log with account details."""
    sb = get_supabase()
    if not sb: return []
    try:
        r = sb.table("account_deletions").select("*").eq("restored", False).order("deleted_at", desc=True).execute()
        return r.data or []
    except Exception as e:
        st.warning(f"Supabase deletion log fetch failed: {e}")
        return []

def sb_fetch_users():
    sb = get_supabase()
    if not sb: return []
    try:
        r = sb.table("users").select("*").execute()
        rows = r.data or []
        for row in rows:
            if isinstance(row.get("extra_fields"), str):
                try: row["extra_fields"] = json.loads(row["extra_fields"])
                except: row["extra_fields"] = {}
            if isinstance(row.get("perms"), list):
                row["perms"] = set(row["perms"])
        return rows
    except Exception as e:
        st.warning(f"Supabase user fetch failed: {e}")
        return []

def sb_upsert_user(user: dict):
    sb = get_supabase()
    if not sb: return
    try:
        p = dict(user)
        if isinstance(p.get("perms"), set): p["perms"] = list(p["perms"])
        # Move password_hash into extra_fields._pw (no dedicated column needed)
        pw = p.pop("password_hash", None)
        ef = p.get("extra_fields") or {}
        if isinstance(ef, str):
            try: ef = json.loads(ef)
            except: ef = {}
        if pw:
            ef["_pw"] = pw
        p["extra_fields"] = json.dumps(ef)
        sb.table("users").upsert(p).execute()
    except Exception as e:
        st.warning(f"Supabase user upsert failed: {e}")

def sb_delete_user(uid: str):
    sb = get_supabase()
    if not sb: return
    try: sb.table("users").delete().eq("id", uid).execute()
    except Exception as e: st.warning(f"Supabase user delete failed: {e}")

def sb_upsert_call_log(account_id: str, note: dict):
    """Append a call log entry to Supabase call_logs table."""
    sb = get_supabase()
    if not sb: return
    try:
        payload = {
            "id": str(uuid.uuid4()),
            "account_id": account_id,
            "date": note["date"],
            "text": note.get("text",""),
            "member_id": note.get("member_id",""),
            "status_id": note.get("status_id",""),
            "extra_fields": json.dumps(note.get("extra_fields",{})),
        }
        sb.table("call_logs").insert(payload).execute()
    except Exception as e:
        st.warning(f"Supabase call log failed: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
import io as _io

def new_id(): return str(uuid.uuid4())[:8]

def read_upload(f) -> pd.DataFrame:
    """Parse an uploaded file (CSV, XLSX or XLS) into a DataFrame."""
    name = f.name.lower()
    if name.endswith(".xlsx"):
        return pd.read_excel(f, engine="openpyxl")
    if name.endswith(".xls"):
        return pd.read_excel(f, engine="xlrd")
    return pd.read_csv(f)

def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = _io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()
def days_since(d):
    if not d: return 999
    try:
        if isinstance(d,str): d=datetime.strptime(d,"%Y-%m-%d").date()
        return (date.today()-d).days
    except: return 999
def rnd_date(n): return str(date.today()-timedelta(days=random.randint(0,n)))
def initials(name): return "".join(p[0] for p in name.split()[:2]).upper()

AFFECT_COLORS = {
    "Accounts":    ("#e3f2fd", "#1565c0"),
    "Calls":       ("#e8f5e9", "#2e7d32"),
    "Users":       ("#fce4ec", "#880e4f"),
    "Navigation":  ("#f3e5f5", "#6a1b9a"),
    "System-wide": ("#fff8e1", "#f57f17"),
}
def affect_badge(level: str):
    bg, fg = AFFECT_COLORS.get(level, ("#f5f5f5", "#555"))
    st.markdown(
        f'<span style="font-size:11px;background:{bg};color:{fg};padding:2px 9px;'
        f'border-radius:10px;font-weight:600;letter-spacing:.02em">Affects: {level}</span>',
        unsafe_allow_html=True
    )
    st.markdown("")

def urgency_badge(d):
    if d>30: return f'<span class="badge-danger">{d}d ago</span>'
    if d>14: return f'<span class="badge-warn">{d}d ago</span>'
    return f'<span class="badge-ok">{d}d ago</span>'

def role_badge_html(role_id):
    r = next((r for r in st.session_state.roles if r["id"]==role_id), None)
    if not r: return f'<span class="badge-info">{role_id}</span>'
    c=r.get("color",VIOLET); bg=r.get("bg",VIOLET_LIGHT)
    return f'<span style="background:{bg};color:{c};padding:2px 9px;border-radius:20px;font-size:12px;font-weight:500">{r["label"]}</span>'

def has_perm(role_id, perm):
    r = next((r for r in st.session_state.roles if r["id"]==role_id), None)
    if not r: return False
    perms = r.get("perms") or set()
    if perm in perms: return True
    # Backward compat: legacy "add_account" covers all granular account write perms
    if perm in ("acc_add","acc_edit","acc_edit_name","acc_edit_brand","acc_edit_f5","acc_delete") and "add_account" in perms:
        return True
    return False

def get_active_user():
    users = st.session_state.get("users", [])
    if not users:
        return {"id":"","name":"Unknown","role":"viewer","email":"","color":VIOLET,"bg":VIOLET_LIGHT,"extra_fields":{}}
    # Admin can "view as" another user
    view_as = st.session_state.get("view_as_user_id")
    if view_as:
        u = next((u for u in users if u["id"]==view_as), None)
        if u: return u
    uid = st.session_state.get("logged_in_user_id", "")
    return next((u for u in users if u["id"]==uid), users[0])

def get_logged_in_user():
    """Always returns the actual logged-in user, ignoring view_as."""
    users = st.session_state.get("users", [])
    uid   = st.session_state.get("logged_in_user_id", "")
    return next((u for u in users if u["id"]==uid), users[0] if users else None)

def get_user(uid): return next((u for u in st.session_state.users if u["id"]==uid), None)
def get_status(sid): return next((s for s in st.session_state.call_statuses if s["id"]==sid), None)

def img_to_b64(f):
    if f is None: return None
    return base64.b64encode(f.read()).decode()

def b64_img_tag(b64, css_class="acc-logo", alt=""):
    if not b64: return ""
    return f'<img src="data:image/png;base64,{b64}" class="{css_class}" alt="{alt}">'

def get_all_logs(user_id=None):
    logs = []
    for a in st.session_state.accounts:
        for n in a.get("notes",[]):
            if user_id and n.get("member_id")!=user_id: continue
            logs.append({**n, "account_id":a["id"], "account_name":a["account_name"], "brand_name":a["brand_name"]})
    return sorted(logs, key=lambda x: x.get("date",""), reverse=True)

# ══════════════════════════════════════════════════════════════════════════════
# STATE INIT
# ══════════════════════════════════════════════════════════════════════════════
def init_state():
    if "initialized" in st.session_state: return

    st.session_state.settings = {
        "system_name":    "Client Interaction Management",
        "system_logo_b64": None,
        "primary_color":  VIOLET,
        "light_color":    VIOLET_LIGHT,
        "button_labels":  dict(DEFAULT_BUTTON_LABELS),
        "account_filters": {
            "search": True, "sector": True, "urgency": True,
            "contact": True, "assignee": True, "branches": True,
            "account_owner": True,
        },
    }
    _all_acc = {"view","log","acc_add","acc_edit","acc_edit_name","acc_edit_brand","acc_edit_f5","acc_delete","import","manage_users","export","manage_schema"}
    _mgr_acc = {"view","log","acc_add","acc_edit","acc_edit_name","acc_edit_brand","acc_edit_f5","acc_delete","import","export"}
    st.session_state.roles = [
        {"id":"admin",  "label":"Admin",   "color":VIOLET,"bg":VIOLET_LIGHT,"perms":_all_acc},
        {"id":"manager","label":"Manager", "color":VIOLET,"bg":VIOLET_LIGHT,"perms":_mgr_acc},
        {"id":"rep",    "label":"Rep",     "color":VIOLET,"bg":VIOLET_LIGHT,"perms":{"view","log"}},
        {"id":"viewer", "label":"Viewer",  "color":VIOLET,"bg":VIOLET_LIGHT,"perms":{"view"}},
    ]
    st.session_state.call_statuses = [
        {"id":"cs1","label":"Completed",         "color":"#6C3FC5"},
        {"id":"cs2","label":"No Answer",         "color":"#6C3FC5"},
        {"id":"cs3","label":"Follow-up Required","color":"#6C3FC5"},
        {"id":"cs4","label":"Meeting Scheduled", "color":"#6C3FC5"},
        {"id":"cs5","label":"Not Interested",    "color":"#6C3FC5"},
        {"id":"cs6","label":"Voicemail Left",    "color":"#6C3FC5"},
    ]
    st.session_state.account_extra_fields = [
        {"id":"ef1","label":"Region",  "type":"text",  "options":[], "sort_order":0, "section_id":None},
        {"id":"ef2","label":"Priority","type":"select","options":["High","Medium","Low"], "sort_order":1, "section_id":None},
    ]
    st.session_state.user_extra_fields   = [{"id":"uf1","label":"Phone","type":"text","options":[]},{"id":"uf2","label":"Territory","type":"text","options":[]}]
    st.session_state.call_extra_fields   = [
        {"id":"cf1","label":"Deal Size","type":"text",  "options":[], "sort_order":0, "section_id":None},
        {"id":"cf2","label":"Next Step","type":"text",  "options":[], "sort_order":1, "section_id":None},
    ]
    st.session_state.visible_columns     = list(CORE_COLUMNS)
    st.session_state.selected_accounts   = set()
    st.session_state.account_sections    = []   # {"id","label","sort_order"}

    # Load from Supabase — no mock fallback; only mark initialized if connected
    if not sb_available():
        return
    users    = sb_fetch_users()
    accounts = sb_fetch_accounts()

    # Load saved layout from admin user's extra_fields
    admin = next((u for u in users if u.get("role") == "admin"), None)
    if admin:
        ef = admin.get("extra_fields") or {}
        if isinstance(ef, str):
            try: ef = json.loads(ef)
            except: ef = {}
        layout = ef.get("_layout", {})
        if layout.get("sections") is not None:
            st.session_state.account_sections = layout["sections"]
        if layout.get("account_extra_fields"):
            st.session_state.account_extra_fields = layout["account_extra_fields"]
        if layout.get("call_extra_fields"):
            for f in layout["call_extra_fields"]:
                f.setdefault("section_id", None); f.setdefault("sort_order", 99)
            st.session_state.call_extra_fields = layout["call_extra_fields"]
        saved_settings = ef.get("_settings", {})
        if saved_settings:
            for k, v in saved_settings.items():
                st.session_state.settings[k] = v

    st.session_state.users    = users
    st.session_state.accounts = accounts
    st.session_state.active_user_id = users[0]["id"] if users else ""
    st.session_state.initialized = True

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    active = get_active_user()
    s = st.session_state.get("settings", {"system_name": "CIMS", "system_logo_b64": None})
    if s.get("system_logo_b64"):
        st.sidebar.markdown(b64_img_tag(s["system_logo_b64"],"sys-logo","Logo"), unsafe_allow_html=True)
        st.sidebar.markdown("")
    else:
        st.sidebar.markdown(f"### {s['system_name']}")
    if sb_available():
        st.sidebar.success("🟢 Supabase connected")
    else:
        st.sidebar.error("🔴 Supabase not connected — check SUPABASE_URL and SUPABASE_KEY in secrets.toml")
    st.sidebar.markdown("---")
    users    = st.session_state.get("users", [])
    accounts = st.session_state.get("accounts", [])

    photo_b64 = (active.get("extra_fields") or {}).get("_photo")
    pc = st.session_state.get("settings", {}).get("primary_color", VIOLET)
    if photo_b64:
        avatar_html = f'<img src="data:image/png;base64,{photo_b64}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;flex-shrink:0">'
    else:
        ini = initials(active["name"])
        avatar_html = f'<div style="width:40px;height:40px;border-radius:50%;background:{pc};display:inline-flex;align-items:center;justify-content:center;font-weight:700;color:#fff;font-size:15px;flex-shrink:0">{ini}</div>'
    st.sidebar.markdown(
        f'<div style="display:flex;align-items:center;gap:10px">{avatar_html}'
        f'<div style="overflow:hidden"><div>{role_badge_html(active["role"])}</div>'
        f'<strong style="font-size:13px">{active["name"]}</strong><br>'
        f'<small style="color:#888">{active["email"]}</small></div></div>',
        unsafe_allow_html=True
    )
    st.sidebar.markdown("")
    sb_col1, sb_col2 = st.sidebar.columns(2)
    if sb_col1.button("👤 Profile", use_container_width=True, key="profile_btn"):
        render_profile()
    if sb_col2.button("🚪 " + get_btn("logout"), use_container_width=True, key="logout_btn"):
        logout()

    # ── Admin: view-as user switcher ──────────────────────────────────────────
    real_user = get_logged_in_user()
    if real_user and real_user.get("role") == "admin" and len(users) > 1:
        st.sidebar.markdown("---")
        st.sidebar.caption("👁 View as user")
        other_users  = [u for u in users if u["id"] != real_user["id"]]
        view_options = ["— Myself —"] + [u["name"] for u in other_users]
        cur_view     = st.session_state.get("view_as_user_id")
        cur_idx      = next((i+1 for i, u in enumerate(other_users) if u["id"]==cur_view), 0)
        sel = st.sidebar.selectbox("", view_options, index=cur_idx, key="view_as_select", label_visibility="collapsed")
        if sel == "— Myself —":
            st.session_state.pop("view_as_user_id", None)
        else:
            target = next((u for u in other_users if u["name"]==sel), None)
            if target and target["id"] != cur_view:
                st.session_state["view_as_user_id"] = target["id"]; st.rerun()

    st.sidebar.markdown("---")
    overdue = sum(1 for a in accounts if days_since(a["last_call_date"]) > 14)
    st.sidebar.metric("Accounts", len(accounts))
    st.sidebar.metric("Overdue >14d", overdue)
    st.sidebar.metric("Team", len(users))

# ══════════════════════════════════════════════════════════════════════════════
# PROFILE  (modal dialog)
# ══════════════════════════════════════════════════════════════════════════════
@st.dialog("My Profile")
def render_profile():
    active    = get_active_user()
    pc        = st.session_state.get("settings", {}).get("primary_color", VIOLET)
    photo_b64 = (active.get("extra_fields") or {}).get("_photo")

    pfc1, pfc2 = st.columns([1, 4])
    with pfc1:
        if photo_b64:
            st.markdown(f'<img src="data:image/png;base64,{photo_b64}" style="width:80px;height:80px;border-radius:50%;object-fit:cover">', unsafe_allow_html=True)
        else:
            ini = initials(active["name"])
            st.markdown(f'<div style="width:80px;height:80px;border-radius:50%;background:{pc};display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:700;color:#fff">{ini}</div>', unsafe_allow_html=True)
    with pfc2:
        st.markdown(f"### {active['name']}")
        st.markdown(f'<small style="color:#888">{active["email"]}</small>', unsafe_allow_html=True)
        st.markdown(role_badge_html(active["role"]), unsafe_allow_html=True)

    st.markdown("---")
    tab_ph, tab_pw = st.tabs(["📷 Photo", "🔑 Password"])

    with tab_ph:
        photo_file = st.file_uploader("Upload profile photo (PNG/JPG)", type=["png","jpg","jpeg"], key="prof_photo_up")
        pp1, pp2 = st.columns(2)
        if photo_file:
            if pp1.button("Save photo", type="primary", key="prof_save_photo"):
                new_b64 = img_to_b64(photo_file)
                ef = dict(active.get("extra_fields") or {})
                ef["_photo"] = new_b64
                for i, u in enumerate(st.session_state.users):
                    if u["id"] == active["id"]:
                        st.session_state.users[i]["extra_fields"] = ef; break
                sb_upsert_user({**active, "extra_fields": ef})
                st.success("Photo updated."); st.rerun()
        if photo_b64:
            if pp2.button("Remove photo", key="prof_remove_photo"):
                ef = dict(active.get("extra_fields") or {})
                ef.pop("_photo", None)
                for i, u in enumerate(st.session_state.users):
                    if u["id"] == active["id"]:
                        st.session_state.users[i]["extra_fields"] = ef; break
                sb_upsert_user({**active, "extra_fields": ef})
                st.success("Photo removed."); st.rerun()

    with tab_pw:
        with st.form("prof_pw_form"):
            old_pw  = st.text_input("Current password",     type="password")
            new_pw  = st.text_input("New password",         type="password")
            conf_pw = st.text_input("Confirm new password", type="password")
            do_change = st.form_submit_button("Change password", type="primary")
        if do_change:
            if not old_pw or not new_pw or not conf_pw:
                st.error("Fill in all password fields.")
            elif new_pw != conf_pw:
                st.error("New passwords don't match.")
            elif len(new_pw) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                ef = active.get("extra_fields") or {}
                if isinstance(ef, str):
                    try: ef = json.loads(ef)
                    except: ef = {}
                pw_hash = active.get("password_hash") or ef.get("_pw", "")
                if not pw_hash or not bcrypt.checkpw(old_pw.encode(), pw_hash.encode()):
                    st.error("Current password is incorrect.")
                else:
                    new_hash = hash_password(new_pw)
                    for i, u in enumerate(st.session_state.users):
                        if u["id"] == active["id"]:
                            st.session_state.users[i]["password_hash"] = new_hash; break
                    sb_upsert_user({**active, "password_hash": new_hash})
                    st.success("Password changed. You can close this window.")

# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
def render_dashboard(active, is_rep):
    if is_rep:
        st.markdown('<div class="rep-banner">My performance view — showing only your activity</div>', unsafe_allow_html=True)
    logs     = get_all_logs(user_id=active["id"] if is_rep else None)
    accounts = st.session_state.accounts
    if is_rep:
        my_accs = [a for a in accounts if any(n["member_id"]==active["id"] for n in a.get("notes",[]))]
        total = len(my_accs); tb = sum(a["branches"] for a in my_accs) or 1
        c30   = sum(1 for a in my_accs if any(n["member_id"]==active["id"] and days_since(n["date"])<=30 for n in a.get("notes",[])))
        cb    = sum(a["branches"] for a in my_accs if any(n["member_id"]==active["id"] and days_since(n["date"])<=30 for n in a.get("notes",[])))
        week_calls = sum(1 for l in logs if days_since(l["date"])<=7)
    else:
        total = len(accounts); tb = sum(a["branches"] for a in accounts) or 1
        c30   = sum(1 for a in accounts if days_since(a["last_call_date"])<=30)
        cb    = sum(a["branches"] for a in accounts if days_since(a["last_call_date"])<=30)
        week_calls = None
    cov = round(c30/total*100) if total else 0
    br  = round(cb/tb*100)   if tb    else 0
    col1,col2,col3,col4 = st.columns(4)
    col1.metric("Coverage (30d)", f"{cov}%", f"{c30}/{total}")
    if is_rep: col2.metric("My calls this week", week_calls, f"{len(logs)} total")
    else:      col2.metric("Overdue >14d", sum(1 for a in accounts if days_since(a["last_call_date"])>14), "need contact")
    col3.metric("Total branches",  f"{tb:,}", "under management")
    col4.metric("Branch coverage", f"{br}%",  f"{cb:,} contacted")
    st.markdown("---")
    _render_chart(logs, is_rep, active)
    st.markdown("---")
    if not is_rep:
        st.subheader("Top priority — overdue accounts")
        urg = sorted([a for a in accounts if days_since(a["last_call_date"])>14], key=lambda x:days_since(x["last_call_date"]),reverse=True)[:5]
        if not urg: st.success("All accounts contacted in the last 14 days.")
        for acc in urg:
            d = days_since(acc["last_call_date"])
            c1,c2,c3 = st.columns([3,1,1])
            c1.markdown(f"**{acc['brand_name']}** <small style='color:#888'>{acc['account_name']} · {acc['branches']} branches</small>", unsafe_allow_html=True)
            c2.markdown(urgency_badge(d), unsafe_allow_html=True)
            if has_perm(active["role"],"log"):
                if c3.button("Log call", key=f"dash_log_{acc['id']}"):
                    st.session_state.log_target=acc["id"]; st.session_state.show_log_modal=True; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# CHART
# ══════════════════════════════════════════════════════════════════════════════
def _render_chart(logs, is_rep, active):
    st.subheader("Call activity")
    c1,c2,c3,c4 = st.columns(4)
    gran      = c1.selectbox("Granularity", ["Daily","Weekly","Monthly","Yearly"], index=1, key="gran")
    ctype     = c2.selectbox("Chart type",  CHART_TYPES, key="ctype")
    offset    = c3.number_input("Periods back", min_value=0, max_value=24, value=0, step=1, key="coffset")
    show_all  = c4.checkbox("All team", value=not is_rep, disabled=is_rep, key="chart_all")
    users     = st.session_state.users
    visible   = [u for u in users if not is_rep or u["id"]==active["id"]] if not show_all else users
    today     = date.today()
    if gran=="Daily":
        size=14; periods=[str(today-timedelta(days=i+offset*size)) for i in range(size-1,-1,-1)]; labels=[(today-timedelta(days=i+offset*size)).strftime("%d/%m") for i in range(size-1,-1,-1)]
        def bkt(d): return d[:10]
    elif gran=="Weekly":
        size=8
        def ws(d):
            if isinstance(d,str): d=datetime.strptime(d,"%Y-%m-%d").date()
            return str(d-timedelta(days=d.weekday()))
        raw=[ws(today-timedelta(weeks=i+offset*size)) for i in range(size-1,-1,-1)]; periods=list(dict.fromkeys(raw)); labels=[datetime.strptime(p,"%Y-%m-%d").strftime("%b %d") for p in periods]
        def bkt(d): return ws(d[:10])
    elif gran=="Monthly":
        size=12; periods=[]
        for i in range(size-1,-1,-1):
            m=today.month-i-offset*size; y=today.year+(m-1)//12; m=((m-1)%12)+1; periods.append(f"{y}-{str(m).zfill(2)}")
        labels=[datetime.strptime(p+"-01","%Y-%m-%d").strftime("%b %Y") for p in periods]
        def bkt(d): return d[:7]
    else:
        size=4; periods=[str(today.year-i-offset*size) for i in range(size-1,-1,-1)]; labels=periods[:]
        def bkt(d): return d[:4]
    rows=[]
    for u in visible:
        for p,lbl in zip(periods,labels):
            cnt=sum(1 for l in logs if bkt(l["date"])==p and l["member_id"]==u["id"]); rows.append({"Period":lbl,"User":u["name"].split()[0],"Calls":cnt})
    df=pd.DataFrame(rows)
    if df.empty or df["Calls"].sum()==0: st.info("No call data for this period."); return
    cmap={u["name"].split()[0]:u["color"] for u in visible}; ct=ctype
    if ct=="Bar":            fig=px.bar(df,x="Period",y="Calls",color="User",color_discrete_map=cmap,barmode="group")
    elif ct=="Stacked Bar":  fig=px.bar(df,x="Period",y="Calls",color="User",color_discrete_map=cmap,barmode="stack")
    elif ct=="Line":         fig=px.line(df,x="Period",y="Calls",color="User",color_discrete_map=cmap,markers=True)
    elif ct=="Area":         fig=px.area(df,x="Period",y="Calls",color="User",color_discrete_map=cmap)
    elif ct=="Horizontal Bar": fig=px.bar(df,y="Period",x="Calls",color="User",color_discrete_map=cmap,barmode="stack",orientation="h")
    elif ct=="Pie":          dfa=df.groupby("User")["Calls"].sum().reset_index(); fig=px.pie(dfa,values="Calls",names="User",color="User",color_discrete_map=cmap)
    elif ct=="Donut":        dfa=df.groupby("User")["Calls"].sum().reset_index(); fig=px.pie(dfa,values="Calls",names="User",color="User",color_discrete_map=cmap,hole=0.4)
    else:                    fig=px.scatter(df,x="Period",y="Calls",color="User",color_discrete_map=cmap,size="Calls",size_max=18)
    fig.update_layout(height=300,margin=dict(l=10,r=10,t=20,b=10),legend=dict(orientation="h",yanchor="bottom",y=1.02,xanchor="right",x=1),plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",xaxis=dict(showgrid=False),yaxis=dict(gridcolor="rgba(0,0,0,0.06)"))
    st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# ACCOUNTS — FILTERS + BULK DELETE + SUPABASE
# ══════════════════════════════════════════════════════════════════════════════
def render_accounts(active, is_rep):
    can_add    = has_perm(active["role"], "acc_add")
    can_edit   = has_perm(active["role"], "acc_edit")
    can_delete = has_perm(active["role"], "acc_delete")
    is_admin   = can_add or can_edit or can_delete
    st.subheader("My accounts" if is_rep else "All accounts")

    # ── Filters (configurable by admin in Account Layout) ─────────────────────
    af = st.session_state.get("settings", {}).get("account_filters", {})
    with st.expander("🔍 Filters", expanded=False):
        active_filters = [k for k, v in af.items() if v]
        n_cols = max(len(active_filters), 1)
        fcols  = st.columns(min(n_cols, 6))
        ci     = 0
        f_search = f_sector = f_urgency = f_contact = f_assignee = f_account_owner = ""
        f_branches = None; f_priority = []
        branch_vals = [a["branches"] for a in st.session_state.accounts if a.get("branches")]
        br_min = int(min(branch_vals)) if branch_vals else 0
        br_max = int(max(branch_vals)) if branch_vals else 1000

        if af.get("search"):
            f_search  = fcols[ci%6].text_input("Search", placeholder="Name / brand / ID", key="f_search"); ci+=1
        if af.get("sector"):
            f_sector  = fcols[ci%6].multiselect("Sector", SECTORS, key="f_sector"); ci+=1
        if af.get("urgency"):
            f_urgency = fcols[ci%6].selectbox("Urgency", ["All","Overdue >14d","Critical >30d","Recent ≤14d"], key="f_urgency"); ci+=1
        if af.get("contact"):
            all_contacts = sorted({a["contact_person"] for a in st.session_state.accounts if a.get("contact_person")})
            f_contact = fcols[ci%6].multiselect("Contact person", all_contacts, key="f_contact"); ci+=1
        if af.get("assignee"):
            f_assignee = fcols[ci%6].multiselect("Last called by", [u["name"] for u in st.session_state.users], key="f_assignee"); ci+=1
        if af.get("account_owner"):
            owner_names = sorted({get_user(a.get("account_owner_id",""))["name"] for a in st.session_state.accounts if get_user(a.get("account_owner_id",""))})
            f_account_owner = fcols[ci%6].multiselect("Account owner", owner_names, key="f_account_owner"); ci+=1
        if af.get("branches"):
            f_branches = st.slider("Branches", br_min, max(br_max,br_min+1), (br_min, max(br_max,br_min+1)), key="f_branches")

        priority_field = next((f for f in st.session_state.account_extra_fields if f["label"]=="Priority"), None)
        if priority_field and priority_field.get("options"):
            f_priority = st.multiselect("Priority", priority_field["options"], key="f_priority")

        if st.button("Clear filters", key="clear_filters"):
            for k in ["f_search","f_sector","f_urgency","f_contact","f_assignee","f_priority","f_account_owner"]:
                st.session_state.pop(k, None)
            st.rerun()

    # ── Sort bar ───────────────────────────────────────────────────────────────
    bc1,bc2,bc3 = st.columns([3,2,2])
    sort_by  = bc2.selectbox("Sort", ["last_call_date","account_name","brand_name","branches"], label_visibility="collapsed", key="sort_by")
    sort_asc = bc3.selectbox("Order", ["Ascending","Descending"], label_visibility="collapsed", key="sort_dir")=="Ascending"

    # ── Apply filters ──────────────────────────────────────────────────────────
    accs = list(st.session_state.accounts)
    if is_rep:
        accs = [a for a in accs if any(n["member_id"]==active["id"] for n in a.get("notes",[]))]

    # search
    q = st.session_state.get("f_search","").lower()
    if q: accs = [a for a in accs if q in a["account_name"].lower() or q in a["brand_name"].lower() or q in a["id"].lower()]

    # sector
    secs = st.session_state.get("f_sector",[])
    if secs: accs = [a for a in accs if a.get("sector") in secs]

    # urgency
    urg_filter = st.session_state.get("f_urgency","All")
    if urg_filter == "Overdue >14d":      accs = [a for a in accs if days_since(a["last_call_date"])>14]
    elif urg_filter == "Critical >30d":   accs = [a for a in accs if days_since(a["last_call_date"])>30]
    elif urg_filter == "Recent ≤14d":     accs = [a for a in accs if days_since(a["last_call_date"])<=14]

    # contact person
    contacts = st.session_state.get("f_contact",[])
    if contacts: accs = [a for a in accs if a.get("contact_person") in contacts]

    # last called by
    assignees = st.session_state.get("f_assignee",[])
    if assignees:
        def last_caller(a):
            if not a.get("notes"): return None
            u = get_user(a["notes"][0].get("member_id",""))
            return u["name"] if u else None
        accs = [a for a in accs if last_caller(a) in assignees]

    # branches range
    br_range = st.session_state.get("f_branches",(br_min, max(br_max,br_min+1)))
    accs = [a for a in accs if br_range[0] <= int(a.get("branches",0)) <= br_range[1]]

    # account owner
    owner_filter = st.session_state.get("f_account_owner", [])
    if owner_filter:
        def _owner_name(a):
            u = get_user(a.get("account_owner_id",""))
            return u["name"] if u else None
        accs = [a for a in accs if _owner_name(a) in owner_filter]

    # priority
    if f_priority:
        ef_id = priority_field["id"]
        accs = [a for a in accs if a.get("extra_fields",{}).get(ef_id,"") in f_priority]

    accs = sorted(accs, key=lambda x: str(x.get(sort_by,"")), reverse=not sort_asc)

    # ── Pagination ─────────────────────────────────────────────────────────────
    page_size   = int(st.session_state.get("settings", {}).get("accounts_per_page", 20))
    total_accs  = len(accs)
    total_pages = max(1, (total_accs + page_size - 1) // page_size)
    cur_page    = min(st.session_state.get("acc_page", 1), total_pages)
    st.session_state["acc_page"] = cur_page

    bc1.caption(f"{total_accs} accounts · page {cur_page}/{total_pages}")

    if total_pages > 1:
        pg1, pg2, pg3 = st.columns([1, 2, 1])
        if pg1.button("◀ Prev", key="acc_prev", disabled=(cur_page <= 1)):
            st.session_state["acc_page"] = cur_page - 1; st.rerun()
        pg2.markdown(
            f"<div style='text-align:center;padding-top:6px'>Page {cur_page} of {total_pages}</div>",
            unsafe_allow_html=True
        )
        if pg3.button("Next ▶", key="acc_next", disabled=(cur_page >= total_pages)):
            st.session_state["acc_page"] = cur_page + 1; st.rerun()

    accs = accs[(cur_page - 1) * page_size : cur_page * page_size]

    # ── Bulk delete toolbar (admin only) ───────────────────────────────────────
    if is_admin and len(accs)>0:
        sel_all = st.checkbox(f"Select all {len(accs)} accounts", key="sel_all_accs")
        if sel_all:
            st.session_state.selected_accounts = {a["id"] for a in accs}
        selected = st.session_state.get("selected_accounts", set())
        if selected:
            n_sel = len(selected)
            dc1,dc2,_ = st.columns([2,2,6])
            dc1.markdown(f"**{n_sel} selected**")
            if dc2.button(f"🗑️ Delete {n_sel} selected", type="primary", key="bulk_delete_btn"):
                st.session_state.confirm_bulk_delete = True; st.rerun()
        if st.session_state.get("confirm_bulk_delete"):
            st.warning(f"⚠️ Delete {len(st.session_state.selected_accounts)} accounts? This is soft-deletable.")
            cd1,cd2 = st.columns(2)
            if cd1.button("Yes, delete", type="primary", key="confirm_bulk_yes"):
                for aid in list(st.session_state.selected_accounts):
                    st.session_state.accounts = [a for a in st.session_state.accounts if a["id"]!=aid]
                    sb_soft_delete_account(aid, active["id"], active["name"])
                st.session_state.selected_accounts = set()
                st.session_state.confirm_bulk_delete = False
                st.success("Accounts deleted and logged."); st.rerun()
            if cd2.button("Cancel", key="confirm_bulk_no"):
                st.session_state.confirm_bulk_delete = False; st.rerun()

    vis = st.session_state.get("visible_columns", list(CORE_COLUMNS))
    selected = st.session_state.get("selected_accounts", set())

    for acc in accs:
        d = days_since(acc["last_call_date"])
        last_note = acc["notes"][0] if acc.get("notes") else None
        last_by   = "—"
        if last_note:
            u = get_user(last_note.get("member_id",""))
            if u: last_by = u["name"].split()[0]

        logo_md = b64_img_tag(acc.get("logo_b64"), "acc-logo", acc["brand_name"])

        with st.expander(f"**{acc['brand_name']}** · {acc['account_name']} · {acc['branches']} branches", expanded=False):
            # Per-row select checkbox (admin)
            if is_admin:
                is_checked = acc["id"] in selected
                chk = st.checkbox("Select for bulk action", value=is_checked, key=f"sel_{acc['id']}")
                if chk and acc["id"] not in selected:
                    st.session_state.selected_accounts.add(acc["id"])
                elif not chk and acc["id"] in selected:
                    st.session_state.selected_accounts.discard(acc["id"])

            # Info grid
            row_cols = st.columns([1,5]) if acc.get("logo_b64") else [st.container()]
            info_c   = row_cols[1] if acc.get("logo_b64") else row_cols[0]
            if acc.get("logo_b64"): row_cols[0].markdown(logo_md, unsafe_allow_html=True)
            with info_c:
                # ── Core fields grid ───────────────────────────────────────────
                g = st.columns(4); ci = 0
                def show_in(grid, label, val, idx):
                    if label in vis:
                        grid[idx%4].markdown(f"**{label}:** {val}")
                        return idx + 1
                    return idx
                ci = show_in(g, "ID",           f"`{acc['id']}`",            ci)
                ci = show_in(g, "Account Name", acc["account_name"],          ci)
                ci = show_in(g, "Brand Name",   acc["brand_name"],            ci)
                ci = show_in(g, "Branches",     acc["branches"],              ci)
                ci = show_in(g, "Sector",       acc["sector"],                ci)
                ci = show_in(g, "Contact",      acc.get("contact_person","—"),ci)
                owner_u = get_user(acc.get("account_owner_id",""))
                ci = show_in(g, "Account Owner", owner_u["name"] if owner_u else "—", ci)
                if "Last Call" in vis:
                    g[ci%4].markdown(f"**Last call:** {acc['last_call_date']} &nbsp;"+urgency_badge(d), unsafe_allow_html=True); ci+=1
                f5 = acc.get("extra_fields",{}).get("f5_number","")
                if f5: ci = show_in(g, "F5 Number", f5, ci)

                # ── Custom fields — grouped by section ─────────────────────────
                extra_fields_sorted = sorted(
                    st.session_state.account_extra_fields,
                    key=lambda x: x.get("sort_order", 99)
                )
                sections = sorted(
                    [s for s in st.session_state.get("account_sections", [])
                     if "Accounts" in s.get("affects", ["Accounts"])],
                    key=lambda x: x.get("sort_order", 99)
                )
                assigned_to_section = {f["id"] for f in extra_fields_sorted if f.get("section_id")}

                for sec in sections:
                    sec_fields = [f for f in extra_fields_sorted if f.get("section_id") == sec["id"]]
                    sec_vals   = [(f, acc.get("extra_fields",{}).get(f["id"],"")) for f in sec_fields]
                    sec_vals   = [(f, v) for f, v in sec_vals if v and f["label"] in vis]
                    if not sec_vals:
                        continue
                    st.markdown(
                        f'<div style="margin-top:12px;margin-bottom:6px;font-weight:600;'
                        f'color:{VIOLET};border-bottom:2px solid {VIOLET_LIGHT};padding-bottom:3px">'
                        f'{sec["label"]}</div>',
                        unsafe_allow_html=True
                    )
                    sg = st.columns(4); si = 0
                    for f, val in sec_vals:
                        sg[si%4].markdown(f"**{f['label']}:** {val}"); si+=1

                # Unsectioned custom fields (no section assigned)
                unsectioned = [f for f in extra_fields_sorted if f["id"] not in assigned_to_section]
                ug = st.columns(4); ui = 0
                for f in unsectioned:
                    val = acc.get("extra_fields",{}).get(f["id"],"")
                    if val and f["label"] in vis:
                        ug[ui%4].markdown(f"**{f['label']}:** {val}"); ui+=1
            st.markdown(f"**Last logged by:** {last_by}")

            if acc.get("notes"):
                st.markdown("**Recent interactions:**")
                for note in acc["notes"][:3]:
                    u = get_user(note.get("member_id","")); s = get_status(note.get("status_id",""))
                    uname=u["name"].split()[0] if u else "—"; slabel=s["label"] if s else ""
                    st.markdown(f"&nbsp;&nbsp;`{note['date']}` **{uname}** {slabel}"+(f" — {note['text']}" if note.get("text") else ""))

            btn_c = st.columns(5)
            if has_perm(active["role"],"log"):
                if btn_c[0].button("📞 " + get_btn("log_call"), key=f"log_{acc['id']}"):
                    st.session_state.log_target=acc["id"]; st.session_state.show_log_modal=True; st.rerun()
            if can_edit:
                if btn_c[1].button("✏️ " + get_btn("edit"), key=f"edit_{acc['id']}"):
                    st.session_state.editing_account=acc["id"]; st.rerun()
            if can_delete:
                if btn_c[2].button("🗑️ " + get_btn("delete"), key=f"del_{acc['id']}"):
                    st.session_state.accounts = [a for a in st.session_state.accounts if a["id"]!=acc["id"]]
                    sb_soft_delete_account(acc["id"], active["id"], active["name"])
                    st.success(f"'{acc['brand_name']}' deleted."); st.rerun()

    if st.session_state.get("editing_account"):
        _render_edit_account()

# ── Edit account ───────────────────────────────────────────────────────────────
def _render_edit_account():
    acc_id = st.session_state.editing_account
    acc = next((a for a in st.session_state.accounts if a["id"]==acc_id), None)
    if not acc: del st.session_state["editing_account"]; return
    active = get_active_user()
    can_name  = has_perm(active["role"], "acc_edit_name")  or has_perm(active["role"], "acc_edit")
    can_brand = has_perm(active["role"], "acc_edit_brand") or has_perm(active["role"], "acc_edit")
    can_f5    = has_perm(active["role"], "acc_edit_f5")    or has_perm(active["role"], "acc_edit")
    can_gen   = has_perm(active["role"], "acc_edit")
    st.markdown("---"); st.subheader(f"Edit — {acc['brand_name']}")
    with st.form(f"edit_acc_{acc_id}"):
        c1,c2 = st.columns(2)
        new_name    = c1.text_input("Account name", value=acc["account_name"],  disabled=not can_name)
        new_brand   = c2.text_input("Brand name",   value=acc["brand_name"],    disabled=not can_brand)
        c3,c4 = st.columns(2)
        new_branches = c3.number_input("# of branches", min_value=1, value=int(acc["branches"]), disabled=not can_gen)
        sect_idx = SECTORS.index(acc["sector"]) if acc["sector"] in SECTORS else 0
        new_sector   = c4.selectbox("Sector", SECTORS, index=sect_idx, disabled=not can_gen)
        c5,c6 = st.columns(2)
        new_contact  = c5.text_input("Contact person", value=acc.get("contact_person",""), disabled=not can_gen)
        cur_f5 = acc.get("extra_fields",{}).get("f5_number","")
        new_f5 = c6.text_input("F5 Number", value=cur_f5, placeholder="6-digit number", max_chars=6, key=f"f5_{acc_id}", disabled=not can_f5)
        user_names_edit = ["— None —"] + [u["name"] for u in st.session_state.users]
        cur_owner = get_user(acc.get("account_owner_id",""))
        cur_owner_idx = user_names_edit.index(cur_owner["name"]) if cur_owner and cur_owner["name"] in user_names_edit else 0
        new_owner_sel = st.selectbox("Account Owner", user_names_edit, index=cur_owner_idx, key=f"owner_{acc_id}", disabled=not can_gen)
        new_logo_f   = st.file_uploader("Brand logo (PNG/JPG)", type=["png","jpg","jpeg"], key=f"logo_up_{acc_id}")
        ef_vals = {}
        for f in st.session_state.account_extra_fields:
            cur = acc.get("extra_fields",{}).get(f["id"],"")
            if f["type"]=="select":
                opts=[""]+(f["options"] or []); idx2=opts.index(cur) if cur in opts else 0
                ef_vals[f["id"]]=st.selectbox(f["label"],opts,index=idx2,key=f"ef_e_{acc_id}_{f['id']}")
            else:
                ef_vals[f["id"]]=st.text_input(f["label"],value=cur,key=f"ef_e_{acc_id}_{f['id']}")
        s1,s2,s3 = st.columns(3)
        do_save=s1.form_submit_button("Save",type="primary"); do_clear=s2.form_submit_button("Remove logo"); do_cancel=s3.form_submit_button("Cancel")
    if do_save:
        if new_f5 and (not new_f5.isdigit() or len(new_f5) != 6):
            st.error("F5 Number must be exactly 6 digits.")
        else:
            ef_vals["f5_number"] = new_f5.strip()
            new_owner_id = next((u["id"] for u in st.session_state.users if u["name"]==new_owner_sel), "") if new_owner_sel != "— None —" else ""
            new_b64 = img_to_b64(new_logo_f) if new_logo_f else acc.get("logo_b64")
            for i,a in enumerate(st.session_state.accounts):
                if a["id"]==acc_id:
                    st.session_state.accounts[i]={**a,"account_name":new_name,"brand_name":new_brand,"branches":int(new_branches),"sector":new_sector,"contact_person":new_contact,"account_owner_id":new_owner_id,"extra_fields":ef_vals,"logo_b64":new_b64}
                    sb_upsert_account(st.session_state.accounts[i]); break
            del st.session_state["editing_account"]; st.success("Account updated."); st.rerun()
    if do_clear:
        for i,a in enumerate(st.session_state.accounts):
            if a["id"]==acc_id: st.session_state.accounts[i]["logo_b64"]=None; sb_upsert_account(st.session_state.accounts[i]); break
        del st.session_state["editing_account"]; st.rerun()
    if do_cancel:
        del st.session_state["editing_account"]; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# DELETED ACCOUNTS — LOG + RESTORE
# ══════════════════════════════════════════════════════════════════════════════
def render_deleted_accounts(active):
    st.subheader("🗂️ Deleted accounts log")
    if not sb_available():
        st.info("Supabase not connected — deletion log unavailable in mock mode.")
        return
    deletions = sb_fetch_deleted_accounts()
    if not deletions:
        st.success("No deleted accounts on record.")
        return
    st.caption(f"{len(deletions)} deletion records")
    for d in deletions:
        c1,c2,c3,c4 = st.columns([2,2,2,1])
        c1.markdown(f"**`{d.get('account_id','?')}`**")
        c2.markdown(f"Deleted by: **{d.get('deleted_by_name','?')}**")
        ts = d.get("deleted_at","")
        c3.markdown(f"<small style='color:#888'>{ts[:19] if ts else '—'}</small>", unsafe_allow_html=True)
        if has_perm(active["role"],"acc_add") or has_perm(active["role"],"acc_edit"):
            if c4.button("↩ " + get_btn("restore"), key=f"restore_{d.get('id')}"):
                sb_restore_account(d["account_id"])
                # also reload into local state
                if sb_available():
                    st.session_state.accounts = sb_fetch_accounts()
                st.success(f"Account {d['account_id']} restored."); st.rerun()
        st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# URGENCY
# ══════════════════════════════════════════════════════════════════════════════
def render_urgency(active):
    st.subheader("Accounts not contacted in 14+ days")
    urgency = sorted([a for a in st.session_state.accounts if days_since(a["last_call_date"])>14], key=lambda x:days_since(x["last_call_date"]),reverse=True)
    st.caption(f"{len(urgency)} overdue")
    if not urgency: st.success("All accounts contacted recently."); return
    for acc in urgency:
        d = days_since(acc["last_call_date"])
        c1,c2,c3,c4 = st.columns([2,2,1,1])
        c1.markdown(f"**{acc['brand_name']}** `{acc['id']}`")
        c2.markdown(f"<small>{acc['account_name']} · {acc['branches']} branches</small>", unsafe_allow_html=True)
        c3.markdown(urgency_badge(d), unsafe_allow_html=True)
        if has_perm(active["role"],"log"):
            if c4.button("Log call", key=f"urg_{acc['id']}"):
                st.session_state.log_target=acc["id"]; st.session_state.show_log_modal=True; st.rerun()
        st.divider()

# ══════════════════════════════════════════════════════════════════════════════
# ACTIVITY LOG
# ══════════════════════════════════════════════════════════════════════════════
def render_log(active, is_rep):
    st.subheader("My interaction log" if is_rep else "Interaction log")
    logs = get_all_logs(user_id=active["id"] if is_rep else None)
    st.caption(f"{len(logs)} entries")
    if not logs: st.info("No interactions logged yet."); return
    rows = []
    for l in logs:
        u=get_user(l.get("member_id","")); s=get_status(l.get("status_id",""))
        ef=l.get("extra_fields",{})
        row={"Date":l["date"],"Brand":l["brand_name"],"Account":l["account_name"],"Team Member":u["name"] if u else "—","Status":s["label"] if s else "—","Notes":l.get("text","")}
        for f in st.session_state.call_extra_fields: row[f["label"]]=ef.get(f["id"],"")
        rows.append(row)
    df=pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    if has_perm(active["role"],"export"):
        st.download_button(get_btn("export_csv"), df.to_csv(index=False).encode(), "activity_log.csv","text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════════════════════
def render_users(active):
    is_admin = has_perm(active["role"],"manage_users")
    st.subheader("User management" if is_admin else "Team members")
    if is_admin:
        with st.expander("📥 Bulk import users via CSV or Excel", expanded=False):
            role_ids=[r["id"] for r in st.session_state.roles]
            tmpl=pd.DataFrame(columns=["Name","Email","Role ("+"/".join(role_ids)+")"])
            ud1,ud2=st.columns(2)
            ud1.download_button("⬇ CSV template",   tmpl.to_csv(index=False).encode(), "users_template.csv",  "text/csv",                                                           key="ul_tmpl_csv")
            ud2.download_button("⬇ Excel template", df_to_excel_bytes(tmpl),           "users_template.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="ul_tmpl_xl")
            up=st.file_uploader("Upload file (CSV, XLSX or XLS)", type=["csv","xlsx","xls"], key="bulk_user_up")
            if up:
                try:
                    df=read_upload(up); df.columns=[c.strip() for c in df.columns]
                    st.caption(f"{len(df)} rows"); st.dataframe(df.head(), use_container_width=True)
                    mode=st.radio("Mode",["Add new","Update existing by email"],horizontal=True,key="bulk_u_mode")
                    if st.button("Import users", type="primary", key="do_bulk_users"):
                        added=updated=skipped=0; total_u=max(len(df),1)
                        prog_u=st.progress(0, text="Importing users…")
                        for i,(_, row) in enumerate(df.iterrows()):
                            prog_u.progress((i+1)/total_u, text=f"Row {i+1} of {total_u}…")
                            name=str(row.get("Name","")).strip(); email=str(row.get("Email","")).strip()
                            role_raw=str(row.iloc[2] if len(row)>2 else "viewer").strip().lower()
                            if not name or not email: skipped+=1; continue
                            role_val=role_raw if role_raw in role_ids else "viewer"
                            existing=next((u for u in st.session_state.users if u["email"].lower()==email.lower()),None)
                            if existing and "Update" in mode:
                                existing["name"]=name; existing["role"]=role_val; sb_upsert_user(existing); updated+=1
                            elif not existing:
                                c=TEAM_COLORS[len(st.session_state.users)%len(TEAM_COLORS)]
                                new_u={"id":"u"+new_id(),"name":name,"email":email,"role":role_val,"extra_fields":{},"color":c["color"],"bg":c["bg"]}
                                st.session_state.users.append(new_u); sb_upsert_user(new_u); added+=1
                            else: skipped+=1
                        prog_u.empty()
                        st.success(f"Done: {added} added · {updated} updated · {skipped} skipped"); st.rerun()
                except Exception as ex: st.error(f"CSV error: {ex}")
    # ── Column headers ────────────────────────────────────────────────────────
    pc = st.session_state.get("settings",{}).get("primary_color", VIOLET)
    lc = st.session_state.get("settings",{}).get("light_color",   VIOLET_LIGHT)
    hc1,hc2,hc3,hc4,hc5 = st.columns([1,3,3,2,2])
    for col, label in zip([hc1,hc2,hc3,hc4,hc5],["","Name","Email","Role","Actions"]):
        col.markdown(f"<small style='color:#888;font-weight:600;text-transform:uppercase;letter-spacing:.06em'>{label}</small>", unsafe_allow_html=True)
    st.markdown(f"<hr style='margin:4px 0 8px;border-color:{lc}'>", unsafe_allow_html=True)

    for u in st.session_state.users:
        uc1,uc2,uc3,uc4,uc5 = st.columns([1,3,3,2,2])
        # Avatar
        ph = (u.get("extra_fields") or {}).get("_photo")
        if ph:
            uc1.markdown(f'<img src="data:image/png;base64,{ph}" style="width:36px;height:36px;border-radius:50%;object-fit:cover">', unsafe_allow_html=True)
        else:
            ini = initials(u["name"])
            uc1.markdown(f'<div style="width:36px;height:36px;border-radius:50%;background:{pc};display:inline-flex;align-items:center;justify-content:center;font-weight:700;color:#fff;font-size:13px">{ini}</div>', unsafe_allow_html=True)
        uc2.markdown(f"**{u['name']}**")
        uc3.markdown(f"<small style='color:#555'>{u['email']}</small>", unsafe_allow_html=True)
        uc4.markdown(role_badge_html(u["role"]), unsafe_allow_html=True)
        if is_admin:
            b1,b2 = uc5.columns(2)
            if b1.button("Edit",   key=f"eu_{u['id']}", use_container_width=True): st.session_state.editing_user=u["id"]; st.rerun()
            if u["id"]!=active["id"] and b2.button("Del", key=f"du_{u['id']}", use_container_width=True):
                st.session_state.users=[x for x in st.session_state.users if x["id"]!=u["id"]]
                sb_delete_user(u["id"]); st.rerun()
        st.markdown(f"<div style='height:1px;background:{lc};margin:2px 0 8px'></div>", unsafe_allow_html=True)
    if is_admin and st.button(get_btn("add_user"), type="primary", key="add_user_btn"):
        st.session_state.editing_user="__new__"; st.rerun()
    if st.session_state.get("editing_user"):
        eid=st.session_state.editing_user
        existing=next((u for u in st.session_state.users if u["id"]==eid),None) if eid!="__new__" else None
        st.markdown("---"); st.subheader("Edit user" if existing else "Add user")
        with st.form("user_form"):
            n_=st.text_input("Full name",value=existing["name"] if existing else "")
            e_=st.text_input("Email",value=existing["email"] if existing else "")
            role_ids=[r["id"] for r in st.session_state.roles]; role_labels=[r["label"] for r in st.session_state.roles]
            cur_i=role_ids.index(existing["role"]) if existing and existing["role"] in role_ids else 2
            is_me=existing and existing["id"]==active["id"]
            if is_me:
                st.selectbox("Role",role_labels,index=cur_i,disabled=True); r_=existing["role"]
                st.caption("You cannot change your own role.")
            else:
                r_sel=st.selectbox("Role",role_labels,index=cur_i); r_=role_ids[role_labels.index(r_sel)]
            ef_={}
            for f in st.session_state.user_extra_fields:
                cur_v=existing.get("extra_fields",{}).get(f["id"],"") if existing else ""
                if f["type"]=="select": ef_[f["id"]]=st.selectbox(f["label"],[""]+(f["options"] or []))
                else: ef_[f["id"]]=st.text_input(f["label"],value=cur_v)
            st.markdown("**Password**")
            if existing:
                pw_new=st.text_input("New password (leave blank to keep current)",type="password",key="pw_edit")
            else:
                pw_new=st.text_input("Initial password (required)",type="password",key="pw_new")
            sv,ca=st.columns(2); do_save=sv.form_submit_button("Save",type="primary"); do_cancel=ca.form_submit_button("Cancel")
        if do_save and n_:
            if not existing and not pw_new:
                st.error("Password is required for new users.")
            else:
                c=TEAM_COLORS[len(st.session_state.users)%len(TEAM_COLORS)]
                new_u={"id":existing["id"] if existing else "u"+new_id(),"name":n_,"email":e_,"role":r_,"extra_fields":ef_,**({"color":existing["color"],"bg":existing["bg"]} if existing else {"color":c["color"],"bg":c["bg"]})}
                if pw_new:
                    new_u["password_hash"] = hash_password(pw_new)
                elif existing:
                    new_u["password_hash"] = existing.get("password_hash","")
                if existing: st.session_state.users=[new_u if u["id"]==existing["id"] else u for u in st.session_state.users]
                else: st.session_state.users.append(new_u)
                sb_upsert_user(new_u); del st.session_state["editing_user"]; st.rerun()
        if do_cancel: del st.session_state["editing_user"]; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# FIELD BUILDER + ROLES + SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
def render_schema():
    t1,t2,t3,t4=st.tabs(["Custom Fields","System Layout","Call Statuses","Role Manager"])
    with t1:
        st.subheader("Custom fields")
        FIELD_TYPES = ["text","number","date","select"]
        all_fields=([(f,"Account") for f in st.session_state.account_extra_fields]+[(f,"User") for f in st.session_state.user_extra_fields]+[(f,"Call") for f in st.session_state.call_extra_fields])
        if not all_fields: st.caption("No custom fields yet.")
        for f,ent in all_fields:
            c1,c2,c3,c4,c5,c6=st.columns([2,1,1,2,1,1])
            c1.markdown(f"**{f['label']}**")
            c2.markdown(f"`{f['type']}`")
            c3.markdown(f'<span class="badge-info">{ent}</span>', unsafe_allow_html=True)
            c4.markdown(", ".join((f.get("options") or [])[:5]) or "—")
            if c5.button("Edit", key=f"ef_edit_{f['id']}"):
                st.session_state["dlg_field_id"]     = f["id"]
                st.session_state["dlg_field_entity"] = ent
                _edit_field_dialog()
            if c6.button("Remove", key=f"df_{f['id']}"):
                if ent=="Account": st.session_state.account_extra_fields=[x for x in st.session_state.account_extra_fields if x["id"]!=f["id"]]
                elif ent=="User":  st.session_state.user_extra_fields=[x for x in st.session_state.user_extra_fields if x["id"]!=f["id"]]
                else:              st.session_state.call_extra_fields=[x for x in st.session_state.call_extra_fields if x["id"]!=f["id"]]
                if ent == "Account": save_layout()
                st.rerun()

        st.markdown("---"); st.markdown("**Add field**")
        with st.form("add_field"):
            fc1,fc2,fc3=st.columns(3); lbl=fc1.text_input("Label"); ftype=fc2.selectbox("Type",FIELD_TYPES); fent=fc3.selectbox("Applies to",["Account","User","Call"])
            opts_str=st.text_input("Options (comma-separated — only for 'select' type)", placeholder="e.g. High, Medium, Low")
            if st.form_submit_button("Add field",type="primary") and lbl:
                nf={"id":"f"+new_id(),"label":lbl,"type":ftype,"options":[o.strip() for o in opts_str.split(",") if o.strip()], "sort_order":99, "section_id":None}
                if fent=="Account": st.session_state.account_extra_fields.append(nf); save_layout()
                elif fent=="User":  st.session_state.user_extra_fields.append(nf)
                else:               st.session_state.call_extra_fields.append(nf)
                st.rerun()
    with t2:
        st.subheader("System Layout")
        st.caption("Click any section to expand it. All settings are persisted to Supabase.")

        s_obj           = st.session_state.settings
        sections        = st.session_state.account_sections
        fields          = st.session_state.account_extra_fields
        sections_sorted = sorted(sections, key=lambda x: x.get("sort_order", 99))

        # ── Column Visibility ──────────────────────────────────────────────────
        with st.expander("🗂 Column Visibility", expanded=False):
            affect_badge("Accounts")
            all_cols = list(CORE_COLUMNS) + [f["label"] for f in st.session_state.account_extra_fields]
            current  = st.session_state.get("visible_columns", list(CORE_COLUMNS))
            col_grid = st.columns(4); new_vis = []
            for i, col in enumerate(all_cols):
                if col_grid[i%4].checkbox(col, value=col in current, key=f"layout_col_vis_{col}"):
                    new_vis.append(col)
            if new_vis != current:
                st.session_state.visible_columns = new_vis; st.rerun()

        # ── Active Filters ─────────────────────────────────────────────────────
        with st.expander("🔍 Active Filters", expanded=False):
            affect_badge("Accounts")
            st.caption("Toggle which filters appear in the Accounts tab.")
            af = s_obj.get("account_filters", {})
            FILTER_LABELS = {
                "search": "Search (text)", "sector": "Sector", "urgency": "Urgency",
                "contact": "Contact person", "assignee": "Last called by",
                "account_owner": "Account owner", "branches": "Branches (slider)",
            }
            fg = st.columns(3); changed = False
            for i, (fk, fl) in enumerate(FILTER_LABELS.items()):
                new_val = fg[i%3].checkbox(fl, value=af.get(fk, True), key=f"af_toggle_{fk}")
                if new_val != af.get(fk, True):
                    af[fk] = new_val; changed = True
            if changed:
                s_obj["account_filters"] = af; save_settings(); st.rerun()

        # ── Page Size ──────────────────────────────────────────────────────────
        with st.expander("📄 Page Size", expanded=False):
            affect_badge("Accounts")
            st.caption("Number of accounts displayed per page in the Accounts tab.")
            cur_ps = int(s_obj.get("accounts_per_page", 20))
            new_ps = st.number_input("Accounts per page", min_value=5, max_value=500, value=cur_ps, step=5, key="layout_page_size")
            if int(new_ps) != cur_ps:
                s_obj["accounts_per_page"] = int(new_ps); save_settings(); st.rerun()

        # ── Sections ──────────────────────────────────────────────────────────
        with st.expander("📑 Sections", expanded=False):
            affect_badge("Accounts")

            if not sections_sorted:
                st.caption("No sections yet. Add one below to group your fields.")

            # Column headers
            if sections_sorted:
                hh1, hh2, hh3, hh4, hh5, hh6 = st.columns([3, 2, 1, 1, 1, 1])
                hh1.caption("Section"); hh2.caption("Affects"); hh3.caption(""); hh4.caption(""); hh5.caption(""); hh6.caption("")

            for idx, sec in enumerate(sections_sorted):
                sec.setdefault("affects", ["Accounts"])  # backward compat

                if st.session_state.get("editing_section") == sec["id"]:
                    st.markdown(f"**Editing: {sec['label']}**")
                    with st.form(f"edit_sec_{sec['id']}"):
                        ef1, ef2 = st.columns(2)
                        new_lbl     = ef1.text_input("Section name", value=sec["label"])
                        new_affects = ef2.multiselect(
                            "Affects",
                            SECTION_AFFECT_OPTIONS,
                            default=[a for a in sec["affects"] if a in SECTION_AFFECT_OPTIONS],
                        )
                        # Fields belonging to this section — filtered by affects
                        affected_fields = []
                        if "Accounts" in sec.get("affects", ["Accounts"]):
                            affected_fields += list(st.session_state.account_extra_fields)
                        if "Calls" in sec.get("affects", []):
                            affected_fields += list(st.session_state.call_extra_fields)
                        all_field_labels     = [f["label"] for f in affected_fields]
                        current_field_labels = [f["label"] for f in affected_fields if f.get("section_id") == sec["id"]]
                        new_field_labels = st.multiselect(
                            "Fields in this section",
                            all_field_labels,
                            default=current_field_labels,
                        )
                        sv, ca = st.columns(2)
                        do_save_sec   = sv.form_submit_button("Save", type="primary")
                        do_cancel_sec = ca.form_submit_button("Cancel")
                    if do_save_sec:
                        sec["label"]   = new_lbl.strip() or sec["label"]
                        sec["affects"] = new_affects or ["Accounts"]
                        new_fids = {f["id"] for f in affected_fields if f["label"] in new_field_labels}
                        for pool in (st.session_state.account_extra_fields, st.session_state.call_extra_fields):
                            for f in pool:
                                if f["id"] in new_fids:
                                    f["section_id"] = sec["id"]
                                elif f.get("section_id") == sec["id"]:
                                    f["section_id"] = None
                        st.session_state.pop("editing_section", None)
                        save_layout(); st.rerun()
                    if do_cancel_sec:
                        st.session_state.pop("editing_section", None); st.rerun()
                else:
                    sc1, sc2, sc3, sc4, sc5, sc6 = st.columns([3, 2, 1, 1, 1, 1])
                    sc1.markdown(f"**{sec['label']}**")
                    # Affects badges inline
                    badges_html = " ".join(
                        f'<span style="font-size:11px;background:{AFFECT_COLORS.get(a,("#f5f5f5","#555"))[0]};'
                        f'color:{AFFECT_COLORS.get(a,("#f5f5f5","#555"))[1]};padding:2px 8px;'
                        f'border-radius:10px;font-weight:600">{a}</span>'
                        for a in sec["affects"]
                    )
                    sc2.markdown(badges_html or "—", unsafe_allow_html=True)
                    if sc3.button("⬆", key=f"sec_up_{sec['id']}", disabled=(idx == 0)):
                        tmp = sections_sorted[:]
                        tmp[idx], tmp[idx-1] = tmp[idx-1], tmp[idx]
                        for i, s in enumerate(tmp): s["sort_order"] = i
                        save_layout(); st.rerun()
                    if sc4.button("⬇", key=f"sec_dn_{sec['id']}", disabled=(idx == len(sections_sorted)-1)):
                        tmp = sections_sorted[:]
                        tmp[idx], tmp[idx+1] = tmp[idx+1], tmp[idx]
                        for i, s in enumerate(tmp): s["sort_order"] = i
                        save_layout(); st.rerun()
                    if sc5.button("✏️", key=f"sec_edit_{sec['id']}"):
                        st.session_state["editing_section"] = sec["id"]; st.rerun()
                    if sc6.button("🗑️", key=f"sec_del_{sec['id']}"):
                        for pool in (st.session_state.account_extra_fields, st.session_state.call_extra_fields):
                            for f in pool:
                                if f.get("section_id") == sec["id"]:
                                    f["section_id"] = None
                        st.session_state.account_sections = [s for s in st.session_state.account_sections if s["id"] != sec["id"]]
                        save_layout(); st.rerun()

            st.markdown("---")
            st.caption("Add a new section")
            with st.form("add_section_form"):
                af1, af2 = st.columns(2)
                new_sec_lbl     = af1.text_input("Section name", placeholder="e.g. Contract Info")
                new_sec_affects = af2.multiselect("Affects", SECTION_AFFECT_OPTIONS, default=["Accounts"])
                if st.form_submit_button("Add section", type="primary") and new_sec_lbl.strip():
                    max_ord = max((s.get("sort_order", 0) for s in sections), default=-1) + 1
                    st.session_state.account_sections.append({
                        "id":         "sec" + new_id(),
                        "label":      new_sec_lbl.strip(),
                        "sort_order": max_ord,
                        "affects":    new_sec_affects or ["Accounts"],
                    })
                    save_layout(); st.rerun()

        # ── Fields ────────────────────────────────────────────────────────────
        with st.expander("🧩 Fields", expanded=False):
            affect_badge("Accounts"); affect_badge("Calls")
            all_fields_combined = (
                [(f, "Account") for f in st.session_state.account_extra_fields] +
                [(f, "Call")    for f in st.session_state.call_extra_fields]
            )
            if not all_fields_combined:
                st.caption("No custom fields defined. Add fields in the Custom Fields tab.")
            else:
                section_opts        = ["— None —"] + [s["label"] for s in sections_sorted]
                section_id_by_label = {s["label"]: s["id"] for s in sections_sorted}
                section_lbl_by_id   = {s["id"]: s["label"] for s in sections_sorted}
                hc1, hc2, hc3, hc4, hc5 = st.columns([3, 1, 2, 1, 1])
                hc1.caption("Field"); hc2.caption("Entity"); hc3.caption("Section"); hc4.caption(""); hc5.caption("")
                groups = [("Unsectioned", None)] + [(s["label"], s["id"]) for s in sections_sorted]
                for grp_label, grp_id in groups:
                    grp_entries = sorted(
                        [(f, ent) for f, ent in all_fields_combined if f.get("section_id") == grp_id],
                        key=lambda x: x[0].get("sort_order", 99)
                    )
                    if not grp_entries:
                        continue
                    st.markdown(f"**{grp_label}**")
                    for i, (f, ent) in enumerate(grp_entries):
                        fc1, fc2, fc3, fc4, fc5 = st.columns([3, 1, 2, 1, 1])
                        fc1.markdown(f"{f['label']} `{f['type']}`")
                        fc2.caption(ent)
                        # Only offer sections compatible with this field's entity
                        ent_affects = "Accounts" if ent == "Account" else "Calls"
                        compat_secs = [s for s in sections_sorted if ent_affects in s.get("affects", ["Accounts"])]
                        compat_opts = ["— None —"] + [s["label"] for s in compat_secs]
                        compat_id_by_lbl = {s["label"]: s["id"] for s in compat_secs}
                        cur_lbl = section_lbl_by_id.get(f.get("section_id"), "— None —")
                        if cur_lbl not in compat_opts: cur_lbl = "— None —"
                        cur_idx = compat_opts.index(cur_lbl)
                        new_lbl = fc3.selectbox(
                            "", compat_opts, index=cur_idx,
                            key=f"fsec_{f['id']}", label_visibility="collapsed"
                        )
                        new_sid = compat_id_by_lbl.get(new_lbl) if new_lbl != "— None —" else None
                        if new_sid != f.get("section_id"):
                            f["section_id"] = new_sid
                            pool = st.session_state.account_extra_fields if ent=="Account" else st.session_state.call_extra_fields
                            max_so = max((x.get("sort_order",0) for x in pool if x.get("section_id")==new_sid and x["id"]!=f["id"]), default=-1)
                            f["sort_order"] = max_so + 1
                            save_layout(); st.rerun()
                        if fc4.button("⬆", key=f"fup_{f['id']}", disabled=(i == 0)):
                            tmp = [e for e, _ in grp_entries]
                            tmp[i], tmp[i-1] = tmp[i-1], tmp[i]
                            for j, x in enumerate(tmp): x["sort_order"] = j
                            save_layout(); st.rerun()
                        if fc5.button("⬇", key=f"fdn_{f['id']}", disabled=(i == len(grp_entries)-1)):
                            tmp = [e for e, _ in grp_entries]
                            tmp[i], tmp[i+1] = tmp[i+1], tmp[i]
                            for j, x in enumerate(tmp): x["sort_order"] = j
                            save_layout(); st.rerun()

        # ── System Identity ───────────────────────────────────────────────────
        with st.expander("🏢 System Identity", expanded=False):
            affect_badge("System-wide")
            s = st.session_state.settings
            with st.form("sys_settings"):
                new_name  = st.text_input("System name", value=s.get("system_name","CIMS"))
                logo_file = st.file_uploader("System logo (PNG/JPG)", type=["png","jpg","jpeg"], key="sys_logo_up")
                if s.get("system_logo_b64"):
                    st.markdown("**Current logo:**")
                    st.markdown(b64_img_tag(s["system_logo_b64"],"sys-logo","Logo"), unsafe_allow_html=True)
                ia,ib,ic = st.columns(3)
                do_save_id  = ia.form_submit_button("Save", type="primary")
                do_clear_id = ib.form_submit_button("Remove logo")
            if do_save_id:
                s["system_name"]    = new_name
                s["system_logo_b64"] = img_to_b64(logo_file) if logo_file else s.get("system_logo_b64")
                save_settings(); st.success("Identity saved."); st.rerun()
            if do_clear_id:
                s["system_logo_b64"] = None
                save_settings(); st.success("Logo removed."); st.rerun()

        # ── Colors ────────────────────────────────────────────────────────────
        with st.expander("🎨 Colors", expanded=False):
            affect_badge("System-wide")
            s = st.session_state.settings
            st.caption("Primary is used for buttons, borders, and text accents. Light is used for badge and banner backgrounds.")
            with st.form("color_settings"):
                cc1, cc2 = st.columns(2)
                new_pc = cc1.color_picker("Primary color",       value=s.get("primary_color", VIOLET))
                new_lc = cc2.color_picker("Accent / light color", value=s.get("light_color",   VIOLET_LIGHT))
                ca1, ca2 = st.columns(2)
                do_save_color  = ca1.form_submit_button("Apply colors", type="primary")
                do_reset_color = ca2.form_submit_button("Reset to defaults")
            if do_save_color:
                s["primary_color"] = new_pc; s["light_color"] = new_lc
                save_settings(); st.success("Colors updated — refresh the page to see the full effect."); st.rerun()
            if do_reset_color:
                s["primary_color"] = VIOLET; s["light_color"] = VIOLET_LIGHT
                save_settings(); st.success("Colors reset."); st.rerun()

        # ── Button Labels ─────────────────────────────────────────────────────
        with st.expander("🔘 Button Labels", expanded=False):
            affect_badge("System-wide")
            s = st.session_state.settings
            st.caption("Rename any action button throughout the app. Leave blank to keep the default.")
            labels = s.get("button_labels", dict(DEFAULT_BUTTON_LABELS))
            with st.form("button_labels_form"):
                new_labels = {}
                bl_cols = st.columns(2)
                for i, (key, default) in enumerate(DEFAULT_BUTTON_LABELS.items()):
                    cur = labels.get(key, default)
                    new_labels[key] = bl_cols[i%2].text_input(
                        default, value=cur, key=f"bl_{key}", placeholder=default
                    )
                bl1, bl2 = st.columns(2)
                do_save_labels  = bl1.form_submit_button("Save labels", type="primary")
                do_reset_labels = bl2.form_submit_button("Reset to defaults")
            if do_save_labels:
                s["button_labels"] = {k: v.strip() or DEFAULT_BUTTON_LABELS[k] for k, v in new_labels.items()}
                save_settings(); st.success("Button labels saved."); st.rerun()
            if do_reset_labels:
                s["button_labels"] = dict(DEFAULT_BUTTON_LABELS)
                save_settings(); st.success("Labels reset."); st.rerun()

        # ── System Tabs ───────────────────────────────────────────────────────
        with st.expander("🗂 System Tabs", expanded=False):
            affect_badge("Navigation")
            st.caption("Show or hide tabs in the main navigation. **Accounts** is always visible.")
            tab_settings = s_obj.get("system_tabs", {})
            tab_changed  = False
            tg = st.columns(3)
            for i, (tk, tl, removable) in enumerate(TAB_DEFS):
                if not removable:
                    tg[i%3].checkbox(tl, value=True, disabled=True, key=f"systab_lock_{tk}")
                else:
                    new_val = tg[i%3].checkbox(tl, value=tab_settings.get(tk, True), key=f"systab_{tk}")
                    if new_val != tab_settings.get(tk, True):
                        tab_settings[tk] = new_val; tab_changed = True
            if tab_changed:
                s_obj["system_tabs"] = tab_settings; save_settings(); st.rerun()

    with t3:
        st.subheader("Call status options")
        for s in st.session_state.call_statuses:
            c1,c2,c3=st.columns([3,1,1]); c1.markdown(f'<span style="display:inline-flex;align-items:center;gap:8px"><span style="width:10px;height:10px;border-radius:50%;background:{s["color"]};display:inline-block"></span>{s["label"]}</span>',unsafe_allow_html=True)
            if c2.button("Edit",key=f"es_{s['id']}"): st.session_state.editing_status=s["id"]; st.rerun()
            if c3.button("Remove",key=f"ds_{s['id']}"): st.session_state.call_statuses=[x for x in st.session_state.call_statuses if x["id"]!=s["id"]]; st.rerun()
        if st.session_state.get("editing_status"):
            sid=st.session_state.editing_status; st_obj=next((s for s in st.session_state.call_statuses if s["id"]==sid),None)
            if st_obj:
                st.markdown("---")
                with st.form("edit_status_form"):
                    nl=st.text_input("Label",value=st_obj["label"]); nc=st.color_picker("Color",value=st_obj["color"])
                    sv,ca=st.columns(2)
                    if sv.form_submit_button("Save",type="primary"): st_obj["label"]=nl; st_obj["color"]=nc; del st.session_state["editing_status"]; st.rerun()
                    if ca.form_submit_button("Cancel"): del st.session_state["editing_status"]; st.rerun()
        st.markdown("---"); st.markdown("**Add status**")
        with st.form("add_status"):
            sc1,sc2=st.columns([3,1]); new_slbl=sc1.text_input("Label"); new_scol=sc2.color_picker("Color",VIOLET)
            if st.form_submit_button("Add",type="primary") and new_slbl: st.session_state.call_statuses.append({"id":"cs"+new_id(),"label":new_slbl,"color":new_scol}); st.rerun()
    with t4:
        st.subheader("Role manager"); PROTECTED={"admin","manager","rep","viewer"}
        for role in st.session_state.roles:
            with st.expander(f"**{role['label']}** ({role['id']})",expanded=False):
                c1,c2=st.columns([4,1]); c1.markdown(role_badge_html(role["id"]),unsafe_allow_html=True)
                b_e,b_d=c2.columns(2)
                if b_e.button("Edit",key=f"er_{role['id']}"): st.session_state.editing_role=role["id"]; st.rerun()
                if role["id"] not in PROTECTED and b_d.button("Del",key=f"dr_{role['id']}"): st.session_state.roles=[r for r in st.session_state.roles if r["id"]!=role["id"]]; st.rerun()
                perms = role.get("perms") or set()
                for mod_name, mod_perms in PERM_MODULES.items():
                    st.markdown(f"<small style='color:#888;font-weight:600;text-transform:uppercase;letter-spacing:.05em'>{mod_name}</small>", unsafe_allow_html=True)
                    pm_cols = st.columns(2)
                    for i, (pk, pl) in enumerate(mod_perms):
                        has = pk in perms or ("add_account" in perms and pk in ("acc_add","acc_edit","acc_edit_name","acc_edit_brand","acc_edit_f5","acc_delete"))
                        pm_cols[i%2].markdown(("✅" if has else "⬜") + " " + pl)
        if st.button("+ New role",type="primary",key="add_role_btn"): st.session_state.editing_role="__new__"; st.rerun()
        if st.session_state.get("editing_role"):
            eid=st.session_state.editing_role; er=next((r for r in st.session_state.roles if r["id"]==eid),None) if eid!="__new__" else None
            st.markdown("---"); st.subheader("Edit role" if er else "New role")
            with st.form("role_form"):
                if not er or er["id"] not in PROTECTED: r_id=st.text_input("Role ID (lowercase)",value=er["id"] if er else "")
                else: r_id=er["id"]; st.text_input("Role ID (protected)",value=r_id,disabled=True)
                r_lbl=st.text_input("Display label",value=er["label"] if er else "")
                rc1,rc2=st.columns(2); r_color=rc1.color_picker("Text color",value=er.get("color",VIOLET) if er else VIOLET); r_bg=rc2.color_picker("Badge background",value=er.get("bg",VIOLET_LIGHT) if er else VIOLET_LIGHT)
                cur_perms = er.get("perms") or set() if er else set()
                new_perms = set()
                for mod_name, mod_perms in PERM_MODULES.items():
                    st.markdown(f"**{mod_name}**")
                    mod_cols = st.columns(2)
                    for i, (pk, pl) in enumerate(mod_perms):
                        default_val = pk in cur_perms or ("add_account" in cur_perms and pk in ("acc_add","acc_edit","acc_edit_name","acc_edit_brand","acc_edit_f5","acc_delete"))
                        if mod_cols[i%2].checkbox(pl, value=default_val, key=f"rp_{eid}_{pk}"):
                            new_perms.add(pk)
                sv,ca=st.columns(2); do_save=sv.form_submit_button("Save role",type="primary"); do_cancel=ca.form_submit_button("Cancel")
            if do_save and r_id and r_lbl:
                rid2=r_id.strip().lower().replace(" ","_"); new_role={"id":rid2,"label":r_lbl,"color":r_color,"bg":r_bg,"perms":new_perms}
                if er: st.session_state.roles=[new_role if r["id"]==er["id"] else r for r in st.session_state.roles]
                elif any(r["id"]==rid2 for r in st.session_state.roles): st.error("Role ID exists.")
                else: st.session_state.roles.append(new_role)
                if "editing_role" in st.session_state: del st.session_state["editing_role"]
                st.rerun()
            if do_cancel:
                if "editing_role" in st.session_state: del st.session_state["editing_role"]
                st.rerun()
        st.markdown("---"); st.subheader("Permissions matrix")
        mat={pl:{r["label"]:("✓" if (pk in (r.get("perms") or set()) or ("add_account" in (r.get("perms") or set()) and pk in ("acc_add","acc_edit","acc_edit_name","acc_edit_brand","acc_edit_f5","acc_delete"))) else "✕") for r in st.session_state.roles} for pk,pl in ALL_PERMS}
        st.dataframe(pd.DataFrame(mat).T, use_container_width=True)
# ══════════════════════════════════════════════════════════════════════════════
# LOG CALL MODAL
# ══════════════════════════════════════════════════════════════════════════════
def render_log_modal(active):
    if not st.session_state.get("show_log_modal"): return
    acc=next((a for a in st.session_state.accounts if a["id"]==st.session_state.get("log_target")),None)
    if not acc: return
    st.markdown("---"); st.subheader(f"📞 Log interaction — {acc['brand_name']}")
    st.caption(f"{acc['account_name']} · {acc['branches']} branches · Last call: {acc['last_call_date']}")
    with st.form("log_form"):
        c1,c2=st.columns(2); names=[u["name"] for u in st.session_state.users]; def_i=next((i for i,u in enumerate(st.session_state.users) if u["id"]==active["id"]),0)
        member_name=c1.selectbox("Team member",names,index=def_i); call_date=c2.date_input("Call date",value=date.today(),max_value=date.today())
        slabels=[s["label"] for s in st.session_state.call_statuses]; status_lbl=st.selectbox("Call status",slabels if slabels else ["—"])
        ef_vals={}
        call_secs = sorted(
            [s for s in st.session_state.get("account_sections",[]) if "Calls" in s.get("affects",[])],
            key=lambda x: x.get("sort_order",99)
        )
        call_fields_sorted = sorted(st.session_state.call_extra_fields, key=lambda x: x.get("sort_order",99))
        def _render_call_field(f):
            if f["type"]=="select": ef_vals[f["id"]]=st.selectbox(f["label"],[""]+(f["options"] or []),key=f"lf_{f['id']}")
            else: ef_vals[f["id"]]=st.text_input(f["label"],key=f"lf_{f['id']}")
        # Unsectioned call fields
        for f in [x for x in call_fields_sorted if not x.get("section_id")]:
            _render_call_field(f)
        # Sectioned call fields
        for sec in call_secs:
            sec_fields = [f for f in call_fields_sorted if f.get("section_id")==sec["id"]]
            if not sec_fields: continue
            st.markdown(f"**{sec['label']}**")
            for f in sec_fields: _render_call_field(f)
        notes_text=st.text_area("Notes",height=80)
        s1,s2=st.columns(2); do_save=s1.form_submit_button("Save log",type="primary"); do_cancel=s2.form_submit_button("Cancel")
    if do_save:
        member=next((u for u in st.session_state.users if u["name"]==member_name),None)
        status=next((s for s in st.session_state.call_statuses if s["label"]==status_lbl),None)
        new_note={"date":str(call_date),"text":notes_text,"member_id":member["id"] if member else "","status_id":status["id"] if status else "","extra_fields":ef_vals}
        for a in st.session_state.accounts:
            if a["id"]==acc["id"]:
                a["notes"].insert(0,new_note); a["last_call_date"]=str(call_date)
                sb_upsert_account(a); sb_upsert_call_log(a["id"], new_note); break
        st.session_state.show_log_modal=False; st.session_state.log_target=None
        st.success(f"Call logged for {acc['brand_name']}"); st.rerun()
    if do_cancel: st.session_state.show_log_modal=False; st.session_state.log_target=None; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ADD ACCOUNT
# ══════════════════════════════════════════════════════════════════════════════
def render_add_account(active):
    if not st.session_state.get("show_add_account"): return
    st.markdown("---"); st.subheader("Add new account")
    with st.form("add_acc_form"):
        c1,c2=st.columns(2); acc_name=c1.text_input("Account name",placeholder="Legal entity"); brand=c2.text_input("Brand name",placeholder="Public name")
        c3,c4=st.columns(2); branches=c3.number_input("# of branches",min_value=1,value=10); sector=c4.selectbox("Sector",SECTORS)
        c5,c6=st.columns(2); contact=c5.text_input("Contact person"); f5_num=c6.text_input("F5 Number",placeholder="6-digit number",max_chars=6)
        user_names=["— None —"]+[u["name"] for u in st.session_state.users]
        owner_sel=st.selectbox("Account Owner",user_names,key="new_acc_owner")
        logo_file=st.file_uploader("Brand logo (PNG/JPG, optional)",type=["png","jpg","jpeg"],key="new_acc_logo")
        ef_vals={}
        for f in st.session_state.account_extra_fields:
            if f["type"]=="select": ef_vals[f["id"]]=st.selectbox(f["label"],[""]+(f["options"] or []))
            else: ef_vals[f["id"]]=st.text_input(f["label"])
        s1,s2=st.columns(2); do_save=s1.form_submit_button("Add account",type="primary"); do_cancel=s2.form_submit_button("Cancel")
    if do_save and acc_name and brand:
        if f5_num and (not f5_num.isdigit() or len(f5_num) != 6):
            st.error("F5 Number must be exactly 6 digits.")
        else:
            ef_vals["f5_number"] = f5_num.strip()
            owner_id = next((u["id"] for u in st.session_state.users if u["name"]==owner_sel), "") if owner_sel != "— None —" else ""
            logo_b64=img_to_b64(logo_file) if logo_file else None
            new_acc={"id":f"ACC-{str(len(st.session_state.accounts)+1).zfill(4)}","account_name":acc_name,"brand_name":brand,"branches":int(branches),"sector":sector,"last_call_date":rnd_date(1),"contact_person":contact,"account_owner_id":owner_id,"notes":[],"extra_fields":ef_vals,"logo_b64":logo_b64,"is_deleted":False}
            st.session_state.accounts.append(new_acc)
            sb_upsert_account(new_acc)
            st.session_state.show_add_account=False; st.success(f"Account '{brand}' added."); st.rerun()
    if do_cancel: st.session_state.show_add_account=False; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# DIALOGS
# ══════════════════════════════════════════════════════════════════════════════
@st.dialog("Import Accounts", width="large")
def _import_dialog():
    cols = (["Account ID","Account Name","Brand Name","# of Branches","Sector",
             "Contact Person","Account Owner","F5 Number"] +
            [f["label"] for f in st.session_state.account_extra_fields])
    tmpl = pd.DataFrame(columns=cols)
    dl1, dl2 = st.columns(2)
    dl1.download_button("⬇ CSV template",   tmpl.to_csv(index=False).encode(),       "accounts_template.csv",  "text/csv",                                                           key="dlg_tmpl_csv")
    dl2.download_button("⬇ Excel template", df_to_excel_bytes(tmpl),                 "accounts_template.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dlg_tmpl_xl")
    mode = st.radio("Import mode", ["Add new rows","Update existing by Account ID","Add new + update existing"], horizontal=True, key="dlg_import_mode")
    uploaded = st.file_uploader("Upload CSV, XLSX or XLS", type=["csv","xlsx","xls"], key="dlg_acc_upload")
    if uploaded:
        try:
            df = read_upload(uploaded); df.columns = [c.strip() for c in df.columns]
            st.caption(f"{len(df)} rows · {uploaded.name}")
            st.dataframe(df.head(5), use_container_width=True)
            if st.button("Confirm import", type="primary", key="dlg_confirm_import"):
                added = updated = skipped = 0; bulk_new = []; bulk_update = []
                prog = st.progress(0, text="Preparing…"); total = max(len(df), 1)
                for i, (_, row) in enumerate(df.iterrows()):
                    prog.progress((i + 1) / total, text=f"Row {i+1} of {total}…")
                    acc_name  = str(row.get("Account Name","")).strip()
                    brand_name = str(row.get("Brand Name","")).strip()
                    if not acc_name or not brand_name: skipped += 1; continue
                    br_raw = row.get("# of Branches", 0)
                    try: branches = int(float(str(br_raw))) if str(br_raw).strip() not in ("","nan") else 0
                    except: branches = 0
                    acc_id_raw = str(row.get("Account ID","")).strip()
                    existing   = next((a for a in st.session_state.accounts if a["id"]==acc_id_raw), None) if acc_id_raw and acc_id_raw.lower()!="nan" else None
                    # Resolve account owner by name
                    owner_name = str(row.get("Account Owner","")).strip()
                    owner_id   = next((u["id"] for u in st.session_state.users if u["name"].lower()==owner_name.lower()), "")
                    new_acc = {
                        "id": existing["id"] if existing else (acc_id_raw if acc_id_raw and acc_id_raw.lower()!="nan" else f"ACC-{str(len(st.session_state.accounts)+added+1).zfill(4)}"),
                        "account_name": acc_name, "brand_name": brand_name, "branches": branches,
                        "sector":         str(row.get("Sector","Retail")).strip() or "Retail",
                        "contact_person": str(row.get("Contact Person","")).strip(),
                        "account_owner_id": owner_id,
                        "last_call_date": str(row.get("Last Call Date", rnd_date(1))).strip() or rnd_date(1),
                        "notes": existing["notes"] if existing else [],
                        "extra_fields": {**{f["id"]: str(row.get(f["label"],"")).strip() for f in st.session_state.account_extra_fields}, "f5_number": str(row.get("F5 Number","")).strip()},
                        "logo_b64": existing["logo_b64"] if existing else None, "is_deleted": False,
                    }
                    if existing and "Update" in mode:
                        idx = st.session_state.accounts.index(existing); st.session_state.accounts[idx] = new_acc; bulk_update.append(new_acc); updated += 1
                    elif not existing:
                        st.session_state.accounts.append(new_acc); bulk_new.append(new_acc); added += 1
                    else:
                        skipped += 1
                prog.empty()
                all_to_write = bulk_new + bulk_update
                if all_to_write: sb_upsert_accounts_bulk(all_to_write)
                st.success(f"Done — {added} added · {updated} updated · {skipped} skipped")
                st.rerun()
        except Exception as ex:
            st.error(f"Import error: {ex}")


@st.dialog("Edit Custom Field")
def _edit_field_dialog():
    field_id = st.session_state.get("dlg_field_id")
    entity   = st.session_state.get("dlg_field_entity")
    FTYPES   = ["text","number","date","select"]
    target   = (st.session_state.account_extra_fields if entity=="Account" else
                st.session_state.user_extra_fields    if entity=="User"    else
                st.session_state.call_extra_fields)
    f = next((x for x in target if x["id"] == field_id), None)
    if not f: st.error("Field not found."); return
    st.caption(f"Applies to **{entity}** · id: `{field_id}`")
    with st.form("dlg_edit_field_form"):
        ef1, ef2 = st.columns(2)
        new_lbl      = ef1.text_input("Label",  value=f["label"])
        type_idx     = FTYPES.index(f.get("type","text")) if f.get("type","text") in FTYPES else 0
        new_type     = ef2.selectbox("Type",    FTYPES, index=type_idx)
        new_opts_str = st.text_input(
            "Options — comma-separated (for 'select' type only)",
            value=", ".join(f.get("options") or []),
            placeholder="e.g. High, Medium, Low"
        )
        es1, es2 = st.columns(2)
        do_save   = es1.form_submit_button("Save changes", type="primary")
        do_cancel = es2.form_submit_button("Cancel")
    if do_save and new_lbl.strip():
        new_opts = [o.strip() for o in new_opts_str.split(",") if o.strip()] if new_type=="select" else []
        for i, fld in enumerate(target):
            if fld["id"] == field_id:
                target[i] = {**fld, "label": new_lbl.strip(), "type": new_type, "options": new_opts}
                break
        if entity == "Account": save_layout()
        st.session_state.pop("dlg_field_id", None); st.session_state.pop("dlg_field_entity", None)
        st.rerun()
    if do_cancel:
        st.session_state.pop("dlg_field_id", None); st.session_state.pop("dlg_field_entity", None)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# IMPORT CSV  (legacy inline — kept for backward compat, unused when dialogs on)
# ══════════════════════════════════════════════════════════════════════════════
def render_import():
    if not st.session_state.get("show_import"): return
    st.markdown("---"); st.subheader("Import accounts — CSV or Excel")
    cols=["Account ID","Account Name","Brand Name","# of Branches","Sector","Contact Person","F5 Number"]+[f["label"] for f in st.session_state.account_extra_fields]
    tmpl=pd.DataFrame(columns=cols)
    dl1,dl2=st.columns(2)
    dl1.download_button("⬇ CSV template",  tmpl.to_csv(index=False).encode(),       "accounts_template.csv",  "text/csv",                                                                    key="dl_acc_tmpl_csv")
    dl2.download_button("⬇ Excel template", df_to_excel_bytes(tmpl),                 "accounts_template.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",          key="dl_acc_tmpl_xl")
    mode=st.radio("Import mode",["Add new rows","Update existing by Account ID","Add new + update existing"],horizontal=True,key="import_mode")
    uploaded=st.file_uploader("Upload file (CSV, XLSX or XLS)", type=["csv","xlsx","xls"], key="acc_csv_upload")
    if uploaded is not None:
        try:
            df=read_upload(uploaded); df.columns=[c.strip() for c in df.columns]
            st.caption(f"{len(df)} rows · {uploaded.name}")
            st.dataframe(df.head(6), use_container_width=True)
            if st.button("Confirm import", type="primary", key="confirm_import"):
                added=updated=skipped=0; bulk_new=[]; bulk_update=[]
                for _,row in df.iterrows():
                    acc_name=str(row.get("Account Name","")).strip(); brand_name=str(row.get("Brand Name","")).strip()
                    if not acc_name or not brand_name: skipped+=1; continue
                    br_raw=row.get("# of Branches",0)
                    try: branches=int(float(str(br_raw))) if str(br_raw).strip() not in ("","nan") else 0
                    except: branches=0
                    acc_id_raw=str(row.get("Account ID","")).strip()
                    existing=next((a for a in st.session_state.accounts if a["id"]==acc_id_raw),None) if acc_id_raw and acc_id_raw.lower()!="nan" else None
                    new_acc={
                        "id": existing["id"] if existing else (acc_id_raw if acc_id_raw and acc_id_raw.lower()!="nan" else f"ACC-{str(len(st.session_state.accounts)+added+1).zfill(4)}"),
                        "account_name":acc_name,"brand_name":brand_name,"branches":branches,
                        "sector":str(row.get("Sector","Retail")).strip() or "Retail",
                        "contact_person":str(row.get("Contact Person","")).strip(),
                        "last_call_date":str(row.get("Last Call Date",rnd_date(1))).strip() or rnd_date(1),
                        "notes":existing["notes"] if existing else [],
                        "extra_fields":{**{f["id"]:str(row.get(f["label"],"")).strip() for f in st.session_state.account_extra_fields},"f5_number":str(row.get("F5 Number","")).strip()},
                        "logo_b64":existing["logo_b64"] if existing else None,"is_deleted":False,
                    }
                    if existing and "Update" in mode:
                        idx=st.session_state.accounts.index(existing); st.session_state.accounts[idx]=new_acc; bulk_update.append(new_acc); updated+=1
                    elif not existing:
                        st.session_state.accounts.append(new_acc); bulk_new.append(new_acc); added+=1
                    else: skipped+=1
                all_to_write = bulk_new + bulk_update
                if all_to_write: sb_upsert_accounts_bulk(all_to_write)
                st.session_state.show_import=False
                st.success(f"Import complete — {added} added · {updated} updated · {skipped} skipped"); st.rerun()
        except Exception as ex: st.error(f"Import error: {ex}")
    if st.button("Close",key="close_import"): st.session_state.show_import=False; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    if not sb_available():
        st.error("## ⚠️ Supabase not connected\n\nSet `SUPABASE_URL` and `SUPABASE_KEY` in `.streamlit/secrets.toml` and restart the app.")
        st.stop()

    if "logged_in_user_id" not in st.session_state:
        render_login_page()
        st.stop()

    init_state()
    apply_theme()
    active  = get_active_user()
    is_rep  = active["role"] == "rep"
    render_sidebar()

    # View-as banner
    if st.session_state.get("view_as_user_id"):
        real = get_logged_in_user()
        pc   = st.session_state.settings.get("primary_color", VIOLET)
        st.markdown(f'<div style="background:#fff8e1;border:1px solid #ffc107;border-radius:8px;padding:8px 14px;margin-bottom:8px;font-size:13px">👁 <strong>Viewing as {active["name"]}</strong> — permissions and filters reflect their role. <em>Switch back via the sidebar.</em></div>', unsafe_allow_html=True)

    s  = st.session_state.settings
    tc = st.columns([4,1,1])
    tc[0].title(s.get("system_name","Client Interaction Management"))
    with tc[1]:
        if has_perm(active["role"],"import") and st.button(get_btn("import_csv"),use_container_width=True,key="top_import"):
            _import_dialog()
    with tc[2]:
        if has_perm(active["role"],"acc_add") and st.button(get_btn("add_account"),type="primary",use_container_width=True,key="top_add"):
            st.session_state.show_add_account=True; st.session_state.show_log_modal=False

    render_add_account(active)
    render_log_modal(active)

    urgency_count = sum(1 for a in st.session_state.accounts if days_since(a["last_call_date"])>14)
    tab_settings  = st.session_state.settings.get("system_tabs", {})

    TAB_RENDERERS = {
        "dashboard":    lambda: render_dashboard(active, is_rep),
        "accounts":     lambda: render_accounts(active, is_rep),
        "urgency":      lambda: render_urgency(active),
        "activity_log": lambda: render_log(active, is_rep),
        "users":        lambda: render_users(active),
        "deleted":      lambda: render_deleted_accounts(active),
    }
    TAB_DISPLAY = {
        "dashboard":    "Dashboard",
        "accounts":     "Accounts",
        "urgency":      f"Urgency ({urgency_count})",
        "activity_log": "Activity Log",
        "users":        "Users",
        "deleted":      "Deleted Accounts",
    }

    visible = [(tk, TAB_DISPLAY[tk]) for tk, _, removable in TAB_DEFS
               if not removable or tab_settings.get(tk, True)]
    if has_perm(active["role"], "manage_schema"):
        visible.append(("schema", "System Settings"))

    tabs = st.tabs([lbl for _, lbl in visible])
    for i, (tk, _) in enumerate(visible):
        with tabs[i]:
            if tk == "schema": render_schema()
            else: TAB_RENDERERS[tk]()

if __name__ == "__main__":
    main()
