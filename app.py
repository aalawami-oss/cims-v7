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
import random, uuid, base64, json
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
  .badge-ok{background:#EAF3DE;color:#27500A;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:500}
  .badge-warn{background:#FAEEDA;color:#633806;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:500}
  .badge-danger{background:#FCEBEB;color:#791F1F;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:500}
  .badge-info{background:#EDE9FC;color:#4A24A8;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:500}
  .rep-banner{background:#EDE9FC;color:#4A24A8;padding:10px 14px;border-radius:8px;margin-bottom:1rem;font-size:13px}
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
VIOLET_TEXT  = "#4A24A8"

ALL_PERMS = [
    ("view",          "View accounts"),
    ("log",           "Log calls"),
    ("add_account",   "Add / Edit / Delete accounts"),
    ("import",        "Import CSV"),
    ("manage_users",  "Manage users"),
    ("export",        "Export data"),
    ("manage_schema", "Manage fields, roles & settings"),
]
TEAM_COLORS = [
    {"color":"#6C3FC5","bg":"#EDE9FC"},{"color":"#0F6E56","bg":"#E1F5EE"},
    {"color":"#993C1D","bg":"#FAECE7"},{"color":"#993556","bg":"#FBEAF0"},
    {"color":"#854F0B","bg":"#FAEEDA"},{"color":"#185FA5","bg":"#E6F1FB"},
    {"color":"#3B6D11","bg":"#EAF3DE"},{"color":"#A32D2D","bg":"#FCEBEB"},
]
SECTORS  = ["Retail","F&B","Finance","Healthcare","Logistics","Tech","Education","Real Estate"]
CHART_TYPES = ["Bar","Stacked Bar","Line","Area","Horizontal Bar","Pie","Donut","Scatter"]
CORE_COLUMNS = ["ID","Account Name","Brand Name","Branches","Sector","Last Call","Contact"]
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
    url = st.secrets.get("SUPABASE_URL","")
    key = st.secrets.get("SUPABASE_KEY","")
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None

def sb_available():
    return get_supabase() is not None

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
        if isinstance(p.get("extra_fields"), dict): p["extra_fields"] = json.dumps(p["extra_fields"])
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
def new_id(): return str(uuid.uuid4())[:8]
def days_since(d):
    if not d: return 999
    try:
        if isinstance(d,str): d=datetime.strptime(d,"%Y-%m-%d").date()
        return (date.today()-d).days
    except: return 999
def rnd_date(n): return str(date.today()-timedelta(days=random.randint(0,n)))
def initials(name): return "".join(p[0] for p in name.split()[:2]).upper()

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
    return perm in (r.get("perms") or set()) if r else False

def get_active_user():
    uid = st.session_state.get("active_user_id","u1")
    return next((u for u in st.session_state.users if u["id"]==uid), st.session_state.users[0])

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
        "system_name": "Client Interaction Management",
        "system_logo_b64": None,
    }
    st.session_state.roles = [
        {"id":"admin",  "label":"Admin",   "color":"#6C3FC5","bg":"#EDE9FC","perms":{"view","log","add_account","import","manage_users","export","manage_schema"}},
        {"id":"manager","label":"Manager", "color":"#085041","bg":"#E1F5EE","perms":{"view","log","add_account","import","export"}},
        {"id":"rep",    "label":"Rep",     "color":"#633806","bg":"#FAEEDA","perms":{"view","log"}},
        {"id":"viewer", "label":"Viewer",  "color":"#444441","bg":"#F1EFE8","perms":{"view"}},
    ]
    st.session_state.call_statuses = [
        {"id":"cs1","label":"Completed",         "color":"#1D9E75"},
        {"id":"cs2","label":"No Answer",          "color":"#BA7517"},
        {"id":"cs3","label":"Follow-up Required", "color":VIOLET},
        {"id":"cs4","label":"Meeting Scheduled",  "color":"#6C3FC5"},
        {"id":"cs5","label":"Not Interested",     "color":"#A32D2D"},
        {"id":"cs6","label":"Voicemail Left",     "color":"#5F5E5A"},
    ]
    st.session_state.account_extra_fields = [
        {"id":"ef1","label":"Region",  "type":"text",  "options":[]},
        {"id":"ef2","label":"Priority","type":"select","options":["High","Medium","Low"]},
    ]
    st.session_state.user_extra_fields   = [{"id":"uf1","label":"Phone","type":"text","options":[]},{"id":"uf2","label":"Territory","type":"text","options":[]}]
    st.session_state.call_extra_fields   = [{"id":"cf1","label":"Deal Size","type":"text","options":[]},{"id":"cf2","label":"Next Step","type":"text","options":[]}]
    st.session_state.visible_columns     = list(CORE_COLUMNS)
    st.session_state.selected_accounts   = set()

    # Load from Supabase if available, else mock
    if sb_available():
        users    = sb_fetch_users()
        accounts = sb_fetch_accounts()
        if not users:    users    = _mock_users()
        if not accounts: accounts = _mock_accounts()
    else:
        users    = _mock_users()
        accounts = _mock_accounts()

    st.session_state.users    = users
    st.session_state.accounts = accounts
    st.session_state.active_user_id = users[0]["id"] if users else "u1"
    st.session_state.initialized = True

def _mock_users():
    return [
        {"id":"u1","name":"Alawi Alawami",    "role":"admin",  "email":"a.alawami@foodics.com", **TEAM_COLORS[0],"extra_fields":{}},
        {"id":"u2","name":"Sara Al-Zahrani",  "role":"manager","email":"sara@corp.com",          **TEAM_COLORS[1],"extra_fields":{}},
        {"id":"u3","name":"Mohammed Al-Ghamdi","role":"rep",   "email":"mohammed@corp.com",       **TEAM_COLORS[2],"extra_fields":{}},
        {"id":"u4","name":"Fatima Al-Otaibi", "role":"rep",    "email":"fatima@corp.com",         **TEAM_COLORS[3],"extra_fields":{}},
        {"id":"u5","name":"Khalid Al-Qahtani","role":"viewer", "email":"khalid@corp.com",         **TEAM_COLORS[4],"extra_fields":{}},
    ]

def _mock_accounts():
    uids=["u1","u2","u3","u4","u5"]; sids=["cs1","cs2","cs3","cs4","cs5","cs6"]
    pool=[]; today=date.today()
    for i in range(89,-1,-1):
        d=today-timedelta(days=i)
        for _ in range(random.randint(0,3)):
            pool.append({"date":str(d),"text":"Follow-up call.","member_id":random.choice(uids),"status_id":random.choice(sids),"extra_fields":{"cf1":"","cf2":""}})
    accounts=[]
    for i,(acc_name,brand) in enumerate(BRANDS):
        my_notes=[n for j,n in enumerate(pool) if j%len(BRANDS)==i][:3]
        last=my_notes[0]["date"] if my_notes else rnd_date(45)
        accounts.append({
            "id":f"ACC-{str(i+1).zfill(4)}","account_name":acc_name,"brand_name":brand,
            "branches":random.randint(3,120),"sector":SECTORS[i%len(SECTORS)],"last_call_date":last,
            "contact_person":f"{['Ahmed','Sara','Mohammed','Fatima','Khalid'][i%5]} {['Al-Harbi','Al-Zahrani','Al-Ghamdi','Al-Otaibi','Al-Qahtani'][i%5]}",
            "notes":my_notes,"extra_fields":{"ef1":"","ef2":"Medium"},"logo_b64":None,"is_deleted":False,
        })
    return accounts

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    active = get_active_user()
    s = st.session_state.settings
    if s.get("system_logo_b64"):
        st.sidebar.markdown(b64_img_tag(s["system_logo_b64"],"sys-logo","Logo"), unsafe_allow_html=True)
        st.sidebar.markdown("")
    else:
        st.sidebar.markdown(f"### {s['system_name']}")
    if sb_available():
        st.sidebar.success("🟢 Supabase connected", icon=None)
    else:
        st.sidebar.warning("🟡 Running on mock data — add Supabase credentials in secrets.toml")
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Switch user**")
    names = [u["name"] for u in st.session_state.users]
    idx   = next((i for i,u in enumerate(st.session_state.users) if u["id"]==active["id"]),0)
    sel   = st.sidebar.selectbox("User", names, index=idx, label_visibility="collapsed")
    sel_u = next(u for u in st.session_state.users if u["name"]==sel)
    if sel_u["id"] != st.session_state.active_user_id:
        st.session_state.active_user_id = sel_u["id"]; st.rerun()
    st.sidebar.markdown(role_badge_html(active["role"])+" &nbsp; **"+active["name"]+"**", unsafe_allow_html=True)
    st.sidebar.markdown(f'<small style="color:#888">{active["email"]}</small>', unsafe_allow_html=True)
    st.sidebar.markdown("---")
    total   = len(st.session_state.accounts)
    overdue = sum(1 for a in st.session_state.accounts if days_since(a["last_call_date"])>14)
    st.sidebar.metric("Accounts", total)
    st.sidebar.metric("Overdue >14d", overdue)
    st.sidebar.metric("Team", len(st.session_state.users))

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
    is_admin = has_perm(active["role"], "add_account")
    st.subheader("My accounts" if is_rep else "All accounts")

    # ── Column visibility ──────────────────────────────────────────────────────
    if is_admin:
        with st.expander("⚙️ Column settings", expanded=False):
            all_cols = list(CORE_COLUMNS)+[f["label"] for f in st.session_state.account_extra_fields]
            current  = st.session_state.get("visible_columns", list(CORE_COLUMNS))
            selected = []
            cols_ui  = st.columns(4)
            for i,col in enumerate(all_cols):
                if cols_ui[i%4].checkbox(col, value=col in current, key=f"col_vis_{col}"):
                    selected.append(col)
            if selected != current:
                st.session_state.visible_columns = selected; st.rerun()

    # ── Filters ────────────────────────────────────────────────────────────────
    with st.expander("🔍 Filters", expanded=False):
        fc1,fc2,fc3,fc4,fc5,fc6 = st.columns(6)
        f_search  = fc1.text_input("Search", placeholder="Name / brand / ID", key="f_search")
        f_sector  = fc2.multiselect("Sector", SECTORS, key="f_sector")
        f_urgency = fc3.selectbox("Urgency", ["All","Overdue >14d","Critical >30d","Recent ≤14d"], key="f_urgency")

        all_contacts = sorted({a["contact_person"] for a in st.session_state.accounts if a.get("contact_person")})
        f_contact = fc4.multiselect("Contact person", all_contacts, key="f_contact")

        all_assignees = [u["name"] for u in st.session_state.users]
        f_assignee = fc5.multiselect("Last called by", all_assignees, key="f_assignee")

        branch_vals = [a["branches"] for a in st.session_state.accounts if a.get("branches")]
        br_min = int(min(branch_vals)) if branch_vals else 0
        br_max = int(max(branch_vals)) if branch_vals else 1000
        f_branches = fc6.slider("Branches", br_min, max(br_max,br_min+1), (br_min, max(br_max,br_min+1)), key="f_branches")

        # extra filter: Priority (if it exists)
        priority_field = next((f for f in st.session_state.account_extra_fields if f["label"]=="Priority"), None)
        if priority_field and priority_field.get("options"):
            f_priority = st.multiselect("Priority", priority_field["options"], key="f_priority")
        else:
            f_priority = []

        if st.button("Clear filters", key="clear_filters"):
            for k in ["f_search","f_sector","f_urgency","f_contact","f_assignee","f_priority"]:
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

    # priority
    if f_priority:
        ef_id = priority_field["id"]
        accs = [a for a in accs if a.get("extra_fields",{}).get(ef_id,"") in f_priority]

    accs = sorted(accs, key=lambda x: str(x.get(sort_by,"")), reverse=not sort_asc)
    bc1.caption(f"{len(accs)} accounts")

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
                g = st.columns(4); ci = 0
                def show(label, val):
                    nonlocal ci
                    if label in vis: g[ci%4].markdown(f"**{label}:** {val}"); ci+=1
                show("ID", f"`{acc['id']}`")
                show("Account Name", acc["account_name"])
                show("Brand Name",   acc["brand_name"])
                show("Branches",     acc["branches"])
                show("Sector",       acc["sector"])
                show("Contact",      acc.get("contact_person","—"))
                if "Last Call" in vis:
                    g[ci%4].markdown(f"**Last call:** {acc['last_call_date']} &nbsp;"+urgency_badge(d), unsafe_allow_html=True); ci+=1
                for f in st.session_state.account_extra_fields:
                    val = acc.get("extra_fields",{}).get(f["id"],"")
                    if val: show(f["label"], val)
            st.markdown(f"**Last logged by:** {last_by}")

            if acc.get("notes"):
                st.markdown("**Recent interactions:**")
                for note in acc["notes"][:3]:
                    u = get_user(note.get("member_id","")); s = get_status(note.get("status_id",""))
                    uname=u["name"].split()[0] if u else "—"; slabel=s["label"] if s else ""
                    st.markdown(f"&nbsp;&nbsp;`{note['date']}` **{uname}** {slabel}"+(f" — {note['text']}" if note.get("text") else ""))

            btn_c = st.columns(5)
            if has_perm(active["role"],"log"):
                if btn_c[0].button("📞 Log call", key=f"log_{acc['id']}"):
                    st.session_state.log_target=acc["id"]; st.session_state.show_log_modal=True; st.rerun()
            if is_admin:
                if btn_c[1].button("✏️ Edit", key=f"edit_{acc['id']}"):
                    st.session_state.editing_account=acc["id"]; st.rerun()
                if btn_c[2].button("🗑️ Delete", key=f"del_{acc['id']}"):
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
    st.markdown("---"); st.subheader(f"Edit — {acc['brand_name']}")
    with st.form(f"edit_acc_{acc_id}"):
        c1,c2 = st.columns(2)
        new_name    = c1.text_input("Account name", value=acc["account_name"])
        new_brand   = c2.text_input("Brand name",   value=acc["brand_name"])
        c3,c4 = st.columns(2)
        new_branches = c3.number_input("# of branches", min_value=1, value=int(acc["branches"]))
        sect_idx = SECTORS.index(acc["sector"]) if acc["sector"] in SECTORS else 0
        new_sector   = c4.selectbox("Sector", SECTORS, index=sect_idx)
        new_contact  = st.text_input("Contact person", value=acc.get("contact_person",""))
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
        new_b64 = img_to_b64(new_logo_f) if new_logo_f else acc.get("logo_b64")
        for i,a in enumerate(st.session_state.accounts):
            if a["id"]==acc_id:
                st.session_state.accounts[i]={**a,"account_name":new_name,"brand_name":new_brand,"branches":int(new_branches),"sector":new_sector,"contact_person":new_contact,"extra_fields":ef_vals,"logo_b64":new_b64}
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
        if has_perm(active["role"],"add_account"):
            if c4.button("↩ Restore", key=f"restore_{d.get('id')}"):
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
        st.download_button("Export as CSV", df.to_csv(index=False).encode(), "activity_log.csv","text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════════════════════
def render_users(active):
    is_admin = has_perm(active["role"],"manage_users")
    st.subheader("User management" if is_admin else "Team members")
    if is_admin:
        with st.expander("📥 Bulk import users via CSV", expanded=False):
            role_ids=[r["id"] for r in st.session_state.roles]
            tmpl=pd.DataFrame(columns=["Name","Email","Role ("+"/".join(role_ids)+")"])
            st.download_button("Download template", tmpl.to_csv(index=False).encode(), "users_template.csv","text/csv",key="ul_tmpl")
            up=st.file_uploader("Upload CSV", type=["csv"], key="bulk_user_up")
            if up:
                try:
                    df=pd.read_csv(up); df.columns=[c.strip() for c in df.columns]
                    st.caption(f"{len(df)} rows"); st.dataframe(df.head(), use_container_width=True)
                    mode=st.radio("Mode",["Add new","Update existing by email"],horizontal=True,key="bulk_u_mode")
                    if st.button("Import users", type="primary", key="do_bulk_users"):
                        added=updated=skipped=0
                        for _,row in df.iterrows():
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
                        st.success(f"Done: {added} added · {updated} updated · {skipped} skipped"); st.rerun()
                except Exception as ex: st.error(f"CSV error: {ex}")
    for u in st.session_state.users:
        c1,c2,c3=st.columns([3,1,2]) if is_admin else st.columns([4,1,1])
        c1.markdown(f"**{u['name']}** &nbsp;<small style='color:#888'>{u['email']}</small>", unsafe_allow_html=True)
        c2.markdown(role_badge_html(u["role"]), unsafe_allow_html=True)
        if is_admin:
            b1,b2=c3.columns(2)
            if b1.button("Edit",key=f"eu_{u['id']}"): st.session_state.editing_user=u["id"]; st.rerun()
            if u["id"]!=active["id"] and b2.button("Delete",key=f"du_{u['id']}"):
                st.session_state.users=[x for x in st.session_state.users if x["id"]!=u["id"]]
                sb_delete_user(u["id"]); st.rerun()
        st.divider()
    if is_admin and st.button("+ Add user", type="primary", key="add_user_btn"):
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
            sv,ca=st.columns(2); do_save=sv.form_submit_button("Save",type="primary"); do_cancel=ca.form_submit_button("Cancel")
        if do_save and n_:
            c=TEAM_COLORS[len(st.session_state.users)%len(TEAM_COLORS)]
            new_u={"id":existing["id"] if existing else "u"+new_id(),"name":n_,"email":e_,"role":r_,"extra_fields":ef_,**({"color":existing["color"],"bg":existing["bg"]} if existing else {"color":c["color"],"bg":c["bg"]})}
            if existing: st.session_state.users=[new_u if u["id"]==existing["id"] else u for u in st.session_state.users]
            else: st.session_state.users.append(new_u)
            sb_upsert_user(new_u); del st.session_state["editing_user"]; st.rerun()
        if do_cancel: del st.session_state["editing_user"]; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# FIELD BUILDER + ROLES + SETTINGS
# ══════════════════════════════════════════════════════════════════════════════
def render_schema():
    t1,t2,t3,t4=st.tabs(["Custom Fields","Call Statuses","Role Manager","System Settings"])
    with t1:
        st.subheader("Custom fields")
        all_fields=([(f,"Account") for f in st.session_state.account_extra_fields]+[(f,"User") for f in st.session_state.user_extra_fields]+[(f,"Call") for f in st.session_state.call_extra_fields])
        if not all_fields: st.caption("No custom fields yet.")
        for f,ent in all_fields:
            c1,c2,c3,c4,c5=st.columns([2,1,1,2,1]); c1.markdown(f"**{f['label']}**"); c2.markdown(f"`{f['type']}`"); c3.markdown(f'<span class="badge-info">{ent}</span>',unsafe_allow_html=True); c4.markdown(", ".join((f.get("options") or [])[:4]) or "—")
            if c5.button("Remove",key=f"df_{f['id']}"):
                if ent=="Account": st.session_state.account_extra_fields=[x for x in st.session_state.account_extra_fields if x["id"]!=f["id"]]
                elif ent=="User": st.session_state.user_extra_fields=[x for x in st.session_state.user_extra_fields if x["id"]!=f["id"]]
                else: st.session_state.call_extra_fields=[x for x in st.session_state.call_extra_fields if x["id"]!=f["id"]]
                st.rerun()
        st.markdown("---"); st.markdown("**Add field**")
        with st.form("add_field"):
            fc1,fc2,fc3=st.columns(3); lbl=fc1.text_input("Label"); ftype=fc2.selectbox("Type",["text","number","date","select"]); fent=fc3.selectbox("Applies to",["Account","User","Call"])
            opts_str=""
            if ftype=="select": opts_str=st.text_input("Options (comma-separated)")
            if st.form_submit_button("Add field",type="primary") and lbl:
                nf={"id":"f"+new_id(),"label":lbl,"type":ftype,"options":[o.strip() for o in opts_str.split(",") if o.strip()]}
                if fent=="Account": st.session_state.account_extra_fields.append(nf)
                elif fent=="User": st.session_state.user_extra_fields.append(nf)
                else: st.session_state.call_extra_fields.append(nf)
                st.rerun()
    with t2:
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
    with t3:
        st.subheader("Role manager"); PROTECTED={"admin","manager","rep","viewer"}
        for role in st.session_state.roles:
            with st.expander(f"**{role['label']}** ({role['id']})",expanded=False):
                c1,c2=st.columns([4,1]); c1.markdown(role_badge_html(role["id"]),unsafe_allow_html=True)
                b_e,b_d=c2.columns(2)
                if b_e.button("Edit",key=f"er_{role['id']}"): st.session_state.editing_role=role["id"]; st.rerun()
                if role["id"] not in PROTECTED and b_d.button("Del",key=f"dr_{role['id']}"): st.session_state.roles=[r for r in st.session_state.roles if r["id"]!=role["id"]]; st.rerun()
                perms=role.get("perms") or set(); pc=st.columns(2)
                for i,(pk,pl) in enumerate(ALL_PERMS): pc[i%2].markdown(("✅" if pk in perms else "⬜")+" "+pl)
        if st.button("+ New role",type="primary",key="add_role_btn"): st.session_state.editing_role="__new__"; st.rerun()
        if st.session_state.get("editing_role"):
            eid=st.session_state.editing_role; er=next((r for r in st.session_state.roles if r["id"]==eid),None) if eid!="__new__" else None
            st.markdown("---"); st.subheader("Edit role" if er else "New role")
            with st.form("role_form"):
                if not er or er["id"] not in PROTECTED: r_id=st.text_input("Role ID (lowercase)",value=er["id"] if er else "")
                else: r_id=er["id"]; st.text_input("Role ID (protected)",value=r_id,disabled=True)
                r_lbl=st.text_input("Display label",value=er["label"] if er else "")
                rc1,rc2=st.columns(2); r_color=rc1.color_picker("Text color",value=er.get("color",VIOLET) if er else VIOLET); r_bg=rc2.color_picker("Badge background",value=er.get("bg",VIOLET_LIGHT) if er else VIOLET_LIGHT)
                st.markdown("**Permissions:**"); new_perms=set(); cur_perms=er.get("perms") or set() if er else set(); pc2=st.columns(2)
                for i,(pk,pl) in enumerate(ALL_PERMS):
                    if pc2[i%2].checkbox(pl,value=pk in cur_perms,key=f"rp_{eid}_{pk}"): new_perms.add(pk)
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
        mat={pl:{r["label"]:("✓" if pk in (r.get("perms") or set()) else "✕") for r in st.session_state.roles} for pk,pl in ALL_PERMS}
        st.dataframe(pd.DataFrame(mat).T, use_container_width=True)
    with t4:
        st.subheader("System settings"); s=st.session_state.settings
        with st.form("sys_settings"):
            new_name=st.text_input("System name",value=s.get("system_name","CIMS"))
            logo_file=st.file_uploader("System logo (PNG/JPG)",type=["png","jpg","jpeg"],key="sys_logo_up")
            if s.get("system_logo_b64"): st.markdown("**Current logo:**"); st.markdown(b64_img_tag(s["system_logo_b64"],"sys-logo","Logo"),unsafe_allow_html=True)
            ca,cb,cc=st.columns(3); do_save=ca.form_submit_button("Save",type="primary"); do_clear=cb.form_submit_button("Remove logo"); do_cancel=cc.form_submit_button("Cancel")
        if do_save: s["system_name"]=new_name; s["system_logo_b64"]=img_to_b64(logo_file) if logo_file else s.get("system_logo_b64"); st.success("Settings saved."); st.rerun()
        if do_clear: s["system_logo_b64"]=None; st.success("Logo removed."); st.rerun()

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
        for f in st.session_state.call_extra_fields:
            if f["type"]=="select": ef_vals[f["id"]]=st.selectbox(f["label"],[""]+(f["options"] or []),key=f"lf_{f['id']}")
            else: ef_vals[f["id"]]=st.text_input(f["label"],key=f"lf_{f['id']}")
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
        contact=st.text_input("Contact person"); logo_file=st.file_uploader("Brand logo (PNG/JPG, optional)",type=["png","jpg","jpeg"],key="new_acc_logo")
        ef_vals={}
        for f in st.session_state.account_extra_fields:
            if f["type"]=="select": ef_vals[f["id"]]=st.selectbox(f["label"],[""]+(f["options"] or []))
            else: ef_vals[f["id"]]=st.text_input(f["label"])
        s1,s2=st.columns(2); do_save=s1.form_submit_button("Add account",type="primary"); do_cancel=s2.form_submit_button("Cancel")
    if do_save and acc_name and brand:
        logo_b64=img_to_b64(logo_file) if logo_file else None
        new_acc={"id":f"ACC-{str(len(st.session_state.accounts)+1).zfill(4)}","account_name":acc_name,"brand_name":brand,"branches":int(branches),"sector":sector,"last_call_date":rnd_date(1),"contact_person":contact,"notes":[],"extra_fields":ef_vals,"logo_b64":logo_b64,"is_deleted":False}
        st.session_state.accounts.append(new_acc)
        sb_upsert_account(new_acc)
        st.session_state.show_add_account=False; st.success(f"Account '{brand}' added."); st.rerun()
    if do_cancel: st.session_state.show_add_account=False; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# IMPORT CSV
# ══════════════════════════════════════════════════════════════════════════════
def render_import():
    if not st.session_state.get("show_import"): return
    st.markdown("---"); st.subheader("Import accounts — CSV")
    cols=["Account ID","Account Name","Brand Name","# of Branches","Sector","Contact Person"]+[f["label"] for f in st.session_state.account_extra_fields]
    tmpl=pd.DataFrame(columns=cols)
    st.download_button("Download CSV template", tmpl.to_csv(index=False).encode(), "accounts_template.csv","text/csv",key="dl_acc_tmpl")
    mode=st.radio("Import mode",["Add new rows","Update existing by Account ID","Add new + update existing"],horizontal=True,key="import_mode")
    uploaded=st.file_uploader("Upload CSV",type=["csv"],key="acc_csv_upload")
    if uploaded is not None:
        try:
            df=pd.read_csv(uploaded); df.columns=[c.strip() for c in df.columns]
            st.caption(f"{len(df)} rows · Columns: {', '.join(df.columns)}")
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
                        "extra_fields":{f["id"]:str(row.get(f["label"],"")).strip() for f in st.session_state.account_extra_fields},
                        "logo_b64":existing["logo_b64"] if existing else None,"is_deleted":False,
                    }
                    if existing and "Update" in mode:
                        idx=st.session_state.accounts.index(existing); st.session_state.accounts[idx]=new_acc; bulk_update.append(new_acc); updated+=1
                    elif not existing:
                        st.session_state.accounts.append(new_acc); bulk_new.append(new_acc); added+=1
                    else: skipped+=1
                # Write to Supabase in bulk
                all_to_write = bulk_new + bulk_update
                if all_to_write: sb_upsert_accounts_bulk(all_to_write)
                st.session_state.show_import=False
                st.success(f"Import complete — {added} added · {updated} updated · {skipped} skipped"); st.rerun()
        except Exception as ex: st.error(f"CSV error: {ex}")
    if st.button("Close",key="close_import"): st.session_state.show_import=False; st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    init_state()
    active  = get_active_user()
    is_rep  = active["role"] == "rep"
    render_sidebar()

    s  = st.session_state.settings
    tc = st.columns([4,1,1])
    tc[0].title(s.get("system_name","Client Interaction Management"))
    with tc[1]:
        if has_perm(active["role"],"import") and st.button("Import CSV",use_container_width=True,key="top_import"):
            st.session_state.show_import=True; st.session_state.show_add_account=False; st.session_state.show_log_modal=False
    with tc[2]:
        if has_perm(active["role"],"add_account") and st.button("+ Account",type="primary",use_container_width=True,key="top_add"):
            st.session_state.show_add_account=True; st.session_state.show_import=False; st.session_state.show_log_modal=False

    render_add_account(active)
    render_import()
    render_log_modal(active)

    urgency_count = sum(1 for a in st.session_state.accounts if days_since(a["last_call_date"])>14)
    tab_labels = ["Dashboard","Accounts",f"Urgency ({urgency_count})","Activity Log","Users","Deleted Accounts"]
    if has_perm(active["role"],"manage_schema"): tab_labels.append("Field Builder & Roles")

    tabs = st.tabs(tab_labels)
    with tabs[0]: render_dashboard(active, is_rep)
    with tabs[1]: render_accounts(active, is_rep)
    with tabs[2]: render_urgency(active)
    with tabs[3]: render_log(active, is_rep)
    with tabs[4]: render_users(active)
    with tabs[5]: render_deleted_accounts(active)
    if has_perm(active["role"],"manage_schema") and len(tabs)>6:
        with tabs[6]: render_schema()

if __name__ == "__main__":
    main()
