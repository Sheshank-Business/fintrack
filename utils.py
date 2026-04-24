"""
utils.py — Shared utilities for Fintrack
"""

from datetime import datetime

# ─── Default Categories (used when no custom ones are saved) ─────
DEFAULT_EXPENSE_CATEGORIES = [
    "🍔 Food",
    "🚗 Transport",
    "🛍️ Shopping",
    "📱 Bills & Utilities",
    "🎬 Entertainment",
    "🏥 Health",
    "📚 Education",
    "🏠 Rent",
    "💼 Business",
    "✈️ Travel",
    "🎁 Gifts",
    "🔧 Maintenance",
    "🐾 Pets",
    "💇 Personal Care",
    "🍺 Dining Out",
    "📦 Other",
]

DEFAULT_INVESTMENT_CATEGORIES = [
    "📈 Stocks",
    "🏦 Mutual Funds",
    "🪙 Crypto",
    "🏠 Real Estate",
    "💰 Fixed Deposit",
    "📦 PPF / NPS",
    "💎 Gold",
    "🌐 International",
    "🎯 Other",
]

# Kept for backward compat (app.py imports these by name)
EXPENSE_CATEGORIES = DEFAULT_EXPENSE_CATEGORIES
INVESTMENT_CATEGORIES = DEFAULT_INVESTMENT_CATEGORIES

MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

CONFIG_KEY_EXPENSE_CATS  = "custom_expense_categories"
CONFIG_KEY_INVEST_CATS   = "custom_investment_categories"


# ─── Dynamic Category Loader ─────────────────────────────────────
def get_expense_categories(db=None) -> list[str]:
    """
    Return expense categories.
    If db is provided, loads user-customised list from config.
    Falls back to defaults if nothing saved.
    """
    if db is None:
        return DEFAULT_EXPENSE_CATEGORIES
    try:
        import json
        raw = db.get_config(CONFIG_KEY_EXPENSE_CATS, "")
        if raw:
            cats = json.loads(raw)
            if cats:
                return cats
    except Exception:
        pass
    return DEFAULT_EXPENSE_CATEGORIES


def get_investment_categories(db=None) -> list[str]:
    """Return investment categories (custom or default)."""
    if db is None:
        return DEFAULT_INVESTMENT_CATEGORIES
    try:
        import json
        raw = db.get_config(CONFIG_KEY_INVEST_CATS, "")
        if raw:
            cats = json.loads(raw)
            if cats:
                return cats
    except Exception:
        pass
    return DEFAULT_INVESTMENT_CATEGORIES


def save_expense_categories(db, cats: list[str]) -> None:
    import json
    db.set_config(CONFIG_KEY_EXPENSE_CATS, json.dumps(cats))


def save_investment_categories(db, cats: list[str]) -> None:
    import json
    db.set_config(CONFIG_KEY_INVEST_CATS, json.dumps(cats))


# ─── Helpers ─────────────────────────────────────────────────────
def format_inr(amount: float) -> str:
    """Format a number as Indian Rupees with commas."""
    if amount < 0:
        return f"-₹{abs(amount):,.0f}"
    return f"₹{amount:,.0f}"


def get_current_month_key() -> str:
    return datetime.now().strftime("%Y-%m")


def get_month_label(month_key: str) -> str:
    try:
        return datetime.strptime(month_key, "%Y-%m").strftime("%B %Y")
    except ValueError:
        return month_key


def get_month_options(n: int = 6) -> list[str]:
    now = datetime.now()
    keys = []
    for i in range(n):
        month = now.month - i
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        keys.append(f"{year}-{month:02d}")
    return keys


def parse_date(date_str: str) -> datetime | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None
