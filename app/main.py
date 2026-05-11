import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

st.set_page_config(
    page_title="Personal Finance Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("Personal Finance Tracker")
st.markdown("---")

st.markdown("""
Welcome to your personal family finance tracker.
Use the sidebar to navigate between sections.

### Quick Guide
- **Dashboard** — monthly summary and KPI cards
- **Transactions** — add and view transactions
- **Members** — manage family members
- **Accounts** — manage bank accounts
- **Categories** — manage expense categories
- **Budgets** — set and track budgets
- **Analytics** — trends and calculations
""")

st.sidebar.success("Select a page above to get started.")