from db.connection import get_connection
from datetime import datetime
# -----------------------------------------
# TRANSACTIONS
# -----------------------------------------

def add_transaction(
    amount, transaction_type, method, member_id, from_account_id, category_id=None, to_account_id=None, note=None, transaction_date=None
):
    conn = None
    cur = None
    if transaction_date is None:
        transaction_date = datetime.now()
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO transactions (
                amount, type, method, date, note, category_id, member_id, from_account_id, to_account_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            amount, transaction_type, method, transaction_date, note, category_id, member_id, from_account_id, to_account_id
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding transaction: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_all_transactions():
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("SELECT * FROM transactions")
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error retrieving transactions: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_transactions_by_member(member_id):
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("SELECT * FROM transactions WHERE member_id = %s", (member_id,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error retrieving transactions by member: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_transactions_by_type(transaction_type):
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("SELECT * FROM transactions WHERE type = %s", (transaction_type,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error retrieving transactions by type: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def update_transaction(transaction_id, **kwargs):
    conn = None
    cur = None
    if not kwargs:
        print("No fields provided to update")
        return None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        field_map = {
            'transaction_type': 'type',
            'transaction_date': 'date'
        }
        set_clause = []
        values = []
        for key, value in kwargs.items():
            col_name = field_map.get(key, key)
            set_clause.append(f"{col_name} = %s")
            values.append(value)
        values.append(transaction_id)
        query = f"UPDATE transactions SET {', '.join(set_clause)} WHERE transaction_id = %s"
        cur.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating transaction: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def delete_transaction(transaction_id):
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("DELETE FROM transactions WHERE transaction_id = %s", (transaction_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting transaction: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()