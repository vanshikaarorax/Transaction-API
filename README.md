# Transaction Ledger API

A FastAPI ledger backed by PostgreSQL/Supabase. Balances are `NUMERIC(18,2)` and are updated in the same database transaction as immutable ledger entries.

## Setup

Use Python 3.11+:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# set DATABASE_URL to a Supabase direct or session-pooler psycopg URL
alembic upgrade head
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`; detailed API usage is in [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

## Database and Supabase

Use `postgresql+psycopg://...` in `DATABASE_URL`. Apply Alembic only to the intended schema; it creates only `accounts` and `transactions`. Do not point tests at a production/submission database. Supabase direct connections can require IPv6; use its session pooler connection if the deployment environment lacks IPv6 support.

## Tests

```bash
pytest -q
```

The default suite uses an isolated temporary SQLite database for request/validation behavior. PostgreSQL locking and concurrent-debit tests require a separately provisioned, disposable PostgreSQL database and are intentionally marked skipped until one is configured.

## Architecture

`app/api` exposes routes, `schemas` validates requests/responses, `services` owns business transactions, `models` defines schema, and `migrations` is the authoritative database setup. Transaction writes lock the account row on PostgreSQL, validate funds, insert the ledger row and update the balance in one commit.
