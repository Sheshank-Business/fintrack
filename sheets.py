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

TRANSACTION_HEADERS = ["Username", "Date", "Category", "Amount", "Type", "Note"]
BUDGET_HEADERS = ["UserMonth", "Month", "Budget", "Username"]
CONFIG_HEADERS = ["Key", "Value"]
USERS_HEADERS  = ["Username", "Name", "PinHash"]


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
    username: str = "default",
) -> None:
    """Add a transaction row to the Transactions sheet."""
    ws = get_or_create_worksheet("Transactions", TRANSACTION_HEADERS)
    ws.append_row([username, date, category, float(amount), txn_type, note])


@st.cache_data(ttl=60)
def get_transactions(month: str | None = None, username: str = "default") -> pd.DataFrame:
    """Fetch transactions for a user, optionally filtered by month ('YYYY-MM')."""
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

    # Filter by user, hide Username column from consumers
    if "Username" in df.columns:
        df = df[df["Username"] == username]
        df = df.drop(columns=["Username"])

    if month:
        df = df[df["Date"].str.startswith(month)]

    return df.reset_index(drop=True)


def get_expenses(month: str | None = None, username: str = "default") -> pd.DataFrame:
    df = get_transactions(month, username)
    if df.empty: return df
    return df[df["Type"] == "Expense"].reset_index(drop=True)


def get_investments(month: str | None = None, username: str = "default") -> pd.DataFrame:
    df = get_transactions(month, username)
    if df.empty: return df
    return df[df["Type"] == "Investment"].reset_index(drop=True)


@st.cache_data(ttl=60)
def get_all_budgets(username: str = "default") -> dict:
    """Fetch ALL budget records for a user. Returns {month: amount}."""
    ws = get_or_create_worksheet("Budget", BUDGET_HEADERS)
    records = ws.get_all_records()
    result = {}
    for row in records:
        if str(row.get("Username", "default")) == username:
            try:
                result[str(row["Month"])] = float(row["Budget"])
            except (ValueError, TypeError, KeyError):
                pass
    return result


def get_budget(month: str, username: str = "default") -> float:
    return get_all_budgets(username).get(month, 0.0)


def set_budget(month: str, amount: float, username: str = "default") -> None:
    ws = get_or_create_worksheet("Budget", BUDGET_HEADERS)
    records = ws.get_all_records()
    usermonth = f"{username}::{month}"
    for i, row in enumerate(records, start=2):
        if str(row.get("Username")) == username and str(row.get("Month")) == month:
            ws.update_cell(i, 3, float(amount))
            get_all_budgets.clear()
            return
    ws.append_row([usermonth, month, float(amount), username])
    get_all_budgets.clear()


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


# ─── Category Limits (stored as JSON string in Config, per user) ─
import json as _json


def get_category_limits(username: str = "default") -> dict:
    """Get per-category budget limits for a user {category: amount}."""
    key = f"category_limits_json__{username}"
    raw = get_config(key, "{}")
    try:
        return _json.loads(raw)
    except Exception:
        return {}


def set_category_limit(category: str, amount: float, username: str = "default") -> None:
    """Set a budget limit for a specific category (per user)."""
    key = f"category_limits_json__{username}"
    limits = get_category_limits(username)
    limits[category] = float(amount)
    set_config(key, _json.dumps(limits))


def remove_category_limit(category: str, username: str = "default") -> None:
    """Remove a category limit (per user)."""
    key = f"category_limits_json__{username}"
    limits = get_category_limits(username)
    limits.pop(category, None)
    set_config(key, _json.dumps(limits))


# ─── Users ───────────────────────────────────────────────────────
def get_all_users() -> list:
    """Return list of all user dicts {username, name, pin_hash}."""
    ws = get_or_create_worksheet("Users", USERS_HEADERS)
    records = ws.get_all_records()
    result = []
    for row in records:
        if row.get("Username"):
            result.append({
                "username": str(row["Username"]),
                "name": str(row.get("Name", row["Username"])),
                "pin_hash": str(row.get("PinHash", "")),
            })
    return result


def create_user(username: str, name: str, pin_hash: str) -> None:
    """Create a new user profile in the Users sheet."""
    ws = get_or_create_worksheet("Users", USERS_HEADERS)
    ws.append_row([username, name, pin_hash])


# ─── Cleanup (no-op stub for cloud mode) ─────────────────────────
def cleanup_old_data(username: str = "default") -> int:
    """In cloud mode, cleanup is a no-op. Returns 0."""
    return 0


# ─── Stub for direct data access (local-mode compat) ────────────
def _load_data() -> dict:
    """Compatibility stub — not used in Sheets mode but prevents AttributeError."""
    return {"transactions": [], "budgets": {}, "category_limits": {}, "config": {}}

