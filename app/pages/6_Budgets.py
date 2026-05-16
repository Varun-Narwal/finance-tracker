import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import time
from datetime import datetime
from src.queries import get_all_members, get_all_categories, add_budget, update_budget, get_budgets_by_month
from src.analytics import budget_status

st.set_page_config(page_title="Budgets", page_icon="💼", layout="wide")

st.title("💼 Budgets")
st.markdown("---")

# load lookups
members = get_all_members()
categories = get_all_categories()

member_map = {m['name']: m['member_id'] for m in members}
category_map = {c['name']: c['category_id'] for c in categories}

# ------------------------------------------
# ADD BUDGET
# ------------------------------------------

st.subheader("Add Budget")

col1, col2, col3, col4 = st.columns(4)

with col1:
    budget_member = st.selectbox("Member", list(member_map.keys()))
with col2:
    budget_category = st.selectbox("Category", list(category_map.keys()))
with col3:
    budget_amount = st.number_input("Budget Amount (₹)", min_value=1.0, step=100.0)
with col4:
    budget_month = st.date_input(
        "Month",
        value=datetime.now().replace(day=1)
    )

if st.button("Add Budget", type="primary"):
    member_id = member_map[budget_member]
    category_id = category_map[budget_category]
    month_str = budget_month.strftime('%Y-%m-01')
    result = add_budget(category_id, member_id, budget_amount, month_str)
    if result:
        st.success(f"Budget added with ID {result}")
        time.sleep(1)
        st.rerun()
    else:
        st.error("Failed to add budget — one may already exist for this member/category/month combination")

st.markdown("---")

# ------------------------------------------
# BUDGET STATUS
# ------------------------------------------

st.subheader("Budget vs Actual")

current_month = datetime.now().strftime('%Y-%m')
selected_month = st.selectbox(
    "Select Month",
    options=[current_month, '2026-05', '2026-04', '2026-03'],
    index=0,
    key="budget_month_select"
)

selected_month = sorted(set([current_month, '2026-05', '2026-04', '2026-03']), reverse=True)[
    [current_month, '2026-05', '2026-04', '2026-03'].index(selected_month)
]

status_data = budget_status(selected_month)

if status_data:
    status_df = pd.DataFrame(status_data)

    # color code status
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

    # summary metrics
    over_count = len(status_df[status_df['status'] == 'over budget'])
    under_count = len(status_df[status_df['status'] == 'under budget'])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Over Budget", over_count, delta=None)
    with col2:
        st.metric("Under Budget", under_count, delta=None)
    with col3:
        total_diff = status_df['difference'].sum()
        st.metric(
            "Total Remaining",
            f"₹{total_diff:,.2f}",
            delta=None
        )

else:
    st.info("No budget data found for selected month")

st.markdown("---")

# ------------------------------------------
# EDIT BUDGETS
# ------------------------------------------

st.subheader("Edit Budgets")

budgets = get_budgets_by_month(selected_month + '-01')

if budgets:
    df = pd.DataFrame(budgets)
    df['month'] = pd.to_datetime(df['month']).dt.strftime('%Y-%m')
    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d')

    # replace IDs with names
    id_to_member = {m['member_id']: m['name'] for m in members}
    id_to_category = {c['category_id']: c['name'] for c in categories}
    df['member_name'] = df['member_id'].map(id_to_member)
    df['category_name'] = df['category_id'].map(id_to_category)

    edited_df = st.data_editor(
        df,
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "budget_id": st.column_config.NumberColumn("ID", disabled=True),
            "member_id": st.column_config.NumberColumn("Member ID", disabled=True),
            "category_id": st.column_config.NumberColumn("Category ID", disabled=True),
            "member_name": st.column_config.TextColumn("Member", disabled=True),
            "category_name": st.column_config.TextColumn("Category", disabled=True),
            "amount": st.column_config.NumberColumn("Budget Amount (₹)", format="₹%.2f"),
            "month": st.column_config.TextColumn("Month", disabled=True),
            "created_at": st.column_config.TextColumn("Created At", disabled=True),
        },
        hide_index=True
    )

    if st.button("Save Budget Changes", type="primary"):
        changes = 0
        for idx, row in edited_df.iterrows():
            if idx in df.index:
                original_row = df.loc[idx]
                if float(row['amount']) != float(original_row['amount']):
                    update_budget(int(row['budget_id']), float(row['amount']))
                    changes += 1
        if changes > 0:
            st.success(f"{changes} budget(s) updated successfully")
            time.sleep(1)
            st.rerun()
        else:
            st.warning("No changes detected")

else:
    st.info("No budgets found for selected month")