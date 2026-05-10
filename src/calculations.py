import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics import monthly_summary, spending_trend
from src.queries import get_all_transactions, get_all_accounts, get_transactions_by_member
import pandas as pd

# -----------------------------------------
# PERIOD COMPARISONS
# -----------------------------------------

def compare_months(month1, month2):
    try:
        summary1 = monthly_summary(month1)
        summary2 = monthly_summary(month2)
        if summary1 is None or summary2 is None:
            return None

        def pct_change(old, new):
            if old == 0:
                return None
            return round(((new - old) / old) * 100, 2)

        return {
            'month1': month1,
            'month2': month2,
            'income_change':   round(summary2['total_income'] - summary1['total_income'], 2),
            'expense_change':  round(summary2['total_expense'] - summary1['total_expense'], 2),
            'savings_change':  round(summary2['total_savings'] - summary1['total_savings'], 2),
            'income_pct':      pct_change(summary1['total_income'], summary2['total_income']),
            'expense_pct':     pct_change(summary1['total_expense'], summary2['total_expense']),
            'savings_pct':     pct_change(summary1['total_savings'], summary2['total_savings']),
        }
    except Exception as e:
        print(f"Error in compare_months: {e}")
        return None


def compare_members(month):
    try:
        from src.analytics import member_spend_breakdown
        result = member_spend_breakdown(month)
        if result is None or len(result) == 0:
            return []
        df = pd.DataFrame(result)
        df = df.sort_values('total_spent', ascending=False).reset_index(drop=True)
        df['rank'] = df.index + 1
        df['label'] = ''
        df.loc[0, 'label'] = 'highest spender'
        df.loc[df.index[-1], 'label'] = 'lowest spender'
        df['total_spent'] = df['total_spent'].apply(lambda x: round(float(x), 2))
        return df.to_dict('records')
    except Exception as e:
        print(f"Error in compare_members: {e}")
        return None

# -----------------------------------------
# AVERAGES
# -----------------------------------------

def daily_average(member_id, month):
    try:
        transactions = get_transactions_by_member(member_id)
        if transactions is None:
            return None
        df = pd.DataFrame(transactions)
        if df.empty:
            return 0.0
        df['date'] = pd.to_datetime(df['date'])
        filtered = df[
            (df['date'].dt.strftime('%Y-%m') == month) &
            (df['type'] == 'expense')
        ]
        if filtered.empty:
            return 0.0
        total = filtered['amount'].sum()
        days = filtered['date'].dt.day.max()
        return round(float(total / days), 2)
    except Exception as e:
        print(f"Error in daily_average: {e}")
        return None


def weekly_average(member_id, month):
    try:
        transactions = get_transactions_by_member(member_id)
        if transactions is None:
            return None
        df = pd.DataFrame(transactions)
        if df.empty:
            return 0.0
        df['date'] = pd.to_datetime(df['date'])
        filtered = df[
            (df['date'].dt.strftime('%Y-%m') == month) &
            (df['type'] == 'expense')
        ]
        if filtered.empty:
            return 0.0
        total = filtered['amount'].sum()
        return round(float(total / 4), 2)
    except Exception as e:
        print(f"Error in weekly_average: {e}")
        return None


def overall_monthly_average(member_id):
    try:
        trend = spending_trend(member_id, num_months=120)
        if trend is None or len(trend) == 0:
            return 0.0
        df = pd.DataFrame(trend)
        return round(float(df['total_spent'].mean()), 2)
    except Exception as e:
        print(f"Error in overall_monthly_average: {e}")
        return None

# -----------------------------------------
# PERCENTAGES
# -----------------------------------------

def category_percentage(category_id, month):
    try:
        transactions = get_all_transactions()
        if transactions is None:
            return None
        df = pd.DataFrame(transactions)
        if df.empty:
            return 0.0
        df['date'] = pd.to_datetime(df['date'])
        filtered = df[
            (df['date'].dt.strftime('%Y-%m') == month) &
            (df['type'] == 'expense')
        ]
        if filtered.empty:
            return 0.0
        total_spend = filtered['amount'].sum()
        category_spend = filtered[
            filtered['category_id'] == category_id
        ]['amount'].sum()
        if total_spend == 0:
            return 0.0
        return round(float((category_spend / total_spend) * 100), 2)
    except Exception as e:
        print(f"Error in category_percentage: {e}")
        return None


def savings_rate(month):
    try:
        summary = monthly_summary(month)
        if summary is None:
            return None
        if summary['total_income'] == 0:
            return 0.0
        rate = (summary['total_savings'] / summary['total_income']) * 100
        return round(rate, 2)
    except Exception as e:
        print(f"Error in savings_rate: {e}")
        return None

# -----------------------------------------
# RUNNING TOTALS
# -----------------------------------------

def running_balance(account_id):
    try:
        transactions = get_all_transactions()
        if transactions is None:
            return None
        df = pd.DataFrame(transactions)
        if df.empty:
            return []
        df['date'] = pd.to_datetime(df['date'])
        account_df = df[
            (df['account_id'] == account_id) |
            (df['target_account_id'] == account_id)
        ].copy()
        if account_df.empty:
            return []
        account_df = account_df.sort_values('date')

        def balance_delta(row):
            if row['type'] == 'income' and row['account_id'] == account_id:
                return float(row['amount'])
            elif row['type'] == 'expense' and row['account_id'] == account_id:
                return -float(row['amount'])
            elif row['type'] == 'transfer':
                if row['account_id'] == account_id:
                    return -float(row['amount'])
                elif row['target_account_id'] == account_id:
                    return float(row['amount'])
            return 0.0

        account_df['delta'] = account_df.apply(balance_delta, axis=1)
        account_df['running_balance'] = account_df['delta'].cumsum()
        result = account_df[['date', 'running_balance']].copy()
        result['date'] = result['date'].astype(str)
        result['running_balance'] = result['running_balance'].apply(
            lambda x: round(x, 2)
        )
        return result.to_dict('records')
    except Exception as e:
        print(f"Error in running_balance: {e}")
        return None


def net_worth():
    try:
        accounts = get_all_accounts()
        if accounts is None:
            return None
        df = pd.DataFrame(accounts)
        if df.empty:
            return 0.0
        total = df['balance'].sum()
        return round(float(total), 2)
    except Exception as e:
        print(f"Error in net_worth: {e}")
        return None