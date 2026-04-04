CREATE TABLE members (
    member_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    relationship VARCHAR(50),
    is_virtual BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE accounts (
    account_id SERIAL PRIMARY KEY,
    bank_name VARCHAR(100) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    owner_member_id INTEGER NOT NULL REFERENCES members(member_id),
    balance NUMERIC(12,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    parent_id INTEGER REFERENCES categories(category_id),
    type_hint VARCHAR(10) CHECK (type_hint IN ('expense', 'income', 'both')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE transactions (
    transaction_id SERIAL PRIMARY KEY,
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
    type VARCHAR(10) CHECK (type IN ('income', 'expense', 'transfer')),
    method VARCHAR(20) CHECK (method IN ('upi', 'cash', 'internet_banking', 'cheque')),
    date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    note TEXT,
    category_id INTEGER REFERENCES categories(category_id),
    member_id INTEGER NOT NULL REFERENCES members(member_id),
    from_account_id INTEGER NOT NULL REFERENCES accounts(account_id),
    to_account_id INTEGER REFERENCES accounts(account_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE budgets (
    budget_id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(category_id),
    member_id INTEGER NOT NULL REFERENCES members(member_id),
    amount NUMERIC(12,2) NOT NULL,
    month DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_budget UNIQUE (category_id, member_id, month)
);