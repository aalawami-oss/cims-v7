# Client Interaction Management System (CIMS)

A Streamlit application for managing client accounts, logging sales calls, and tracking team performance — backed by Supabase.

---

## Quick start

```bash
# 1. Clone or unzip the project
# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your Supabase credentials
cp .streamlit/secrets.toml .streamlit/secrets.toml
# Edit secrets.toml with your SUPABASE_URL and SUPABASE_KEY

# 4. Run the database schema (once)
# Paste the contents of schema.sql into Supabase Dashboard → SQL Editor → Run

# 5. Start the app
streamlit run app.py
```

Opens at `http://localhost:8501`

---

## Features at a glance

| Area | What it does |
|---|---|
| **Dashboard** | Coverage rate, branch metrics, overdue list, call activity chart |
| **Activity chart** | 8 chart types · Daily / Weekly / Monthly / Yearly · team filter |
| **Accounts** | Add, edit, delete, bulk CSV import, brand logo, custom fields |
| **Bulk delete** | Checkbox-select multiple accounts, soft-delete with one click |
| **Deleted accounts** | Full deletion log with who/when, one-click restore |
| **Filters** | Search, sector, urgency, contact, last caller, branch range, priority |
| **Call logging** | Team member, date, status, notes, custom call fields |
| **Activity log** | Full sortable log, CSV export |
| **Users** | Add, edit, delete, bulk CSV import |
| **Roles** | 4 built-in + custom roles, 7 permission flags each |
| **Field builder** | Custom fields for Accounts, Users, Calls (text/number/date/select) |
| **Call statuses** | Configurable with color picker |
| **System settings** | Upload logo, rename system |
| **Supabase** | All data persisted; graceful fallback to mock data if no credentials |

---

## Supabase setup

### 1. Create a project
Go to [supabase.com](https://supabase.com), create a new project, and note your **Project URL** and **anon key** from Settings → API.

### 2. Run the schema
Open **SQL Editor** in your Supabase dashboard, paste the contents of `schema.sql`, and click **Run**. This creates four tables:

| Table | Purpose |
|---|---|
| `accounts` | All client accounts (soft-delete with `is_deleted`) |
| `account_deletions` | Audit log of every deletion with who and when |
| `call_logs` | Individual call log entries (separate from account JSONB) |
| `users` | Team members |

### 3. Add credentials to secrets.toml
```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
```

### 4. First run
The app checks for data on startup. If the tables are empty it seeds mock data for demo purposes.

---

## CSV import format

### Accounts
```
Account ID, Account Name, Brand Name, # of Branches, Sector, Contact Person
```
- `Account ID` is optional for new rows (auto-generated)
- Three import modes: Add new / Update existing / Both

### Users
```
Name, Email, Role
```
Valid role values: `admin`, `manager`, `rep`, `viewer` (or any custom role ID)

---

## Default users

| Name | Role | Email |
|---|---|---|
| Alawi Alawami | Admin | a.alawami@foodics.com |
| Sara Al-Zahrani | Manager | sara@corp.com |
| Mohammed Al-Ghamdi | Rep | mohammed@corp.com |
| Fatima Al-Otaibi | Rep | fatima@corp.com |
| Khalid Al-Qahtani | Viewer | khalid@corp.com |

Switch the active user from the sidebar to preview any role's permissions.

---

## Deployment

### Streamlit Community Cloud (free)
1. Push project to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Set `SUPABASE_URL` and `SUPABASE_KEY` in the **Secrets** section of the app settings
4. Deploy — live in ~60 seconds

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Azure / AWS / GCP
Deploy the Docker container to any cloud container service. Set `SUPABASE_URL` and `SUPABASE_KEY` as environment variables or secrets.

---

## File structure

```
cims_v7/
├── app.py              # Main application (single file)
├── schema.sql          # Supabase database schema
├── requirements.txt    # Python dependencies
├── .streamlit/
│   └── secrets.toml    # Credentials (never commit this)
├── README.md           # This file
└── TECHNICAL_DOC.md    # Developer reference
```
