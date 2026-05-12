"""
app.py — Fintrack V2
A premium, mobile-first personal finance tracker
Built with Streamlit — 100% FREE, no signups needed

V2 Features:
  - Delete transactions (in History)
  - Edit transactions (in History)
  - Export to CSV
  - Category budget limits with progress bars
  - Analytics tab (monthly comparison, savings rate)
"""

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
    page_title="💰 Fintrack",
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

# ─── Auth gate (Google OAuth or family mode) ──────────────────
def _get_auth_mode() -> str:
    try:
        mode = str(st.secrets.get("app_auth", {}).get("mode", "google")).strip().lower()
        if mode in {"google", "passcode", "name_only"}:
            return mode
    except Exception:
        pass
    return "google"


def _normalize_user_id(name: str) -> str:
    user_id = re.sub(r"[^a-z0-9]+", "_", name.strip().lower())
    user_id = user_id.strip("_")
    return user_id or "guest"


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

    shared_passcode = str(st.secrets.get("app_auth", {}).get("shared_passcode", "")).strip()
    if mode == "passcode" and not shared_passcode:
        st.error("App auth is set to passcode mode, but shared_passcode is missing in secrets.")
        st.stop()

    st.title("💸 Fintrack")
    st.write("Family login")
    with st.form("family_login_form", clear_on_submit=False):
        display_name = st.text_input("Your name", placeholder="e.g. Shanky")
        passcode_input = ""
        if mode == "passcode":
            passcode_input = st.text_input("Family passcode", type="password")
        submit_login = st.form_submit_button("Continue", use_container_width=True)

    if submit_login:
        if not display_name.strip():
            st.error("Please enter your name.")
        elif mode == "passcode" and passcode_input.strip() != shared_passcode:
            st.error("Wrong passcode.")
        else:
            st.session_state["ft_simple_user_name"] = display_name.strip()
            st.session_state["ft_simple_user_id"] = _normalize_user_id(display_name)
            st.rerun()

    st.stop()


AUTH_MODE = _get_auth_mode()

if DB_MODE.startswith("☁️"):
    if AUTH_MODE == "google":
        if not _is_logged_in():
            st.title("💸 Fintrack")
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

# ─── Detect if user is admin ────────────────────────────────────
def _is_admin() -> bool:
    admin_user = st.secrets.get("app_auth", {}).get("admin_user", "").strip()
    return bool(admin_user and CURRENT_USER == admin_user)

IS_ADMIN = _is_admin()

# Run 1-year cleanup silently on login (once per session)
if not st.session_state.get("_cleanup_done"):
    try:
        db.cleanup_old_data(CURRENT_USER)
    except Exception:
        pass
    st.session_state["_cleanup_done"] = True

# ═══════════════════════════════════════════════════════════════
# PLOTLY THEME
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

# ═══════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════
if "edit_idx" not in st.session_state:
    st.session_state.edit_idx = None
if "confirm_delete_idx" not in st.session_state:
    st.session_state.confirm_delete_idx = None

# ─── Load dynamic categories ─────────────────────────────────
EXPENSE_CATS  = get_expense_categories(db, CURRENT_USER)
INVEST_CATS   = get_investment_categories(db, CURRENT_USER)

# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"## 💰 Fintrack")
    if IS_ADMIN:
        st.markdown(f"**👤 {CURRENT_USER_NAME}** 👑 *Admin*")
    else:
        st.markdown(f"**👤 {CURRENT_USER_NAME}**")
    st.markdown("---")

    # Quick add from sidebar
    st.markdown("### ⚡ Quick Add Expense")
    with st.form("quick_add_form", clear_on_submit=True):
        q_category = st.selectbox("Category", EXPENSE_CATS, key="q_cat")
        q_amount = st.number_input("Amount (₹)", min_value=1, max_value=500000, value=100, step=10, key="q_amt")
        q_note = st.text_input("Note", placeholder="e.g. Zomato", key="q_note")
        q_submitted = st.form_submit_button("➕ Add", use_container_width=True)

    if q_submitted:
        db.add_transaction(
            date.today().strftime("%Y-%m-%d"),
            q_category, q_amount, "Expense", q_note,
            username=CURRENT_USER,
        )
        st.toast(f"✅ {format_inr(q_amount)} added!", icon="💸")
        st.rerun()

    st.markdown("---")
    st.markdown(
        f"<div style='text-align:center;color:#9BA1B0;font-size:0.75rem;'>"
        f"Fintrack v2.0 · <span style='color:#6C63FF;'>{DB_MODE}</span></div>",
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
# HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown('<p class="app-title">💰 Fintrack</p>', unsafe_allow_html=True)

# ─── Inline controls (visible on mobile without sidebar) ─────
ctrl1, ctrl2, ctrl3 = st.columns([2, 2, 1])
with ctrl1:
    month_options = get_month_options(6)
    month_labels  = {k: get_month_label(k) for k in month_options}
    selected_month = st.selectbox(
        "📅 Month",
        options=month_options,
        format_func=lambda x: month_labels[x],
        index=0,
        key="month_selector_main",
        label_visibility="collapsed",
    )
with ctrl2:
    _cur_bud = db.get_budget(selected_month, CURRENT_USER)
    with st.form("budget_inline_form", clear_on_submit=False):
        _bud_val = st.number_input(
            "Budget (₹)", min_value=0, max_value=10_000_000,
            value=int(_cur_bud) if _cur_bud > 0 else 25000,
            step=1000, key="budget_inline_input",
            label_visibility="collapsed",
        )
        if st.form_submit_button("🎯 Set Budget"):
            db.set_budget(selected_month, _bud_val, CURRENT_USER)
            st.toast(f"Budget → {format_inr(_bud_val)}", icon="✅")
            st.rerun()
with ctrl3:
    st.markdown(
        f"<div style='text-align:right;padding-top:8px;font-size:0.7rem;color:#9BA1B0;'>{DB_MODE}</div>",
        unsafe_allow_html=True,
    )

st.markdown(
    f'<p class="app-subtitle">Your financial command center | {get_month_label(selected_month)}</p>',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════════════════════
expenses_df     = db.get_expenses(selected_month, CURRENT_USER)
investments_df  = db.get_investments(selected_month, CURRENT_USER)
all_txns_df     = db.get_transactions(selected_month, CURRENT_USER)
budget_val      = db.get_budget(selected_month, CURRENT_USER)
category_limits = db.get_category_limits(CURRENT_USER)

spent     = total_spent(expenses_df)
invested  = total_invested(investments_df)
remaining = calculate_remaining(budget_val, expenses_df)
alert     = check_alert(remaining, budget_val)

# ═══════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════
tab_names = [
    "📊 Dashboard",
    "➕ Add",
    "📜 History",
    "📈 Analytics",
]
if IS_ADMIN:
    tab_names.append("👑 Admin")
tab_names.append("⚙️ Settings")

tabs = st.tabs(tab_names)
tab_dash = tabs[0]
tab_add = tabs[1]
tab_history = tabs[2]
tab_analytics = tabs[3]
if IS_ADMIN:
    tab_admin = tabs[4]
    tab_settings = tabs[5]
else:
    tab_settings = tabs[4]

# ───────────────────────────────────────────────────────────────
# TAB 1 · DASHBOARD
# ───────────────────────────────────────────────────────────────
with tab_dash:
    # Alert banner
    if alert == "critical":
        st.markdown(
            '<div class="alert-critical">🚨 <strong>Budget Overspent!</strong> '
            "You've gone over your budget this month.</div>",
            unsafe_allow_html=True,
        )
    elif alert == "warning":
        pct = (remaining / budget_val * 100) if budget_val > 0 else 0
        st.markdown(
            f'<div class="alert-warning">⚠️ <strong>Low Budget!</strong> '
            f"Only {pct:.0f}% remaining — {format_inr(remaining)} left.</div>",
            unsafe_allow_html=True,
        )
    elif budget_val > 0:
        st.markdown('<div class="alert-ok">✅ Budget is healthy — keep going!</div>', unsafe_allow_html=True)

    # Metric cards
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("💰 Budget", format_inr(budget_val))
    with m2:
        st.metric("💸 Spent", format_inr(spent),
                  delta=f"-{format_inr(spent)}" if spent > 0 else None,
                  delta_color="inverse")
    with m3:
        st.metric("🟢 Remaining", format_inr(remaining),
                  delta=f"{remaining/budget_val*100:.0f}%" if budget_val > 0 else None,
                  delta_color="normal" if remaining >= 0 else "inverse")
    with m4:
        st.metric("📈 Invested", format_inr(invested))

    st.markdown("---")

    if not expenses_df.empty:
        # Budget progress bar
        if budget_val > 0:
            pct_used = min(spent / budget_val, 1.0)
            bar_color = "#FF5252" if pct_used >= 1 else "#FFD740" if pct_used >= 0.8 else "#6C63FF"
            st.markdown(
                f"<div style='margin-bottom:8px;color:#9BA1B0;font-size:0.85rem;font-weight:500;'>"
                f"Overall Budget Usage — {pct_used*100:.1f}%</div>"
                f"<div style='background:rgba(255,255,255,0.06);border-radius:8px;height:10px;overflow:hidden;'>"
                f"<div style='width:{pct_used*100:.1f}%;background:{bar_color};height:100%;border-radius:8px;"
                f"transition:width 0.5s ease;'></div></div>",
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)

        # Charts
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### 🍩 Spending by Category")
            cat_df = category_breakdown(expenses_df)
            fig = px.pie(cat_df, values="Amount", names="Category",
                         color_discrete_sequence=CHART_COLORS, hole=0.55)
            fig.update_layout(**PLOTLY_LAYOUT, showlegend=True, height=360)
            fig.update_traces(textposition="inside", textinfo="percent+label",
                              textfont_size=11,
                              marker=dict(line=dict(color="#0E1117", width=2)))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("#### 📈 Daily Spending")
            daily_df = daily_spending(expenses_df)
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=daily_df["Date"], y=daily_df["Amount"],
                mode="lines+markers", fill="tozeroy",
                line=dict(color="#6C63FF", width=3, shape="spline"),
                marker=dict(size=8, color="#A78BFA"),
                fillcolor="rgba(108,99,255,0.1)",
            ))
            fig2.update_layout(**PLOTLY_LAYOUT, height=360,
                               xaxis=dict(showgrid=False),
                               yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickprefix="₹"))
            st.plotly_chart(fig2, use_container_width=True)

        # Category limits progress bars
        if category_limits:
            st.markdown("#### 🎯 Category Budget Limits")
            cat_spent = category_breakdown(expenses_df).set_index("Category")["Amount"].to_dict()
            cols = st.columns(min(len(category_limits), 3))
            for i, (cat, limit) in enumerate(category_limits.items()):
                spent_cat = cat_spent.get(cat, 0)
                pct = min(spent_cat / limit, 1.0) if limit > 0 else 0
                color = "#FF5252" if pct >= 1 else "#FFD740" if pct >= 0.8 else "#34D399"
                with cols[i % 3]:
                    st.markdown(
                        f"<div style='background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);"
                        f"border-radius:12px;padding:14px 16px;margin-bottom:12px;'>"
                        f"<div style='font-size:0.8rem;color:#9BA1B0;margin-bottom:6px;'>{cat}</div>"
                        f"<div style='display:flex;justify-content:space-between;margin-bottom:8px;'>"
                        f"<span style='font-weight:600;color:#FAFAFA;font-size:0.95rem;'>{format_inr(spent_cat)}</span>"
                        f"<span style='color:#9BA1B0;font-size:0.8rem;'>/ {format_inr(limit)}</span></div>"
                        f"<div style='background:rgba(255,255,255,0.06);border-radius:6px;height:6px;'>"
                        f"<div style='width:{pct*100:.1f}%;background:{color};height:100%;border-radius:6px;'></div>"
                        f"</div><div style='font-size:0.75rem;color:{color};margin-top:4px;text-align:right;'>"
                        f"{pct*100:.0f}% used</div></div>",
                        unsafe_allow_html=True,
                    )

        # Top categories bar
        st.markdown("#### 🏆 Top Categories")
        cat_df_top = category_breakdown(expenses_df).head(6)
        fig3 = px.bar(cat_df_top, x="Amount", y="Category", orientation="h",
                      color="Amount", color_continuous_scale=["#6C63FF", "#C084FC", "#F472B6"])
        fig3.update_layout(**PLOTLY_LAYOUT, height=280, showlegend=False,
                           coloraxis_showscale=False,
                           xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickprefix="₹"),
                           yaxis=dict(showgrid=False, categoryorder="total ascending"))
        fig3.update_traces(texttemplate="₹%{x:,.0f}", textposition="outside",
                           marker_line_color="#0E1117", marker_line_width=1)
        st.plotly_chart(fig3, use_container_width=True)

    else:
        st.markdown(
            "<div style='text-align:center;padding:60px 20px;color:#9BA1B0;'>"
            "<p style='font-size:3rem;'>📭</p>"
            "<p style='font-size:1.1rem;'>No expenses yet this month.</p>"
            "<p style='font-size:0.85rem;'>Use the sidebar or <strong>Add</strong> tab to get started!</p>"
            "</div>", unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────────
# TAB 2 · ADD TRANSACTION
# ───────────────────────────────────────────────────────────────
with tab_add:
    st.markdown("### ➕ New Transaction")

    txn_type = st.radio("Type", ["💸 Expense", "📈 Investment"],
                        horizontal=True, key="txn_type_radio")
    is_expense = txn_type == "💸 Expense"

    with st.form("add_transaction_form", clear_on_submit=True):
        col_l, col_r = st.columns(2)
        with col_l:
            txn_date = st.date_input("📅 Date", value=date.today(), max_value=date.today(), key="txn_date")
            category = st.selectbox("📂 Category",
                                    EXPENSE_CATS if is_expense else INVEST_CATS,
                                    key="txn_category")
        with col_r:
            amount = st.number_input("💵 Amount (₹)", min_value=1, max_value=10_000_000,
                                     value=100, step=10, key="txn_amount")
            note = st.text_input("📝 Note (optional)", placeholder="e.g. Lunch at café", key="txn_note")
        submitted = st.form_submit_button("✅ Add Transaction", use_container_width=True)

    if submitted:
        db.add_transaction(
            txn_date.strftime("%Y-%m-%d"), category, amount,
            "Expense" if is_expense else "Investment", note,
            username=CURRENT_USER,
        )
        st.toast(f"{'💸' if is_expense else '📈'} {format_inr(amount)} added!", icon="✅")
        st.balloons()
        st.rerun()

    # Recent 5
    st.markdown("---")
    st.markdown("#### 🕐 Recent Transactions")
    if not all_txns_df.empty:
        for _, row in all_txns_df.tail(5).iloc[::-1].iterrows():
            icon  = "💸" if row["Type"] == "Expense" else "📈"
            color = "#FF5252" if row["Type"] == "Expense" else "#00E676"
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:10px 16px;margin:4px 0;background:rgba(255,255,255,0.03);"
                f"border-radius:10px;border:1px solid rgba(255,255,255,0.06);'>"
                f"<div>{icon} <strong>{row['Category']}</strong>"
                f"<span style='color:#9BA1B0;font-size:0.8rem;margin-left:8px;'>{row['Date']}</span>"
                f"{f'<span style=color:#9BA1B0;font-size:0.75rem;margin-left:6px;> · {row[chr(78)+chr(111)+chr(116)+chr(101)]}</span>' if row.get('Note') else ''}"
                f"</div><div style='color:{color};font-weight:600;'>{format_inr(row['Amount'])}</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No transactions yet. Add your first one above! 🎯")

# ───────────────────────────────────────────────────────────────
# TAB 3 · HISTORY  (with Edit & Delete)
# ───────────────────────────────────────────────────────────────
with tab_history:
    st.markdown("### 📜 Transaction History")
    st.markdown(f"Showing **{get_month_label(selected_month)}**")

    if not all_txns_df.empty:
        # Filters
        f1, f2, f3 = st.columns(3)
        with f1:
            type_filter = st.selectbox("🔖 Type", ["All", "Expense", "Investment"], key="h_type")
        with f2:
            all_cats = sorted(all_txns_df["Category"].unique().tolist())
            cat_filter = st.multiselect("📂 Category", all_cats, default=all_cats, key="h_cat")
        with f3:
            sort_order = st.selectbox("🔃 Sort", ["Newest first", "Oldest first", "Highest amount"], key="h_sort")

        # Apply filters
        filtered = all_txns_df.copy()
        if type_filter != "All":
            filtered = filtered[filtered["Type"] == type_filter]
        if cat_filter:
            filtered = filtered[filtered["Category"].isin(cat_filter)]

        if sort_order == "Newest first":
            filtered = filtered.sort_values("Date", ascending=False)
        elif sort_order == "Oldest first":
            filtered = filtered.sort_values("Date", ascending=True)
        else:
            filtered = filtered.sort_values("Amount", ascending=False)

        filtered = filtered.reset_index(drop=True)

        # Export CSV
        csv_buf = io.StringIO()
        filtered.to_csv(csv_buf, index=False)
        st.download_button(
            label="⬇️ Export CSV",
            data=csv_buf.getvalue(),
            file_name=f"fintrack_{selected_month}.csv",
            mime="text/csv",
            key="export_csv",
        )

        st.markdown("---")

        # Transaction rows with edit/delete
        # We need _idx for correct deletion — fetch indexed version
        try:
            indexed_df = db.get_transactions_with_index(selected_month, CURRENT_USER)
        except AttributeError:
            # Fallback for backends that do not expose indexed reads.
            indexed_df = filtered.copy()
            indexed_df.insert(0, "_idx", filtered.index)

        # Apply same filters to indexed_df
        i_filtered = indexed_df.copy()
        if type_filter != "All":
            i_filtered = i_filtered[i_filtered["Type"] == type_filter]
        if cat_filter:
            i_filtered = i_filtered[i_filtered["Category"].isin(cat_filter)]
        if sort_order == "Newest first":
            i_filtered = i_filtered.sort_values("Date", ascending=False)
        elif sort_order == "Oldest first":
            i_filtered = i_filtered.sort_values("Date", ascending=True)
        else:
            i_filtered = i_filtered.sort_values("Amount", ascending=False)
        i_filtered = i_filtered.reset_index(drop=True)

        for i, row in i_filtered.iterrows():
            real_idx = row["_idx"]
            icon  = "💸" if row["Type"] == "Expense" else "📈"
            color = "#FF5252" if row["Type"] == "Expense" else "#00E676"

            with st.container():
                rc1, rc2, rc3, rc4 = st.columns([3, 1.5, 1, 1])
                with rc1:
                    st.markdown(
                        f"{icon} **{row['Category']}**"
                        f"<span style='color:#9BA1B0;font-size:0.8rem;margin-left:8px;'>{row['Date']}"
                        f"{' · ' + str(row['Note']) if row.get('Note') else ''}</span>",
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
                        if st.button("✅ Sure?", key=f"confirm_{real_idx}", type="primary"):
                            db.delete_transaction(real_idx, CURRENT_USER)
                            st.session_state.confirm_delete_idx = None
                            st.toast("Transaction deleted!", icon="🗑️")
                            st.rerun()
                    else:
                        if st.button("🗑️", key=f"del_{real_idx}_{i}", help="Delete"):
                            st.session_state.confirm_delete_idx = real_idx
                            st.rerun()

            st.markdown("<hr style='border-color:rgba(255,255,255,0.04);margin:4px 0;'>",
                        unsafe_allow_html=True)

        # Edit modal (shown below list when edit_idx is set)
        if st.session_state.edit_idx is not None:
            eidx = st.session_state.edit_idx
            match = indexed_df[indexed_df["_idx"].astype(str) == str(eidx)]
            orig = match.iloc[0].to_dict() if not match.empty else {}

            st.markdown("---")
            st.markdown("#### ✏️ Edit Transaction")
            with st.form("edit_form", clear_on_submit=False):
                e1, e2 = st.columns(2)
                with e1:
                    e_date = st.date_input("Date", value=datetime.strptime(orig.get("Date", str(date.today())), "%Y-%m-%d").date(), key="e_date")
                    e_type = st.selectbox("Type", ["Expense", "Investment"],
                                          index=0 if orig.get("Type") == "Expense" else 1, key="e_type")
                    e_cats = EXPENSE_CATEGORIES if e_type == "Expense" else INVESTMENT_CATEGORIES
                    safe_cat = orig.get("Category", e_cats[0])
                    e_cat = st.selectbox("Category", e_cats,
                                         index=e_cats.index(safe_cat) if safe_cat in e_cats else 0, key="e_cat")
                with e2:
                    e_amt = st.number_input("Amount (₹)", min_value=1, max_value=10_000_000,
                                            value=int(orig.get("Amount", 100)), step=10, key="e_amt")
                    e_note = st.text_input("Note", value=orig.get("Note", ""), key="e_note")

                ec1, ec2 = st.columns(2)
                with ec1:
                    save_edit = st.form_submit_button("💾 Save Changes", use_container_width=True)
                with ec2:
                    cancel_edit = st.form_submit_button("✖ Cancel", use_container_width=True)

            if save_edit:
                db.update_transaction(eidx, e_date.strftime("%Y-%m-%d"), e_cat, e_amt, e_type, e_note, CURRENT_USER)
                st.session_state.edit_idx = None
                st.toast("Transaction updated!", icon="✅")
                st.rerun()
            if cancel_edit:
                st.session_state.edit_idx = None
                st.rerun()

        # Summary stats
        st.markdown("---")
        s1, s2, s3, s4 = st.columns(4)
        with s1:
            st.metric("Transactions", len(i_filtered))
        with s2:
            st.metric("Total Expenses", format_inr(i_filtered[i_filtered["Type"] == "Expense"]["Amount"].sum()))
        with s3:
            st.metric("Total Investments", format_inr(i_filtered[i_filtered["Type"] == "Investment"]["Amount"].sum()))
        with s4:
            avg = i_filtered[i_filtered["Type"] == "Expense"]["Amount"].mean() if not i_filtered.empty else 0
            st.metric("Avg Expense", format_inr(avg) if avg else "—")

    else:
        st.markdown(
            "<div style='text-align:center;padding:60px 20px;color:#9BA1B0;'>"
            "<p style='font-size:3rem;'>📭</p>"
            "<p style='font-size:1.1rem;'>No transactions this month.</p></div>",
            unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────────
# TAB 4 · ANALYTICS
# ───────────────────────────────────────────────────────────────
with tab_analytics:
    st.markdown("### 📈 Analytics")

    # Fetch ALL data in ONE call each — avoid rate limits
    all_txns_bulk   = db.get_transactions(None, CURRENT_USER)  # all months, 1 API call
    all_budgets_bulk = db.get_all_budgets(CURRENT_USER)       # all budgets, 1 API call

    months_6 = get_month_options(6)
    monthly_data = []
    for m in months_6:
        if not all_txns_bulk.empty and "Date" in all_txns_bulk.columns:
            m_df = all_txns_bulk[all_txns_bulk["Date"].str.startswith(m)]
            m_exp = m_df[m_df["Type"] == "Expense"]
            m_inv = m_df[m_df["Type"] == "Investment"]
        else:
            m_exp = pd.DataFrame()
            m_inv = pd.DataFrame()
        m_bud = float(all_budgets_bulk.get(m, 0))
        monthly_data.append({
            "Month": get_month_label(m),
            "Spent": total_spent(m_exp),
            "Invested": total_invested(m_inv),
            "Budget": m_bud,
        })
    monthly_df = pd.DataFrame(monthly_data).iloc[::-1].reset_index(drop=True)

    if monthly_df["Spent"].sum() > 0 or monthly_df["Invested"].sum() > 0:
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(name="💸 Spent", x=monthly_df["Month"], y=monthly_df["Spent"],
                                  marker_color="#FF5252"))
        fig_bar.add_trace(go.Bar(name="📈 Invested", x=monthly_df["Month"], y=monthly_df["Invested"],
                                  marker_color="#00E676"))
        fig_bar.add_trace(go.Scatter(name="🎯 Budget", x=monthly_df["Month"], y=monthly_df["Budget"],
                                      mode="lines+markers", line=dict(color="#6C63FF", width=2, dash="dot"),
                                      marker=dict(size=6)))
        fig_bar.update_layout(**PLOTLY_LAYOUT, barmode="group", height=380,
                               xaxis=dict(showgrid=False),
                               yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickprefix="₹"))
        st.plotly_chart(fig_bar, use_container_width=True)

        # Savings rate
        st.markdown("#### 💰 Savings Rate")
        sr_cols = st.columns(len(monthly_df))
        for i, row in monthly_df.iterrows():
            if row["Budget"] > 0:
                savings = row["Budget"] - row["Spent"]
                rate = (savings / row["Budget"]) * 100
                color = "#00E676" if rate > 30 else "#FFD740" if rate > 10 else "#FF5252"
                with sr_cols[i]:
                    st.markdown(
                        f"<div style='text-align:center;background:rgba(255,255,255,0.04);"
                        f"border-radius:12px;padding:16px 8px;border:1px solid rgba(255,255,255,0.06);'>"
                        f"<div style='font-size:0.7rem;color:#9BA1B0;'>{row['Month'].split()[0]}</div>"
                        f"<div style='font-size:1.4rem;font-weight:700;color:{color};'>"
                        f"{'↑' if savings >= 0 else '↓'}{abs(rate):.0f}%</div>"
                        f"<div style='font-size:0.7rem;color:#9BA1B0;'>saved</div></div>",
                        unsafe_allow_html=True,
                    )

        # Current month category breakdown table
        st.markdown("---")
        st.markdown(f"#### 🗂️ Category Breakdown — {get_month_label(selected_month)}")
        if not expenses_df.empty:
            cat_table = category_breakdown(expenses_df).copy()
            cat_table["% of Spend"] = (cat_table["Amount"] / cat_table["Amount"].sum() * 100).round(1)
            cat_table["Amount"] = cat_table["Amount"].apply(format_inr)
            cat_table["% of Spend"] = cat_table["% of Spend"].apply(lambda x: f"{x}%")
            st.dataframe(cat_table, use_container_width=True, hide_index=True)
        else:
            st.info("No expenses to analyse this month.")
    else:
        st.markdown(
            "<div style='text-align:center;padding:60px 20px;color:#9BA1B0;'>"
            "<p style='font-size:3rem;'>📊</p>"
            "<p>Not enough data yet — add some transactions first!</p></div>",
            unsafe_allow_html=True)

# ───────────────────────────────────────────────────────────────
# TAB 5 · ADMIN (if user is admin)
# ───────────────────────────────────────────────────────────────
if IS_ADMIN:
    with tab_admin:
        st.markdown("### 👑 Admin Panel")
        st.markdown("View all family members' financial data.")
        st.markdown("---")

        # Get all family members
        all_users = db.get_all_users_list()
        
        if not all_users:
            st.info("No family members yet.")
        else:
            # Summary table
            st.markdown("#### 📊 Family Summary")
            summary_df = db.get_all_users_summary()
            if not summary_df.empty:
                st.dataframe(summary_df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # View individual member's data
            st.markdown("#### 👤 View Member Data")
            selected_member = st.selectbox("Select member:", all_users, key="admin_member_select")
            
            if selected_member:
                member_month = st.selectbox(
                    "📅 Month:",
                    options=get_month_options(12),
                    format_func=lambda x: get_month_label(x),
                    index=0,
                    key="admin_member_month",
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    member_expenses = db.get_expenses(member_month, selected_member)
                    if not member_expenses.empty:
                        st.markdown(f"**💸 {selected_member}'s Expenses**")
                        st.dataframe(member_expenses, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"No expenses for {selected_member} this month.")
                
                with col2:
                    member_investments = db.get_investments(member_month, selected_member)
                    if not member_investments.empty:
                        st.markdown(f"**📈 {selected_member}'s Investments**")
                        st.dataframe(member_investments, use_container_width=True, hide_index=True)
                    else:
                        st.info(f"No investments for {selected_member} this month.")
                
                st.markdown("---")
                st.markdown(f"#### 💰 {selected_member}'s Budget")
                member_budget = db.get_budget(member_month, selected_member)
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(f"Budget ({member_month})", format_inr(member_budget))
                with col2:
                    member_spent = total_spent(member_expenses) if not member_expenses.empty else 0
                    st.metric("Spent This Month", format_inr(member_spent))
            
            st.markdown("---")
            
            # All transactions view
            st.markdown("#### 📜 All Family Transactions")
            all_month = st.selectbox(
                "📅 Filter by month:",
                options=[None] + get_month_options(12),
                format_func=lambda x: "All Time" if x is None else get_month_label(x),
                index=0,
                key="admin_all_txns_month",
            )
            
            all_transactions = db.get_transactions(all_month, is_admin=True)
            if not all_transactions.empty:
                st.dataframe(all_transactions, use_container_width=True, hide_index=True)
            else:
                st.info("No transactions found.")

with tab_settings:
    st.markdown("### ⚙️ Settings")

    settings_tab1, settings_tab2, settings_tab3, settings_tab4 = st.tabs([
        "📂 My Categories",
        "🎯 Budget Limits",
        "⚠️ Alerts",
        "🗄️ App Info",
    ])

    # ─── Custom Categories ─────────────────────────────────────
    with settings_tab1:
        st.markdown("#### Expense Categories")
        st.caption("These appear in the Add Transaction form and sidebar Quick Add.")

        current_exp_cats = get_expense_categories(db, CURRENT_USER)

        # Add new expense category
        with st.form("add_exp_cat_form", clear_on_submit=True):
            ec1, ec2 = st.columns([4, 1])
            with ec1:
                new_exp_cat = st.text_input(
                    "New category name",
                    placeholder="e.g. 🎮 Gaming  or  🐶 Pet Care",
                    label_visibility="collapsed",
                    key="new_exp_cat_input",
                )
            with ec2:
                add_exp_cat = st.form_submit_button("➕ Add", use_container_width=True)

        if add_exp_cat and new_exp_cat.strip():
            cat_name = new_exp_cat.strip()
            if cat_name not in current_exp_cats:
                current_exp_cats.append(cat_name)
                save_expense_categories(db, current_exp_cats, CURRENT_USER)
                st.toast(f"Added: {cat_name}", icon="✅")
                st.rerun()
            else:
                st.warning("Category already exists!")

        # Show & delete existing
        st.markdown("**Current categories:**")
        for i, cat in enumerate(current_exp_cats):
            cc1, cc2 = st.columns([5, 1])
            with cc1:
                st.markdown(
                    f"<div style='padding:6px 12px;background:rgba(255,255,255,0.04);border-radius:8px;"
                    f"border:1px solid rgba(255,255,255,0.06);font-size:0.9rem;'>{cat}</div>",
                    unsafe_allow_html=True,
                )
            with cc2:
                is_default = cat in DEFAULT_EXPENSE_CATEGORIES
                if st.button("🗑️", key=f"del_ecat_{i}", disabled=is_default,
                             help="Remove" if not is_default else "Default category (can't delete)"):
                    current_exp_cats.remove(cat)
                    save_expense_categories(db, current_exp_cats, CURRENT_USER)
                    st.toast(f"Removed: {cat}", icon="✅")
                    st.rerun()

        if st.button("🔄 Reset to Defaults", key="reset_exp_cats"):
            save_expense_categories(db, list(DEFAULT_EXPENSE_CATEGORIES), CURRENT_USER)
            st.toast("Reset to default categories", icon="✅")
            st.rerun()

        st.markdown("---")
        st.markdown("#### Investment Categories")
        current_inv_cats = get_investment_categories(db, CURRENT_USER)

        with st.form("add_inv_cat_form", clear_on_submit=True):
            ic1, ic2 = st.columns([4, 1])
            with ic1:
                new_inv_cat = st.text_input(
                    "New investment category",
                    placeholder="e.g. 🪧 Angel Investing",
                    label_visibility="collapsed",
                    key="new_inv_cat_input",
                )
            with ic2:
                add_inv_cat = st.form_submit_button("➕ Add", use_container_width=True)

        if add_inv_cat and new_inv_cat.strip():
            cat_name = new_inv_cat.strip()
            if cat_name not in current_inv_cats:
                current_inv_cats.append(cat_name)
                save_investment_categories(db, current_inv_cats, CURRENT_USER)
                st.toast(f"Added: {cat_name}", icon="✅")
                st.rerun()
            else:
                st.warning("Category already exists!")

        for i, cat in enumerate(current_inv_cats):
            ic1, ic2 = st.columns([5, 1])
            with ic1:
                st.markdown(
                    f"<div style='padding:6px 12px;background:rgba(255,255,255,0.04);border-radius:8px;"
                    f"border:1px solid rgba(255,255,255,0.06);font-size:0.9rem;'>{cat}</div>",
                    unsafe_allow_html=True,
                )
            with ic2:
                is_default = cat in DEFAULT_INVESTMENT_CATEGORIES
                if st.button("🗑️", key=f"del_icat_{i}", disabled=is_default,
                             help="Remove" if not is_default else "Default"):
                    current_inv_cats.remove(cat)
                    save_investment_categories(db, current_inv_cats, CURRENT_USER)
                    st.toast(f"Removed: {cat}", icon="✅")
                    st.rerun()

        if st.button("🔄 Reset to Defaults", key="reset_inv_cats"):
            save_investment_categories(db, list(DEFAULT_INVESTMENT_CATEGORIES), CURRENT_USER)
            st.toast("Reset to default categories", icon="✅")
            st.rerun()

    # ─── Category Budget Limits ────────────────────────────────
    with settings_tab2:
        st.markdown("#### 🎯 Category Budget Limits")
        st.caption("Set spending limits per category. Progress bars appear on the Dashboard.")

        with st.form("cat_limit_form", clear_on_submit=True):
            sl1, sl2, sl3 = st.columns(3)
            with sl1:
                limit_cat = st.selectbox("Category", EXPENSE_CATS, key="limit_cat")
            with sl2:
                limit_amt = st.number_input("Monthly Limit (₹)", min_value=100, max_value=500_000,
                                            value=5000, step=500, key="limit_amt")
            with sl3:
                st.markdown("<br>", unsafe_allow_html=True)
                limit_submitted = st.form_submit_button("➕ Set Limit", use_container_width=True)

        if limit_submitted:
            db.set_category_limit(limit_cat, limit_amt, CURRENT_USER)
            st.toast(f"Limit set: {limit_cat} → {format_inr(limit_amt)}", icon="✅")
            st.rerun()

        if category_limits:
            st.markdown("**Current Limits:**")
            for cat, lim in category_limits.items():
                lc1, lc2, lc3 = st.columns([4, 2, 1])
                with lc1:
                    st.markdown(f"**{cat}**")
                with lc2:
                    st.markdown(f"{format_inr(lim)}/month")
                with lc3:
                    if st.button("🗑️", key=f"rmlimit_{cat}"):
                        db.remove_category_limit(cat, CURRENT_USER)
                        st.toast(f"Removed limit for {cat}", icon="✅")
                        st.rerun()
        else:
            st.info("No category limits set yet.")

    # ─── Alert Threshold ──────────────────────────────────────
    with settings_tab3:
        st.markdown("#### ⚠️ Budget Alert Threshold")
        threshold_key = f"warning_threshold__{CURRENT_USER}"
        threshold_val = int(db.get_config(threshold_key, "20"))
        with st.form("threshold_form"):
            new_threshold = st.slider(
                "Show warning when budget remaining is below",
                min_value=5, max_value=50, value=threshold_val, step=5, format="%d%%",
            )
            threshold_saved = st.form_submit_button("💾 Save Threshold")
        if threshold_saved:
            db.set_config(threshold_key, str(new_threshold))
            st.toast(f"Alert threshold set to {new_threshold}%", icon="✅")
            st.rerun()

    # ─── App Info ────────────────────────────────────────────────
    with settings_tab4:
        st.markdown("#### 🗄️ App Info")
        st.markdown(
            f"<div style='background:rgba(255,255,255,0.04);border-radius:12px;padding:16px;"
            f"border:1px solid rgba(255,255,255,0.08);'>"
            f"<b>Mode:</b> {DB_MODE}<br>"
            f"<b>Total transactions:</b> {len(db.get_transactions(None, CURRENT_USER))}<br>"
            f"<b>Expense categories:</b> {len(EXPENSE_CATS)}<br>"
            f"<b>Investment categories:</b> {len(INVEST_CATS)}</div>",
            unsafe_allow_html=True,
        )

