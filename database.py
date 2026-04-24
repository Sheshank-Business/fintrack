"""
database.py — Local JSON-based data layer for Personal Finance OS

Zero-cost, zero-setup. All data stored in a local data.json file.
No Google Cloud, no API keys, no signups needed.
"""

import json
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

# ─── Data File ───────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"
DATA_FILE = DATA_DIR / "finance_data.json"


def _ensure_data_dir():
    """Create data directory if it doesn't exist."""
    DATA_DIR.mkdir(exist_ok=True)


def _load_data() -> dict:
    """Load all data from the JSON file."""
    _ensure_data_dir()
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return _default_data()
    return _default_data()


def _save_data(data: dict) -> None:
    """Save all data to the JSON file."""
    _ensure_data_dir()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _default_data() -> dict:
    """Return default empty data structure."""
    return {
        "transactions": [],
        "budgets": {},
        "category_limits": {},
        "users": [],
        "config": {
            "warning_threshold": 20,
        },
    }


# ─── Transactions ────────────────────────────────────────────
def add_transaction(
    date: str,
    category: str,
    amount: float,
    txn_type: str,
    note: str = "",
    username: str = "default",
) -> None:
    """Add a transaction."""
    data = _load_data()
    data["transactions"].append({
        "Username": username,
        "Date": date,
        "Category": category,
        "Amount": float(amount),
        "Type": txn_type,
        "Note": note,
        "Timestamp": datetime.now().isoformat(),
    })
    _save_data(data)


def delete_transaction(index: int) -> bool:
    """Delete a transaction by its index in the full list. Returns True if deleted."""
    data = _load_data()
    if 0 <= index < len(data["transactions"]):
        data["transactions"].pop(index)
        _save_data(data)
        return True
    return False


def update_transaction(
    index: int,
    date: str,
    category: str,
    amount: float,
    txn_type: str,
    note: str = "",
) -> bool:
    """Update a transaction by its index. Returns True if updated."""
    data = _load_data()
    if 0 <= index < len(data["transactions"]):
        data["transactions"][index].update({
            "Date": date,
            "Category": category,
            "Amount": float(amount),
            "Type": txn_type,
            "Note": note,
            "Timestamp": datetime.now().isoformat(),
        })
        _save_data(data)
        return True
    return False


def get_transactions_with_index(month: str | None = None) -> pd.DataFrame:
    """Like get_transactions but keeps a '_idx' column = original JSON index."""
    data = _load_data()
    txns = data.get("transactions", [])
    if not txns:
        return pd.DataFrame(columns=["_idx", "Date", "Category", "Amount", "Type", "Note"])
    df = pd.DataFrame(txns)
    df.insert(0, "_idx", range(len(df)))
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    if "Timestamp" in df.columns:
        df = df.drop(columns=["Timestamp"])
    if month:
        df = df[df["Date"].str.startswith(month)]
    return df.reset_index(drop=True)


def get_transactions(month: str | None = None, username: str = "default") -> pd.DataFrame:
    """Fetch transactions for a user, optionally filtered by month."""
    data = _load_data()
    txns = data.get("transactions", [])

    if not txns:
        return pd.DataFrame(columns=["Date", "Category", "Amount", "Type", "Note"])

    df = pd.DataFrame(txns)
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    # Filter by user
    if "Username" in df.columns:
        df = df[df["Username"] == username]
    if "Timestamp" in df.columns:
        df = df.drop(columns=["Timestamp"])
    if "Username" in df.columns:
        df = df.drop(columns=["Username"])
    if month:
        df = df[df["Date"].str.startswith(month)]

    return df.reset_index(drop=True)


def get_expenses(month: str | None = None, username: str = "default") -> pd.DataFrame:
    """Get only Expense-type transactions for a user."""
    df = get_transactions(month, username)
    if df.empty:
        return df
    return df[df["Type"] == "Expense"].reset_index(drop=True)


def get_investments(month: str | None = None, username: str = "default") -> pd.DataFrame:
    """Get only Investment-type transactions for a user."""
    df = get_transactions(month, username)
    if df.empty:
        return df
    return df[df["Type"] == "Investment"].reset_index(drop=True)


# ─── Budget ──────────────────────────────────────────────────
def set_budget(month: str, amount: float, username: str = "default") -> None:
    """Set or update the budget for a user+month."""
    data = _load_data()
    key = f"{username}::{month}"
    data["budgets"][key] = float(amount)
    _save_data(data)


def get_budget(month: str, username: str = "default") -> float:
    """Get budget for a user+month."""
    data = _load_data()
    key = f"{username}::{month}"
    # Try new keyed format first, fall back to old
    return float(data.get("budgets", {}).get(key, data.get("budgets", {}).get(month, 0)))


def get_all_budgets(username: str = "default") -> dict:
    """Get all budgets for a user as {month: amount}."""
    data = _load_data()
    prefix = f"{username}::"
    result = {}
    for k, v in data.get("budgets", {}).items():
        if k.startswith(prefix):
            month = k[len(prefix):]
            result[month] = float(v)
    return result


# ─── Config ──────────────────────────────────────────────────
def get_config(key: str, default: str = "") -> str:
    """Read a config value by key."""
    data = _load_data()
    return str(data.get("config", {}).get(key, default))


def set_config(key: str, value: str) -> None:
    """Set a config value."""
    data = _load_data()
    if "config" not in data:
        data["config"] = {}
    data["config"][key] = value
    _save_data(data)


# ─── Users ───────────────────────────────────────────────────
def get_all_users() -> list:
    """Return list of all user dicts {username, name, pin_hash}."""
    data = _load_data()
    return data.get("users", [])


def create_user(username: str, name: str, pin_hash: str) -> None:
    """Create a new user profile."""
    data = _load_data()
    if "users" not in data:
        data["users"] = []
    data["users"].append({
        "username": username,
        "name": name,
        "pin_hash": pin_hash,
    })
    _save_data(data)


# ─── Auto-cleanup: delete data older than 1 year ─────────────
def cleanup_old_data(username: str = "default") -> int:
    """Delete transactions older than 365 days for this user. Returns count deleted."""
    from datetime import date, timedelta
    cutoff = (date.today() - timedelta(days=365)).strftime("%Y-%m-%d")
    data = _load_data()
    before = len(data["transactions"])
    data["transactions"] = [
        t for t in data["transactions"]
        if t.get("Username", "default") != username or t.get("Date", "9999") >= cutoff
    ]
    removed = before - len(data["transactions"])
    if removed > 0:
        _save_data(data)
    return removed


# ─── Category Limits (per user) ──────────────────────────────
def get_category_limits(username: str = "default") -> dict:
    data = _load_data()
    key = f"cat_limits_{username}"
    return data.get("category_limits", {}).get(key, {})


def set_category_limit(category: str, amount: float, username: str = "default") -> None:
    data = _load_data()
    if "category_limits" not in data:
        data["category_limits"] = {}
    key = f"cat_limits_{username}"
    if key not in data["category_limits"]:
        data["category_limits"][key] = {}
    data["category_limits"][key][category] = float(amount)
    _save_data(data)


def remove_category_limit(category: str, username: str = "default") -> None:
    data = _load_data()
    key = f"cat_limits_{username}"
    data.get("category_limits", {}).get(key, {}).pop(category, None)
    _save_data(data)

