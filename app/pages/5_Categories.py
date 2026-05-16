import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
import time
from src.queries import get_all_categories, add_category, delete_category, update_category

st.set_page_config(page_title="Categories", page_icon="🏷️", layout="wide")

st.title("🏷️ Categories")
st.markdown("---")

# -----------------------------------------
# ADD CATEGORY
# -----------------------------------------

st.subheader("Add Category")

categories = get_all_categories()
parent_categories = [c for c in categories if c['parent_id'] is None]
parent_map = {c['name']: c['category_id'] for c in parent_categories}

col1, col2, col3 = st.columns(3)

with col1:
    cat_name = st.text_input("Category Name")
with col2:
    type_hint = st.selectbox("Type", ['expense', 'income'])
with col3:
    parent_options = ["None (Top Level)"] + list(parent_map.keys())
    parent_name = st.selectbox("Parent Category", parent_options)

if st.button("Add Category", type="primary"):
    if not cat_name:
        st.error("Please enter a category name")
        st.stop()
    parent_id = parent_map.get(parent_name) if parent_name != "None (Top Level)" else None
    result = add_category(cat_name, type_hint, parent_id)
    if result:
        st.success(f"Category '{cat_name}' added with ID {result}")
        time.sleep(1)
        st.rerun()
    else:
        st.error("Failed to add category — name may already exist")

st.markdown("---")

# -----------------------------------------
# VIEW CATEGORY TREE
# -----------------------------------------

st.subheader("Category Tree")

if categories:
    # tree view
    parent_cats = [c for c in categories if c['parent_id'] is None]
    child_cats  = [c for c in categories if c['parent_id'] is not None]

    tree_rows = []
    for parent in parent_cats:
        tree_rows.append({
            'category_id': parent['category_id'],
            'name': f"📁 {parent['name']}",
            'type_hint': parent['type_hint'],
            'parent': '—'
        })
        children = [c for c in child_cats if c['parent_id'] == parent['category_id']]
        for child in children:
            tree_rows.append({
                'category_id': child['category_id'],
                'name': f"    └─ {child['name']}",
                'type_hint': child['type_hint'],
                'parent': parent['name']
            })

    tree_df = pd.DataFrame(tree_rows)
    st.dataframe(tree_df, use_container_width=True, hide_index=True)
    st.caption(f"{len(categories)} categories total — {len(parent_cats)} top level, {len(child_cats)} subcategories")

else:
    st.info("No categories found")

st.markdown("---")

# -----------------------------------------
# EDIT / DELETE CATEGORIES
# -----------------------------------------

st.subheader("Edit / Delete Categories")

if categories:
    df = pd.DataFrame(categories)
    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d')

    id_to_name = {c['category_id']: c['name'] for c in categories}
    df['parent_name'] = df['parent_id'].apply(
        lambda x: id_to_name.get(x, '—') if pd.notna(x) else '—'
    )
    df.insert(0, "Select", False)

    edited_df = st.data_editor(
        df,
        num_rows="fixed",
        use_container_width=True,
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", default=False),
            "category_id": st.column_config.NumberColumn("ID", disabled=True),
            "name": st.column_config.TextColumn("Name"),
            "type_hint": st.column_config.SelectboxColumn(
                "Type", options=['expense', 'income']
            ),
            "parent_id": st.column_config.NumberColumn("Parent ID", disabled=True),
            "parent_name": st.column_config.TextColumn("Parent", disabled=True),
            "created_at": st.column_config.TextColumn("Created At", disabled=True),
        },
        hide_index=True
    )

    original_ids = set(df['category_id'].astype(int))

    col_s, col_d = st.columns(2)

    with col_s:
        if st.button("Save Changes", type="primary"):
            changes = 0
            for idx, row in edited_df.iterrows():
                if idx in df.index:
                    original_row = df.loc[idx]
                    is_changed = (
                        str(row['name']) != str(original_row['name']) or
                        str(row['type_hint']) != str(original_row['type_hint'])
                    )
                    if is_changed:
                        update_category(
                            int(row['category_id']),
                            name=row['name'],
                            type_hint=row['type_hint']
                        )
                        changes += 1
            if changes > 0:
                st.success(f"{changes} category(ies) updated successfully")
                time.sleep(1)
                st.rerun()
            else:
                st.warning("No changes detected")

    with col_d:
        if st.button("Delete Selected", type="secondary"):
            rows_to_delete = edited_df[edited_df['Select'] == True]
            valid_rows = rows_to_delete.dropna(subset=['category_id'])
            deleted_ids = valid_rows['category_id'].astype(int).tolist()

            if deleted_ids:
                success_count = 0
                for cid in deleted_ids:
                    result = delete_category(cid)
                    if result:
                        success_count += 1
                    else:
                        cat_name = valid_rows[
                            valid_rows['category_id'] == cid
                        ]['name'].values[0]
                        st.error(
                            f"Cannot delete '{cat_name}' — "
                            f"it has existing transactions or subcategories. "
                            f"Remove those first."
                        )
                if success_count > 0:
                    st.toast(f"{success_count} category(ies) deleted", icon="✅")
                    time.sleep(1)
                    st.rerun()
            else:
                st.warning("No rows selected for deletion")