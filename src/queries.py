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
    if transaction_type == 'transfer' and to_account_id is None:
        print("Error: to_account_id is required for transfer transactions")
        return None

    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO transactions (
                amount, type, method, date, note, category_id,
                member_id, from_account_id, to_account_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING transaction_id
        """, (
            amount, transaction_type, method, transaction_date, note,
            category_id, member_id, from_account_id, to_account_id
        ))

        transaction_id = cur.fetchone()[0]

        if transaction_type == 'income':
            cur.execute("""
                UPDATE accounts SET balance = balance + %s
                WHERE account_id = %s
            """, (amount, from_account_id))

        elif transaction_type == 'expense':
            cur.execute("""
                UPDATE accounts SET balance = balance - %s
                WHERE account_id = %s
            """, (amount, from_account_id))

        elif transaction_type == 'transfer':
            cur.execute("""
                UPDATE accounts SET balance = balance - %s
                WHERE account_id = %s
            """, (amount, from_account_id))
            cur.execute("""
                UPDATE accounts SET balance = balance + %s
                WHERE account_id = %s
            """, (amount, to_account_id))

        conn.commit()
        return transaction_id

    except Exception as e:
        if conn:
            conn.rollback()
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

# -----------------------------------------
# ACCOUNTS
# -----------------------------------------

def add_account(bank_name, account_type, owner_member_id, balance=0.00):
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO accounts (bank_name, account_type, owner_member_id, balance)
            VALUES (%s, %s, %s, %s)
            RETURNING account_id
        """, (bank_name, account_type, owner_member_id, balance))
        account_id = cur.fetchone()[0]
        conn.commit()
        return account_id
    except Exception as e:
        print(f"Error adding account: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_all_accounts():
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("SELECT * FROM accounts")
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error retrieving accounts: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_accounts_by_member(member_id):
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("SELECT * FROM accounts WHERE owner_member_id = %s", (member_id,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error retrieving accounts by member: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def update_account_balance(account_id, amount, operation):
    if operation not in ('add', 'subtract'):
        print("Invalid operation. Use 'add' or 'subtract'.")
        return None
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        if operation == 'add':
            cur.execute("""
                UPDATE accounts
                SET balance = balance + %s
                WHERE account_id = %s
                RETURNING account_id
            """, (amount, account_id))
        else:  # subtract
            cur.execute("""
                UPDATE accounts
                SET balance = balance - %s
                WHERE account_id = %s
                RETURNING account_id
            """, (amount, account_id))
        result = cur.fetchone()
        if not result:
            return None
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating account balance: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# -----------------------------------------
# MEMBERS
# -----------------------------------------

def add_member(name, relationship, is_virtual=False):
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO members (name, relationship, is_virtual)
            VALUES (%s, %s, %s)
            RETURNING member_id""", (name, relationship, is_virtual))
        member_id = cur.fetchone()[0]
        conn.commit()
        return member_id
    except Exception as e:
        print(f"Error adding member: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_all_members():
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("SELECT * FROM members")
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error retrieving members: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_member_by_id(member_id):
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("SELECT * FROM members WHERE member_id = %s", (member_id,))
        row = cur.fetchone()
        if row:
            columns = [desc[0] for desc in cur.description]
            return dict(zip(columns, row))
        return None
    except Exception as e:
        print(f"Error retrieving member: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

# -----------------------------------------
# CATEGORIES
# -----------------------------------------

def add_category(name, type_hint, parent_id=None):
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO categories (name, type_hint, parent_id)
            VALUES (%s, %s, %s)
            RETURNING category_id""", (name, type_hint, parent_id))
        category_id = cur.fetchone()[0]
        conn.commit()
        return category_id
    except Exception as e:
        print(f"Error adding category: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_all_categories():
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("SELECT * FROM categories")
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error retrieving all categories: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_subcategories(parent_id):
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("SELECT * FROM categories WHERE parent_id = %s", (parent_id,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error retrieving subcategories: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

def get_categories_by_type(type_hint):
    conn = None
    cur = None
    try:
        conn = get_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute("SELECT * FROM categories WHERE type_hint = %s", (type_hint,))
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"Error retrieving categories by type: {e}")
        return None
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()