"""
supabase_db.py - Supabase-backed data layer for Fintrack

Implements the same function contract as database.py/sheets.py so app.py
can switch backends without changing business logic.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st
from supabase import create_client


@st.cache_resource(ttl=300)
def get_client():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


def _month_bounds(month: str) -> tuple[str, str]:
    year, month_num = [int(x) for x in month.split("-")]
    last_day = monthrange(year, month_num)[1]
    return (f"{month}-01", f"{month}-{last_day:02d}")


def _empty_txn_df(with_index: bool = False) -> pd.DataFrame:
    cols = ["Date", "Category", "Amount", "Type", "Note"]
    if with_index:
        cols = ["_idx"] + cols
    return pd.DataFrame(columns=cols)


def _safe_table_select(table: str, query_fn):
    try:
        return query_fn().execute()
    except Exception:
        return None


def add_transaction(
    date: str,
    category: str,
    amount: float,
    txn_type: str,
    note: str = "",
    username: str = "default",
) -> None:
    db = get_client()
    db.table("transactions").insert(
        {
            "user_id": username,
            "date": str(date),
            "type": str(txn_type),
            "category": str(category),
            "amount": float(amount),
            "note": str(note or ""),
        }
    ).execute()


def get_transactions(month: str | None = None, username: str = "default", is_admin: bool = False) -> pd.DataFrame:
    db = get_client()

    query = db.table("transactions").select("id,date,category,amount,type,note,user_id")
    if not is_admin:
        query = query.eq("user_id", username)
    if month:
        start, end = _month_bounds(month)
        query = query.gte("date", start).lte("date", end)

    res = _safe_table_select("transactions", lambda: query.order("date", desc=False))
    rows = (res.data if res and res.data else [])
    if not rows:
        cols = ["Date", "Category", "Amount", "Type", "Note"]
        if is_admin:
            cols = ["User", "Date", "Category", "Amount", "Type", "Note"]
        return pd.DataFrame(columns=cols)

    out = pd.DataFrame(rows)
    rename_dict = {
        "date": "Date",
        "category": "Category",
        "amount": "Amount",
        "type": "Type",
        "note": "Note",
        "user_id": "User",
    }
    out = out.rename(columns=rename_dict)
    out["Amount"] = pd.to_numeric(out.get("Amount", 0), errors="coerce").fillna(0)
    for col in ["Date", "Category", "Type", "Note"]:
        if col not in out.columns:
            out[col] = ""
    
    if is_admin:
        return out[["User", "Date", "Category", "Amount", "Type", "Note"]].reset_index(drop=True)
    return out[["Date", "Category", "Amount", "Type", "Note"]].reset_index(drop=True)


def get_transactions_with_index(month: str | None = None, username: str = "default", is_admin: bool = False) -> pd.DataFrame:
    db = get_client()

    query = db.table("transactions").select("id,date,category,amount,type,note,user_id")
    if not is_admin:
        query = query.eq("user_id", username)
    if month:
        start, end = _month_bounds(month)
        query = query.gte("date", start).lte("date", end)

    res = _safe_table_select("transactions", lambda: query.order("date", desc=False))
    rows = (res.data if res and res.data else [])
    if not rows:
        cols = ["_idx", "Date", "Category", "Amount", "Type", "Note"]
        if is_admin:
            cols = ["_idx", "User", "Date", "Category", "Amount", "Type", "Note"]
        return pd.DataFrame(columns=cols)

    out = pd.DataFrame(rows)
    out = out.rename(
        columns={
            "id": "_idx",
            "date": "Date",
            "category": "Category",
            "amount": "Amount",
            "type": "Type",
            "note": "Note",
            "user_id": "User",
        }
    )
    out["Amount"] = pd.to_numeric(out.get("Amount", 0), errors="coerce").fillna(0)
    for col in ["Date", "Category", "Type", "Note"]:, is_admin: bool = False) -> pd.DataFrame:
    df = get_transactions(month, username, is_admin)
    if df.empty:
        return df
    return df[df["Type"].str.lower() == "expense"].reset_index(drop=True)


def get_investments(month: str | None = None, username: str = "default", is_admin: bool = False) -> pd.DataFrame:
    df = get_transactions(month, username, is_admin
def get_expenses(month: str | None = None, username: str = "default") -> pd.DataFrame:
    df = get_transactions(month, username)
    if df.empty:
        return df
    return df[df["Type"].str.lower() == "expense"].reset_index(drop=True)


def get_investments(month: str | None = None, username: str = "default") -> pd.DataFrame:
    df = get_transactions(month, username)
    if df.empty:
        return df
    return df[df["Type"].str.lower() == "investment"].reset_index(drop=True)


def delete_transaction(index: str, username: str = "default") -> bool:
    db = get_client()
    try:
        check = (
            db.table("transactions")
            .select("id")
            .eq("id", str(index))
            .eq("user_id", username)
            .limit(1)
            .execute()
        )
        if not check.data:
            return False
        db.table("transactions").delete().eq("id", str(index)).eq("user_id", username).execute()
        return True
    except Exception:
        return False


def update_transaction(
    index: str,
    date: str,
    category: str,
    amount: float,
    txn_type: str,
    note: str = "",
    username: str = "default",
) -> bool:
    db = get_client()
    try:
        check = (
            db.table("transactions")
            .select("id")
            .eq("id", str(index))
            .eq("user_id", username)
            .limit(1)
            .execute()
        )
        if not check.data:
            return False
        db.table("transactions").update(
            {
                "date": str(date),
                "category": str(category),
                "amount": float(amount),
                "type": str(txn_type),
                "note": str(note or ""),
            }
        ).eq("id", str(index)).eq("user_id", username).execute()
        return True
    except Exception:
        return False


def set_budget(month: str, amount: float, username: str = "default") -> None:
    db = get_client()
    db.table("budgets").upsert(
        {
            "user_id": username,
            "month": month,
            "amount": float(amount),
        },
        on_conflict="user_id,month",
    ).execute()


def get_budget(month: str, username: str = "default") -> float:
    db = get_client()
    try:
        res = (
            db.table("budgets")
            .select("amount")
            .eq("user_id", username)
            .eq("month", month)
            .limit(1)
            .execute()
        )
        if res.data:
            return float(res.data[0].get("amount", 0) or 0)
    except Exception:
        pass
    return 0.0


def get_all_budgets(username: str = "default") -> dict:
    db = get_client()
    out: dict[str, float] = {}
    try:
        res = db.table("budgets").select("month,amount").eq("user_id", username).execute()
        for row in (res.data or []):
            month = str(row.get("month", ""))
            if month:
                out[month] = float(row.get("amount", 0) or 0)
    except Exception:
        pass
    return out


def get_config(key: str, default: str = "") -> str:
    db = get_client()
    try:
        res = db.table("configs").select("value").eq("key", key).limit(1).execute()
        if res.data:
            return str(res.data[0].get("value", default))
    except Exception:
        pass
    return str(default)


def set_config(key: str, value: str) -> None:
    db = get_client()
    try:
        db.table("configs").upsert({"key": key, "value": str(value)}, on_conflict="key").execute()
    except Exception:
        # Graceful no-op when optional table is not configured yet.
        return


def get_category_limits(username: str = "default") -> dict:
    db = get_client()
    out: dict[str, float] = {}
    try:
        res = (
            db.table("category_limits")
            .select("category,amount")
            .eq("user_id", username)
            .execute()
        )
        for row in (res.data or []):
            out[str(row.get("category", ""))] = float(row.get("amount", 0) or 0)
    except Exception:
        pass
    return out


def set_category_limit(category: str, amount: float, username: str = "default") -> None:
    db = get_client()
    try:
        db.table("category_limits").upsert(
            {
                "user_id": username,
                "category": str(category),
                "amount": float(amount),
            },
            on_conflict="user_id,category",
        ).execute()
    except Exception:
        return


def remove_category_limit(category: str, username: str = "default") -> None:
    db = get_client()
    try:
        db.table("category_limits").delete().eq("user_id", username).eq("category", str(category)).execute()
    except Exception:
        return


def cleanup_old_data(username: str = "default") -> int:
    cutoff = (date.today() - timedelta(days=365)).isoformat()
    db = get_client()
    try:
        res = (
            db.table("transactions")
            .delete()
            .eq("user_id", username)
            .lt("date", cutoff)
            .execute()
        )
        return len(res.data or [])
    except Exception:
        return 0


# ═══════════════════════════════════════════════════════════════
# ADMIN FUNCTIONS — View all family members' data
# ═══════════════════════════════════════════════════════════════

def get_all_users_list() -> list[str]:
    """Get list of all unique user_ids in the system."""
    db = get_client()
    try:
        res = db.table("transactions").select("user_id").execute()
        users = list(set([row.get("user_id") for row in (res.data or []) if row.get("user_id")]))
        return sorted(users)
    except Exception:
        return []


def get_all_transactions_admin(month: str | None = None) -> pd.DataFrame:
    """Get ALL transactions across all users (admin view)."""
    df = get_transactions(month=month, username="default", is_admin=True)
    return df


def get_all_budgets_admin() -> dict:
    """Get all budgets for all users. Returns {user: {month: amount}}."""
    db = get_client()
    out: dict[str, dict[str, float]] = {}
    try:
        res = db.table("budgets").select("user_id,month,amount").execute()
        for row in (res.data or []):
            user = str(row.get("user_id", ""))
            month = str(row.get("month", ""))
            amount = float(row.get("amount", 0) or 0)
            if user and month:
                if user not in out:
                    out[user] = {}
                out[user][month] = amount
    except Exception:
        pass
    return out


def get_user_total_spent(username: str) -> float:
    """Total amount spent (all expenses) by a user."""
    df = get_expenses(username=username)
    if df.empty:
        return 0.0
    return float(df["Amount"].sum())


def get_user_total_invested(username: str) -> float:
    """Total amount invested (all investments) by a user."""
    df = get_investments(username=username)
    if df.empty:
        return 0.0
    return float(df["Amount"].sum())


def get_all_users_summary() -> pd.DataFrame:
    """Get all users' summary - admin view."""
    users = get_all_users_list()
    current_month = date.today().strftime("%Y-%m")
    
    rows = []
    for user in users:
        spent = get_user_total_spent(user)
        invested = get_user_total_invested(user)
        budget = get_budget(current_month, user)
        rows.append({
            "Member": user,
            "Total Spent": float(spent),
            "Total Invested": float(invested),
            f"Budget ({current_month})": float(budget),
        })
    
    if not rows:
        return pd.DataFrame()
    
    df = pd.DataFrame(rows)
    for col in ["Total Spent", "Total Invested", f"Budget ({current_month})"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def get_all_users() -> list:
    # No profile table needed when using Google OAuth.
    return []


def create_user(username: str, name: str, pin_hash: str) -> None:
    # No-op for compatibility with legacy auth module.
    return


def _load_data() -> dict:
    # Compatibility stub used by older app paths.
    return {"transactions": [], "budgets": {}, "category_limits": {}, "config": {}}
