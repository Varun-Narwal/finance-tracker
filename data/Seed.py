import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.queries import add_member, add_account, add_category, add_budget

def main():
    # SEED MEMBERS
    members_data = [
        ('Me', 'self', False),
        ('Dad', 'parent', False),
        ('Mom', 'parent', False),
        ('House', 'household', True)
    ]
    member_ids = {}
    for name, relationship, is_virtual in members_data:
        result = add_member(name, relationship, is_virtual)
        if result:
            print(f"Member '{name}' added with id {result}")
            member_ids[name] = result
        else:
            print(f"Member '{name}' already exists, skipping")

    # if members already exist fetch their IDs
    if not member_ids:
        from src.queries import get_all_members
        existing = get_all_members()
        member_ids = {row['name']: row['member_id'] for row in existing}
        print("Using existing members:")
        for name, mid in member_ids.items():
            print(f"  {mid} - {name}")

    # SEED ACCOUNTS
    accounts = [
        ("SBI Savings", "savings", member_ids['Me'], 50000),
        ("HDFC Current", "current", member_ids['Dad'], 75000),
        ("SBI Savings Dad", "savings", member_ids['Dad'], 130000),
        ("Paytm Wallet", "wallet", member_ids['Me'], 2000),
        ("Cash", "cash", member_ids['Me'], 5000)
    ]
    for name, account_type, owner_id, balance in accounts:
        result = add_account(name, account_type, owner_id, balance)
        if result:
            print(f"Account '{name}' added with id {result}")

    # SEED PARENT CATEGORIES
    parent_categories = [
        ("Salary", "income", None),
        ("Investments", "income", None),
        ("Home Expense", "expense", None),
        ("Personal", "expense", None),
        ("Medical", "expense", None),
        ("Festival", "expense", None)
    ]
    parent_ids = {}
    for name, type_hint, parent_id in parent_categories:
        result = add_category(name, type_hint, parent_id)
        if result:
            print(f"Category '{name}' added with id {result}")
            parent_ids[name] = result

    # SEED SUBCATEGORIES
    subcategories = [
        ("Grocery", "expense", "Home Expense"),
        ("Electricity", "expense", "Home Expense"),
        ("Water Bill", "expense", "Home Expense"),
        ("Clothes", "expense", "Personal"),
        ("Education", "expense", "Personal"),
        ("Doctor Visit", "expense", "Medical"),
        ("Medicines", "expense", "Medical")
    ]
    sub_ids = {}
    for name, type_hint, parent_name in subcategories:
        parent_id = parent_ids.get(parent_name)
        if parent_id:
            result = add_category(name, type_hint, parent_id)
            if result:
                print(f"Subcategory '{name}' added with id {result}")
                sub_ids[name] = result
        else:
            print(f"Warning: Parent category for '{name}' not found")

    # SEED BUDGETS
    budgets = [
        # House - shared household expenses
        (parent_ids['Home Expense'], member_ids['House'], 15000, '2026-05-01'),
        (sub_ids['Grocery'], member_ids['House'], 6000, '2026-05-01'),
        (sub_ids['Electricity'], member_ids['House'], 2500, '2026-05-01'),
        (sub_ids['Water Bill'], member_ids['House'], 500, '2026-05-01'),

        # Me - personal expenses
        (parent_ids['Personal'], member_ids['Me'], 5000, '2026-05-01'),
        (sub_ids['Education'], member_ids['Me'], 3000, '2026-05-01'),
        (sub_ids['Clothes'], member_ids['Me'], 1500, '2026-05-01'),
        (parent_ids['Medical'], member_ids['Me'], 1000, '2026-05-01'),
        (sub_ids['Doctor Visit'], member_ids['Me'], 1500, '2026-05-01'),

        # Dad - personal expenses
        (parent_ids['Personal'], member_ids['Dad'], 4000, '2026-05-01'),
        (sub_ids['Clothes'], member_ids['Dad'], 1000, '2026-05-01'),
        (parent_ids['Medical'], member_ids['Dad'], 2000, '2026-05-01'),
        (sub_ids['Doctor Visit'], member_ids['Dad'], 1500, '2026-05-01'),

        # Mom - personal expenses
        (parent_ids['Personal'], member_ids['Mom'], 4000, '2026-05-01'),
        (sub_ids['Clothes'], member_ids['Mom'], 1500, '2026-05-01'),
        (parent_ids['Medical'], member_ids['Mom'], 3000, '2026-05-01'),
        (sub_ids['Doctor Visit'], member_ids['Mom'], 1500, '2026-05-01'),
    ]
    for category_id, member_id, amount, month in budgets:
        result = add_budget(category_id, member_id, amount, month)
        if result:
            print(f"Budget added with id {result}")
        else:
            print(f"Warning: Budget for category_id={category_id}, member_id={member_id} skipped")

if __name__ == "__main__":
    main()