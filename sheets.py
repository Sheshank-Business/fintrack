"""
sheets.py — Google Sheets data layer for Personal Finance OS

Handles all CRUD operations against the Google Sheet backend.
Uses Streamlit secrets for credentials.
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime


# ─── Constants ───────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TRANSACTION_HEADERS = ["Date", "Category", "Amount", "Type", "Note"]
BUDGET_HEADERS = ["Month", "Budget"]
CONFIG_HEADERS = ["Key", "Value"]


# ─── Connection ──────────────────────────────────────────────────
@st.cache_resource(ttl=300)
def get_client() -> gspread.Client:
    """Create and return an authenticated gspread client."""
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def get_spreadsheet() -> gspread.Spreadsheet:
    """Get the main spreadsheet with friendly error handling."""
    client = get_client()
    sheet_id = st.secrets["sheets"]["spreadsheet_id"]
    try:
        return client.open_by_key(sheet_id)
    except gspread.exceptions.APIError:
        st.error(
            "### 🔑 Google Sheet Access Denied\n\n"
            "The app cannot open your Google Sheet. **You need to share it** with the service account.\n\n"
            "**Do this now:**\n"
            "1. Open your Google Sheet\n"
            "2. Click **Share** (top right)\n"
            "3. Add this email as **Editor**:\n\n"
            "```\nfinance-os@nexgen-fintrack.iam.gserviceaccount.com\n```\n\n"
            "4. Uncheck 'Notify people' → Click **Share**\n\n"
            "Then refresh this page."
        )
        st.stop()
    except Exception as e:
        st.error(
            f"### ❌ Cannot open Google Sheet\n\n"
            f"Check that your Sheet ID in secrets is correct.\n\n"
            f"Error: `{type(e).__name__}`"
        )
        st.stop()


def get_or_create_worksheet(
    name: str, headers: list[str]
) -> gspread.Worksheet:
    """Get a worksheet by name, creating it with headers if missing."""
    spreadsheet = get_spreadsheet()
    try:
        ws = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.append_row(headers)
    return ws



# ─── Transactions ────────────────────────────────────────────────
def add_transaction(
    date: str,
    category: str,
    amount: float,
    txn_type: str,
    note: str = "",
) -> None:
    """Add a transaction row to the Transactions sheet."""
    ws = get_or_create_worksheet("Transactions", TRANSACTION_HEADERS)
    ws.append_row([date, category, float(amount), txn_type, note])


def get_transactions(month: str | None = None) -> pd.DataFrame:
    """Fetch transactions, optionally filtered by month ('YYYY-MM')."""
    try:
        ws = get_or_create_worksheet("Transactions", TRANSACTION_HEADERS)
        records = ws.get_all_records()
    except gspread.exceptions.APIError as e:
        import streamlit as _st
        _st.error(
            "🔑 **Google Sheets Access Error**\n\n"
            "The app cannot access your Google Sheet. Please make sure you have shared "
            "the sheet with the service account:\n\n"
            f"`finance-os@nexgen-fintrack.iam.gserviceaccount.com`\n\n"
            "**Steps:** Open your Google Sheet → Share → Add above email as Editor → Share"
        )
        _st.stop()
    except Exception as e:
        import streamlit as _st
        _st.error(f"❌ Database error: {e}")
        _st.stop()

    if not records:
        return pd.DataFrame(columns=TRANSACTION_HEADERS)

    df = pd.DataFrame(records)
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    if month:
        df = df[df["Date"].str.startswith(month)]

    return df.reset_index(drop=True)


def get_expenses(month: str | None = None) -> pd.DataFrame:
    """Get only Expense-type transactions."""
    df = get_transactions(month)
    if df.empty:
        return df
    return df[df["Type"] == "Expense"].reset_index(drop=True)


def get_investments(month: str | None = None) -> pd.DataFrame:
    """Get only Investment-type transactions."""
    df = get_transactions(month)
    if df.empty:
        return df
    return df[df["Type"] == "Investment"].reset_index(drop=True)


# ─── Budget ──────────────────────────────────────────────────────
def set_budget(month: str, amount: float) -> None:
    """Set or update the budget for a given month."""
    ws = get_or_create_worksheet("Budget", BUDGET_HEADERS)
    records = ws.get_all_records()

    # Check if month already exists → update
    for i, row in enumerate(records):
        if row.get("Month") == month:
            ws.update_cell(i + 2, 2, float(amount))  # +2 for header + 0-index
            return

    # Otherwise append
    ws.append_row([month, float(amount)])


def get_budget(month: str) -> float:
    """Get budget for a given month. Returns 0 if not set."""
    ws = get_or_create_worksheet("Budget", BUDGET_HEADERS)
    records = ws.get_all_records()

    for row in records:
        if row.get("Month") == month:
            try:
                return float(row["Budget"])
            except (ValueError, TypeError):
                return 0.0
    return 0.0


# ─── Config ──────────────────────────────────────────────────────
def get_config(key: str, default: str = "") -> str:
    """Read a config value by key."""
    ws = get_or_create_worksheet("Config", CONFIG_HEADERS)
    records = ws.get_all_records()

    for row in records:
        if row.get("Key") == key:
            return str(row.get("Value", default))
    return default


def set_config(key: str, value: str) -> None:
    """Set a config value (inserts or updates)."""
    ws = get_or_create_worksheet("Config", CONFIG_HEADERS)
    records = ws.get_all_records()

    for i, row in enumerate(records):
        if row.get("Key") == key:
            ws.update_cell(i + 2, 2, value)
            return

    ws.append_row([key, value])


# ─── Delete / Update Transactions ───────────────────────────────
def delete_transaction(index: int) -> bool:
    """Delete a transaction row by its 0-based index (excludes header)."""
    ws = get_or_create_worksheet("Transactions", TRANSACTION_HEADERS)
    try:
        ws.delete_rows(index + 2)  # +2: 1-based + header row
        return True
    except Exception:
        return False


def update_transaction(
    index: int,
    date: str,
    category: str,
    amount: float,
    txn_type: str,
    note: str = "",
) -> bool:
    """Update a transaction row by its 0-based index."""
    ws = get_or_create_worksheet("Transactions", TRANSACTION_HEADERS)
    try:
        row_num = index + 2  # +2: 1-based + header
        ws.update(f"A{row_num}:E{row_num}",
                  [[date, category, float(amount), txn_type, note]])
        return True
    except Exception:
        return False


def get_transactions_with_index(month: str | None = None) -> pd.DataFrame:
    """Like get_transactions but keeps a '_idx' column = 0-based sheet row index."""
    ws = get_or_create_worksheet("Transactions", TRANSACTION_HEADERS)
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame(columns=["_idx", "Date", "Category", "Amount", "Type", "Note"])
    df = pd.DataFrame(records)
    df.insert(0, "_idx", range(len(df)))
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    if month:
        df = df[df["Date"].str.startswith(month)]
    return df.reset_index(drop=True)


# ─── Category Limits (stored as JSON string in Config) ───────────
import json as _json

_CAT_LIMITS_KEY = "category_limits_json"


def get_category_limits() -> dict:
    """Get per-category budget limits {category: amount}."""
    raw = get_config(_CAT_LIMITS_KEY, "{}")
    try:
        return _json.loads(raw)
    except Exception:
        return {}


def set_category_limit(category: str, amount: float) -> None:
    """Set a budget limit for a specific category."""
    limits = get_category_limits()
    limits[category] = float(amount)
    set_config(_CAT_LIMITS_KEY, _json.dumps(limits))


def remove_category_limit(category: str) -> None:
    """Remove a category limit."""
    limits = get_category_limits()
    limits.pop(category, None)
    set_config(_CAT_LIMITS_KEY, _json.dumps(limits))


# ─── Stub for direct data access (local-mode compat) ────────────
def _load_data() -> dict:
    """Compatibility stub — not used in Sheets mode but prevents AttributeError."""
    return {"transactions": [], "budgets": {}, "category_limits": {}, "config": {}}

