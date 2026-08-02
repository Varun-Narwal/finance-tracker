# Personal Finance Tracker

A web application for logging, managing, and visualizing personal and family finance records, with a loosely coupled machine learning layer for intelligent transaction categorisation. Built with Python, PostgreSQL, Streamlit, and FastAPI — no spreadsheets, no manual formulas, no hassle.

> **Inspiration:** My father manages our family's monthly finances on Excel. I watched him spend hours on manual calculations, poorly structured data, and charts that broke every time a row was added. This project solves every problem he faced — structured data, instant analytics, and a clean interface anyone can use.

---

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![XGBoost](https://img.shields.io/badge/XGBoost-FF6600?logo=xgboost&logoColor=white)

---

## Application Screenshots

<details>
  <summary><strong>Dashboard</strong></summary>
  <br>
  <img src="./assets/Dashboard.png" alt="Dashboard">
</details>

<details>
  <summary><strong>Transaction (add transactions)</strong></summary>
  <br>
  <img src="./assets/Transaction(add_transaction).png" alt="Add Transaction">
</details>

<details>
  <summary><strong>Transaction (view, edit, delete) and CSV ingestion</strong></summary>
  <br>
  <img src="./assets/Transaction(view, edit, delete).png" alt="CSV Ingestion and Manage Transactions">
</details>

<details>
  <summary><strong>Analytics (spending trend)</strong></summary>
  <br>
  <img src="./assets/Analytics(spending_trend).png" alt="Spending Trend">
</details>

<details>
  <summary><strong>Analytics (month comparison)</strong></summary>
  <br>
  <img src="./assets/Analytics(month_comaparison).png" alt="Month Comparison">
</details>

<details>
  <summary><strong>Analytics (running balance)</strong></summary>
  <br>
  <img src="./assets/Analytics(running_balance).png" alt="Running Balance">
</details>

---

## Features

### Base Application
- **Daily transaction logging** — add income, expense, and transfer transactions via a clean web form with dropdown validation for members, accounts, and categories
- **ML-assisted categorisation** — tap ✨ while logging a transaction to get top-3 category suggestions from the trained XGBoost model; the highest-confidence suggestion is pre-selected, user can override
- **Bulk CSV ingestion** — import historical transactions in bulk using the provided CSV template; the app validates, resolves names to IDs, and updates account balances automatically
- **Member-wise tracking** — track spending per family member or shared virtual members (e.g. "House" for shared household expenses)
- **Multi-account support** — manage multiple bank accounts and wallets; balances update automatically on every transaction
- **Budget management** — set monthly budgets per member per category and track actual vs budgeted spending
- **Analytics dashboard** — monthly summaries, spending trends, member and category breakdowns, running account balances, month comparisons, and spend averages — all without writing a single formula
- **Full CRUD** — add, view, edit, and delete transactions, members, accounts, categories, and budgets directly from the app

### ML Layer
- **Auto-categorisation** — XGBoost classifier inside a scikit-learn Pipeline combining numeric features, ordinal-encoded categoricals, and TF-IDF on transaction notes; returns top-N suggestions with confidence scores
- **Point-in-time correct features** — rolling 7-day and 30-day statistics (mean, standard deviation, transaction frequency) are computed at each transaction's own date to prevent data leakage
- **Atomic model persistence** — artifacts are written to `.tmp` files and renamed atomically so a concurrent inference call never reads a half-written model
- **Async-safe inference** — CPU-bound operations (`pipeline.fit`, `predict_proba`, `joblib.load`) are offloaded to a thread pool via `asyncio.to_thread` to avoid blocking the FastAPI event loop
- **Graceful degradation** — if the ML service is unreachable, the base Streamlit app continues to function normally with manual category selection

---

## Tech Stack

### Base Application

| Layer | Technology | Reason |
|---|---|---|
| Database | PostgreSQL | Open source, industry grade, excellent for structured financial data |
| Data layer | Python + psycopg2 | Direct SQL control, no ORM overhead, full transparency of every query |
| Analytics | pandas | Powerful aggregation on top of query results without rewriting SQL |
| Web app | Streamlit | Removes frontend complexity, purpose-built for data science workloads |
| Environment | WSL2 Ubuntu | Linux tooling on Windows, PostgreSQL runs natively |

### ML Service

| Layer | Technology | Reason |
|---|---|---|
| API framework | FastAPI | Native async, automatic OpenAPI docs, Pydantic validation |
| DB driver | psycopg3 (psycopg) | Native async support, fits naturally with FastAPI's event loop |
| Connection pooling | psycopg-pool | AsyncConnectionPool with read-only session enforcement at PostgreSQL level |
| ML pipeline | scikit-learn | ColumnTransformer + Pipeline prevents training-serving skew |
| Classifier | XGBoost | Strong out-of-the-box performance on small tabular datasets |
| Text features | TF-IDF (sklearn) | Extracts signal from transaction notes without a separate NLP model |
| Model persistence | joblib | Efficient serialisation of sklearn-compatible objects |

**Why psycopg2 (base) and psycopg3 (ML service) coexist:** The base app was built and tested on psycopg2. The ML service is a greenfield FastAPI microservice where native async support is essential — psycopg3 was adopted here first, with migration of the base app planned as a future step. Both packages coexist without conflict.

**Why a separate FastAPI microservice:** Loose coupling. The ML layer is an optional enhancement — the base app functions fully without it. A FastAPI service communicating over HTTP means the ML layer can be retrained, redeployed, or replaced independently without touching the Streamlit application.

**Why psycopg2 over SQLAlchemy:** SQLAlchemy's ORM abstracts away exactly what this project is meant to demonstrate — direct SQL query writing and database interaction. psycopg2 keeps every query explicit and readable.

**Why Streamlit over Flask:** The core value of this project is the analytics and finance management, not a flashy UI. Streamlit lets you build a functional, clean interface in pure Python without touching HTML, CSS, or JavaScript.

---

## Project Structure

```
finance-tracker/
├── app/                                     # Streamlit web application
│   ├── main.py                              # Entry point and home page
│   └── pages/
│       ├── 1_Dashboard.py                   # Monthly KPI cards and charts
│       ├── 2_Transactions.py                # Add, view, edit, delete, bulk import
│       ├── 3_Members.py                     # Manage family members
│       ├── 4_Accounts.py                    # Manage bank accounts and wallets
│       ├── 5_Categories.py                  # Manage expense/income categories
│       ├── 6_Budgets.py                     # Set and track monthly budgets
│       └── 7_Analytics.py                   # Full analytics workspace
├── assets/                                  # Screenshots for README
├── data/
│   ├── Seed.py                              # Populates database with initial members, accounts, categories
│   ├── Test_analytics.py
│   ├── Transaction_sample.csv               # 556-row synthetic dataset (18 months)
│   └── transactions_template.csv            # CSV format reference for bulk import
├── db/
│   ├── connection.py                        # psycopg2 connection via .env
│   └── schema.sql                           # All table definitions
├── ml/                                      # FastAPI ML microservice
│   ├── main.py                              # FastAPI entry point, lifespan, health check
│   ├── db/
│   │   └── connection.py                    # psycopg3 async read-only connection pool
│   ├── features/
│   │   ├── extractor.py                     # Typed dataclasses, async DB queries, bulk stats map
│   │   └── engineer.py                      # Feature matrix builder, TF-IDF, column registry
│   ├── models/
│   │   ├── categorizer.py                   # XGBoost pipeline, training, inference, persistence
│   │   ├── anomaly.py                       # Isolation Forest (planned)
│   │   └── forecaster.py                    # XGBoost regression forecaster (planned)
│   ├── routers/
│   │   ├── categorize.py                    # POST /predict, POST /retrain, GET /status
│   │   ├── anomaly.py                       # Anomaly detection endpoints (planned)
│   │   └── forecast.py                      # Spending forecast endpoints (planned)
│   └── artifacts/                           # Trained model artifacts — gitignored
│       └── .gitkeep
├── src/
│   ├── queries.py                           # Full CRUD functions for all 5 tables
│   ├── ingest.py                            # Bulk CSV ingestion pipeline
│   ├── analytics.py                         # Business intelligence functions
│   └── calculations.py                      # Utility math and comparison functions
├── .env.example                             # Environment variable template
├── requirements.txt                         # Python dependencies
└── README.md
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/Varun-Narwal/finance-tracker.git
cd finance-tracker
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS/WSL
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and fill in your details:

```bash
cp .env.example .env
```

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=finance_tracker
DB_USER=postgres
DB_PASSWORD=
ML_SERVICE_URL=http://localhost:8001
ML_SERVICE_PORT=8001
```

> Everything runs locally on your own machine. Your credentials never leave your system.

### 5. Create the database

```bash
psql -U postgres -c "CREATE DATABASE finance_tracker;"
```

### 6. Run the schema

```bash
psql -U postgres -d finance_tracker -f db/schema.sql
```

This creates all 5 tables (`members`, `accounts`, `categories`, `transactions`, `budgets`) with their relationships and seeds 4 default members: `Me`, `Dad`, `Mom`, and `House`.

### 7. Seed accounts, categories, and budgets

```bash
python data/Seed.py
```

Edit `Seed.py` to match your real accounts and family setup before running.

### 8. Run the Streamlit app

```bash
streamlit run app/main.py
```

Open `http://localhost:8501` in your browser.

### 9. Start the ML service (optional)

The ML service is optional — the base app works fully without it. To enable category suggestions:

```bash
python -m uvicorn ml.main:app --reload --port 8001
```

### 10. Train the categorisation model

Once you have at least 50 labeled transactions in the database, open `http://localhost:8001/docs` and call `POST /categorize/retrain` with body `{}`.

The model requires a minimum of 50 labeled transactions and will issue a warning below 100. Accuracy improves significantly as real transaction data accumulates.

---

## ML Layer — Categorisation Model

### Architecture

A scikit-learn `Pipeline` combining a `ColumnTransformer` preprocessor with an `XGBClassifier`:

```
Raw transaction
      │
ColumnTransformer
  ├── Numeric features    → passthrough (16 features: amount, log_amount, temporal, rolling stats)
  ├── Categorical features → OrdinalEncoder (method, type, account_type, bank_name)
  └── note (text)         → TfidfVectorizer (max_features=100, unigrams + bigrams)
      │
XGBClassifier
      │
LabelEncoder⁻¹ → real category_id + name
```

### Features

**Numeric (16):** `amount`, `log_amount`, `day_of_week`, `day_of_month`, `week_of_month`, `month`, `days_until_month_end`, `is_weekend`, `is_start_of_month`, `is_end_of_month`, `z_score_7d`, `z_score_30d`, `tx_freq_7d`, `tx_freq_30d`, `note_length`, `note_is_null`

**Categorical (4):** `method`, `type`, `account_type`, `bank_name`

**Text (1):** `note` — TF-IDF vectorised, unigrams and bigrams

### Data Leakage Prevention

Rolling statistics (`z_score_7d`, `z_score_30d`, `tx_freq_7d`, `tx_freq_30d`) are computed point-in-time correct — for each training transaction, only transactions with `date <= that transaction's date` are used in the rolling window. This mirrors inference exactly and prevents look-ahead bias.

### Evaluation

Evaluated on a stratified 80/20 train/val split with 5-fold stratified cross-validation reporting macro F1 score. Macro F1 was chosen over weighted accuracy to treat all 13 categories equally regardless of class size.

**Current metrics (551 labeled transactions, 13 categories, synthetic dataset):**

| Metric | Value |
|---|---|
| Cross-validated macro F1 | 0.7792 ± 0.0307 |
| Validation accuracy | 0.7027 |

**Per-category F1 on validation set:**

| Category | F1 | Note |
|---|---|---|
| Salary | 1.00 | Highly distinct pattern |
| Investments | 1.00 | Highly distinct pattern |
| Electricity | 1.00 | Highly distinct pattern |
| Water Bill | 1.00 | Highly distinct pattern |
| Medical | 0.90 | Strong signal |
| Grocery | 0.70 | Acceptable |
| Personal | 0.70 | Acceptable |
| Clothes | 0.71 | Acceptable |
| Home Expense | 0.67 | Acceptable |
| Medicines | 0.56 | Weak — overlaps with Medical |
| Doctor Visit | 0.55 | Weak — low support in val set |
| Festival | 0.50 | Weak — irregular, low frequency |
| Education | 0.38 | Weak — high feature variance |

**Important caveats:**
- Trained on synthetic data. Performance on real family transactions is expected to differ — utility and accuracy categories (Salary, Electricity, Water Bill) will remain strong; lifestyle categories (Education, Festival, Medicines) will improve as real spending patterns emerge
- Hyperparameters are set to sensible defaults. RandomizedSearchCV tuning is planned once real transaction data exceeds ~2000 labeled rows with balanced category distribution
- A three-way train/val/test split is planned at the same threshold — current dataset size makes a held-out test set statistically unreliable for thin categories

---

## CSV Ingestion

To bulk import historical transactions, use the provided template:

```
data/transactions_template.csv
```

Column format:
```
amount, transaction_type, method, member_name, account_name, to_account_name, category_name, note, transaction_date
```

- `transaction_type` — `income`, `expense`, or `transfer`
- `method` — `upi`, `cash`, `internet_banking`, or `cheque`
- `to_account_name` — only required for `transfer` type
- `category_name` — leave empty for `transfer` type
- `transaction_date` — format `YYYY-MM-DD`
- Member and account names must exactly match what is in your database

Upload the CSV from the Transactions page and click **Run Ingestion**. The app validates each row, resolves names to database IDs, inserts all valid rows in a single batch, and updates account balances automatically. Skipped rows are reported with reasons.

---

## Database Schema

```
members ──────────────── accounts
   │                         │
   │              from/to    │
   └──── transactions ───────┘
              │
         categories (self-referential parent_id)
              │
           budgets
```

Key design decisions:
- `amount` is always positive — direction is determined by `type` (`income`, `expense`, `transfer`)
- `transfer` transactions use both `account_id` (source) and `target_account_id` (destination)
- Categories support a two-level hierarchy via self-referential `parent_id`
- The `House` member is a virtual member (`is_virtual = TRUE`) for shared household expenses
- Account balances update atomically with each transaction

---

## API Reference

The ML service exposes a self-documenting Swagger UI at `http://localhost:8001/docs`.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Liveness probe — DB connectivity and model status |
| POST | `/categorize/predict` | Top-N category suggestions for a new transaction |
| POST | `/categorize/retrain` | Train or retrain the categorisation model |
| GET | `/categorize/status` | Current model metadata without retraining |

---

## Roadmap

- [x] **PostgreSQL schema and CRUD** — full 5-table schema with constraints and relationships
- [x] **Streamlit multi-page app** — Dashboard, Transactions, Members, Accounts, Categories, Budgets, Analytics
- [x] **Bulk CSV ingestion** — validated batch import with balance updates
- [x] **ML microservice** — FastAPI service with async psycopg3 read-only connection pool
- [x] **Auto-categorisation** — XGBoost pipeline with TF-IDF on notes, top-3 suggestions in UI
- [ ] **ML Dashboard page** — model status, retrain button, per-category performance metrics in Streamlit
- [ ] **Anomaly detection** — Isolation Forest per-member models to flag unusual transactions
- [ ] **Spending forecast** — XGBoost regression to predict end-of-month spend and flag budget overrun risk
- [ ] **SMS-based transaction ingestion** — LLM-powered parser using a local Qwen3 model 
      via Ollama for robust extraction of amount, type, account, merchant, and timestamp 
      from Indian bank SMS templates; merchant-to-category lookup, staged review before 
      committing to DB
- [ ] **Power BI integration** — connect directly to PostgreSQL for DAX-powered financial dashboards
- [ ] **Export to CSV/Excel** — backup and sharing of transaction data

---

## Notes

- Built and tested on WSL2 Ubuntu with PostgreSQL running via CLI. Works on any system with Python 3.10+ and PostgreSQL installed.
- The ML service (`ml/`) uses psycopg3 while the base app uses psycopg2. Both coexist without conflict — `psycopg2-binary` and `psycopg[binary]` are separate packages.
- Trained model artifacts (`ml/artifacts/`) are gitignored and regenerated by calling `POST /categorize/retrain`. They are user-specific and not suitable for version control.
- The `.env` file is gitignored. Never commit it. Use `.env.example` as the reference.
- PostgreSQL-specific syntax (`SERIAL`, `RETURNING`, `INTERVAL`, `FILTER`) is used intentionally. Switching to another DBMS would require query adjustments.