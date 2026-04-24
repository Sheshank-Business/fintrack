# 📖 Fintrack — Complete Technical Documentation
> **Version:** 1.0 | **Last Updated:** April 2026 | **Author:** Shanky
> 
> *This document is the single source of truth for the Fintrack project — architecture, data flow, stack decisions, and implementation details.*

---

## Table of Contents

1. [Product Vision](#1-product-vision)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Software Stack](#3-software-stack)
4. [Project Structure](#4-project-structure)
5. [Module Breakdown](#5-module-breakdown)
6. [Database Design](#6-database-design)
7. [Data Flow & Communication](#7-data-flow--communication)
8. [UI/UX Architecture](#8-uiux-architecture)
9. [Security Design](#9-security-design)
10. [Deployment Pipeline](#10-deployment-pipeline)
11. [Environment Setup](#11-environment-setup)
12. [Roadmap (V1 → V3)](#12-roadmap-v1--v3)
13. [Known Issues & Decisions](#13-known-issues--decisions)

---

## 1. Product Vision

### What is Fintrack?

**Fintrack** is a personal finance OS — not just an expense tracker. It is designed to give a founder/individual complete financial awareness in under 5 seconds per interaction.

### Core Principles

| Principle | Description |
|-----------|-------------|
| ⚡ **Fast** | Add expense in < 5 seconds |
| 📱 **Mobile-first** | Works seamlessly on phone, no app install needed |
| 🧠 **Insightful** | Not just numbers — patterns and warnings |
| 🧾 **Minimal** | Zero clutter. Every element earns its place |
| 💸 **₹0 cost** | Entirely free stack, no credit card ever |

### Target User

Solo founder / individual who needs:
- Real-time remaining budget awareness
- Expense + investment tracking in one place
- Accessible from any device, anytime

---

## 2. System Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────┐
│              USER DEVICE                    │
│  Browser (Phone / Laptop / Tablet)          │
└───────────────────┬─────────────────────────┘
                    │ HTTPS
                    ▼
┌─────────────────────────────────────────────┐
│         STREAMLIT CLOUD (Host)              │
│  ┌─────────────────────────────────────┐   │
│  │          app.py (UI Layer)          │   │
│  │   Dashboard | Add Txn | History     │   │
│  └──────────────┬──────────────────────┘   │
│                 │                           │
│  ┌──────────────▼──────────────────────┐   │
│  │        Logic Layer                  │   │
│  │  budget.py | utils.py               │   │
│  └──────────────┬──────────────────────┘   │
│                 │                           │
│  ┌──────────────▼──────────────────────┐   │
│  │        Data Layer (Dual Mode)       │   │
│  │  sheets.py (Cloud) ◄── auto-detect  │   │
│  │  database.py (Local) ◄── fallback   │   │
│  └──────────────┬──────────────────────┘   │
└─────────────────┼───────────────────────────┘
                  │ gspread / Google Auth
                  ▼
┌─────────────────────────────────────────────┐
│         GOOGLE SHEETS (Database)            │
│  Sheet 1: Transactions                      │
│  Sheet 2: Budget                            │
│  Sheet 3: Config                            │
└─────────────────────────────────────────────┘
```

### Dual-Mode Database Design

The app **auto-detects** which database to use at runtime:

```
On startup:
  IF st.secrets["gcp_service_account"] exists:
      → use sheets.py  (Cloud mode — Google Sheets)
  ELSE:
      → use database.py (Local mode — JSON file)
```

This means:
- **Local dev** → no setup needed, JSON file auto-created in `data/`
- **Cloud deploy** → add secrets → automatically uses Google Sheets

---

## 3. Software Stack

### Core Technologies

| Layer | Technology | Version | Why |
|-------|-----------|---------|-----|
| **UI Framework** | Streamlit | ≥ 1.30 | Fastest Python → web UI, built-in state management |
| **Language** | Python | 3.11 | Stable, great data ecosystem |
| **Charts** | Plotly | ≥ 5.18 | Interactive charts, transparent background support |
| **Data Processing** | Pandas | ≥ 2.1 | DataFrame operations for filtering/grouping |
| **Cloud Database** | Google Sheets | — | Free, persistent, accessible from any device |
| **Sheets Client** | gspread | ≥ 6.0 | Clean Python wrapper for Google Sheets API |
| **Auth** | google-auth | ≥ 2.25 | Service account authentication |
| **Local Database** | JSON file | — | Zero-setup dev experience |
| **Hosting** | Streamlit Community Cloud | — | Free, Git-integrated, HTTPS |
| **Env Manager** | Conda | — | Isolated Python 3.11 environment |

### Why Not React / Django / FastAPI?

Fintrack is a **personal tool** for one user. Streamlit gives:
- Zero frontend code (no HTML/CSS/JS needed for logic)
- Built-in state management (`st.session_state`)
- One-command deploy to Streamlit Cloud
- Mobile browser compatible out of the box

### Why Google Sheets over SQLite / PostgreSQL?

| Factor | Google Sheets | SQLite | PostgreSQL |
|--------|--------------|--------|-----------|
| Cost | ₹0 | ₹0 local only | ₹500+/mo |
| Multi-device access | ✅ | ❌ | ✅ |
| Manual editing | ✅ (open Sheet directly) | ❌ | ❌ |
| Backups | Auto (Google Drive) | Manual | Manual |
| Setup complexity | Medium (one-time) | None | High |

---

## 4. Project Structure

```
D:\SHANKY\Expense_app\
│
├── app.py                    # 🏠 Main application — UI, tabs, state
├── budget.py                 # 🧮 Budget engine — calculations & alerts
├── database.py               # 💾 Local JSON data layer (dev mode)
├── sheets.py                 # ☁️  Google Sheets data layer (cloud mode)
├── utils.py                  # 🔧 Shared constants & helper functions
│
├── requirements.txt          # 📦 Python dependencies for Streamlit Cloud
│
├── assets/
│   └── style.css             # 🎨 Premium dark glassmorphism CSS
│
├── .streamlit/
│   ├── config.toml           # ⚙️  Streamlit theme & server config
│   ├── secrets.toml          # 🔐 Google credentials (NEVER commit)
│   └── secrets.toml.example  # 📝 Template for new contributors
│
├── data/
│   └── finance_data.json     # 💾 Local data store (auto-created, gitignored)
│
├── service_account.json      # 🔑 Google SA key (NEVER commit, gitignored)
└── .gitignore                # 🚫 Protects secrets from being pushed
```

### File Roles at a Glance

```
User clicks button
       │
       ▼
    app.py  ──── reads/writes ──► sheets.py OR database.py
       │                                │
       │                                ▼
       │                         Google Sheets / JSON
       │
       ├── calls ──► budget.py   (math: remaining, alerts)
       │
       └── uses  ──► utils.py    (formatting, categories, dates)
```

---

## 5. Module Breakdown

### `app.py` — Main Application

**Responsibilities:**
- Page config, CSS injection
- Sidebar: month selector, budget form
- Tab 1 (Dashboard): alert banners, metric cards, Plotly charts
- Tab 2 (Add Transaction): form with validation, success toast
- Tab 3 (History): filterable dataframe with summary stats
- Auto-detects database mode at import time

**Key design decisions:**
- No `st.cache_data` on `load_data()` — intentional. Each rerun fetches fresh data so dashboard is always current after a write.
- `st.balloons()` on transaction submit — micro-delight UX
- CSS loaded from file with explicit `encoding="utf-8"` to prevent Windows `charmap` errors

---

### `budget.py` — Budget Engine

**Responsibilities:**
- Pure functions, no Streamlit imports (fully testable)
- `calculate_remaining(budget, expenses_df)` → float
- `total_spent(expenses_df)` → float
- `total_invested(investments_df)` → float
- `check_alert(remaining, budget, threshold=0.20)` → `"ok"` | `"warning"` | `"critical"`
- `category_breakdown(expenses_df)` → sorted DataFrame
- `daily_spending(expenses_df)` → daily totals DataFrame

**Alert logic:**
```
remaining < 0           → "critical"  (overspent)
remaining < 20% budget  → "warning"   (low)
else                    → "ok"
```

---

### `database.py` — Local JSON Layer

**Responsibilities:**
- Stores all data in `data/finance_data.json`
- Auto-creates file + directory if missing
- CRUD: `add_transaction`, `get_transactions`, `get_expenses`, `get_investments`
- Budget: `set_budget`, `get_budget`
- Config: `get_config`, `set_config`

**JSON schema:**
```json
{
  "transactions": [
    {
      "Date": "2026-04-13",
      "Category": "🍔 Food",
      "Amount": 250.0,
      "Type": "Expense",
      "Note": "Lunch",
      "Timestamp": "2026-04-13T14:22:00"
    }
  ],
  "budgets": {
    "2026-04": 25000.0
  },
  "config": {
    "warning_threshold": 20
  }
}
```

---

### `sheets.py` — Google Sheets Layer

**Responsibilities:**
- Same interface as `database.py` (drop-in replacement)
- Auth via `google.oauth2.service_account.Credentials`
- `@st.cache_resource(ttl=300)` — caches the gspread client for 5 min (avoids re-auth on every rerun)
- Auto-creates worksheets with headers if they don't exist
- Upserts budget rows (updates existing month, appends new)

**Google Sheets structure:**

**Sheet 1: Transactions**
| Date | Category | Amount | Type | Note |
|------|----------|--------|------|------|
| 2026-04-13 | 🍔 Food | 250 | Expense | Lunch |

**Sheet 2: Budget**
| Month | Budget |
|-------|--------|
| 2026-04 | 25000 |

**Sheet 3: Config**
| Key | Value |
|-----|-------|
| warning_threshold | 20 |

---

### `utils.py` — Shared Utilities

**Responsibilities:**
- `EXPENSE_CATEGORIES` — list of 10 emoji-prefixed categories
- `INVESTMENT_CATEGORIES` — list of 7 categories
- `format_inr(amount)` → `"₹1,234"` (Indian Rupee formatting)
- `get_current_month_key()` → `"2026-04"`
- `get_month_label("2026-04")` → `"April 2026"`
- `get_month_options(n=6)` → last 6 months, newest first

---

## 6. Database Design

### Mode Detection Flow

```python
# In app.py at import time:
try:
    _ = st.secrets["gcp_service_account"]
    import sheets as db        # Google Sheets mode
    DB_MODE = "☁️ Cloud (Google Sheets)"
except (FileNotFoundError, KeyError):
    import database as db      # Local JSON mode
    DB_MODE = "💾 Local (JSON)"
```

### Data Contract (Both Layers)

Both `sheets.py` and `database.py` expose **identical function signatures**:

```python
# Read
get_transactions(month: str | None) -> pd.DataFrame
get_expenses(month: str | None) -> pd.DataFrame
get_investments(month: str | None) -> pd.DataFrame
get_budget(month: str) -> float
get_config(key: str, default: str) -> str

# Write
add_transaction(date, category, amount, txn_type, note) -> None
set_budget(month, amount) -> None
set_config(key, value) -> None
```

This is the **Repository Pattern** — `app.py` never knows which database it's talking to.

### Monthly Filtering

All transaction reads are filtered by month prefix:
```python
df[df["Date"].str.startswith("2026-04")]
# matches: 2026-04-01, 2026-04-13, 2026-04-30
```

---

## 7. Data Flow & Communication

### Flow 1: Adding an Expense

```
User fills form (Tab 2)
        │
        ▼
st.form submitted
        │
        ▼
app.py validates input
        │
        ├── date_str = txn_date.strftime("%Y-%m-%d")
        ├── txn_type_clean = "Expense"
        │
        ▼
db.add_transaction(date, category, amount, type, note)
        │
        ├── [LOCAL]  → appends to data/finance_data.json
        └── [CLOUD]  → ws.append_row([...]) via gspread
                              │
                              ▼
                    Google Sheets API (HTTPS)
                    sheets.googleapis.com
        │
        ▼
st.toast("✅ Expense added!")
st.balloons()
st.rerun()  ← causes full page rerender
        │
        ▼
load_data() called again → fresh data fetched
        │
        ▼
Dashboard updates with new totals
```

---

### Flow 2: Setting a Budget

```
User enters amount in sidebar form
        │
        ▼
db.set_budget("2026-04", 25000)
        │
        ├── [LOCAL]  → data["budgets"]["2026-04"] = 25000 → save JSON
        └── [CLOUD]  → check if month exists in Budget sheet
                          │
                          ├── EXISTS → update_cell(row, col, value)
                          └── NEW    → append_row(["2026-04", 25000])
        │
        ▼
st.rerun() → budget_val refreshed → remaining recalculated
```

---

### Flow 3: Dashboard Render

```
selected_month = "2026-04"
        │
        ▼
expenses_df  = db.get_expenses("2026-04")      # Type == "Expense"
investments_df = db.get_investments("2026-04") # Type == "Investment"
all_txns_df  = db.get_transactions("2026-04")  # All types
budget_val   = db.get_budget("2026-04")        # float
        │
        ▼
spent     = budget.total_spent(expenses_df)
invested  = budget.total_invested(investments_df)
remaining = budget.calculate_remaining(budget_val, expenses_df)
alert     = budget.check_alert(remaining, budget_val)
        │
        ├── alert == "critical" → red pulsing banner
        ├── alert == "warning"  → amber pulsing banner
        └── alert == "ok"       → green banner (if budget set)
        │
        ▼
Metric Cards: Budget | Spent | Remaining | Invested
        │
        ▼
Charts (if expenses exist):
        ├── Pie chart (Plotly) → category_breakdown(expenses_df)
        ├── Line chart (Plotly) → daily_spending(expenses_df)
        └── Bar chart (Plotly) → top 5 categories
```

---

### Google Sheets API Communication

```
App (Streamlit Cloud)
        │
        │  1. Auth: service account credentials
        ▼
google-auth library
        │
        │  2. OAuth2 token request
        ▼
https://oauth2.googleapis.com/token
        │
        │  3. Bearer token received
        ▼
gspread client (cached 5 min)
        │
        │  4. API calls
        ▼
https://sheets.googleapis.com/v4/spreadsheets/{id}/values/{range}:append
        │
        │  5. Response: updated sheet data
        ▼
Python DataFrame → UI render
```

**Rate Limits (Google Sheets API free tier):**
- 300 requests/minute per project
- 60 requests/minute per user
- Well within limits for personal use

---

## 8. UI/UX Architecture

### Design System

**Color Palette:**
```css
--primary:        #6C63FF   /* Electric purple — primary actions */
--primary-glow:   rgba(108, 99, 255, 0.25)
--accent-green:   #00E676   /* Remaining balance, investments */
--accent-red:     #FF5252   /* Overspent, expenses */
--accent-amber:   #FFD740   /* Warning state */
--bg-dark:        #0E1117   /* Page background */
--bg-card:        rgba(26, 29, 41, 0.7) /* Glassmorphism cards */
--text-primary:   #FAFAFA
--text-secondary: #9BA1B0
```

**Typography:**
- Font: `Inter` (Google Fonts) — weights 300–800
- Fallback: `-apple-system, BlinkMacSystemFont, sans-serif`

**Design Language:**
- Glassmorphism cards with `backdrop-filter: blur(12px)`
- Gradient text for titles (CSS `-webkit-background-clip: text`)
- Animated alert banners (CSS `@keyframes pulse-warning` / `pulse-critical`)
- Cubic-bezier hover transitions on all interactive elements
- Custom scrollbar (6px, purple tint)

### Tab Architecture

```
┌──────────────────────────────────────────────────┐
│  📊 Dashboard  │  ➕ Add Transaction  │  📜 History │
└──────────────────────────────────────────────────┘
       │                  │                   │
       ▼                  ▼                   ▼
  Alert banner        Type toggle         Type filter
  4 metric cards      Date picker         Category filter
  Pie chart           Category select     Sortable table
  Line chart          Amount input        Summary stats
  Bar chart           Note input          (count/spent/invested)
                      Submit button
                      Recent 5 txns
```

### Mobile Responsiveness

Streamlit natively renders as responsive HTML. Additional CSS for mobile:
```css
@media (max-width: 768px) {
  /* Metric cards: smaller font */
  /* Buttons: full width */
  /* Tabs: smaller padding */
}
```

On Streamlit Cloud, users can **add the app to home screen** (PWA-like behavior) via browser's "Add to Home Screen".

---

## 9. Security Design

### Secrets Management

| Secret | Where Stored | Who Can See |
|--------|-------------|------------|
| `secrets.toml` (local) | `.streamlit/secrets.toml` | Only on your machine |
| `service_account.json` | `D:\SHANKY\Expense_app\` | Only on your machine |
| Streamlit Cloud secrets | Streamlit Cloud encrypted storage | Only you (via dashboard) |
| GitHub repo | Only code, NO secrets | Public/private repo |

### `.gitignore` Protections
```gitignore
.streamlit/secrets.toml   # Google credentials
service_account.json      # Service account key
data/                     # Local JSON data
```

### Service Account Principle of Least Privilege

The `finance-os` service account has:
- ✅ Access to **only one specific Google Sheet** (via share)
- ✅ Google Sheets API scope: read/write spreadsheets
- ✅ Google Drive API scope: find files by name
- ❌ No access to other Drive files
- ❌ No Compute, Storage, or other GCP services

### No User Authentication (By Design)

Fintrack is a **personal tool** — single user. Authentication would add friction with no security benefit (the Streamlit Cloud URL is private/unlisted unless shared).

If multi-user is ever needed → add Streamlit's `st.login()` or move to Supabase with row-level security.

---

## 10. Deployment Pipeline

### Architecture

```
Local Dev (Windows)
│
│  git push origin main
▼
GitHub Repository (Private)
│
│  Streamlit Cloud pulls on every push (auto-deploy)
▼
Streamlit Community Cloud
│  ├── Reads requirements.txt → installs packages
│  ├── Reads secrets from Streamlit Cloud dashboard
│  └── Runs: streamlit run app.py
▼
Live URL: https://your-app-name.streamlit.app
```

### Deploy Checklist

- [ ] `requirements.txt` has all dependencies
- [ ] `secrets.toml` contents pasted into Streamlit Cloud dashboard
- [ ] `service_account.json` NOT in repo (gitignored)
- [ ] Google Sheet shared with `finance-os@nexgen-fintrack.iam.gserviceaccount.com`
- [ ] `spreadsheet_id` in secrets.toml is correct
- [ ] App tested locally with `conda run -n finance_os streamlit run app.py`

### Streamlit Cloud Secrets Format

In Streamlit Cloud dashboard → App settings → Secrets, paste:
```toml
[gcp_service_account]
type = "service_account"
project_id = "nexgen-fintrack"
# ... (full contents of secrets.toml minus the [sheets] section)

[sheets]
spreadsheet_id = "YOUR_SHEET_ID"
```

### CI/CD: No Pipeline Needed

Streamlit Cloud auto-deploys on every `git push main`. For personal use, this is sufficient. If needed later, GitHub Actions can be added for:
- Linting (ruff / flake8)
- Type checking (mypy)
- Smoke tests

---

## 11. Environment Setup

### Local Development

```bash
# 1. Create conda environment
conda create -n finance_os python=3.11 -y

# 2. Activate
conda activate finance_os

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run locally (uses JSON database automatically)
streamlit run app.py
# → App at http://localhost:8501
# → Phone access at http://192.168.1.x:8501 (same WiFi)
```

### Switching to Google Sheets Locally

```bash
# Copy secrets template
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# Fill in your credentials + spreadsheet_id
# Then run normally — app auto-detects and uses Google Sheets
streamlit run app.py
```

### Python Dependencies

```
streamlit>=1.30.0     # UI framework
plotly>=5.18.0        # Interactive charts
pandas>=2.1.0         # Data manipulation
gspread>=6.0.0        # Google Sheets client
google-auth>=2.25.0   # Google service account auth
```

---

## 12. Roadmap (V1 → V3)

### ✅ V1 — MVP (COMPLETED)

| Feature | Status | File |
|---------|--------|------|
| Add Expense | ✅ | `app.py` Tab 2 |
| Add Investment | ✅ | `app.py` Tab 2 |
| Set Monthly Budget | ✅ | `app.py` sidebar |
| Remaining balance | ✅ | `budget.py` |
| Budget alert (20%) | ✅ | `budget.py`, `app.py` |
| Pie chart (categories) | ✅ | `app.py` Tab 1 |
| Daily trend line chart | ✅ | `app.py` Tab 1 |
| Top categories bar chart | ✅ | `app.py` Tab 1 |
| Transaction history + filters | ✅ | `app.py` Tab 3 |
| Mobile-first UI | ✅ | `assets/style.css` |
| Dual-mode database | ✅ | `database.py`, `sheets.py` |
| Cloud deploy (Streamlit Cloud) | 🔄 In Progress | — |

---

### ⚡ V2 — Smart System (Next)

| Feature | Description | Complexity |
|---------|-------------|------------|
| Edit/Delete transactions | In-place editing in History tab | Medium |
| Monthly auto-reset | Button to archive old month & start fresh | Low |
| Category budget limits | Set per-category budget (e.g., Food: ₹5K) | Medium |
| Separate Personal vs Business | Tag transactions; filter view by type | Medium |
| Export to CSV | Download button in History tab | Low |
| Weekly summary notification | Email digest via `smtplib` or webhook | High |

---

### 🔥 V3 — Advanced (Future)

| Feature | Description | Tech |
|---------|-------------|------|
| AI spending insights | "You spend 40% more on weekends" | Gemini API |
| Next month burn forecast | Linear regression on daily spend | scikit-learn |
| Goal tracking | Set savings target, track progress | New Sheet tab |
| Multi-account | Cash / Bank / UPI tagging | Schema change |
| SaaS migration | Login system, per-user data | Supabase + Auth |

---

## 13. Known Issues & Decisions

### Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| Apr 2026 | Used Streamlit over React | Single user tool, Python-first, faster to build |
| Apr 2026 | Google Sheets over SQLite | Multi-device access without hosting a DB server |
| Apr 2026 | Dual-mode database | Dev experience (local JSON) without sacrificing cloud capability |
| Apr 2026 | No auth system | Personal tool, friction outweighs security benefit |
| Apr 2026 | Conda env (`finance_os`) | Isolated from system Python, reproducible |

### Known Limitations

| Issue | Impact | Workaround |
|-------|--------|------------|
| Google Sheets API rate limit (300 req/min) | None for personal use | Caching gspread client |
| Streamlit re-renders full page on each interaction | Minor latency | Acceptable for personal tool |
| No offline support | Can't add expense without internet (cloud mode) | Use local mode for offline |
| `secrets.toml` must be manually added to Streamlit Cloud | One-time setup friction | Documented in deploy checklist |
| Windows `UnicodeDecodeError` on CSS | Fixed — `open(..., encoding="utf-8")` | Already patched |
| `st.cache_resource` on gspread client | Stale connection after 5 min → auto-refreshes | TTL=300 handles it |

---

*End of Fintrack Technical Documentation v1.0*

> 💡 **Tip:** Keep this doc updated whenever you make architectural changes. It's your project's memory.
