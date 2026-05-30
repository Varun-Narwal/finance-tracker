"""
Pulls raw transaction rows from the DB into typed TransactionRecord dataclasses.
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


# ---------------------------------------------------------------------------
# Data contract
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TransactionRecord:

    # core fields (always present) 
    transaction_id: int
    amount: Decimal
    type: str                          # 'income' | 'expense' | 'transfer'
    method: str | None                 # 'upi' | 'cash' | 'internet_banking' | 'cheque' | None
    date: datetime
    member_id: int

    # text 
    note: str | None

    # category (None when predicting) 
    category_id: int | None
    category_name: str | None
    parent_category_id: int | None
    parent_category_name: str | None
    category_type_hint: str | None     # 'expense' | 'income' | None

    # account context 
    account_id: int
    bank_name: str
    account_type: str                  # e.g. 'savings', 'current', 'credit'

    # transfer target (None for non-transfers) 
    target_account_id: int | None


@dataclass(frozen=True, slots=True)
class CategoryRecord:
    # Flat representation of a category row (with parent name resolved).
    category_id: int
    name: str
    parent_id: int | None
    parent_name: str | None
    type_hint: str | None              # 'expense' | 'income' | None


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

# Shared SELECT + JOIN block reused by both labeled and unlabeled queries.

_SELECT = """
    SELECT
        t.transaction_id,
        t.amount,
        t.type,
        t.method,
        t.date,
        t.member_id,
        t.note,
        t.category_id,
        t.account_id,
        t.target_account_id,

        -- leaf category
        c.name          AS category_name,
        c.parent_id     AS parent_category_id,
        c.type_hint     AS category_type_hint,

        -- parent category (may be NULL for top-level categories)
        pc.name         AS parent_category_name,

        -- account
        a.bank_name,
        a.account_type

    FROM transactions t
    LEFT JOIN categories  c  ON c.category_id  = t.category_id
    LEFT JOIN categories  pc ON pc.category_id = c.parent_id
    LEFT JOIN accounts    a  ON a.account_id   = t.account_id
"""


def _row_to_record(row: tuple, columns: list[str]) -> TransactionRecord:
    data = dict(zip(columns, row))
    data["note"] = _clean_note(data.get("note"))
    return TransactionRecord(**data)


_WHITESPACE_RE = re.compile(r"\s+")

def _clean_note(note: str | None) -> str | None:
    """
    Light normalisation applied at extraction time so the engineer
    always receives clean text:
      - strip surrounding whitespace
      - collapse internal whitespace runs to a single space
      - lower-case
    Returns None if the result is empty.
    """
    if not note:
        return None
    note = note.strip().lower()
    note = _WHITESPACE_RE.sub(" ", note)
    return note or None


# ---------------------------------------------------------------------------
# Public coroutines
# ---------------------------------------------------------------------------

async def fetch_labeled(
    conn,
    member_id: int,
    limit: int = 5_000,
    exclude_transfers: bool = True,
) -> list[TransactionRecord]:
    """
    Fetch transactions that already have a category assigned.
    Used to build/refresh the training dataset.
    """
    conditions = ["t.member_id = %s", "t.category_id IS NOT NULL"]
    params: list = [member_id]

    if exclude_transfers:
        conditions.append("t.type != 'transfer'")

    where = "WHERE " + " AND ".join(conditions)
    sql = f"{_SELECT} {where} ORDER BY t.date DESC LIMIT %s"
    params.append(limit)

    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()
        columns = [col.name for col in cur.description]

    return [_row_to_record(r, columns) for r in rows]


async def fetch_for_inference(
    conn,
    member_id: int,
    amount: Decimal,
    type_: str,
    method: str | None,
    date: datetime,
    note: str | None,
    account_id: int,
) -> TransactionRecord:

    sql = """
        SELECT a.bank_name, a.account_type
        FROM accounts a
        WHERE a.account_id = %s AND a.owner_member_id = %s
    """
    async with conn.cursor() as cur:
        await cur.execute(sql, (account_id, member_id))
        row = await cur.fetchone()

    if row is None:
        raise ValueError(
            f"Account {account_id} not found or does not belong to member {member_id}"
        )

    bank_name, account_type = row

    return TransactionRecord(
        transaction_id=-1,           
        amount=amount,               
        type=type_,
        method=method,
        date=date,
        member_id=member_id,
        note=_clean_note(note),
        category_id=None,            
        category_name=None,
        parent_category_id=None,
        parent_category_name=None,
        category_type_hint=None,
        account_id=account_id,
        bank_name=bank_name,
        account_type=account_type,
        target_account_id=None,
    )


async def fetch_categories(conn, type_hint: str | None = None) -> list[CategoryRecord]:
    """
    Return the full category catalogue (with parent names resolved).
    Used by the /categorize router to populate the Streamlit selectbox options.
    """
    sql = """
        SELECT
            c.category_id,
            c.name,
            c.parent_id,
            p.name  AS parent_name,
            c.type_hint
        FROM categories c
        LEFT JOIN categories p ON p.category_id = c.parent_id
    """
    params = []
    if type_hint:
        sql += " WHERE c.type_hint = %s OR c.type_hint IS NULL"
        params.append(type_hint)
    sql += " ORDER BY p.name NULLS FIRST, c.name"

    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()

    return [
        CategoryRecord(
            category_id=r[0],
            name=r[1],
            parent_id=r[2],
            parent_name=r[3],
            type_hint=r[4],
        )
        for r in rows
    ]


async def fetch_member_recent_stats(
    conn,
    member_id: int,
    reference_date: datetime,
) -> dict:
    """
    Returns dict with keys:
        avg_7d, std_7d, count_7d,avg_30d, std_30d, count_30d
    """
    sql = """
        SELECT
            AVG(amount) FILTER (WHERE date >= %(ref)s - INTERVAL '7 days')   AS avg_7d,
            STDDEV(amount) FILTER (WHERE date >= %(ref)s - INTERVAL '7 days') AS std_7d,
            COUNT(*) FILTER (WHERE date >= %(ref)s - INTERVAL '7 days')       AS count_7d,

            AVG(amount) FILTER (WHERE date >= %(ref)s - INTERVAL '30 days')  AS avg_30d,
            STDDEV(amount) FILTER (WHERE date >= %(ref)s - INTERVAL '30 days') AS std_30d,
            COUNT(*) FILTER (WHERE date >= %(ref)s - INTERVAL '30 days')      AS count_30d
        FROM transactions
        WHERE member_id = %(mid)s
          AND type != 'transfer'
    """

    async with conn.cursor() as cur:
        await cur.execute(sql, {"ref": reference_date, "mid": member_id})
        row = await cur.fetchone()

    keys = ("avg_7d", "std_7d", "count_7d", "avg_30d", "std_30d", "count_30d")
    return dict(zip(keys, row))