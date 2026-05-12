# 📘 Nexgen Fintrack — User Manual

**Made by Sheshank with ❤️**

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [The 7 Tabs Explained](#2-the-7-tabs-explained)
3. [Daily Workflow](#3-daily-workflow)
4. [Advanced Features](#4-advanced-features)
5. [Admin Features (Family Mode)](#5-admin-features-family-mode)
6. [Tips & Tricks](#6-tips--tricks)
7. [FAQs](#7-faqs)

---

## 1. Getting Started

### Login

**Passcode Mode (Family):**
1. Enter your name (e.g., "Shanky")
2. Enter family passcode: **1234**
3. Click "Continue"

**Google OAuth Mode:**
1. Click "Sign in with Google"
2. Select your Google account
3. Grant access

### Your First Transaction

1. Open the **➕ Add** tab (default)
2. Select "💸 Expense"
3. Choose category (e.g., "🍔 Food")
4. Enter amount: 250
5. Choose payment method: "💵 Cash"
6. Add note (optional): "Lunch at café"
7. Click "💸 Add Expense"
8. ✅ Toast notification confirms!

---

## 2. The 7 Tabs Explained

### Tab 1: ➕ Add (Your Daily Companion)

**What:** Log expenses and investments instantly.

**How to use:**
1. Choose type: **💸 Expense** or **📈 Investment**
2. Pick category from dropdown
3. Enter amount in rupees
4. (Expense only) Select payment method
5. Add optional note
6. Click date expander if not today
7. Submit

**What you see after:**
- Today's transactions list
- Last 7 days summary
- Quick stats in sidebar

---

### Tab 2: 📊 Overview (Month at a Glance)

**What:** Current month dashboard with metrics and charts.

**Key elements:**
- **Alert banner:** Red (overspent) / Yellow (low) / Green (healthy)
- **4 metric cards:** Budget | Spent | Remaining | Invested
- **Budget bar:** Visual progress (color changes at 80% / 100%)
- **Pie chart:** Where your money goes (by category)
- **Line chart:** Daily spending trend
- **Category limits:** Individual category progress bars
- **Top categories:** Bar chart of biggest spending categories
- **Payment breakdown:** How you paid (Cash/Card/UPI/etc)

**How to read:**
- Budget bar at 50% green = spending OK
- Budget bar at 90% yellow = warning, be careful
- Budget bar over 100% red = you've overspent

---

### Tab 3: 📈 Analytics (Understand Patterns)

**What:** Trends, insights, and spending analysis.

**Sections:**
1. **12-Month Trend**
   - Bar chart showing spent, invested, and budget for last 12 months
   - Spot patterns: "I spend more in monsoon season"

2. **Savings Rate**
   - Cards showing monthly savings % (Budget - Spent) / Budget
   - Green = 30%+ saved | Yellow = 10-30% | Red = <10% saved

3. **Category Breakdown**
   - Select any month
   - See expense breakdown % by category
   - See investment breakdown

4. **Month-on-Month Change**
   - Table showing "Food: ₹15K last month → ₹18K this month (+20%)"
   - Quick way to spot increases/decreases

5. **Smart Insights** (Auto-generated)
   - "🚨 You've overspent by ₹2,000 this month"
   - "🏆 Food is your top expense — ₹18,000 (45% of spend)"
   - "📈 Spending up by ₹5,000 vs last month (+25%)"
   - "🟡 Entertainment near limit: ₹4,800 / ₹5,000"

---

### Tab 4: 📜 History (Manage Past)

**What:** View, edit, and delete transactions.

**How to use:**
1. Select **month** (dropdown)
2. Filter by **type** (All / Expense / Investment)
3. Click **"⬇️ Export CSV"** to download spreadsheet
4. See summary stats (total expenses, investments, count)

**Each transaction row:**
- 💸 Category, Date, Payment method, Note
- Amount (in rupees)
- ✏️ Edit button
- 🗑️ Delete button (confirm to remove)

**Edit a transaction:**
1. Click ✏️ on any row
2. Edit modal appears
3. Change any field (date, category, amount, payment, note)
4. Click "💾 Save"

**Delete a transaction:**
1. Click 🗑️
2. Confirm button appears
3. Click ✅ to confirm delete

---

### Tab 5: 💰 Budget

**Inner Tab: 💸 Expense Budget**

*Set monthly spending limit:*
1. Last 3 months summary (non-editable)
2. Choose month from dropdown
3. Enter budget amount (e.g., 25000)
4. Click "💾 Save Budget"

*Set category spending limits:*
1. Select category (e.g., "🍔 Food")
2. Enter limit (e.g., 5000)
3. Click "➕ Set"
4. See progress bars on Overview tab

**Inner Tab: 📈 Investment Budget**

*Set per-category investment targets:*
1. Select investment category (e.g., "🪙 Nifty 50")
2. Enter monthly target (e.g., 10000)
3. Click "➕ Set"
4. See progress vs actual this month

*Track progress:*
- Green bar = on track (≥100% of target)
- Yellow bar = halfway to target
- Red bar = behind target
- Updates automatically as you log investments

---

### Tab 6: 👑 Admin (Shanky Only)

**What:** Family financial overview (if you're the admin).

**Appears only if:** You're logged in as "Shanky" (admin_user from secrets)

**Sections:**

1. **Family Summary Table**
   - List of all family members
   - Their spent, invested, budget, remaining for current month

2. **Member Detail View**
   - Select a family member
   - Pick a month
   - See their expenses (left) and investments (right)
   - Shows their budget vs actual spent

3. **All Transactions**
   - Month selector (or "All Time")
   - Table of EVERY family member's transactions
   - Includes name column so you see who spent what

---

### Tab 7: ⚙️ Settings (Customize)

**My Categories**
- Add custom expense categories (e.g., "🎮 Gaming")
- Add custom investment categories (e.g., "🪧 Angel Investing")
- Delete custom categories (default categories locked)
- Reset to defaults (removes all custom, back to originals)

**Alerts**
- Slider: "Warn when budget remaining falls below ___%"
- Default: 20%
- Example: Budget = ₹25,000, Alert = 20% → Warning at ₹5,000 remaining
- Change and save

**App Info**
- Mode: "☁️ Cloud (Supabase)" or "💾 Local (JSON)"
- Your username
- Total transactions logged
- Number of categories
- **"Made by Sheshank with ❤️"**

---

## 3. Daily Workflow

### Morning Routine
1. Open app
2. Check **Overview** tab → see remaining budget
3. Plan day based on remaining

### During Day
1. Make purchase
2. Open **➕ Add** tab
3. Log expense (2 seconds)
4. See today's transactions update

### Evening
1. Check **Overview** → see daily total
2. Check **Overview** → pie chart shows category breakdown
3. Plan tomorrow based on pace

### Weekly Review
1. Open **📈 Analytics** tab
2. Check savings rate
3. Review top categories
4. Adjust budget if needed

### Monthly
1. Set next month's budget in 💰 **Budget** tab
2. Check **Analytics** for month-on-month changes
3. Archive old month (optional: export CSV from 📜 **History**)

---

## 4. Advanced Features

### Payment Method Tracking

Every expense records HOW you paid:
- 💵 **Cash** — physical money handed over
- 💳 **Credit Card** — card payment (pay later)
- 📱 **UPI** — instant digital transfer
- 🏦 **Net Banking** — bank transfer

**Why track?**
- See payment method breakdown pie on Overview
- Useful for reconciling with bank/card statements
- Understand payment behavior

### Category Limits

Set spending caps per category:
1. Go to **💰 Budget** → **💸 Expense Budget**
2. Scroll to "Category Spending Limits"
3. Pick category, set limit (e.g., "Food: ₹5,000/month")
4. See progress bar on Overview
5. Get warning if exceeded

### Investment Targets

Set monthly investment goals:
1. Go to **💰 Budget** → **📈 Investment Budget**
2. Add target (e.g., "Nifty 50: ₹10,000/month")
3. See progress vs actual below
4. Track if on track (green), halfway (yellow), or behind (red)

### Export & Backup

Export any month's data:
1. Go to **📜 History**
2. Select month
3. Click "⬇️ Export CSV"
4. File downloads (open in Excel)

### Custom Categories

Add personal categories:
1. Go to **⚙️ Settings** → **My Categories**
2. Type new category (e.g., "🎮 Gaming" or "🪧 Angel Investing")
3. Click "➕ Add"
4. Use in transactions

---

## 5. Admin Features (Family Mode)

### View All Family Data (If You're Admin)

**Prerequisites:**
- You're logged in as the admin user (e.g., "Shanky")
- App auth mode is "passcode"

**What you can see:**
- All family members' expenses
- All family members' investments
- Their budgets vs actual
- Entire transaction history

**Use cases:**
- Monitor if family is within budget
- See who spent most this month
- Identify spending patterns
- Ensure financial responsibility

### Access Admin Tab

1. Log in as admin (Shanky + passcode 1234)
2. An extra tab appears: **👑 Admin**
3. See family summary table
4. Click on member name → view their detail
5. See their expenses, investments, budget

---

## 6. Tips & Tricks

**💡 Log Expenses Immediately**
- Don't wait until evening — log instantly
- You'll remember payment method better
- Keeps running total accurate

**💡 Use Notes**
- "Lunch with client" vs just "Food"
- Notes help you analyze later
- Searchable in History tab

**💡 Set Realistic Budgets**
- Start with last month's average
- Adjust up/down based on income
- Revisit monthly

**💡 Review Weekly, Not Daily**
- Daily checking = obsessive
- Weekly review = healthy habit
- See patterns better

**💡 Use Category Limits for Problem Categories**
- If you overspend on dining, set limit
- Helps you stay accountable
- Visual progress bar is motivating

**💡 Investment Targets ≠ Savings**
- Savings = Budget - Spent
- Investment targets = specific categories you want to grow
- Set both for complete financial picture

---

## 7. FAQs

### Q: I forgot my passcode. How do I change it?
**A:** Change in secrets.toml (local dev) or Streamlit Cloud dashboard (production). Reload app.

### Q: Can I edit someone else's transactions?
**A:** No. Non-admin users see only their own data. Admin can see all but can't edit (by design).

### Q: What if I'm offline?
**A:** 
- **Cloud mode:** No access (needs internet)
- **Local mode:** Works offline, syncs when online again

### Q: Can I have recurring expenses?
**A:** Not yet. V4 planned feature. For now, log each one.

### Q: Where is my data stored?
**A:** 
- **Cloud mode:** Supabase PostgreSQL (Google Cloud, US)
- **Local mode:** data/finance_data.json on your computer

### Q: Can I delete my account?
**A:** 
- Contact admin to delete all family data
- Or export CSV and manage locally

### Q: Why two payment methods for same category?
**A:** Build profile of spending behavior. E.g., "I spend more on Credit Card for rewards, less Cash for discipline."

### Q: Can I add multiple users?
**A:** Yes, in passcode mode. Each enters their name + shared passcode. Admin sees all.

### Q: Is my data secure?
**A:**
- All data encrypted in transit (HTTPS)
- Supabase has backups
- No third-party access to your data
- Service account key never shared

### Q: Can I download all my data?
**A:** Yes. Export CSV from History tab for each month. Or access Supabase directly.

---

## Support

**Questions?** See DOCS.md for technical details.

**Bug?** Contact: Sheshank

---

**Made by Sheshank with ❤️**

Nexgen Fintrack — Your personal finance OS.
