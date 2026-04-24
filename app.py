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
    _ = st.secrets["gcp_service_account"]
    import sheets as db
    DB_MODE = "☁️ Cloud (Google Sheets)"
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

# ─── Setup Wizard (first-time users) ─────────────────────────
from setup_wizard import is_setup_complete, show_wizard
if not is_setup_complete():
    show_wizard()
    st.stop()  # Don't render the rest of the app until setup is done

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
EXPENSE_CATS  = get_expense_categories(db)
INVEST_CATS   = get_investment_categories(db)

# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 💰 Fintrack")
    st.markdown("---")

    # Month selector
    month_options = get_month_options(6)
    month_labels = {k: get_month_label(k) for k in month_options}
    selected_month = st.selectbox(
        "📅 Select Month",
        options=month_options,
        format_func=lambda x: month_labels[x],
        index=0,
        key="month_selector",
    )

    st.markdown("---")

    # Budget setter
    st.markdown("### 🎯 Monthly Budget")
    current_budget = db.get_budget(selected_month)

    with st.form("budget_form", clear_on_submit=False):
        budget_amount = st.number_input(
            "Total Budget (₹)",
            min_value=0,
            max_value=10_000_000,
            value=int(current_budget) if current_budget > 0 else 25000,
            step=1000,
            key="budget_input",
        )
        budget_submitted = st.form_submit_button("💾 Save Budget", use_container_width=True)

    if budget_submitted:
        db.set_budget(selected_month, budget_amount)
        st.toast(f"Budget set to {format_inr(budget_amount)}!", icon="✅")
        st.rerun()

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
        )
        st.toast(f"✅ {format_inr(q_amount)} added!", icon="💸")
        st.rerun()

    st.markdown("---")
    st.markdown(
        f"<div style='text-align:center;color:#9BA1B0;font-size:0.75rem;'>"
        f"Fintrack v2.0 · Made with ❤️ by Shanky<br>"
        f"<span style='color:#6C63FF;'>{DB_MODE}</span></div>",
        unsafe_allow_html=True,
    )

# ═══════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown('<p class="app-title">💰 Fintrack</p>', unsafe_allow_html=True)
st.markdown(
    f'<p class="app-subtitle">Fintrack — Your financial command center | {get_month_label(selected_month)}</p>',
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════════════════════
expenses_df     = db.get_expenses(selected_month)
investments_df  = db.get_investments(selected_month)
all_txns_df     = db.get_transactions(selected_month)
budget_val      = db.get_budget(selected_month)
category_limits = db.get_category_limits()

spent     = total_spent(expenses_df)
invested  = total_invested(investments_df)
remaining = calculate_remaining(budget_val, expenses_df)
alert     = check_alert(remaining, budget_val)

# ═══════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════
tab_dash, tab_add, tab_history, tab_analytics, tab_settings = st.tabs([
    "📊 Dashboard",
    "➕ Add",
    "📜 History",
    "📈 Analytics",
    "⚙️ Settings",
])

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
            indexed_df = db.get_transactions_with_index(selected_month)
        except AttributeError:
            # sheets.py doesn't have get_transactions_with_index yet
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
            real_idx = int(row["_idx"])
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
                            db.delete_transaction(real_idx)
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
            try:
                all_data = db._load_data()
                orig = all_data["transactions"][eidx]
            except Exception:
                orig = {}

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
                db.update_transaction(eidx, e_date.strftime("%Y-%m-%d"), e_cat, e_amt, e_type, e_note)
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

    # 6-month overview
    st.markdown("#### 📅 6-Month Spending Overview")
    months_6 = get_month_options(6)
    monthly_data = []
    for m in months_6:
        m_exp = db.get_expenses(m)
        m_inv = db.get_investments(m)
        m_bud = db.get_budget(m)
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

        current_exp_cats = get_expense_categories(db)

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
                save_expense_categories(db, current_exp_cats)
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
                    save_expense_categories(db, current_exp_cats)
                    st.toast(f"Removed: {cat}", icon="✅")
                    st.rerun()

        if st.button("🔄 Reset to Defaults", key="reset_exp_cats"):
            save_expense_categories(db, list(DEFAULT_EXPENSE_CATEGORIES))
            st.toast("Reset to default categories", icon="✅")
            st.rerun()

        st.markdown("---")
        st.markdown("#### Investment Categories")
        current_inv_cats = get_investment_categories(db)

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
                save_investment_categories(db, current_inv_cats)
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
                    save_investment_categories(db, current_inv_cats)
                    st.toast(f"Removed: {cat}", icon="✅")
                    st.rerun()

        if st.button("🔄 Reset to Defaults", key="reset_inv_cats"):
            save_investment_categories(db, list(DEFAULT_INVESTMENT_CATEGORIES))
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
            db.set_category_limit(limit_cat, limit_amt)
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
                        db.remove_category_limit(cat)
                        st.toast(f"Removed limit for {cat}", icon="✅")
                        st.rerun()
        else:
            st.info("No category limits set yet.")

    # ─── Alert Threshold ──────────────────────────────────────
    with settings_tab3:
        st.markdown("#### ⚠️ Budget Alert Threshold")
        threshold_val = int(db.get_config("warning_threshold", "20"))
        with st.form("threshold_form"):
            new_threshold = st.slider(
                "Show warning when budget remaining is below",
                min_value=5, max_value=50, value=threshold_val, step=5, format="%d%%",
            )
            threshold_saved = st.form_submit_button("💾 Save Threshold")
        if threshold_saved:
            db.set_config("warning_threshold", str(new_threshold))
            st.toast(f"Alert threshold set to {new_threshold}%", icon="✅")
            st.rerun()

    # ─── App Info ────────────────────────────────────────────────
    with settings_tab4:
        st.markdown("#### 🗄️ App Info")
        st.markdown(
            f"<div style='background:rgba(255,255,255,0.04);border-radius:12px;padding:16px;"
            f"border:1px solid rgba(255,255,255,0.08);'>"
            f"<b>Mode:</b> {DB_MODE}<br>"
            f"<b>Total transactions:</b> {len(db.get_transactions())}<br>"
            f"<b>Expense categories:</b> {len(EXPENSE_CATS)}<br>"
            f"<b>Investment categories:</b> {len(INVEST_CATS)}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("")
        if st.button("🔄 Change Data Storage (Re-run Setup)", key="redo_setup_btn"):
            from setup_wizard import SETUP_DONE_KEY
            st.session_state[SETUP_DONE_KEY] = False
            st.session_state.pop("show_sheets_setup", None)
            st.rerun()

