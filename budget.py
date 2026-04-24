"""
budget.py — Budget calculation engine for Personal Finance OS
"""

import pandas as pd


def calculate_remaining(budget: float, expenses_df: pd.DataFrame) -> float:
    """Calculate remaining budget after expenses.

    Args:
        budget: Total monthly budget amount.
        expenses_df: DataFrame with an 'Amount' column (expenses only).

    Returns:
        Remaining budget (can be negative if overspent).
    """
    if expenses_df.empty or budget <= 0:
        return budget
    total_spent = expenses_df["Amount"].sum()
    return budget - total_spent


def total_spent(expenses_df: pd.DataFrame) -> float:
    """Sum of all expenses."""
    if expenses_df.empty:
        return 0.0
    return float(expenses_df["Amount"].sum())


def total_invested(investments_df: pd.DataFrame) -> float:
    """Sum of all investments."""
    if investments_df.empty:
        return 0.0
    return float(investments_df["Amount"].sum())


def check_alert(remaining: float, budget: float, threshold: float = 0.20) -> str:
    """Check budget alert status.

    Returns:
        'critical' — overspent (remaining < 0)
        'warning'  — remaining < threshold * budget
        'ok'       — healthy
    """
    if budget <= 0:
        return "ok"
    if remaining < 0:
        return "critical"
    if remaining < threshold * budget:
        return "warning"
    return "ok"


def category_breakdown(expenses_df: pd.DataFrame) -> pd.DataFrame:
    """Get spending grouped by category, sorted descending."""
    if expenses_df.empty:
        return pd.DataFrame(columns=["Category", "Amount"])
    breakdown = (
        expenses_df.groupby("Category")["Amount"]
        .sum()
        .reset_index()
        .sort_values("Amount", ascending=False)
    )
    return breakdown


def daily_spending(expenses_df: pd.DataFrame) -> pd.DataFrame:
    """Get daily expense totals."""
    if expenses_df.empty:
        return pd.DataFrame(columns=["Date", "Amount"])
    daily = (
        expenses_df.groupby("Date")["Amount"]
        .sum()
        .reset_index()
        .sort_values("Date")
    )
    return daily
