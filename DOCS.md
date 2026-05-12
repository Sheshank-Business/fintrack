# 📖 Nexgen Fintrack — Complete Technical Documentation

> **Version:** 3.0 | **Last Updated:** May 2026 | **Author:** Sheshank with ❤️  
> **Product:** Nexgen Fintrack — Personal Finance OS for founders & individuals

---

## Quick Links

| Section | Details |
|---------|---------|
| **Live App** | https://fintrack-dnqyqec9hfpdehyum3vmkh.streamlit.app |
| **Database** | Supabase PostgreSQL (Cloud) or Local JSON (Dev) |
| **Auth** | Family passcode or Google OAuth |
| **Stack** | Streamlit + Python + Plotly + Supabase |
| **Deploy** | Streamlit Cloud (auto-deploy on git push) |

---

## What's New in V3

✅ **7 Organized Tabs** — Add (primary) | Overview | Analytics | History | Budget | Admin | Settings  
✅ **Payment Methods** — Track Cash, Credit Card, UPI, Net Banking  
✅ **Investment Targets** — Set monthly per-category goals with progress bars  
✅ **Admin Panel** — One dashboard for all family members' finances  
✅ **Smart Insights** — Automatic spending conclusions & trend analysis  
✅ **Brand Identity** — "Made by Sheshank with ❤️"  

---

## Setup: Supabase SQL Migration

### Step 1: Open Supabase SQL Editor
- Go: https://app.supabase.com/projects
- Select your project
- Click: **SQL Editor** (left sidebar)
- Click: **New Query**

### Step 2: Paste This SQL
\\\sql
alter table transactions add column if not exists payment_method text default 'Cash';
\\\

### Step 3: Run
- Click green **Run** button
- Choose: **"Run without RLS"** (middle button)
- Wait for success ✅

### Why?
Existing table needs the new column. This adds it with a default value of 'Cash' for all existing rows.

---

## Database Schema

### transactions table
\\\sql
CREATE TABLE transactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL,
  date date NOT NULL,
  type text NOT NULL,           -- 'Expense' or 'Investment'
  category text NOT NULL,
  amount numeric NOT NULL,
  payment_method text DEFAULT 'Cash',  -- NEW in V3
  note text DEFAULT '',
  created_at timestamp DEFAULT now()
);
\\\

**Payment Method Values:**
- \'💵 Cash'\
- \'💳 Credit Card'\
- \'📱 UPI'\
- \'🏦 Net Banking'\
- \'—'\ (for investments, which don't need payment tracking)

---

## UI: 7 Tabs Architecture

### Tab 1: ➕ Add (Daily-Use, Default)
Primary tab for quick logging.
- Type toggle (Expense ↔ Investment)
- Category selector
- Amount input (₹)
- Payment method (Expense only)
- Note field
- Date expander (default: today)
- Today's transactions list
- Last 7 days summary

### Tab 2: 📊 Overview
Current month dashboard.
- Alert banner (critical/warning/ok)
- 4 metric cards (Budget, Spent, Remaining, Invested)
- Budget progress bar (colored)
- Pie chart: Spending by category
- Line chart: Daily spending trend
- Category limit progress bars
- Top categories bar chart
- Payment method breakdown pie

### Tab 3: 📈 Analytics
Trends & insights.
- 12-month bar chart (Spent vs Invested vs Budget)
- Savings rate cards (monthly)
- Category breakdown by month
- Month-on-month category diff table
- Smart insights (auto-generated conclusions)

### Tab 4: 📜 History
Transaction management.
- Month & type filters
- CSV export button
- Inline edit/delete buttons
- Edit modal (all fields editable)
- Delete confirmation

### Tab 5: 💰 Budget
Set limits & goals.
- Inner tab: **💸 Expense Budget**
  - Last 3 months summary
  - Monthly budget setter
  - Category limit manager
- Inner tab: **📈 Investment Budget**
  - Per-category targets
  - Progress vs actual bars

### Tab 6: 👑 Admin (Admin only)
Family financial overview.
- Family summary table
- Member detail view (select member + month)
- All transactions view (with user column)

### Tab 7: ⚙️ Settings
Customization.
- Expense category manager
- Investment category manager
- Alert threshold slider (5-50%, default 20%)
- App info (mode, user, transaction count)
- **"Made by Sheshank with ❤️"**

---

## Core Features

### Payment Method Tracking
Every expense now records how you paid:
- Added to transaction form in ➕ Add tab
- Editable in 📜 History tab
- Visualized in 📊 Overview (payment breakdown pie chart)

### Investment Targets
Set monthly goals per investment category:
- Define in 💰 Budget → 📈 Investment Budget tab
- Stored as JSON in configs table
- Progress bars show actual vs target
- Auto-tracked investments in 📈 Analytics

### Category Limits
Set per-category spending caps:
- Define in 💰 Budget → 💸 Expense Budget tab
- Progress bars show limit usage
- Warnings in 📈 Analytics if exceeded

### Admin Panel
Admin (Shanky) can see all family finances:
- 👑 Admin tab only shows if logged in as admin_user
- Family summary: name, spent, invested, budget, remaining
- Member detail: expenses, investments, budget
- All transactions: search across whole family

### Smart Insights
Auto-generated conclusions:
- Budget overspent/underspent messages
- Top category identification
- Month-on-month spending change analysis
- Category limit violation alerts
- Savings rate badges

---

## Deployment

### Push to GitHub
\\\ash
cd D:\\SHANKY\\Projects\\Expense_app
git add .
git commit -m "V3: Nexgen Fintrack - Payment methods, investment targets, redesigned UI"
git push
\\\

### Auto-Deploy on Streamlit Cloud
- Every git push → Streamlit Cloud auto-deploys
- Live app: https://fintrack-dnqyqec9hfpdehyum3vmkh.streamlit.app

### Update Secrets on Streamlit Cloud
Make sure Streamlit Cloud has these secrets configured:
\\\	oml
[supabase]
url = "https://mbcrvybeirvuezbowpmg.supabase.co"
key = "eyJhbGc..."

[app_auth]
mode = "passcode"
shared_passcode = "1234"
admin_user = "Shanky"
\\\

---

## Author & Credit

**Made by Sheshank with ❤️**

Nexgen Fintrack is your personal finance OS — complete financial awareness in under 5 seconds.

---

*For user guide, see USER_MANUAL.md*
