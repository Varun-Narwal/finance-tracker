import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from db.connection import get_connection
from src.queries import get_all_members, get_all_accounts, get_all_categories, update_account_balance

def bulk_ingest_csv(filepath):
    # STEP 1 - Read CSV
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return None

    required_columns = ['amount', 'transaction_type', 'method', 'member_name',
                        'account_name', 'to_account_name', 'category_name', 
                        'note', 'transaction_date']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        print(f"Missing required columns: {', '.join(missing_cols)}")
        return None

    # STEP 2 - Load lookup tables
    members = get_all_members()
    accounts = get_all_accounts()
    categories = get_all_categories()

    member_dict   = {row['name']: row['member_id'] for row in members}
    account_dict  = {row['bank_name']: row['account_id'] for row in accounts}
    category_dict = {row['name']: row['category_id'] for row in categories}

    # STEP 3 - Resolve and validate each row
    valid_rows = []
    skipped_rows = []

    for index, row in df.iterrows():
        try:
            member_id = member_dict.get(row['member_name'])
            if not member_id:
                skipped_rows.append((index, 'Invalid member name'))
                continue

            account_id = account_dict.get(row['account_name'])
            if not account_id:
                skipped_rows.append((index, 'Invalid account name'))
                continue

            target_account_id = None
            if row['transaction_type'] == 'transfer':
                to_account_name = row['to_account_name']
                if pd.isna(to_account_name):
                    skipped_rows.append((index, 'Missing to_account_name for transfer'))
                    continue
                target_account_id = account_dict.get(to_account_name)
                if not target_account_id:
                    skipped_rows.append((index, 'Invalid to account name'))
                    continue

            category_id = category_dict.get(row['category_name']) if pd.notna(row['category_name']) else None

            if row['transaction_type'] not in ['income', 'expense', 'transfer']:
                skipped_rows.append((index, 'Invalid transaction type'))
                continue

            transaction_date = pd.to_datetime(row['transaction_date']).date()
            amount = float(row['amount'])

            valid_rows.append((
                amount,
                row['transaction_type'],
                row['method'],
                transaction_date,
                row['note'] if pd.notna(row['note']) else None,
                category_id,
                member_id,
                account_id,
                target_account_id
            ))
        except Exception as e:
            skipped_rows.append((index, f"Error processing row: {e}"))

    # STEP 4 - Bulk insert
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.executemany("""
            INSERT INTO transactions (
                amount, type, method, date, note,
                category_id, member_id, account_id, target_account_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, valid_rows)
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error inserting transactions: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

    # STEP 5 - Update account balances
    account_changes = {}
    for row in valid_rows:
        amount, transaction_type, method, transaction_date, note, category_id, member_id, account_id, target_account_id = row
        if transaction_type == 'income':
            account_changes[account_id] = account_changes.get(account_id, 0) + amount
        elif transaction_type == 'expense':
            account_changes[account_id] = account_changes.get(account_id, 0) - amount
        elif transaction_type == 'transfer':
            account_changes[account_id] = account_changes.get(account_id, 0) - amount
            account_changes[target_account_id] = account_changes.get(target_account_id, 0) + amount

    for account_id, delta in account_changes.items():
        if delta >= 0:
            update_account_balance(account_id, delta, 'add')
        else:
            update_account_balance(account_id, abs(delta), 'subtract')

    # STEP 6 - Report
    print(f"Inserted {len(valid_rows)} rows")
    print(f"Skipped {len(skipped_rows)} rows")
    if skipped_rows:
        for row_index, reason in skipped_rows:
            print(f"  Row {row_index}: {reason}")
    return len(valid_rows)
if __name__ == "__main__":
    bulk_ingest_csv('data/Transaction_sample.csv')