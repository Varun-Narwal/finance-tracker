import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import time
from src.queries import get_all_accounts, add_account, get_all_members, update_account, delete_account

st.set_page_config(page_title="Accounts", page_icon="🏦", layout="wide")

st.title("🏦 Accounts")
st.markdown("---")

# load members for owner dropdown
members = get_all_members()
member_map = {m['name']: m['member_id'] for m in members}

# -----------------------------------------
# ADD ACCOUNT
# -----------------------------------------

st.subheader("Add Account")

col1, col2, col3 = st.columns(3)

with col1:
    bank_name = st.text_input("Account Name / Bank")
with col2:
    account_type = st.selectbox(
        "Account Type",
        ['savings', 'current', 'wallet', 'cash']
    )
with col3:
    owner_name = st.selectbox("Owner", list(member_map.keys()))
    balance = st.number_input("Opening Balance (₹)", min_value=0.0, step=0.01)

if st.button("Add Account", type="primary"):
    if not bank_name:
        st.error("Please enter an account name")
        st.stop()
    owner_id = member_map[owner_name]
    result = add_account(bank_name, account_type, owner_id, balance)
    if result:
        st.success(f"Account '{bank_name}' added with ID {result}")
        st.rerun()
    else:
        st.error("Failed to add account")

st.markdown("---")

# -----------------------------------------
# VIEW / EDIT / DELETE ACCOUNTS
# -----------------------------------------

st.subheader("View / Edit / Delete Accounts")

accounts = get_all_accounts()

if accounts:
    df = pd.DataFrame(accounts)
    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d')
    df.insert(0, "Select", False)

    # replace owner_member_id with name for readability
    id_to_name = {m['member_id']: m['name'] for m in members}
    df['owner'] = df['owner_member_id'].map(id_to_name)

    st.caption("Edit cells directly and click Save. Check Select to delete.")

    edited_df = st.data_editor(
        df,
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", default=False),
            "account_id": st.column_config.NumberColumn("ID", disabled=True),
            "bank_name": st.column_config.TextColumn("Account Name"),
            "account_type": st.column_config.SelectboxColumn(
                "Type", options=['savings', 'current', 'wallet', 'cash']
            ),
            "owner_member_id": st.column_config.NumberColumn("Owner ID", disabled=True),
            "owner": st.column_config.TextColumn("Owner", disabled=True),
            "balance": st.column_config.NumberColumn("Balance (₹)", format="₹%.2f"),
            "created_at": st.column_config.TextColumn("Created At", disabled=True),
        },
        hide_index=True
    )

    original_ids = set(df['account_id'].astype(int))

    col_s, col_d = st.columns(2)

    with col_s:
        if st.button("Save Changes", type="primary"):
            changes = 0
            for idx, row in edited_df.iterrows():
                if idx in df.index:
                    original_row = df.loc[idx]
                    is_changed = (
                        str(row['bank_name']) != str(original_row['bank_name']) or
                        str(row['account_type']) != str(original_row['account_type']) or
                        float(row['balance']) != float(original_row['balance'])
                    )
                    if is_changed:
                        update_account(
                            int(row['account_id']),
                            bank_name=row['bank_name'],
                            account_type=row['account_type'],
                            balance=float(row['balance'])
                        )

                        changes += 1
            if changes > 0:
                st.success(f"{changes} account(s) updated successfully")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("No changes detected")

    with col_d:
        if st.button("Delete Selected", type="secondary"):
            rows_to_delete = edited_df[edited_df['Select'] == True]
            valid_rows = rows_to_delete.dropna(subset=['account_id'])
            deleted_ids = valid_rows['account_id'].astype(int).tolist()

            if deleted_ids:
                success_count = 0
                for aid in deleted_ids:
                    result = delete_account(aid)
                    if result:
                        success_count += 1
                    else:
                        acc_name = valid_rows[
                            valid_rows['account_id'] == aid
                        ]['bank_name'].values[0]
                        st.error(
                            f"Cannot delete '{acc_name}' — "
                            f"it has existing transactions. "
                            f"Delete those transactions first."
                        )
                if success_count > 0:
                    st.toast(f"{success_count} account(s) deleted", icon="✅")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("No rows selected for deletion")

    st.caption(f"{len(accounts)} accounts total")

else:
    st.info("No accounts found")