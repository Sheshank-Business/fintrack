"""
app.py — Nexgen Fintrack V3
Simple, mobile-first personal finance tracker.
New UX: Add (front) | Overview | Analytics | History | Budget | Admin | Settings
Auth: Name-only login with optional "Remember Me"
Sidebar: Fully collapsible with hamburger menu ☰
Made by Sheshank with ❤️
"""

import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os
import io
import re

from utils import (
    EXPENSE_CATEGORIES,
    INVESTMENT_CATEGORIES,
    format_inr,
    get_month_label,
    get_month_options,
    get_expense_categories,
    get_investment_categories,
    save_expense_categories,
    save_investment_categories,
    DEFAULT_EXPENSE_CATEGORIES,
    DEFAULT_INVESTMENT_CATEGORIES,
)
from budget import (
    calculate_remaining,
    total_spent,
    total_invested,
    check_alert,
    category_breakdown,
    daily_spending,
)

# ─── Auto-detect database mode ────────────────────────────────
try:
    _ = st.secrets["supabase"]["url"]
    _ = st.secrets["supabase"]["key"]
    import supabase_db as db
    DB_MODE = "☁️ Cloud (Supabase)"
except (FileNotFoundError, KeyError, ModuleNotFoundError, Exception):
    import database as db
    DB_MODE = "💾 Local (JSON)"

# ═══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="💰 Nexgen Fintrack",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Load Custom CSS ──────────────────────────────────────────
css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
try:
    with open(css_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# ─── Auth ──────────────────────────────────────────────────────
def _get_auth_mode() -> str:
    try:
        mode = str(st.secrets.get("app_auth", {}).get("mode", "google")).strip().lower()
        if mode in {"google", "passcode", "name_only"}:
            return mode
    except Exception:
        pass
    return "google"


def _normalize_user_id(name: str) -> str:
    uid = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return uid or "guest"


def _is_logged_in() -> bool:
    try:
        return bool(st.experimental_user.is_logged_in)
    except Exception:
        try:
            return bool(st.user.is_logged_in)
        except Exception:
            return False


def _get_user_email() -> str:
    try:
        return str(st.experimental_user.email)
    except Exception:
        try:
            return str(st.user.email)
        except Exception:
            return ""


def _family_auth_login(mode: str) -> tuple[str, str]:
    if st.session_state.get("ft_simple_user_id"):
        return (
            st.session_state.get("ft_simple_user_id", "default"),
            st.session_state.get("ft_simple_user_name", "default"),
        )
    st.title("💸 Nexgen Fintrack")
    st.write("Welcome to your personal finance dashboard")
    
    with st.form("family_login_form", clear_on_submit=False):
        display_name = st.text_input("Enter your name", placeholder="e.g. Sheshank")
        col1, col2 = st.columns(2)
        with col1:
            submit_login = st.form_submit_button("✅ Continue", use_container_width=True)
        with col2:
            remember = st.checkbox("Remember me", value=True)
    
    if submit_login:
        if not display_name.strip():
            st.error("Please enter your name.")
        else:
            st.session_state["ft_simple_user_name"] = display_name.strip()
            st.session_state["ft_simple_user_id"] = _normalize_user_id(display_name)
            
            # Save to localStorage if Remember Me is checked
            if remember:
                st.markdown(f"""
                <script>
                localStorage.setItem('fintrack_user_name', '{display_name.strip()}');
                </script>
                """, unsafe_allow_html=True)
            
            st.rerun()
    st.stop()


AUTH_MODE = _get_auth_mode()

if DB_MODE.startswith("☁️"):
    if AUTH_MODE == "google":
        if not _is_logged_in():
            st.title("💸 Nexgen Fintrack")
            st.write("Sign in to access your personal finance dashboard.")
            st.login("google")
            st.stop()
        CURRENT_USER = _get_user_email()
        CURRENT_USER_NAME = CURRENT_USER.split("@")[0] if "@" in CURRENT_USER else CURRENT_USER
    else:
        CURRENT_USER, CURRENT_USER_NAME = _family_auth_login(AUTH_MODE)
else:
    CURRENT_USER = st.session_state.get("ft_local_user", "default")
    CURRENT_USER_NAME = CURRENT_USER

if not CURRENT_USER:
    CURRENT_USER = "default"
if not CURRENT_USER_NAME:
    CURRENT_USER_NAME = CURRENT_USER

# Admin check
def _is_admin() -> bool:
    try:
        admin_user = st.secrets.get("app_auth", {}).get("admin_user", "").strip()
        admin_normalized = _normalize_user_id(admin_user)
        return bool(admin_normalized and CURRENT_USER == admin_normalized)
    except Exception:
        return False

IS_ADMIN = _is_admin()

# 1-year cleanup on login
if not st.session_state.get("_cleanup_done"):
    try:
        db.cleanup_old_data(CURRENT_USER)
    except Exception:
        pass
    st.session_state["_cleanup_done"] = True

# ═══════════════════════════════════════════════════════════════
# THEME / CONSTANTS
# ═══════════════════════════════════════════════════════════════
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#FAFAFA"),
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=12)),
)
CHART_COLORS = [
    "#6C63FF", "#A78BFA", "#C084FC", "#F472B6", "#FB923C",
    "#FBBF24", "#34D399", "#22D3EE", "#60A5FA", "#818CF8",
]
PAYMENT_METHODS = ["💵 Cash", "💳 Credit Card", "📱 UPI", "🏦 Net Banking"]

# ─── Session state ────────────────────────────────────────────
if "edit_idx" not in st.session_state:
    st.session_state.edit_idx = None
if "confirm_delete_idx" not in st.session_state:
    st.session_state.confirm_delete_idx = None

# ─── Dynamic categories & current month ───────────────────────
EXPENSE_CATS = get_expense_categories(db, CURRENT_USER)
INVEST_CATS  = get_investment_categories(db, CURRENT_USER)
CURRENT_MONTH = date.today().strftime("%Y-%m")

# ═══════════════════════════════════════════════════════════════
# SIDEBAR — user info + quick stats + logout
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 💰 Nexgen Fintrack")
    if IS_ADMIN:
        st.markdown(f"**👤 {CURRENT_USER_NAME}** 👑 *Admin*")
    else:
        st.markdown(f"**👤 {CURRENT_USER_NAME}**")
    st.markdown("---")

    # Quick stats
    _today_str = date.today().strftime("%Y-%m-%d")
    _month_txns = db.get_transactions(CURRENT_MONTH, CURRENT_USER)
    if not _month_txns.empty:
        _today_exp = _month_txns[
            (_month_txns["Date"] == _today_str) & (_month_txns["Type"] == "Expense")
        ]["Amount"].sum()
        _month_exp  = _month_txns[_month_txns["Type"] == "Expense"]["Amount"].sum()
        _month_bud  = db.get_budget(CURRENT_MONTH, CURRENT_USER)
        _remaining  = _month_bud - _month_exp if _month_bud > 0 else None

        st.markdown("**📅 Today**")
        st.markdown(
            f"<div style='background:rgba(255,255,255,0.05);border-radius:10px;padding:10px 14px;'>"
            f"<div style='font-size:1.3rem;font-weight:700;color:#FF8A65;'>{format_inr(_today_exp)}</div>"
            f"<div style='font-size:0.75rem;color:#9BA1B0;'>spent today</div></div>",
            unsafe_allow_html=True,
        )
        if _remaining is not None:
            color = "#FF5252" if _remaining < 0 else "#34D399" if _remaining > _month_bud * 0.3 else "#FFD740"
            st.markdown(
                f"<div style='background:rgba(255,255,255,0.04);border-radius:10px;padding:10px 14px;margin-top:8px;'>"
                f"<div style='font-size:1.1rem;font-weight:600;color:{color};'>{format_inr(_remaining)}</div>"
                f"<div style='font-size:0.75rem;color:#9BA1B0;'>remaining this month</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No transactions this month yet.")

    st.markdown("---")
    st.markdown(
        f"<div style='text-align:center;color:#9BA1B0;font-size:0.75rem;'>"
        f"Nexgen Fintrack v3 · <span style='color:#6C63FF;'>{DB_MODE}</span></div>",
        unsafe_allow_html=True,
    )
    if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
        if DB_MODE.startswith("☁️") and AUTH_MODE == "google":
            st.logout()
        elif DB_MODE.startswith("☁️"):
            st.session_state.pop("ft_simple_user_id", None)
            st.session_state.pop("ft_simple_user_name", None)
            st.rerun()
        else:
            st.session_state.pop("ft_local_user", None)
            st.rerun()


# ═══════════════════════════════════════════════════════════════
# HEADER + SIDEBAR TOGGLE
# ═══════════════════════════════════════════════════════════════
col1, col2 = st.columns([0.9, 0.1])
with col1:
    st.markdown('<p class="app-title">💰 Nexgen Fintrack</p>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="app-subtitle">{get_month_label(CURRENT_MONTH)} · Hey {CURRENT_USER_NAME}!</p>',
        unsafe_allow_html=True,
    )
with col2:
    # Hamburger menu to toggle sidebar
    st.markdown("""
    <style>
    .hamburger-btn {
        background: rgba(108, 99, 255, 0.2);
        border: 2px solid rgba(108, 99, 255, 0.4);
        border-radius: 8px;
        padding: 8px;
        cursor: pointer;
        font-size: 24px;
        width: 100%;
        text-align: center;
        transition: all 0.3s ease;
    }
    .hamburger-btn:hover {
        background: rgba(108, 99, 255, 0.4);
        border-color: rgba(108, 99, 255, 0.7);
    }
    </style>
    <script>
    function toggleSidebar() {
        const sidebar = document.querySelector('[data-testid="stSidebar"]');
        if (sidebar) {
            sidebar.style.display = sidebar.style.display === 'none' ? 'block' : 'none';
        }
    }
    </script>
    """, unsafe_allow_html=True)
    if st.button("☰", help="Toggle sidebar", key="sidebar_toggle_btn"):
        st.markdown(
            "<script>document.querySelector('[data-testid=\"stSidebar\"]').style.display = "
            "document.querySelector('[data-testid=\"stSidebar\"]').style.display === 'none' ? 'block' : 'none';</script>",
            unsafe_allow_html=True
        )

# ═══════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════
tab_names = ["➕ Add", "📊 Overview", "📈 Analytics", "📜 History", "💰 Budget"]
if IS_ADMIN:
    tab_names.append("👑 Admin")
tab_names.append("⚙️ Settings")

tabs = st.tabs(tab_names)
tab_add      = tabs[0]
tab_overview = tabs[1]
tab_analytics = tabs[2]
tab_history  = tabs[3]
tab_budget   = tabs[4]
if IS_ADMIN:
    tab_admin    = tabs[5]
    tab_settings = tabs[6]
else:
    tab_settings = tabs[5]

# ─── Load current-month data once ─────────────────────────────
expenses_df    = db.get_expenses(CURRENT_MONTH, CURRENT_USER)
investments_df = db.get_investments(CURRENT_MONTH, CURRENT_USER)
all_txns_df    = db.get_transactions(CURRENT_MONTH, CURRENT_USER)
budget_val     = db.get_budget(CURRENT_MONTH, CURRENT_USER)
category_limits = db.get_category_limits(CURRENT_USER)
spent          = total_spent(expenses_df)
invested       = total_invested(investments_df)
remaining      = calculate_remaining(budget_val, expenses_df)
alert          = check_alert(remaining, budget_val)


# ═══════════════════════════════════════════════════════════════
# TAB 1 · ADD  — primary daily-use
# ═══════════════════════════════════════════════════════════════
with tab_add:
    st.markdown("### ➕ Add Transaction")

    txn_type_sel = st.radio(
        "Type",
        ["💸 Expense", "📈 Investment"],
        horizontal=True,
        key="txn_type_radio",
        label_visibility="collapsed",
    )
    is_expense = txn_type_sel == "💸 Expense"

    with st.form("add_transaction_form", clear_on_submit=True):
        c1, c2 = st.columns([3, 2])
        with c1:
            category = st.selectbox(
                "📂 Category",
                EXPENSE_CATS if is_expense else INVEST_CATS,
                key="txn_category",
            )
        with c2:
            amount = st.number_input(
                "💵 Amount (₹)", min_value=1, max_value=10_000_000,
                value=100, step=10, key="txn_amount",
            )

        if is_expense:
            p1, p2 = st.columns([2, 3])
            with p1:
                payment = st.selectbox("💳 Payment", PAYMENT_METHODS, key="txn_payment")
            with p2:
                note = st.text_input("📝 Note", placeholder="e.g. Lunch at café", key="txn_note")
        else:
            note = st.text_input("📝 Note", placeholder="e.g. Nifty 50 SIP", key="txn_note_inv")
            payment = "—"

        with st.expander("📅 Change date (default: today)"):
            txn_date = st.date_input("Date", value=date.today(), max_value=date.today(), key="txn_date")

        submitted = st.form_submit_button(
            f"{'💸 Add Expense' if is_expense else '📈 Add Investment'}",
            use_container_width=True,
            type="primary",
        )

    if submitted:
        db.add_transaction(
            txn_date.strftime("%Y-%m-%d"),
            category, amount,
            "Expense" if is_expense else "Investment",
            note,
            username=CURRENT_USER,
            payment_method=payment if is_expense else "—",
        )
        st.toast(f"{'💸' if is_expense else '📈'} {format_inr(amount)} added!", icon="✅")
        st.rerun()

    # ── Today's entries ────────────────────────────────────────
    st.markdown("---")
    _today_str2 = date.today().strftime("%Y-%m-%d")
    today_txns = all_txns_df[all_txns_df["Date"] == _today_str2] if not all_txns_df.empty else pd.DataFrame()

    if not today_txns.empty:
        _t_exp = today_txns[today_txns["Type"] == "Expense"]["Amount"].sum()
        _t_inv = today_txns[today_txns["Type"] == "Investment"]["Amount"].sum()
        parts = [f"<span style='color:#FF8A65;'>💸 {format_inr(_t_exp)}</span>"]
        if _t_inv > 0:
            parts.append(f"<span style='color:#34D399;'>📈 {format_inr(_t_inv)}</span>")
        st.markdown(f"**Today** &nbsp; {'&nbsp;&nbsp;'.join(parts)}", unsafe_allow_html=True)

        for _, row in today_txns.iloc[::-1].iterrows():
            icon  = "💸" if row["Type"] == "Expense" else "📈"
            color = "#FF8A65" if row["Type"] == "Expense" else "#34D399"
            pay   = f" · {row.get('Payment','')}" if row.get("Payment") and row.get("Payment") not in ("", "—") else ""
            nte   = f" · {row['Note']}" if row.get("Note") else ""
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:10px 14px;margin:3px 0;background:rgba(255,255,255,0.03);"
                f"border-radius:10px;border:1px solid rgba(255,255,255,0.06);'>"
                f"<div>{icon} <b>{row['Category']}</b>"
                f"<span style='color:#9BA1B0;font-size:0.78rem;'>{pay}{nte}</span></div>"
                f"<div style='color:{color};font-weight:600;'>{format_inr(row['Amount'])}</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No transactions yet today — log your first one above! 🎯")

    # ── Last 7 days ────────────────────────────────────────────
    if not all_txns_df.empty:
        _cutoff = (date.today() - pd.Timedelta(days=7)).strftime("%Y-%m-%d")
        recent7 = all_txns_df[
            (all_txns_df["Date"] < _today_str2) & (all_txns_df["Date"] >= _cutoff)
        ].tail(8).iloc[::-1]
        if not recent7.empty:
            st.markdown("---")
            st.markdown("**Recent (last 7 days)**")
            for _, row in recent7.iterrows():
                icon  = "💸" if row["Type"] == "Expense" else "📈"
                color = "#FF8A65" if row["Type"] == "Expense" else "#34D399"
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;"
                    f"padding:7px 14px;margin:2px 0;background:rgba(255,255,255,0.02);"
                    f"border-radius:8px;border:1px solid rgba(255,255,255,0.04);'>"
                    f"<div>{icon} <b>{row['Category']}</b>"
                    f"<span style='color:#9BA1B0;font-size:0.78rem;'> · {row['Date']}"
                    f"{'  ·  ' + row['Note'] if row.get('Note') else ''}</span></div>"
                    f"<div style='color:{color};font-weight:600;'>{format_inr(row['Amount'])}</div></div>",
                    unsafe_allow_html=True,
                )


# ═══════════════════════════════════════════════════════════════
# TAB 2 · OVERVIEW — current month summary
# ═══════════════════════════════════════════════════════════════
with tab_overview:
    st.markdown(f"### 📊 {get_month_label(CURRENT_MONTH)} Overview")

    if alert == "critical":
        st.markdown('<div class="alert-critical">🚨 <strong>Budget Overspent!</strong> You\'ve gone over your budget this month.</div>', unsafe_allow_html=True)
    elif alert == "warning":
        pct = (remaining / budget_val * 100) if budget_val > 0 else 0
        st.markdown(f'<div class="alert-warning">⚠️ <strong>Low Budget!</strong> Only {pct:.0f}% remaining — {format_inr(remaining)} left.</div>', unsafe_allow_html=True)
    elif budget_val > 0:
        st.markdown('<div class="alert-ok">✅ Budget is healthy — keep going!</div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("🎯 Budget", format_inr(budget_val) if budget_val > 0 else "Not set")
    with m2:
        st.metric("💸 Spent", format_inr(spent), delta=f"-{format_inr(spent)}" if spent > 0 else None, delta_color="inverse")
    with m3:
        st.metric("🟢 Remaining",
                  format_inr(remaining) if budget_val > 0 else "—",
                  delta=f"{remaining/budget_val*100:.0f}%" if budget_val > 0 else None,
                  delta_color="normal" if remaining >= 0 else "inverse")
    with m4:
        st.metric("📈 Invested", format_inr(invested))

    if not expenses_df.empty:
        if budget_val > 0:
            pct_used = min(spent / budget_val, 1.0)
            bar_color = "#FF5252" if pct_used >= 1 else "#FFD740" if pct_used >= 0.8 else "#6C63FF"
            st.markdown(
                f"<div style='margin:16px 0 4px;color:#9BA1B0;font-size:0.85rem;'>Budget used — {pct_used*100:.1f}%</div>"
                f"<div style='background:rgba(255,255,255,0.06);border-radius:8px;height:10px;overflow:hidden;'>"
                f"<div style='width:{pct_used*100:.1f}%;background:{bar_color};height:100%;border-radius:8px;'></div></div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🍩 Spending by Category")
            cat_df = category_breakdown(expenses_df)
            fig_pie = px.pie(cat_df, values="Amount", names="Category",
                             color_discrete_sequence=CHART_COLORS, hole=0.55)
            fig_pie.update_layout(**PLOTLY_LAYOUT, showlegend=True, height=340)
            fig_pie.update_traces(textposition="inside", textinfo="percent+label", textfont_size=11,
                                  marker=dict(line=dict(color="#0E1117", width=2)))
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            st.markdown("#### 📅 Daily Spending")
            daily_df = daily_spending(expenses_df)
            fig_daily = go.Figure()
            fig_daily.add_trace(go.Scatter(
                x=daily_df["Date"], y=daily_df["Amount"],
                mode="lines+markers", fill="tozeroy",
                line=dict(color="#6C63FF", width=3, shape="spline"),
                marker=dict(size=8, color="#A78BFA"),
                fillcolor="rgba(108,99,255,0.1)",
            ))
            fig_daily.update_layout(**PLOTLY_LAYOUT, height=340,
                                    xaxis=dict(showgrid=False),
                                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickprefix="₹"))
            st.plotly_chart(fig_daily, use_container_width=True)

        # Category limits
        if category_limits:
            st.markdown("#### 🎯 Category Budget Limits")
            cat_spent_dict = category_breakdown(expenses_df).set_index("Category")["Amount"].to_dict()
            lim_cols = st.columns(min(len(category_limits), 3))
            for i, (cat, limit) in enumerate(category_limits.items()):
                s = cat_spent_dict.get(cat, 0)
                pct = min(s / limit, 1.0) if limit > 0 else 0
                clr = "#FF5252" if pct >= 1 else "#FFD740" if pct >= 0.8 else "#34D399"
                with lim_cols[i % 3]:
                    st.markdown(
                        f"<div style='background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);"
                        f"border-radius:12px;padding:14px 16px;margin-bottom:12px;'>"
                        f"<div style='font-size:0.8rem;color:#9BA1B0;margin-bottom:6px;'>{cat}</div>"
                        f"<div style='display:flex;justify-content:space-between;margin-bottom:8px;'>"
                        f"<span style='font-weight:600;'>{format_inr(s)}</span>"
                        f"<span style='color:#9BA1B0;font-size:0.8rem;'>/ {format_inr(limit)}</span></div>"
                        f"<div style='background:rgba(255,255,255,0.06);border-radius:6px;height:6px;'>"
                        f"<div style='width:{pct*100:.1f}%;background:{clr};height:100%;border-radius:6px;'></div></div>"
                        f"<div style='font-size:0.75rem;color:{clr};margin-top:4px;text-align:right;'>{pct*100:.0f}% used</div></div>",
                        unsafe_allow_html=True,
                    )

        # Top categories bar
        st.markdown("#### 🏆 Top Spending Categories")
        cat_top = category_breakdown(expenses_df).head(6)
        fig_bar = px.bar(cat_top, x="Amount", y="Category", orientation="h",
                         color="Amount", color_continuous_scale=["#6C63FF", "#C084FC", "#F472B6"])
        fig_bar.update_layout(**PLOTLY_LAYOUT, height=260, showlegend=False, coloraxis_showscale=False,
                              xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickprefix="₹"),
                              yaxis=dict(showgrid=False, categoryorder="total ascending"))
        fig_bar.update_traces(texttemplate="₹%{x:,.0f}", textposition="outside",
                              marker_line_color="#0E1117", marker_line_width=1)
        st.plotly_chart(fig_bar, use_container_width=True)

        # Payment method breakdown
        if "Payment" in expenses_df.columns and expenses_df["Payment"].notna().any():
            st.markdown("#### 💳 Spending by Payment Method")
            pay_df = expenses_df[expenses_df["Payment"].notna() & (expenses_df["Payment"] != "—")].groupby("Payment")["Amount"].sum().reset_index()
            if not pay_df.empty:
                fig_pay = px.pie(pay_df, values="Amount", names="Payment",
                                 color_discrete_sequence=CHART_COLORS, hole=0.45)
                fig_pay.update_layout(**PLOTLY_LAYOUT, height=280)
                fig_pay.update_traces(textposition="inside", textinfo="percent+label", textfont_size=12)
                st.plotly_chart(fig_pay, use_container_width=True)
    else:
        st.info("No expenses this month yet. Go to ➕ Add to log your first one!")


# ═══════════════════════════════════════════════════════════════
# TAB 3 · ANALYTICS — trends, insights, comparisons
# ═══════════════════════════════════════════════════════════════
with tab_analytics:
    st.markdown("### 📈 Analytics & Insights")

    all_txns_bulk    = db.get_transactions(None, CURRENT_USER)
    all_budgets_bulk = db.get_all_budgets(CURRENT_USER)
    months_12 = get_month_options(12)

    monthly_data = []
    for m in months_12:
        if not all_txns_bulk.empty and "Date" in all_txns_bulk.columns:
            m_df  = all_txns_bulk[all_txns_bulk["Date"].str.startswith(m)]
            m_exp = m_df[m_df["Type"] == "Expense"]
            m_inv = m_df[m_df["Type"] == "Investment"]
        else:
            m_exp = pd.DataFrame()
            m_inv = pd.DataFrame()
        monthly_data.append({
            "month_key": m,
            "Month": get_month_label(m),
            "Spent": total_spent(m_exp),
            "Invested": total_invested(m_inv),
            "Budget": float(all_budgets_bulk.get(m, 0)),
        })
    monthly_df = pd.DataFrame(monthly_data).iloc[::-1].reset_index(drop=True)

    if monthly_df["Spent"].sum() > 0 or monthly_df["Invested"].sum() > 0:

        # Monthly trend bar
        st.markdown("#### 📊 Monthly Spending vs Budget")
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Bar(name="💸 Spent",    x=monthly_df["Month"], y=monthly_df["Spent"],    marker_color="#FF5252"))
        fig_trend.add_trace(go.Bar(name="📈 Invested", x=monthly_df["Month"], y=monthly_df["Invested"], marker_color="#34D399"))
        fig_trend.add_trace(go.Scatter(name="🎯 Budget", x=monthly_df["Month"], y=monthly_df["Budget"],
                                       mode="lines+markers", line=dict(color="#6C63FF", width=2, dash="dot"),
                                       marker=dict(size=6)))
        fig_trend.update_layout(**PLOTLY_LAYOUT, barmode="group", height=380,
                                xaxis=dict(showgrid=False),
                                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickprefix="₹"))
        st.plotly_chart(fig_trend, use_container_width=True)

        # Savings rate cards
        st.markdown("#### 💰 Monthly Savings Rate")
        has_bud = monthly_df[monthly_df["Budget"] > 0]
        if not has_bud.empty:
            sr_cols = st.columns(min(len(has_bud), 6))
            for ci, (_, row) in enumerate(has_bud.iterrows()):
                savings = row["Budget"] - row["Spent"]
                rate    = (savings / row["Budget"]) * 100
                color   = "#34D399" if rate > 30 else "#FFD740" if rate > 10 else "#FF5252"
                with sr_cols[ci % 6]:
                    st.markdown(
                        f"<div style='text-align:center;background:rgba(255,255,255,0.04);"
                        f"border-radius:12px;padding:14px 6px;border:1px solid rgba(255,255,255,0.06);'>"
                        f"<div style='font-size:0.7rem;color:#9BA1B0;'>{row['Month'].split()[0]}</div>"
                        f"<div style='font-size:1.3rem;font-weight:700;color:{color};'>"
                        f"{'↑' if savings >= 0 else '↓'}{abs(rate):.0f}%</div>"
                        f"<div style='font-size:0.7rem;color:#9BA1B0;'>saved</div></div>",
                        unsafe_allow_html=True,
                    )
        else:
            st.info("Set monthly budgets in the 💰 Budget tab to see savings rates.")

        st.markdown("---")

        # Per-month category breakdown
        st.markdown("#### 🗂️ Category Breakdown by Month")
        sel_m = st.selectbox("Select month", options=months_12,
                             format_func=lambda x: get_month_label(x), index=0, key="analytics_month_sel")

        sel_exp = all_txns_bulk[(all_txns_bulk["Date"].str.startswith(sel_m)) & (all_txns_bulk["Type"] == "Expense")] if not all_txns_bulk.empty else pd.DataFrame()
        sel_inv = all_txns_bulk[(all_txns_bulk["Date"].str.startswith(sel_m)) & (all_txns_bulk["Type"] == "Investment")] if not all_txns_bulk.empty else pd.DataFrame()

        ac1, ac2 = st.columns(2)
        with ac1:
            if not sel_exp.empty:
                cat_tbl = category_breakdown(sel_exp).copy()
                cat_tbl["% of Spend"] = (cat_tbl["Amount"] / cat_tbl["Amount"].sum() * 100).round(1)
                total_row = pd.DataFrame([{"Category": "TOTAL", "Amount": cat_tbl["Amount"].sum(), "% of Spend": 100.0}])
                cat_tbl = pd.concat([cat_tbl, total_row], ignore_index=True)
                cat_tbl["Amount"] = cat_tbl["Amount"].apply(format_inr)
                cat_tbl["% of Spend"] = cat_tbl["% of Spend"].apply(lambda x: f"{x}%")
                st.markdown("**💸 Expenses**")
                st.dataframe(cat_tbl, use_container_width=True, hide_index=True)
            else:
                st.info("No expenses this month.")
        with ac2:
            if not sel_inv.empty:
                inv_tbl = category_breakdown(sel_inv).copy()
                inv_tbl = inv_tbl.rename(columns={"Amount": "Invested"})
                inv_tbl["Invested"] = inv_tbl["Invested"].apply(format_inr)
                st.markdown("**📈 Investments**")
                st.dataframe(inv_tbl, use_container_width=True, hide_index=True)
            else:
                st.info("No investments this month.")

        st.markdown("---")

        # Month-on-month category change
        st.markdown("#### 📉 Category Trend (Current vs Previous Month)")
        months_2 = get_month_options(2)
        if len(months_2) >= 2 and not all_txns_bulk.empty:
            cur_m, prev_m = months_2[0], months_2[1]
            cur_exp_  = all_txns_bulk[(all_txns_bulk["Date"].str.startswith(cur_m))  & (all_txns_bulk["Type"] == "Expense")]
            prev_exp_ = all_txns_bulk[(all_txns_bulk["Date"].str.startswith(prev_m)) & (all_txns_bulk["Type"] == "Expense")]
            cur_cat   = category_breakdown(cur_exp_).set_index("Category")["Amount"].to_dict()  if not cur_exp_.empty  else {}
            prev_cat  = category_breakdown(prev_exp_).set_index("Category")["Amount"].to_dict() if not prev_exp_.empty else {}
            all_cats  = sorted(set(list(cur_cat.keys()) + list(prev_cat.keys())))
            if all_cats:
                trend_rows = []
                for cat in all_cats:
                    c = cur_cat.get(cat, 0)
                    p = prev_cat.get(cat, 0)
                    chg = c - p
                    pct_chg = (chg / p * 100) if p > 0 else None
                    trend_rows.append({
                        "Category": cat,
                        get_month_label(prev_m): format_inr(p),
                        get_month_label(cur_m):  format_inr(c),
                        "Change": ("+" if chg >= 0 else "") + format_inr(chg),
                        "% Change": f"{pct_chg:+.0f}%" if pct_chg is not None else "New",
                    })
                st.dataframe(pd.DataFrame(trend_rows), use_container_width=True, hide_index=True)

        st.markdown("---")

        # Insights
        st.markdown("#### 💡 Smart Insights")
        insights = []
        if budget_val > 0 and spent > 0:
            pct_used = spent / budget_val * 100
            if pct_used > 100:
                insights.append(f"🚨 You've **overspent** by {format_inr(spent - budget_val)} this month.")
            elif pct_used > 80:
                insights.append(f"⚠️ Used **{pct_used:.0f}%** of budget — {format_inr(budget_val - spent)} left.")
            else:
                insights.append(f"✅ Healthy! Used {pct_used:.0f}% of budget — {format_inr(budget_val - spent)} remaining.")

        if not expenses_df.empty:
            top_cat = category_breakdown(expenses_df).iloc[0]
            pct_top = top_cat["Amount"] / expenses_df["Amount"].sum() * 100
            insights.append(f"🏆 **{top_cat['Category']}** is your biggest expense — {format_inr(top_cat['Amount'])} ({pct_top:.0f}% of spend).")

        if len(months_2) >= 2 and not all_txns_bulk.empty:
            cur_total  = all_txns_bulk[(all_txns_bulk["Date"].str.startswith(months_2[0])) & (all_txns_bulk["Type"] == "Expense")]["Amount"].sum()
            prev_total = all_txns_bulk[(all_txns_bulk["Date"].str.startswith(months_2[1])) & (all_txns_bulk["Type"] == "Expense")]["Amount"].sum()
            if prev_total > 0:
                delta = cur_total - prev_total
                if delta > 0:
                    insights.append(f"📈 Spending **up by {format_inr(delta)}** vs last month ({delta/prev_total*100:.0f}% more).")
                else:
                    insights.append(f"📉 Spending **down by {format_inr(abs(delta))}** vs last month — great job!")

        # Category limit warnings
        if not expenses_df.empty:
            cat_spent_dict_ = category_breakdown(expenses_df).set_index("Category")["Amount"].to_dict()
            for cat, limit in category_limits.items():
                s_ = cat_spent_dict_.get(cat, 0)
                if s_ > limit:
                    insights.append(f"🔴 **{cat}** over limit: {format_inr(s_)} spent vs {format_inr(limit)} limit.")
                elif limit > 0 and s_ > 0.8 * limit:
                    insights.append(f"🟡 **{cat}** near limit: {format_inr(s_)} / {format_inr(limit)}.")

        if insights:
            for ins in insights:
                st.markdown(f"- {ins}")
        else:
            st.info("Add more transactions to see personalised insights here.")

    else:
        st.info("Not enough data yet — add some transactions first!")


# ═══════════════════════════════════════════════════════════════
# TAB 4 · HISTORY — view, edit, delete, export
# ═══════════════════════════════════════════════════════════════
with tab_history:
    st.markdown("### 📜 Transaction History")

    h_col1, h_col2 = st.columns([3, 2])
    with h_col1:
        hist_month = st.selectbox("📅 Month", options=get_month_options(12),
                                  format_func=lambda x: get_month_label(x), index=0, key="history_month_sel")
    with h_col2:
        hist_type = st.selectbox("🔖 Type", ["All", "Expense", "Investment"], key="h_type")

    hist_txns = db.get_transactions(hist_month, CURRENT_USER)

    if not hist_txns.empty:
        if hist_type != "All":
            hist_txns = hist_txns[hist_txns["Type"] == hist_type]

        csv_buf = io.StringIO()
        hist_txns.to_csv(csv_buf, index=False)
        st.download_button("⬇️ Export CSV", data=csv_buf.getvalue(),
                           file_name=f"fintrack_{hist_month}.csv", mime="text/csv", key="export_csv")

        s1, s2, s3 = st.columns(3)
        with s1:
            st.metric("💸 Expenses",    format_inr(hist_txns[hist_txns["Type"] == "Expense"]["Amount"].sum()))
        with s2:
            st.metric("📈 Investments", format_inr(hist_txns[hist_txns["Type"] == "Investment"]["Amount"].sum()))
        with s3:
            st.metric("📝 Count", len(hist_txns))

        st.markdown("---")

        try:
            indexed_df = db.get_transactions_with_index(hist_month, CURRENT_USER)
        except Exception:
            indexed_df = hist_txns.copy()
            indexed_df.insert(0, "_idx", range(len(hist_txns)))

        if hist_type != "All":
            indexed_df = indexed_df[indexed_df["Type"] == hist_type]
        indexed_df = indexed_df.sort_values("Date", ascending=False).reset_index(drop=True)

        for i, row in indexed_df.iterrows():
            real_idx = row["_idx"]
            icon  = "💸" if row["Type"] == "Expense" else "📈"
            color = "#FF8A65" if row["Type"] == "Expense" else "#34D399"
            pay   = f" · {row.get('Payment','')}" if row.get("Payment") and row.get("Payment") not in ("", "—") else ""

            rc1, rc2, rc3, rc4 = st.columns([3, 1.5, 0.7, 0.7])
            with rc1:
                st.markdown(
                    f"{icon} **{row['Category']}**"
                    f"<span style='color:#9BA1B0;font-size:0.78rem;margin-left:8px;'>{row['Date']}{pay}"
                    f"{'  ·  ' + str(row['Note']) if row.get('Note') else ''}</span>",
                    unsafe_allow_html=True,
                )
            with rc2:
                st.markdown(f"<span style='color:{color};font-weight:600;'>{format_inr(row['Amount'])}</span>",
                            unsafe_allow_html=True)
            with rc3:
                if st.button("✏️", key=f"edit_{real_idx}_{i}", help="Edit"):
                    st.session_state.edit_idx = real_idx
                    st.rerun()
            with rc4:
                if st.session_state.confirm_delete_idx == real_idx:
                    if st.button("✅", key=f"confirm_{real_idx}", type="primary"):
                        db.delete_transaction(real_idx, CURRENT_USER)
                        st.session_state.confirm_delete_idx = None
                        st.toast("Deleted!", icon="🗑️")
                        st.rerun()
                else:
                    if st.button("🗑️", key=f"del_{real_idx}_{i}"):
                        st.session_state.confirm_delete_idx = real_idx
                        st.rerun()

            st.markdown("<hr style='border-color:rgba(255,255,255,0.04);margin:3px 0;'>", unsafe_allow_html=True)

        # Edit modal
        if st.session_state.edit_idx is not None:
            eidx = st.session_state.edit_idx
            all_idx = db.get_transactions_with_index(hist_month, CURRENT_USER)
            match = all_idx[all_idx["_idx"].astype(str) == str(eidx)]
            orig = match.iloc[0].to_dict() if not match.empty else {}

            st.markdown("---")
            st.markdown("#### ✏️ Edit Transaction")
            with st.form("edit_form", clear_on_submit=False):
                e1, e2 = st.columns(2)
                with e1:
                    e_date = st.date_input("Date",
                                           value=datetime.strptime(orig.get("Date", str(date.today())), "%Y-%m-%d").date(),
                                           key="e_date")
                    e_type = st.selectbox("Type", ["Expense", "Investment"],
                                          index=0 if orig.get("Type") == "Expense" else 1, key="e_type")
                    e_cats = EXPENSE_CATS if e_type == "Expense" else INVEST_CATS
                    safe_cat = orig.get("Category", e_cats[0])
                    e_cat = st.selectbox("Category", e_cats,
                                         index=e_cats.index(safe_cat) if safe_cat in e_cats else 0, key="e_cat")
                with e2:
                    e_amt = st.number_input("Amount (₹)", min_value=1, max_value=10_000_000,
                                            value=int(orig.get("Amount", 100)), step=10, key="e_amt")
                    cur_pay = orig.get("Payment", "💵 Cash")
                    e_pay = st.selectbox("Payment", PAYMENT_METHODS,
                                         index=PAYMENT_METHODS.index(cur_pay) if cur_pay in PAYMENT_METHODS else 0,
                                         key="e_pay")
                    e_note = st.text_input("Note", value=orig.get("Note", ""), key="e_note")

                ec1, ec2 = st.columns(2)
                with ec1:
                    save_edit = st.form_submit_button("💾 Save", use_container_width=True)
                with ec2:
                    cancel_edit = st.form_submit_button("✖ Cancel", use_container_width=True)

            if save_edit:
                db.update_transaction(eidx, e_date.strftime("%Y-%m-%d"), e_cat, e_amt, e_type, e_note, CURRENT_USER, e_pay)
                st.session_state.edit_idx = None
                st.toast("Updated!", icon="✅")
                st.rerun()
            if cancel_edit:
                st.session_state.edit_idx = None
                st.rerun()
    else:
        st.info(f"No transactions in {get_month_label(hist_month)}.")


# ═══════════════════════════════════════════════════════════════
# TAB 5 · BUDGET — set once, two inner tabs
# ═══════════════════════════════════════════════════════════════
with tab_budget:
    st.markdown("### 💰 Budget Setup")
    st.caption("Set your monthly limits once — update only when needed.")

    btab_exp, btab_inv = st.tabs(["💸 Expense Budget", "📈 Investment Budget"])

    # ── Expense Budget ─────────────────────────────────────────
    with btab_exp:
        st.markdown("#### Monthly Expense Budget")
        st.caption("Total amount you plan to spend on expenses each month.")

        _all_bud = db.get_all_budgets(CURRENT_USER)
        _bud_months = get_month_options(3)
        bcols = st.columns(len(_bud_months))
        for bi, bm in enumerate(_bud_months):
            bval = _all_bud.get(bm, 0)
            with bcols[bi]:
                st.metric(get_month_label(bm), format_inr(bval) if bval > 0 else "Not set")

        st.markdown("---")
        st.markdown("**Set or update:**")
        with st.form("budget_set_form", clear_on_submit=False):
            bset_col1, bset_col2 = st.columns(2)
            with bset_col1:
                bset_month = st.selectbox("Month", options=get_month_options(6),
                                          format_func=lambda x: get_month_label(x), index=0, key="bset_month")
            with bset_col2:
                _cur_bval = int(_all_bud.get(bset_month, 25000)) if _all_bud.get(bset_month, 0) > 0 else 25000
                bset_amount = st.number_input("Amount (₹)", min_value=0, max_value=10_000_000,
                                              value=_cur_bval, step=1000, key="bset_amount")
            bset_submit = st.form_submit_button("💾 Save Budget", use_container_width=True, type="primary")

        if bset_submit:
            db.set_budget(bset_month, bset_amount, CURRENT_USER)
            st.toast(f"Budget for {get_month_label(bset_month)} → {format_inr(bset_amount)}", icon="✅")
            st.rerun()

        st.markdown("---")
        st.markdown("#### 🎯 Category Spending Limits")
        st.caption("Optional caps per category. Progress bars show on Overview tab.")

        with st.form("cat_limit_form", clear_on_submit=True):
            cl1, cl2, cl3 = st.columns([3, 2, 1])
            with cl1:
                limit_cat = st.selectbox("Category", EXPENSE_CATS, key="limit_cat")
            with cl2:
                limit_amt = st.number_input("Monthly Limit (₹)", min_value=100, max_value=500_000,
                                            value=5000, step=500, key="limit_amt")
            with cl3:
                st.markdown("<br>", unsafe_allow_html=True)
                limit_submitted = st.form_submit_button("➕ Set", use_container_width=True)

        if limit_submitted:
            db.set_category_limit(limit_cat, limit_amt, CURRENT_USER)
            st.toast(f"Limit: {limit_cat} → {format_inr(limit_amt)}", icon="✅")
            st.rerun()

        if category_limits:
            for cat, lim in category_limits.items():
                lc1, lc2, lc3 = st.columns([4, 2, 1])
                with lc1:
                    st.markdown(f"**{cat}**")
                with lc2:
                    st.markdown(f"{format_inr(lim)}/mo")
                with lc3:
                    if st.button("🗑️", key=f"rmlim_{cat}"):
                        db.remove_category_limit(cat, CURRENT_USER)
                        st.rerun()
        else:
            st.caption("No category limits set yet.")

    # ── Investment Budget ──────────────────────────────────────
    with btab_inv:
        st.markdown("#### Monthly Investment Targets")
        st.caption("Set how much you aim to invest per category each month.")

        _inv_targets_key = f"investment_targets_monthly__{CURRENT_USER}"

        def _get_inv_targets() -> dict:
            raw = db.get_config(_inv_targets_key, "")
            try:
                return json.loads(raw) if raw else {}
            except Exception:
                return {}

        inv_targets = _get_inv_targets()

        if inv_targets:
            st.markdown("**Current targets:**")
            for cat, tgt in inv_targets.items():
                itc1, itc2, itc3 = st.columns([4, 2, 1])
                with itc1:
                    st.markdown(f"**{cat}**")
                with itc2:
                    st.markdown(f"{format_inr(tgt)}/mo")
                with itc3:
                    if st.button("🗑️", key=f"rmtgt_{cat}"):
                        del inv_targets[cat]
                        db.set_config(_inv_targets_key, json.dumps(inv_targets))
                        st.rerun()
        else:
            st.caption("No investment targets set yet.")

        st.markdown("---")
        with st.form("inv_target_form", clear_on_submit=True):
            it1, it2, it3 = st.columns([3, 2, 1])
            with it1:
                tgt_cat = st.selectbox("Category", INVEST_CATS, key="inv_tgt_cat")
            with it2:
                tgt_amt = st.number_input("Monthly Target (₹)", min_value=100, max_value=10_000_000,
                                          value=5000, step=500, key="inv_tgt_amt")
            with it3:
                st.markdown("<br>", unsafe_allow_html=True)
                tgt_submitted = st.form_submit_button("➕ Set", use_container_width=True)

        if tgt_submitted:
            inv_targets[tgt_cat] = tgt_amt
            db.set_config(_inv_targets_key, json.dumps(inv_targets))
            st.toast(f"Target: {tgt_cat} → {format_inr(tgt_amt)}/mo", icon="✅")
            st.rerun()

        # Progress vs actual
        if inv_targets and not investments_df.empty:
            st.markdown("---")
            st.markdown(f"**Progress this month — {get_month_label(CURRENT_MONTH)}:**")
            inv_by_cat = investments_df.groupby("Category")["Amount"].sum().to_dict()
            for cat, tgt in inv_targets.items():
                actual = inv_by_cat.get(cat, 0)
                pct = min(actual / tgt, 1.0) if tgt > 0 else 0
                clr = "#34D399" if pct >= 1 else "#FFD740" if pct >= 0.5 else "#FF8A65"
                st.markdown(
                    f"<div style='background:rgba(255,255,255,0.04);border-radius:10px;"
                    f"padding:12px 16px;margin:6px 0;border:1px solid rgba(255,255,255,0.07);'>"
                    f"<div style='display:flex;justify-content:space-between;margin-bottom:6px;'>"
                    f"<span style='font-weight:600;'>{cat}</span>"
                    f"<span style='color:#9BA1B0;font-size:0.85rem;'>{format_inr(actual)} / {format_inr(tgt)}</span></div>"
                    f"<div style='background:rgba(255,255,255,0.06);border-radius:6px;height:8px;'>"
                    f"<div style='width:{pct*100:.1f}%;background:{clr};height:100%;border-radius:6px;'></div></div>"
                    f"<div style='font-size:0.75rem;color:{clr};margin-top:4px;text-align:right;'>{pct*100:.0f}% of target</div></div>",
                    unsafe_allow_html=True,
                )


# ═══════════════════════════════════════════════════════════════
# TAB 6 · ADMIN (admin only)
# ═══════════════════════════════════════════════════════════════
if IS_ADMIN:
    with tab_admin:
        st.markdown("### 👑 Admin Panel")
        st.caption("View all family members' financial data.")
        st.markdown("---")

        all_users = db.get_all_users_list()
        if not all_users:
            st.info("No family members yet.")
        else:
            st.markdown("#### 📊 Family Summary")
            summary_df = db.get_all_users_summary()
            if not summary_df.empty:
                st.dataframe(summary_df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("#### 👤 Member Detail")
            selected_member = st.selectbox("Select member:", all_users, key="admin_member_select")
            if selected_member:
                member_month = st.selectbox("📅 Month:", options=get_month_options(12),
                                            format_func=lambda x: get_month_label(x), index=0,
                                            key="admin_member_month")
                col1, col2 = st.columns(2)
                with col1:
                    mem_exp = db.get_expenses(member_month, selected_member)
                    if not mem_exp.empty:
                        st.markdown(f"**💸 {selected_member}'s Expenses**")
                        st.dataframe(mem_exp, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"No expenses for {selected_member} this month.")
                with col2:
                    mem_inv = db.get_investments(member_month, selected_member)
                    if not mem_inv.empty:
                        st.markdown(f"**📈 {selected_member}'s Investments**")
                        st.dataframe(mem_inv, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"No investments for {selected_member} this month.")
                mem_bud   = db.get_budget(member_month, selected_member)
                mem_spent = total_spent(mem_exp) if not mem_exp.empty else 0
                bc1, bc2  = st.columns(2)
                with bc1:
                    st.metric(f"Budget ({member_month})", format_inr(mem_bud) if mem_bud > 0 else "Not set")
                with bc2:
                    st.metric("Spent", format_inr(mem_spent))

            st.markdown("---")
            st.markdown("#### 📜 All Transactions")
            adm_month = st.selectbox(
                "Month:",
                options=[None] + get_month_options(12),
                format_func=lambda x: "All Time" if x is None else get_month_label(x),
                index=0, key="admin_all_txns_month",
            )
            adm_txns = db.get_transactions(adm_month, is_admin=True)
            if not adm_txns.empty:
                st.dataframe(adm_txns, use_container_width=True, hide_index=True)
            else:
                st.info("No transactions found.")


# ═══════════════════════════════════════════════════════════════
# TAB 7 · SETTINGS — categories + alerts
# ═══════════════════════════════════════════════════════════════
with tab_settings:
    st.markdown("### ⚙️ Settings")
    stab1, stab2, stab3 = st.tabs(["📂 My Categories", "⚠️ Alerts", "🗄️ App Info"])

    with stab1:
        st.markdown("#### Expense Categories")
        cur_exp_cats = get_expense_categories(db, CURRENT_USER)
        with st.form("add_exp_cat_form", clear_on_submit=True):
            ec1, ec2 = st.columns([4, 1])
            with ec1:
                new_exp_cat = st.text_input("New expense category", placeholder="e.g. 🎮 Gaming",
                                            label_visibility="collapsed", key="new_exp_cat_input")
            with ec2:
                add_exp_cat = st.form_submit_button("➕ Add", use_container_width=True)
        if add_exp_cat and new_exp_cat.strip():
            cn = new_exp_cat.strip()
            if cn not in cur_exp_cats:
                cur_exp_cats.append(cn)
                save_expense_categories(db, cur_exp_cats, CURRENT_USER)
                st.toast(f"Added: {cn}", icon="✅")
                st.rerun()
            else:
                st.warning("Category already exists!")
        for i, cat in enumerate(cur_exp_cats):
            cc1, cc2 = st.columns([5, 1])
            with cc1:
                st.markdown(
                    f"<div style='padding:6px 12px;background:rgba(255,255,255,0.04);border-radius:8px;font-size:0.9rem;'>{cat}</div>",
                    unsafe_allow_html=True)
            with cc2:
                is_def = cat in DEFAULT_EXPENSE_CATEGORIES
                if st.button("🗑️", key=f"del_ecat_{i}", disabled=is_def):
                    cur_exp_cats.remove(cat)
                    save_expense_categories(db, cur_exp_cats, CURRENT_USER)
                    st.rerun()
        if st.button("🔄 Reset Expense to Defaults", key="reset_exp_cats"):
            save_expense_categories(db, list(DEFAULT_EXPENSE_CATEGORIES), CURRENT_USER)
            st.toast("Reset to defaults", icon="✅")
            st.rerun()

        st.markdown("---")
        st.markdown("#### Investment Categories")
        cur_inv_cats = get_investment_categories(db, CURRENT_USER)
        with st.form("add_inv_cat_form", clear_on_submit=True):
            ic1, ic2 = st.columns([4, 1])
            with ic1:
                new_inv_cat = st.text_input("New investment category", placeholder="e.g. 🪧 Angel Investing",
                                            label_visibility="collapsed", key="new_inv_cat_input")
            with ic2:
                add_inv_cat = st.form_submit_button("➕ Add", use_container_width=True)
        if add_inv_cat and new_inv_cat.strip():
            cn = new_inv_cat.strip()
            if cn not in cur_inv_cats:
                cur_inv_cats.append(cn)
                save_investment_categories(db, cur_inv_cats, CURRENT_USER)
                st.toast(f"Added: {cn}", icon="✅")
                st.rerun()
            else:
                st.warning("Category already exists!")
        for i, cat in enumerate(cur_inv_cats):
            ic1, ic2 = st.columns([5, 1])
            with ic1:
                st.markdown(
                    f"<div style='padding:6px 12px;background:rgba(255,255,255,0.04);border-radius:8px;font-size:0.9rem;'>{cat}</div>",
                    unsafe_allow_html=True)
            with ic2:
                is_def = cat in DEFAULT_INVESTMENT_CATEGORIES
                if st.button("🗑️", key=f"del_icat_{i}", disabled=is_def):
                    cur_inv_cats.remove(cat)
                    save_investment_categories(db, cur_inv_cats, CURRENT_USER)
                    st.rerun()
        if st.button("🔄 Reset Investment to Defaults", key="reset_inv_cats"):
            save_investment_categories(db, list(DEFAULT_INVESTMENT_CATEGORIES), CURRENT_USER)
            st.toast("Reset to defaults", icon="✅")
            st.rerun()

    with stab2:
        st.markdown("#### ⚠️ Budget Alert Threshold")
        threshold_key = f"warning_threshold__{CURRENT_USER}"
        threshold_val = int(db.get_config(threshold_key, "20"))
        with st.form("threshold_form"):
            new_threshold = st.slider("Warn when remaining budget falls below",
                                      min_value=5, max_value=50, value=threshold_val, step=5, format="%d%%")
            threshold_saved = st.form_submit_button("💾 Save")
        if threshold_saved:
            db.set_config(threshold_key, str(new_threshold))
            st.toast(f"Alert threshold → {new_threshold}%", icon="✅")
            st.rerun()

    with stab3:
        st.markdown("#### 🗄️ App Info")
        total_txns = len(db.get_transactions(None, CURRENT_USER))
        st.markdown(
            f"<div style='background:rgba(255,255,255,0.04);border-radius:12px;padding:16px;"
            f"border:1px solid rgba(255,255,255,0.08);line-height:2;'>"
            f"<b>Mode:</b> {DB_MODE}<br>"
            f"<b>User:</b> {CURRENT_USER_NAME}<br>"
            f"<b>Total transactions:</b> {total_txns}<br>"
            f"<b>Expense categories:</b> {len(EXPENSE_CATS)}<br>"
            f"<b>Investment categories:</b> {len(INVEST_CATS)}<br>"
            f"<br><span style='font-size:0.85rem;color:#9BA1B0;'>Made by Sheshank with ❤️</span></div>",
            unsafe_allow_html=True,
        )
