import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
from datetime import datetime
from src.analytics import (
    monthly_summary,
    member_spend_breakdown,
    category_spend_breakdown,
    budget_status,
    spending_trend
)
from src.calculations import (
    compare_months,
    compare_members,
    daily_average,
    weekly_average,
    overall_monthly_average,
    category_percentage,
    savings_rate,
    running_balance,
    net_worth
)
from src.queries import get_all_members, get_all_accounts, get_all_categories
from datetime import timedelta

st.set_page_config(page_title="Analytics", page_icon="📈", layout="wide")

st.title("📈 Analytics")
st.markdown("---")

# load lookups
members = get_all_members()
accounts = get_all_accounts()
categories = get_all_categories()

member_map    = {m['name']: m['member_id'] for m in members}
account_map   = {a['bank_name']: a['account_id'] for a in accounts}
category_map  = {c['name']: c['category_id'] for c in categories}

def get_last_n_months(n=6):
    months = []
    for i in range(n):
        date = datetime.now().replace(day=1) - timedelta(days=i*30)
        months.append(date.strftime('%Y-%m'))
    seen = set()
    unique = []
    for m in months:
        if m not in seen:
            seen.add(m)
            unique.append(m)
    return unique

# -----------------------------------------
# TABS
# -----------------------------------------

tab1, tab2, tab3 = st.tabs(["📊 Summary", "📉 Trends", "🔍 Comparisons"])

# -----------------------------------------
# TAB 1 — SUMMARY
# -----------------------------------------

with tab1:

    selected_month = st.selectbox(
        "Select Month",
        options=get_last_n_months(12),
        index=0,
        key="analytics_month"
    )

    st.markdown("---")

    # -- KPI Cards --
    st.subheader("Monthly Summary")

    summary   = monthly_summary(selected_month)
    s_rate    = savings_rate(selected_month)

    if summary:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Income", f"₹{summary['total_income']:,.2f}")
        with col2:
            st.metric("Total Expense", f"₹{summary['total_expense']:,.2f}")
        with col3:
            st.metric("Total Savings", f"₹{summary['total_savings']:,.2f}")
        with col4:
            st.metric("Savings Rate", f"{s_rate}%")
    else:
        st.info("No data for selected month")

    st.markdown("---")

    # -- Spend Breakdowns --
    st.subheader("Spend Breakdowns")

    member_breakdown   = member_spend_breakdown(selected_month)
    category_breakdown = category_spend_breakdown(selected_month)

    col5, col6 = st.columns(2)

    with col5:
        st.markdown("**By Member**")
        if member_breakdown:
            member_df = pd.DataFrame(member_breakdown)
            st.bar_chart(member_df.set_index('member_name')['total_spent'])
        else:
            st.info("No expense data for this month")

    with col6:
        st.markdown("**By Category**")
        if category_breakdown:
            cat_df = pd.DataFrame(category_breakdown)
            st.bar_chart(cat_df.set_index('category_name')['total_spent'])
        else:
            st.info("No expense data for this month")

    st.markdown("---")

    # -- Budget Status --
    st.subheader("Budget vs Actual")

    status_data = budget_status(selected_month)

    if status_data:
        status_df = pd.DataFrame(status_data)

        def highlight_status(row):
            if row['status'] == 'over budget':
                return ['background-color: #ffcccc'] * len(row)
            else:
                return ['background-color: #ccffcc'] * len(row)

        st.dataframe(
            status_df.style.apply(highlight_status, axis=1),
            use_container_width=True,
            hide_index=True
        )

        over_count  = len(status_df[status_df['status'] == 'over budget'])
        under_count = len(status_df[status_df['status'] == 'under budget'])
        total_diff  = status_df['difference'].sum()

        col7, col8, col9 = st.columns(3)
        with col7:
            st.metric("Over Budget",     over_count)
        with col8:
            st.metric("Under Budget",    under_count)
        with col9:
            st.metric("Total Remaining", f"₹{total_diff:,.2f}")
    else:
        st.info("No budget data for selected month")


# -----------------------------------------
# TAB 2 — TRENDS
# -----------------------------------------

with tab2:

    st.markdown("---")

    # -- Spending Trend --
    st.subheader("Spending Trend")

    trend_member = st.selectbox(
        "Select Member",
        list(member_map.keys()),
        key="trend_member"
    )

    n_months = st.slider(
        "Last N months",
        min_value=3,
        max_value=24,
        value=6
    )
    member_id = member_map[trend_member]
    trend_data = spending_trend(member_id, n_months)

    if trend_data:
        trend_df = pd.DataFrame(trend_data)
        st.line_chart(trend_df.set_index('month')['total_spent'])
    else:
        st.info("No spending data found for this member")

    st.markdown("---")

    # -- Running Balance --
    st.subheader("Running Balance")

    selected_account = st.selectbox(
        "Select Account",
        list(account_map.keys()),
        key="balance_account"
    )

    account_id = account_map[selected_account]
    balance_data = running_balance(account_id)

    if balance_data:
        balance_df = pd.DataFrame(balance_data)
        balance_df['date'] = pd.to_datetime(balance_df['date'])
        st.line_chart(balance_df.set_index('date')['running_balance'])
    else:
        st.info("No transaction history for this account")

    st.markdown("---")

    # -- Net Worth --
    st.subheader("Net Worth")

    nw = net_worth()
    st.metric("Total Net Worth Across All Accounts", f"₹{nw:,.2f}")


# -----------------------------------------
# TAB 3 — COMPARISONS
# -----------------------------------------

with tab3:

    st.markdown("---")

    # -- Month Comparison --
    st.subheader("Month Comparison")

    month_options = get_last_n_months(12)
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        month1 = st.selectbox("Month 1", month_options, index=1, key="month1")
    with col_m2:
        month2 = st.selectbox("Month 2", month_options, index=0, key="month2")

    if month1 == month2:
        st.warning("Please select two different months")
    else:
        comparison = compare_months(month1, month2)
        if comparison:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Income Change",
                    f"₹{comparison['income_change']:,.2f}",
                    delta=f"{comparison['income_pct']}%" if comparison['income_pct'] else "N/A"
                )
            with col2:
                st.metric(
                    "Expense Change",
                    f"₹{comparison['expense_change']:,.2f}",
                    delta=f"{comparison['expense_pct']}%" if comparison['expense_pct'] else "N/A"
                )
            with col3:
                st.metric(
                    "Savings Change",
                    f"₹{comparison['savings_change']:,.2f}",
                    delta=f"{comparison['savings_pct']}%" if comparison['savings_pct'] else "N/A"
                )
        else:
            st.info("No data available for comparison")

    st.markdown("---")

    # -- Member Rankings --
    st.subheader("Member Rankings")

    ranking_month = st.selectbox(
        "Select Month",
        get_last_n_months(12),
        index=0,
        key="ranking_month"
    )

    rankings = compare_members(ranking_month)
    if rankings:
        rank_df = pd.DataFrame(rankings)
        st.dataframe(rank_df, use_container_width=True, hide_index=True)
    else:
        st.info("No spend data for selected month")

    st.markdown("---")

    # -- Averages --
    st.subheader("Spending Averages")

    avg_member = st.selectbox(
        "Select Member",
        list(member_map.keys()),
        key="avg_member"
    )
    avg_month = st.selectbox(
        "Select Month",
        get_last_n_months(12),
        index=0,
        key="avg_month"
    )

    avg_member_id = member_map[avg_member]
    d_avg  = daily_average(avg_member_id, avg_month)
    w_avg  = weekly_average(avg_member_id, avg_month)
    om_avg = overall_monthly_average(avg_member_id)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Daily Average",          f"₹{d_avg:,.2f}"  if d_avg  else "₹0.00")
    with col2:
        st.metric("Weekly Average",         f"₹{w_avg:,.2f}"  if w_avg  else "₹0.00")
    with col3:
        st.metric("Overall Monthly Average",f"₹{om_avg:,.2f}" if om_avg else "₹0.00")

    st.markdown("---")

    # -- Category Percentage --
    st.subheader("Category Percentage of Total Spend")

    col_cp1, col_cp2 = st.columns(2)
    with col_cp1:
        pct_category = st.selectbox(
            "Select Category",
            list(category_map.keys()),
            key="pct_category"
        )
    with col_cp2:
        pct_month = st.selectbox(
            "Select Month",
            get_last_n_months(12),
            index=0,
            key="pct_month"
        )

    cat_id = category_map[pct_category]
    pct = category_percentage(cat_id, pct_month)

    if pct is not None:
        st.metric(
            f"{pct_category} as % of total spend in {pct_month}",
            f"{pct}%"
        )
        st.progress(min(pct / 100, 1.0))
    else:
        st.info("No data available")