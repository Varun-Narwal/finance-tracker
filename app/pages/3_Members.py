import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import time
from src.queries import get_all_members, add_member, update_member, delete_member

st.set_page_config(page_title="Members", page_icon="👥", layout="wide")

st.title("👥 Members")
st.markdown("---")

# -----------------------------------------
# ADD MEMBER
# -----------------------------------------

st.subheader("Add Member")

col1, col2, col3 = st.columns(3)

with col1:
    name = st.text_input("Name")
with col2:
    relationship = st.selectbox(
        "Relationship",
        ['self', 'spouse', 'parent', 'child', 'household', 'other']
    )
with col3:
    is_virtual = st.checkbox("Virtual Member (e.g. House)")

if st.button("Add Member", type="primary"):
    if not name:
        st.error("Please enter a name")
        st.stop()
    result = add_member(name, relationship, is_virtual)
    if result:
        st.success(f"Member '{name}' added with ID {result}")
        st.rerun()
    else:
        st.error("Failed to add member — name may already exist")

st.markdown("---")

# -----------------------------------------
# VIEW EDIT DELETE MEMBERS
# -----------------------------------------

st.subheader("View / Edit / Delete Members")

members = get_all_members()

if members:
    df = pd.DataFrame(members)
    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d')
    df.insert(0, "Select", False)

    st.caption("Edit cells directly and click Save. Check Select box to delete.")

    edited_df = st.data_editor(
        df,
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", default=False),
            "member_id": st.column_config.NumberColumn("ID", disabled=True),
            "name": st.column_config.TextColumn("Name"),
            "relationship": st.column_config.SelectboxColumn(
                "Relationship",
                options=['self', 'spouse', 'parent', 'child', 'household', 'other']
            ),
            "is_virtual": st.column_config.CheckboxColumn("Virtual"),
            "created_at": st.column_config.TextColumn("Created At", disabled=True),
        },
        hide_index=True
    )

    col_s, col_d = st.columns(2)

    with col_s:
        if st.button("Save Changes", type="primary"):
            changes = 0
            for idx, row in edited_df.iterrows():
                if pd.notna(row.get('member_id')) and idx in df.index:
                    original_row = df.loc[idx]
                    is_changed = (
                        str(row['name']) != str(original_row['name']) or
                        str(row['relationship']) != str(original_row['relationship']) or
                        str(row['is_virtual']) != str(original_row['is_virtual'])
                    )
                    if is_changed:
                        update_member(
                            int(row['member_id']),
                            name=row['name'],
                            relationship=row['relationship'],
                            is_virtual=bool(row['is_virtual'])
                        )
                        changes += 1
            if changes > 0:
                st.success(f"{changes} member(s) updated successfully")
                st.rerun()
            else:
                st.warning("No changes detected")

    with col_d:
        if st.button("Delete Selected", type="secondary"):
            rows_to_delete = edited_df[edited_df['Select'] == True]
            valid_rows = rows_to_delete.dropna(subset=['member_id'])
            deleted_ids = valid_rows['member_id'].astype(int).tolist()

            if deleted_ids:
                success_count = 0
                for mid in deleted_ids:
                    result = delete_member(mid)
                    if result:
                        success_count += 1
                    else:
                        member_name = valid_rows[
                            valid_rows['member_id'] == mid
                        ]['name'].values[0]
                        st.error(
                            f"Cannot delete '{member_name}' — "
                            f"they have existing transactions. "
                            f"Delete their transactions first."
                        )
                if success_count > 0:
                    st.toast(f"{success_count} member(s) deleted", icon="✅")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("No rows selected for deletion")

    st.caption(f"{len(members)} members total")

else:
    st.info("No members found")