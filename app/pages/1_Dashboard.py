import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from src.analytics import monthly_summary, member_spend_breakdown, category_spend_breakdown
from src.calculations import savings_rate, net_worth

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

st.title("📊 Dashboard")
st.markdown("---")

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

selected_month = st.selectbox(
    "Select Month",
    options=get_last_n_months(6),
    index=0
)

st.markdown(f"### Summary for {selected_month}")
st.markdown("---")

# fetch data
summary = monthly_summary(selected_month)
s_rate = savings_rate(selected_month)
nw = net_worth()
member_breakdown = member_spend_breakdown(selected_month)
category_breakdown = category_spend_breakdown(selected_month)

if summary:
    # KPI cards row 1
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Income", f"₹{summary['total_income']:,.2f}")
    with col2:
        st.metric("Total Expense", f"₹{summary['total_expense']:,.2f}")
    with col3:
        st.metric("Total Savings", f"₹{summary['total_savings']:,.2f}")
    with col4:
        st.metric("Savings Rate", f"{s_rate}%")

    st.markdown("---")

    # KPI cards row 2
    col5, col6 = st.columns(2)
    with col5:
        st.metric("Biggest Spender", 
              member_breakdown[0]['member_name'] if member_breakdown else "N/A")
    with col6:
        st.metric("Net Worth", f"₹{nw:,.2f}")
        
    st.markdown("---")

    # charts
    col7, col8 = st.columns(2)

    with col7:
        st.subheader("Spend by Member")
        if member_breakdown:
            member_df = pd.DataFrame(member_breakdown)
            st.bar_chart(member_df.set_index('member_name')['total_spent'])
        else:
            st.info("No expense data for this month")

    with col8:
        st.subheader("Spend by Category")
        if category_breakdown:
            cat_df = pd.DataFrame(category_breakdown)
            st.bar_chart(cat_df.set_index('category_name')['total_spent'])
        else:
            st.info("No expense data for this month")

else:
    st.warning("No data available for selected month")