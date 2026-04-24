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
) -> None:
    """Add a transaction."""
    data = _load_data()
    data["transactions"].append({
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


def get_transactions(month: str | None = None) -> pd.DataFrame:
    """Fetch transactions, optionally filtered by month ('YYYY-MM')."""
    data = _load_data()
    txns = data.get("transactions", [])

    if not txns:
        return pd.DataFrame(columns=["Date", "Category", "Amount", "Type", "Note"])

    df = pd.DataFrame(txns)
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)

    # Drop internal fields
    if "Timestamp" in df.columns:
        df = df.drop(columns=["Timestamp"])

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


# ─── Budget ──────────────────────────────────────────────────
def set_budget(month: str, amount: float) -> None:
    """Set or update the budget for a given month."""
    data = _load_data()
    data["budgets"][month] = float(amount)
    _save_data(data)


def get_budget(month: str) -> float:
    """Get budget for a given month. Returns 0 if not set."""
    data = _load_data()
    return float(data.get("budgets", {}).get(month, 0))


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


# ─── Category Limits ─────────────────────────────────────────
def get_category_limits() -> dict:
    """Get per-category budget limits {category: amount}."""
    data = _load_data()
    return data.get("category_limits", {})


def set_category_limit(category: str, amount: float) -> None:
    """Set a budget limit for a specific category."""
    data = _load_data()
    if "category_limits" not in data:
        data["category_limits"] = {}
    data["category_limits"][category] = float(amount)
    _save_data(data)


def remove_category_limit(category: str) -> None:
    """Remove a category limit."""
    data = _load_data()
    data.get("category_limits", {}).pop(category, None)
    _save_data(data)
