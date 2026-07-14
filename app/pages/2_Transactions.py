import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import time
from datetime import datetime
from src.queries import (
    add_transaction, get_all_transactions,
    get_all_members, get_all_accounts, get_all_categories,
    delete_transaction, update_transaction, add_category
)

import requests
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://localhost:8001")

st.set_page_config(page_title="Transactions", page_icon="💸", layout="wide")

st.title("💸 Transactions")
st.markdown("---")

# load lookup data
members = get_all_members()
accounts = get_all_accounts()
categories = get_all_categories()

member_map = {m['name']: m['member_id'] for m in members}
account_map = {a['bank_name']: a['account_id'] for a in accounts}
category_map = {c['name']: c['category_id'] for c in categories}

if "ml_suggestion" not in st.session_state:
    st.session_state["ml_suggestion"] = None

#------------------------------------------
# ADD TRANSACTION
#------------------------------------------

# Initialize state for multiple suggestions if it doesn't exist
if "ml_suggestions" not in st.session_state:
    st.session_state["ml_suggestions"] = []

st.subheader("Add Transaction")

col1, col2 = st.columns(2)

with col1:
    amount = st.number_input("Amount (₹)", min_value=0.01, step=0.01)
    transaction_type = st.selectbox("Type", ['income', 'expense', 'transfer'])
    method = st.selectbox("Method", ['upi', 'cash', 'internet_banking', 'cheque'])

with col2:
    member_name = st.selectbox("Member", list(member_map.keys()))
    account_name = st.selectbox("Account", list(account_map.keys()))
    transaction_date = st.date_input("Date", value=datetime.now())
    
    to_account_name = None
    if transaction_type == "transfer":
        to_account_name = st.selectbox(
            "To Account",
            [a for a in account_map.keys() if a != account_name],
            key="to_account"
        )

st.markdown("<br>", unsafe_allow_html=True)
note = st.text_input("Note (optional)", key="txn_note")

cat_col, btn_col = st.columns([4, 1])

with btn_col:
    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
    suggest_clicked = st.button("✨ Suggest", use_container_width=True)

if suggest_clicked:
    if amount > 0 and transaction_type != "transfer":
        with st.spinner("Predicting..."):
            try:
                resp = requests.post(
                    f"{ML_SERVICE_URL}/categorize/predict",
                    json={
                        "member_id": member_map[member_name],
                        "amount":    float(amount),
                        "type":      transaction_type,
                        "method":    method,
                        "date":      datetime.combine(transaction_date, datetime.min.time()).isoformat(),
                        "note":      note if note else None,
                        "account_id": account_map[account_name],
                        "top_n":     3, 
                    },
                    timeout=5,
                )
                data = resp.json()
                if data.get("status") == "ok" and data.get("suggestions"):
                    # Extract all suggestion names into a list
                    suggestions = [s["category_name"] for s in data["suggestions"]]
                    st.session_state["ml_suggestions"] = suggestions
                    
                    # Force the selectbox to visually snap to the #1 suggestion
                    if suggestions and suggestions[0] in category_map:
                        st.session_state["category_select"] = suggestions[0]
                    
                    st.rerun()
            except Exception:
                st.error("ML service currently unavailable.")
    else:
        st.warning("Enter an amount and ensure type is not 'transfer'.")

with cat_col:
    base_options = list(category_map.keys())
    
    suggested_options = [
        s for s in st.session_state.get("ml_suggestions", []) 
        if s in base_options
    ]
    
    remaining_options = [c for c in base_options if c not in suggested_options]
    
    # Top 3 suggestions first -> Remaining categories -> Add new
    ordered_options = suggested_options + remaining_options + ["+ Add new category"]

    category_name = st.selectbox("Category", ordered_options, key="category_select")

if category_name == "+ Add new category":
    new_cat_col1, new_cat_col2 = st.columns(2)
    with new_cat_col1:
        new_cat_name = st.text_input("New Category Name")
        type_hint    = st.selectbox("Category Type", ["expense", "income"])
    with new_cat_col2:
        parent_options = ["None"] + [c["name"] for c in categories if c["parent_id"] is None]
        parent_name = st.selectbox("Parent Category", parent_options)

if st.button("Add Transaction", type="primary"):
    if category_name == "+ Add new category":
        if not new_cat_name:
            st.error("Please enter a category name")
            st.stop()
        parent_id = category_map.get(parent_name) if parent_name != "None" else None
        new_cat_id = add_category(new_cat_name, type_hint, parent_id)
        if not new_cat_id:
            st.error("Failed to add new category")
            st.stop()
        category_id = new_cat_id
        st.success(f"Category '{new_cat_name}' added successfully")
    else:
        category_id = category_map.get(category_name)

    member_id = member_map[member_name]
    account_id = account_map[account_name]
    to_account_id = account_map.get(to_account_name) if to_account_name else None

    if transaction_type == 'transfer' and not to_account_id:
        st.error("Please select a destination account for transfer")
        st.stop()

    result = add_transaction(
        amount=amount,
        transaction_type=transaction_type,
        method=method,
        member_id=member_id,
        account_id=account_id,
        category_id=category_id if transaction_type != 'transfer' else None,
        target_account_id=to_account_id,
        note=note if note else None,
        transaction_date=transaction_date
    )

    if result:
        st.success(f"Transaction added successfully with ID {result}")
        st.session_state["ml_suggestions"] = []
        time.sleep(1)
        st.rerun()
    else:
        st.error("Failed to add transaction")

st.markdown("---")

#------------------------------------------
# VIEW EDIT DELETE TRANSACTIONS
#------------------------------------------

st.subheader("View / Edit / Delete Transactions")

transactions = get_all_transactions()

if transactions:
    df = pd.DataFrame(transactions)
    original_df = df.copy()
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    df.insert(0, "Select", False) 

    # filters
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filter_type = st.selectbox(
            "Filter by Type",
            ['All', 'income', 'expense', 'transfer']
        )
    with col_f2:
        filter_member = st.selectbox(
            "Filter by Member",
            ['All'] + list(member_map.keys())
        )
    with col_f3:
        filter_month = st.text_input("Filter by Month (YYYY-MM)", "")

    if filter_type != 'All':
        df = df[df['type'] == filter_type]
    if filter_member != 'All':
        df = df[df['member_id'] == member_map[filter_member]]
    if filter_month:
        df = df[df['date'].str.startswith(filter_month)]

    st.caption("Edit cells directly and click Save. To delete, check the 'Select' box and click Delete.")

    edited_df = st.data_editor(
        df,
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", default=False), # 2. Configure the new column
            "transaction_id": st.column_config.NumberColumn("ID", disabled=True),
            "amount": st.column_config.NumberColumn("Amount (₹)", min_value=0.01),
            "type": st.column_config.SelectboxColumn(
                "Type", options=['income', 'expense', 'transfer']
            ),
            "method": st.column_config.SelectboxColumn(
                "Method", options=['upi', 'cash', 'internet_banking', 'cheque']
            ),
            "date": st.column_config.TextColumn("Date"),
        },
        hide_index=True
    )

    col_s, col_d = st.columns(2)

    with col_s:
        if st.button("Save Changes", type="primary"):
            changes = 0
            for idx, row in edited_df.iterrows():
                if pd.notna(row.get('transaction_id')) and idx in df.index:
                    original_row = df.loc[idx]
                    
                    is_changed = (
                        str(row['amount']) != str(original_row['amount']) or
                        str(row['type']) != str(original_row['type']) or
                        str(row['method']) != str(original_row['method']) or
                        str(row['date']) != str(original_row['date'])
                    )
                    
                    if 'note' in row and 'note' in original_row:
                        if str(row['note']) != str(original_row['note']):
                            is_changed = True

                    if is_changed:
                        note_val = row['note'] if 'note' in row else ""
                        update_transaction(
                            int(row['transaction_id']),
                            amount=float(row['amount']),
                            transaction_type=row['type'],
                            method=row['method'],
                            note=note_val,
                            transaction_date=row['date']
                        )
                        changes += 1
                        
            if changes > 0:
                st.success(f"{changes} transaction(s) updated successfully")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("No changes detected.")

    with col_d:
        if st.button("Delete Selected Rows", type="secondary"):
            rows_to_delete = edited_df[edited_df['Select'] == True]
            
            # Drop NaNs to ensure we don't try to delete a blank dynamically added row
            valid_tids = rows_to_delete.dropna(subset=['transaction_id'])
            deleted_ids = valid_tids['transaction_id'].astype(int).tolist()
            
            if deleted_ids:
                for tid in deleted_ids:
                    delete_transaction(tid)
                st.toast(f"{len(deleted_ids)} transaction(s) deleted", icon="✅")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("No valid rows deleted. Please check the 'Select' box first.")

else:
    st.info("No transactions found")

st.markdown("---")

#------------------------------------------
# CSV INGESTION
#------------------------------------------

st.subheader("Bulk Import via CSV")
st.caption("Upload a CSV file matching the template format")

uploaded_file = st.file_uploader("Choose CSV file", type=['csv'])

if uploaded_file:
    temp_path = f"/tmp/{uploaded_file.name}"
    with open(temp_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Preview CSV"):
            preview_df = pd.read_csv(temp_path)
            st.dataframe(preview_df, use_container_width=True)
    with col_b:
        if st.button("Run Ingestion", type="primary"):
            from src.ingest import bulk_ingest_csv
            with st.spinner("Ingesting data..."):
                result = bulk_ingest_csv(temp_path)
            if result:
                st.success(f"Successfully inserted {result} transactions")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Ingestion failed — check CSV format")