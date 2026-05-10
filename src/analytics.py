import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.queries import (
    get_all_transactions,
    get_transactions_by_member,
    get_budget_vs_actual,
    get_all_members,
    get_all_categories
)
import pandas as pd

def monthly_summary(month):
    try:
        transactions = get_all_transactions()
        if transactions is None:
            return None
        df = pd.DataFrame(transactions)
        if df.empty:
            return {'total_income': 0, 'total_expense': 0, 'total_savings': 0}
        df['date'] = pd.to_datetime(df['date'])
        filtered = df[
            (df['date'].dt.strftime('%Y-%m') == month) &
            (df['type'].isin(['income', 'expense']))
        ]
        total_income = filtered[filtered['type'] == 'income']['amount'].sum()
        total_expense = filtered[filtered['type'] == 'expense']['amount'].sum()
        total_savings = total_income - total_expense
        return {
            'total_income': float(total_income),
            'total_expense': float(total_expense),
            'total_savings': float(total_savings)
        }
    except Exception as e:
        print(f"Error in monthly_summary: {e}")
        return None

def member_spend_breakdown(month):
    try:
        transactions = get_all_transactions()
        if transactions is None:
            return None
        df = pd.DataFrame(transactions)
        if df.empty:
            return []
        df['date'] = pd.to_datetime(df['date'])
        filtered = df[
            (df['date'].dt.strftime('%Y-%m') == month) &
            (df['type'] == 'expense')
        ]
        if filtered.empty:
            return []
        grouped = filtered.groupby('member_id')['amount'].sum().reset_index()
        members = get_all_members()
        if members is None:
            return None
        member_df = pd.DataFrame(members)
        merged = pd.merge(grouped, member_df, on='member_id', how='left')
        merged = merged[['name', 'amount']].rename(columns={
            'name': 'member_name',
            'amount': 'total_spent'
        })
        merged['total_spent'] = merged['total_spent'].apply(float)
        return merged.to_dict('records')
    except Exception as e:
        print(f"Error in member_spend_breakdown: {e}")
        return None

def category_spend_breakdown(month):
    try:
        transactions = get_all_transactions()
        if transactions is None:
            return None
        df = pd.DataFrame(transactions)
        if df.empty:
            return []
        df['date'] = pd.to_datetime(df['date'])
        filtered = df[
            (df['date'].dt.strftime('%Y-%m') == month) &
            (df['type'] == 'expense')
        ]
        if filtered.empty:
            return []
        grouped = filtered.groupby('category_id')['amount'].sum().reset_index()
        categories = get_all_categories()
        if categories is None:
            return None
        category_df = pd.DataFrame(categories)
        merged = pd.merge(grouped, category_df, on='category_id', how='left')
        merged = merged[['name', 'amount']].rename(columns={
            'name': 'category_name',
            'amount': 'total_spent'
        })
        merged['total_spent'] = merged['total_spent'].apply(float)
        return merged.to_dict('records')
    except Exception as e:
        print(f"Error in category_spend_breakdown: {e}")
        return None

def budget_status(month):
    try:
        budget_data = get_budget_vs_actual(month + '-01')
        if budget_data is None:
            return None
        df = pd.DataFrame(budget_data)
        if df.empty:
            return []
        df['status'] = df['difference'].apply(
            lambda x: 'over budget' if x < 0 else 'under budget'
        )
        members = get_all_members()
        if members is None:
            return None
        member_df = pd.DataFrame(members)
        categories = get_all_categories()
        if categories is None:
            return None
        category_df = pd.DataFrame(categories)
        merged = pd.merge(df, member_df, on='member_id', how='left')
        merged = merged.rename(columns={'name': 'member_name'})
        merged = pd.merge(merged, category_df, on='category_id', how='left')
        merged = merged.rename(columns={'name': 'category_name'})
        merged = merged[[
            'member_name', 'category_name', 'budgeted_amount',
            'actual_spent', 'difference', 'status'
        ]]
        for col in ['budgeted_amount', 'actual_spent', 'difference']:
            merged[col] = merged[col].apply(float)
        return merged.to_dict('records')
    except Exception as e:
        print(f"Error in budget_status: {e}")
        return None

def spending_trend(member_id, num_months):
    try:
        transactions = get_transactions_by_member(member_id)
        if transactions is None:
            return None
        df = pd.DataFrame(transactions)
        if df.empty:
            return []
        df['date'] = pd.to_datetime(df['date'])
        filtered = df[df['type'] == 'expense'].copy()
        if filtered.empty:
            return []
        filtered['month'] = filtered['date'].dt.to_period('M').astype(str)
        grouped = filtered.groupby('month')['amount'].sum().reset_index()
        grouped.sort_values('month', ascending=True, inplace=True)
        grouped = grouped.tail(num_months)
        grouped['amount'] = grouped['amount'].apply(float)
        grouped = grouped.rename(columns={'amount': 'total_spent'})
        return grouped.to_dict('records')
    except Exception as e:
        print(f"Error in spending_trend: {e}")
        return None