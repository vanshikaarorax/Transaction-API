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

Open `http://127.0.0.1:8000/docs`


# Transaction Ledger API
A transaction-ledger backend built with **FastAPI, SQLAlchemy, PostgreSQL, and Supabase**. It provides account creation, credit/debit transactions, balance retrieval, paginated transaction history, and atomic transfers between accounts.
The project emphasizes correctness: money is represented with decimal values, every successful balance change has a corresponding ledger entry, duplicate references are rejected, insufficient-funds operations do not change balances, and PostgreSQL integration tests exercise concurrent requests.
> **Current scope:** This repository implements a REST API and its interactive Swagger UI. Swagger UI is the developer-facing interface for manually exercising the API; a separate custom React/Streamlit frontend is not part of the current implementation unless you add one later.
------------------------------------------------------------------------
## Table of Contents
1.  [Project Overview](#project-overview)
2.  [Features](#features)
3.  [Technology Stack](#technology-stack)
4.  [Architecture](#architecture)
5.  [Project Structure](#project-structure)
6.  [Requirements and Business Rules](#requirements-and-business-rules)
7.  [Data Model](#data-model)
8.  [API Endpoints](#api-endpoints)
9.  [Error Handling](#error-handling)
10. [Local Setup](#local-setup)
11. [Environment Configuration](#environment-configuration)
12. [Database and Supabase Setup](#database-and-supabase-setup)
13. [Run the Application](#run-the-application)
14. [Swagger UI: Manual API Testing](#swagger-ui-manual-api-testing)
15. [End-to-End Testing Walkthrough](#end-to-end-testing-walkthrough)
16. [Transaction History and Pagination](#transaction-history-and-pagination)
17. [Money Transfer Workflow](#money-transfer-workflow)
18. [Automated Tests](#automated-tests)
19. [PostgreSQL Concurrency Testing](#postgresql-concurrency-testing)
20. [Database Integrity and Atomicity](#database-integrity-and-atomicity)
21. [Validation Rules](#validation-rules)
22. [Security and Operational Notes](#security-and-operational-notes)
23. [Troubleshooting](#troubleshooting)
24. [Assumptions and Design Decisions](#assumptions-and-design-decisions)
25. [Limitations and Future Improvements](#limitations-and-future-improvements)
------------------------------------------------------------------------
## Project Overview
The Transaction Ledger API manages accounts and the money movements associated with them.
An account is created with a server-generated identifier, a name, a zero starting balance, and a creation timestamp. Money is introduced through a credit transaction. Money is removed through a debit transaction. A transfer creates a debit on the source account and a matching credit on the destination account.
The ledger is the record of account activity. Clients cannot directly set an account's starting balance, edit an existing transaction, or delete a transaction through the API.
### Example use case
1.  Create a source account and a destination account.
2.  Credit the source account with `100.00`.
3.  Debit the source account by `30.00`.
4.  Transfer `25.00` from the source to the destination.
5.  Check both balances and inspect their transaction histories.
Expected balances after these operations:
-   Source: `100.00 - 30.00 - 25.00 = 45.00`
-   Destination: `0.00 + 25.00 = 25.00`
The transfer changes how money is distributed, not the combined total.
## Features
-   Create accounts with server-generated IDs and timestamps.
-   Initialize every account balance to zero.
-   Credit and debit accounts.
-   Reject debit requests when funds are insufficient.
-   Prevent duplicate transaction references within the same account.
-   Allow the same reference ID to be used by different accounts, subject to each account's own uniqueness constraint.
-   Retrieve an account's current balance.
-   Retrieve transaction history, newest first.
-   Filter transaction history by transaction type.
-   Paginate transaction history with metadata.
-   Transfer money between two accounts.
-   Write both sides of a transfer atomically.
-   Lock PostgreSQL account rows during balance-changing operations.
-   Use database constraints to protect uniqueness and referential integrity.
-   Return structured application errors for expected failures.
-   Expose interactive API documentation through Swagger UI.
-   Run unit tests using isolated temporary SQLite databases.
-   Run PostgreSQL integration tests for concurrency behavior.
-   Keep PostgreSQL integration-test tables in a temporary, isolated schema rather than the application's `public` schema.
## Technology Stack
--------------------------------------------------------------------------------------------------------------- Area                    Technology                     Purpose ----------------------- ------------------------------ -------------------------------------------------------- Language                Python                         Application and test code
API framework           FastAPI                        REST endpoints, dependency injection, OpenAPI
Validation              Pydantic / Pydantic Settings   Request/response validation and configuration
ORM                     SQLAlchemy                     Database models, queries, sessions, transactions
Database                PostgreSQL                     Persistent relational storage and row-level locking
Hosted database         Supabase                       Managed PostgreSQL project
PostgreSQL driver       Psycopg 3                      SQLAlchemy connectivity to PostgreSQL
Migrations              Alembic                        Versioned database schema changes
API documentation       OpenAPI / Swagger UI           Interactive endpoint documentation
Testing                 pytest                         Automated unit and integration tests
HTTP testing            FastAPI TestClient             Endpoint-level tests
Test databases          SQLite and PostgreSQL          Fast unit tests plus real PostgreSQL concurrency tests
Server                  Uvicorn                        Local ASGI development server ---------------------------------------------------------------------------------------------------------------
### Why PostgreSQL?
PostgreSQL provides transactional guarantees, uniqueness constraints, foreign keys, and row-level locks. Those features are important when two requests attempt to update the same account at nearly the same time.
SQLite is useful for fast unit tests, but it does not reproduce PostgreSQL's row-locking behavior. The concurrency tests therefore need to run against PostgreSQL.
## Architecture
The application separates HTTP routing, request/response schemas, business logic, database configuration, and persistence models.

``` text
Client / Swagger UI
        |
        v
FastAPI routes
        |
        v
Pydantic request validation
        |
        v
Service layer
  - account operations
  - credit/debit transactions
  - money transfers
        |
        v
SQLAlchemy session and transaction
        |
        v
PostgreSQL / Supabase
  - accounts
  - transactions
```

### Request lifecycle
1.  A client sends an HTTP request.
2.  FastAPI validates the path parameters and JSON body.
3.  The route obtains a database session through the `get_db` dependency.
4.  The route calls the appropriate service function.
5.  The service performs the required reads and writes inside a database transaction.
6.  SQLAlchemy commits successful changes or rolls them back on failure.
7.  FastAPI serializes the response using the declared response schema.
### Frontend / developer interface
The current project includes **Swagger UI**, served by FastAPI at `/docs`. It is an interactive interface for trying endpoints and inspecting responses.
There is no separate custom web frontend in the current codebase described here. A React, Vue, or Streamlit interface could be added later and would call the same REST endpoints.
## Project Structure
The following is the application/test structure currently used by the project. Some supporting files, such as environment files and migration revisions, may differ by local checkout.

``` text
Confluencr-Project/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── exceptions.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── account.py
│   │   └── transaction.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── account.py
│   │   ├── transaction.py
│   │   └── transfer.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── accounts.py
│   │       └── transfers.py
│   └── services/
│       ├── __init__.py
│       ├── accounts.py
│       ├── transactions.py
│       └── transfers.py
├── migrations/
│   └── versions/
│       └── 0001_initial_ledger.py
├── tests/
│   ├── conftest.py
│   ├── test_accounts.py
│   ├── test_integrity.py
│   ├── test_transactions.py
│   └── test_transfers.py
├── .env.example
├── .gitignore
├── alembic.ini
├── pytest.ini
├── API_DOCUMENTATION.md
├── ASSUMPTIONS.md
├── README.md
└── requirements.txt
```

### Important files
------------------------------------------------------------------------------------------------------- File                               Responsibility ---------------------------------- -------------------------------------------------------------------- `app/main.py`                      Creates the FastAPI application and registers routes
`app/core/config.py`               Reads settings such as `DATABASE_URL` from environment variables
`app/core/exceptions.py`           Defines structured application/API errors
`app/db/base.py`                   Defines the SQLAlchemy declarative base
`app/db/session.py`                Creates the SQLAlchemy engine/session factory and exposes `get_db`
`app/models/account.py`            Account persistence model
`app/models/transaction.py`        Immutable-ledger transaction persistence model
`app/schemas/account.py`           Account request and response schemas
`app/schemas/transaction.py`       Transaction request, response, and history schemas
`app/schemas/transfer.py`          Transfer request and response schemas
`app/api/routes/accounts.py`       Account, balance, transaction, and history endpoints
`app/api/routes/transfers.py`      Transfer endpoint
`app/services/accounts.py`         Account lookup and account-related business logic
`app/services/transactions.py`     Credit/debit creation, duplicate handling, balance updates
`app/services/transfers.py`        Atomic transfer logic and account row locking
`tests/conftest.py`                Test fixtures and database/session overrides
`tests/test_accounts.py`           Account creation, validation, and balance tests
`tests/test_transactions.py`       Credit/debit, duplicate, and history tests
`tests/test_integrity.py`          Balance reconciliation and concurrent debit test
`tests/test_transfers.py`          Transfer behavior, rollback, and concurrent transfer test
`pytest.ini`                       Pytest configuration and PostgreSQL marker -------------------------------------------------------------------------------------------------------
## Requirements and Business Rules
### Account rules
-   Account IDs are generated by the server.
-   Account names are required and must satisfy schema validation.
-   A new account always starts with a balance of `0.00`.
-   A client must not be allowed to supply an initial balance.
-   The creation timestamp is generated by the system.
-   Requests for nonexistent accounts return an appropriate not-found error.
### Transaction rules
-   A transaction belongs to one account.
-   Transaction type is `credit` or `debit`.
-   Amount must be greater than zero.
-   A reference ID is required.
-   A reference ID must be unique within its account.
-   Credit adds the amount to the account balance.
-   Debit subtracts the amount only when sufficient funds exist.
-   A rejected transaction must not change the balance or create a ledger record.
-   Transactions are not updated or deleted through the API.
### Transfer rules
-   Source and destination accounts must exist.
-   Source and destination must be different accounts.
-   Amount must be greater than zero.
-   The source must have enough funds.
-   A successful transfer creates a source debit and a destination credit.
-   Both ledger entries and both balance changes must commit together.
-   If either side fails, the entire transfer must roll back.
-   Reusing a transfer reference for the same source account is rejected.
-   Concurrent transfers must not allow the source account to be overspent.
## Data Model
### Account
The account record represents the current account state.
Field          Meaning -------------- -------------------------------------------------- `id`           Unique account identifier, represented as a UUID `name`         Account name `balance`      Current account balance `created_at`   System-generated creation timestamp
New accounts start at `0.00`. The API does not expose a balance-edit endpoint.
### Transaction
A transaction record represents an immutable ledger event.
Field            Meaning ---------------- -------------------------------------------------- `id`             Unique transaction identifier `account_id`     Account associated with the entry `type`           `credit` or `debit` `amount`         Positive monetary amount `description`    Human-readable transaction description `reference_id`   Caller-supplied idempotency/uniqueness reference `created_at`     System-generated transaction timestamp
The account's balance is the current stored balance. Transaction history provides the events used to audit how the balance changed.
### Money representation
Monetary values should use decimal arithmetic and a fixed-precision database type such as `NUMERIC(18, 2)`, rather than binary floating-point arithmetic. This avoids common rounding errors associated with floats.
The API commonly serializes decimal values as strings, for example `"25.00"`. Clients should preserve decimal precision when submitting or reading monetary amounts.
### Relationships and constraints
-   Transactions reference their owning account.
-   The database enforces uniqueness of `(account_id, reference_id)`.
-   Foreign-key constraints protect account/transaction relationships.
-   Database transactions ensure related writes succeed or fail together.
## API Endpoints
All API endpoints are served from the local base URL:

``` text
http://127.0.0.1:8000/docs
```

### Endpoint summary
--------------------------------------------------------------------------------------------------------- Method       Path                                           Purpose                     Typical success ------------ ---------------------------------------------- --------------------------- ----------------- `GET`        `/health`                                      Health check                `200 OK`
`POST`       `/api/v1/accounts`                             Create account              `201 Created`
`GET`        `/api/v1/accounts/{account_id}/balance`        Get balance                 `200 OK`
`POST`       `/api/v1/accounts/{account_id}/transactions`   Create credit/debit         `201 Created`
`GET`        `/api/v1/accounts/{account_id}/transactions`   Transaction history         `200 OK`
`POST`       `/api/v1/transfers`                            Transfer between accounts   `201 Created` ---------------------------------------------------------------------------------------------------------
The actual response body and error code are defined by the implementation and its schemas. Swagger UI displays the generated OpenAPI contract.
### 1. Health check

``` http
GET /health
```

Use this to check whether the application responds. It is not necessarily a full database-readiness check unless the handler explicitly tests the database.
Example:

``` bash
curl -i http://127.0.0.1:8000/health
```

### 2. Create an account

``` http
POST /api/v1/accounts
Content-Type: application/json
```

Request:

``` json
{
  "name": "Personal Account"
}
```

Expected success status: `201 Created`.
The response includes the server-generated account ID, name, initial balance, and creation timestamp.
Do not submit a starting balance. The server controls the initial balance and initializes it to zero.
Example:

``` bash
curl -X POST \
  http://127.0.0.1:8000/api/v1/accounts \
  -H 'Content-Type: application/json' \
  -d '{"name":"Personal Account"}'
```

### 3. Get an account balance

``` http
GET /api/v1/accounts/{account_id}/balance
```

Example:

``` bash
curl -i \
  http://127.0.0.1:8000/api/v1/accounts/YOUR_ACCOUNT_UUID/balance
```

Expected success status: `200 OK`.
A valid account returns its ID and current balance. A valid-format UUID for a nonexistent account should return `404 Not Found`.
### 4. Create a credit or debit transaction

``` http
POST /api/v1/accounts/{account_id}/transactions
Content-Type: application/json
```

Credit example:

``` json
{
  "type": "credit",
  "amount": "100.00",
  "description": "Initial funding",
  "reference_id": "FUND-001"
}
```

Debit example:

``` json
{
  "type": "debit",
  "amount": "30.00",
  "description": "Purchase",
  "reference_id": "PURCHASE-001"
}
```

Expected success status: `201 Created`.
A debit exceeding the available balance is rejected. Reusing a reference ID for the same account is rejected and must not apply another balance change.
### 5. Get transaction history

``` http
GET /api/v1/accounts/{account_id}/transactions
```

The endpoint supports pagination and an optional transaction-type filter.
Typical query parameters:
-   `page`: page number, starting at 1.
-   `limit`: maximum records per page.
-   `type`: optional `credit` or `debit` filter.
Example:

``` bash
curl -G \
  http://127.0.0.1:8000/api/v1/accounts/YOUR_ACCOUNT_UUID/transactions \
  --data-urlencode 'page=1' \
  --data-urlencode 'limit=20'
```

Filter to credits:

``` bash
curl -G \
  http://127.0.0.1:8000/api/v1/accounts/YOUR_ACCOUNT_UUID/transactions \
  --data-urlencode 'page=1' \
  --data-urlencode 'limit=20' \
  --data-urlencode 'type=credit'
```

History is ordered newest first. The response includes the items and pagination metadata, such as current page, page size, total records, and total pages.
### 6. Transfer money

``` http
POST /api/v1/transfers
Content-Type: application/json
```

Request:

``` json
{
  "source_account_id": "SOURCE_ACCOUNT_UUID",
  "destination_account_id": "DESTINATION_ACCOUNT_UUID",
  "amount": "25.00",
  "reference_id": "TRANSFER-001",
  "description": "Payment"
}
```

Expected success status: `201 Created`.
The response includes a source debit transaction and a destination credit transaction. The same transfer reference is associated with both entries.
A failed transfer must not leave a debit without a credit or change either balance.
## Error Handling
The API uses HTTP status codes to distinguish successful operations from validation and business-rule failures.
------------------------------------------------------------------------------------------------------- Status                  Meaning                     Example ----------------------- --------------------------- --------------------------------------------------- `200`                   Request succeeded           Balance or history retrieved
`201`                   Resource created            Account or transaction created
`404`                   Resource not found          Account ID does not exist
`409`                   Business conflict           Insufficient funds or duplicate reference
`422`                   Request validation failed   Invalid UUID, invalid type, or nonpositive amount
`500`                   Unexpected server error     Unhandled application/database failure -------------------------------------------------------------------------------------------------------
Expected application errors use a structured response. For example:

``` json
{
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "The source account has insufficient funds."
  }
}
```

Exact error codes/messages depend on the particular failure and current implementation.
## Local Setup
### Prerequisites
Install or configure:
-   Python compatible with the project's dependency versions.
-   Git.
-   Access to a PostgreSQL database, such as Supabase.
-   The project source code.
-   A terminal.
### 1. Open the project

``` bash
cd /path/to/Confluencr-Project
```

Replace the example path with your actual local repository path.
### 2. Create a virtual environment
On macOS/Linux:

``` bash
python3 -m venv .venv
```

Activate it:

``` bash
source .venv/bin/activate
```

Confirm the interpreter:

``` bash
which python
python --version
```

On this project, use the explicit `.venv/bin/python` path if a shell alias named `python` bypasses the virtual environment.
### 3. Install dependencies
If `requirements.txt` is present and maintained:

``` bash
./.venv/bin/python -m pip install -r requirements.txt
```

If the dependency file changes, review and test the changes before committing them.
### 4. Configure environment variables
Create `.env` in the project root, or copy `.env.example` if it exists:

``` bash
cp .env.example .env
```

Edit `.env` and set your database URL. Do not commit the real `.env` file.
## Environment Configuration
The settings module reads configuration from environment variables and `.env`.
Example template:

``` dotenv
DATABASE_URL=postgresql+psycopg://USER:URL_ENCODED_PASSWORD@HOST:5432/postgres
APP_ENV=development
```

Use your own Supabase connection details. Never copy example credentials into a real deployment.
### Password URL encoding
Database passwords containing URL-reserved characters must be percent-encoded when placed in a connection URL. For example:
Character   Encoded ----------- --------- `@`         `%40` `?`         `%3F` `%`         `%25` `:`         `%3A` `/`         `%2F` `#`         `%23`
Prefer a password-safe connection method from the Supabase dashboard and verify the final connection without printing secrets.
### Keep secrets out of Git
The `.env` file should be ignored by Git. Check:

``` bash
git status --short
```

Do not paste database URLs containing passwords into tickets, commits, screenshots, or public documentation. If a credential is exposed, rotate it and update the environment configuration.
## Database and Supabase Setup
### 1. Create or open the Supabase project
Open the Supabase dashboard and select the project. Use the dashboard's **Connect** information to obtain the PostgreSQL connection details.
### 2. Verify the connection
A TCP check only confirms that the host and port are reachable. To verify PostgreSQL authentication, run a simple read-only connection test:

``` bash
./.venv/bin/python -c \
'from sqlalchemy import create_engine, text; from app.core.config import get_settings; e=create_engine(get_settings().database_url, connect_args={"connect_timeout":8}); c=e.connect(); print(c.execute(text("SELECT current_database()")).scalar()); print(c.execute(text("SELECT current_schema()")).scalar()); c.close(); e.dispose()'
```

This command should not print the connection URL or password.
### 3. Schema migrations
The repository includes an Alembic migration. On a fresh database, review `alembic.ini`, the migration configuration, and the target database before applying migrations.

``` bash
./.venv/bin/python -m alembic upgrade head
```

**Safety:** Do not run migrations blindly against a database containing important data. Confirm the configured URL and migration operations first. Do not use `drop_all`, `truncate`, or reset operations against the application database.
### 4. Verify records in Supabase
Use the Supabase Table Editor to inspect the `accounts` and `transactions` tables in the schema used by the running API.
For a manual test, compare: - The account ID returned by the API. - The stored account balance. - The transaction rows and their reference IDs. - The debit and credit entries generated by a transfer.
Avoid modifying production rows directly through the SQL editor while testing API behavior.
## Run the Application
Start Uvicorn from the project root:

``` bash
./.venv/bin/python -m uvicorn app.main:app --reload
```

The development server should be available at:
-   API base: `http://127.0.0.1:8000`
-   Swagger UI: `http://127.0.0.1:8000/docs`
-   OpenAPI schema: `http://127.0.0.1:8000/openapi.json`
-   Health endpoint: `http://127.0.0.1:8000/health`
Keep the terminal running while using Swagger UI. Stop the development server with `Ctrl+C`.
### Why the root URL may look empty
The root URL `/` may not have a homepage route. This is an API project; use `/docs` to interact with endpoints. A missing custom homepage does not by itself indicate that the backend is broken.
## Swagger UI: Manual API Testing
Swagger UI is generated by FastAPI from the registered routes and Pydantic schemas.
### Open Swagger UI
1.  Start the application.
2.  Open `http://127.0.0.1:8000/docs` in a browser.
3.  Expand the endpoint you want to test.
4.  Click **Try it out**.
5.  Fill in path parameters and query parameters.
6.  Enter the JSON request body where required.
7.  Click **Execute**.
8.  Review the status code, response body, and generated curl command.
The example UUID shown in Swagger schemas is a placeholder. Use a real account ID returned by `POST /api/v1/accounts`.
### Recommended manual test order
1.  `GET /health`.
2.  Create a source account.
3.  Create a destination account.
4.  Check both initial balances.
5.  Credit the source.
6.  Check the source balance.
7.  Debit the source.
8.  Test an insufficient debit.
9.  Test a duplicate reference.
10. Transfer money to the destination.
11. Check both balances.
12. Retry the transfer with the same reference.
13. Inspect both transaction histories.
14. Inspect the records in Supabase.
Use new account names and unique reference IDs for each manual run. This avoids confusing a previous test's state with the current one.
## End-to-End Testing Walkthrough
This section gives a reproducible scenario using two new accounts.
### Step 1: Create two accounts
Create the source:

``` json
{
  "name": "Ledger Manual Test Source"
}
```

Create the destination:

``` json
{
  "name": "Ledger Manual Test Destination"
}
```

Save both returned account IDs. Both balances should start at `0.00`.
### Step 2: Credit the source by 100

``` json
{
  "type": "credit",
  "amount": "100.00",
  "description": "Manual test funding",
  "reference_id": "MANUAL-FUND-001"
}
```

Expected: `201 Created`; source balance becomes `100.00`.
### Step 3: Debit the source by 30

``` json
{
  "type": "debit",
  "amount": "30.00",
  "description": "Manual test debit",
  "reference_id": "MANUAL-DEBIT-001"
}
```

Expected: `201 Created`; source balance becomes `70.00`.
### Step 4: Try an insufficient debit
Attempt to debit `100.00` using a new reference ID.
Expected: `409 Conflict`. Balance remains `70.00`; no transaction is added for the rejected request.
### Step 5: Transfer 25

``` json
{
  "source_account_id": "SOURCE_ACCOUNT_UUID",
  "destination_account_id": "DESTINATION_ACCOUNT_UUID",
  "amount": "25.00",
  "reference_id": "MANUAL-TRANSFER-001",
  "description": "Manual transfer test"
}
```

Expected: `201 Created`, with one debit and one credit ledger entry.
Final balances:
Account            Balance ---------------- --------- Source             `45.00` Destination        `25.00` Combined total     `70.00`
### Step 6: Retry the transfer
Submit the same transfer request with the same reference ID.
Expected: a conflict response, with no additional debit or credit.
### Step 7: Check history
The source should have three successful transactions: credit 100, debit 30, and transfer debit 25. The destination should have one successful transfer credit of 25. Rejected requests should not create ledger entries.
## Transaction History and Pagination
The history endpoint supports page-based pagination.
Example request:

``` http
GET /api/v1/accounts/{account_id}/transactions?page=1&limit=20
```

Typical metadata includes:
-   `current_page`: requested page number.
-   `page_size`: requested page size.
-   `total_records`: number of matching transactions.
-   `total_pages`: number of pages available.
-   `items`: transactions for the requested page.
The history should be ordered newest first. When filtering by `type=credit` or `type=debit`, totals and items should reflect the filtered result set.
Test pagination by using `limit=1` and checking successive pages. Ensure no record is duplicated across pages in a stable dataset.
## Money Transfer Workflow
A transfer has two accounting entries:
1.  Debit the source account.
2.  Credit the destination account.
Both entries must be committed in one database transaction.
### Atomicity
If the source debit succeeds in memory but the destination insert fails, the database transaction must roll back all staged changes. Neither account balance should change, and neither transfer ledger entry should persist.
### Locking
For PostgreSQL, the service locks both account rows while performing the transfer. The accounts are locked in a deterministic UUID order to reduce deadlock risk when concurrent transfers involve the same accounts in opposite directions.
### Duplicate protection
The service checks the transfer reference and the database uniqueness constraint protects against duplicate transaction references. A conflict must not create another pair of ledger entries.
### Concurrency
If two requests simultaneously try to transfer 80 from an account holding 100, only one can succeed. The other must observe the updated balance and be rejected.
## Automated Tests
The suite currently contains 12 tests, covering account creation, validation, balances, transactions, history, transfers, rollback, and PostgreSQL concurrency.
Run the full suite:

``` bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./.venv/bin/python -m pytest -v
```

The `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` setting is used in this environment to avoid unrelated globally installed pytest plugin compatibility problems.
### Unit tests only
The normal tests use isolated temporary SQLite databases:

``` bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./.venv/bin/python -m pytest -q -m "not postgresql"
```

Expected result in the currently tested version: `10 passed, 2 deselected`.
### PostgreSQL integration tests only

``` bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./.venv/bin/python -m pytest -v -m postgresql -rs
```

The PostgreSQL tests exercise actual database locking and concurrent API requests.
### Latest verified test result
The full test suite was run successfully in the development environment:

``` text
12 passed, 1 warning
```

The PostgreSQL-only run reported:

``` text
2 passed, 10 deselected, 1 warning
```

The warning concerns a deprecation in the installed FastAPI/Starlette/httpx test-client integration. It did not cause the tests to fail.
Test outcomes can differ on another machine if the database is unreachable, credentials are incorrect, schema permissions differ, or dependencies differ.
## PostgreSQL Concurrency Testing
The PostgreSQL tests are marked with the `postgresql` marker so they can be selected independently.
### Concurrent debit test
The test funds an account with 100 and submits two concurrent debit requests for 80.
Expected: - One request succeeds. - One request returns the insufficient-balance conflict. - Final balance is 20. - Exactly one debit is recorded.
### Concurrent transfer test
The test funds a source with 100 and submits competing transfers of 80 to different destination accounts.
Expected: - One transfer succeeds. - One transfer fails for insufficient funds. - Source balance is 20. - Exactly one destination receives 80. - The source ledger has only one successful transfer debit. - The debit and credit entries remain consistent.
### Test schema isolation
The PostgreSQL integration fixture creates a uniquely named temporary schema, for example `ledger_test_<random_suffix>`, and configures SQLAlchemy schema translation so the test's ORM operations target that schema.
The intended safety properties are: - No `drop_all()` against the application's `public` schema. - No truncation or reset of application tables. - No modification or deletion of existing manual-testing records. - Cleanup targets only the temporary schema created by the fixture.
If the schema cannot be created or the expected tables cannot be verified, the integration tests should fail or report an explicit environmental limitation rather than silently using the application schema.
Always inspect changes to `tests/conftest.py` before relying on these guarantees.
## Database Integrity and Atomicity
The core integrity properties are:
### Balance consistency
Every accepted credit increases the account balance by its amount. Every accepted debit decreases it by its amount. A transfer decreases the source and increases the destination by the same amount.
### No overspending
The balance check and update occur under a database transaction with PostgreSQL row locking. Competing debit requests should not both spend the same funds.
### Transaction immutability
The API exposes creation and history operations, not transaction update or delete operations.
### Idempotency and reference uniqueness
The same `(account_id, reference_id)` must not create multiple ledger entries. Duplicate requests are rejected without changing the balance.
### Rollback
If any required write fails, the transaction must roll back. In a transfer, both account balance changes and both ledger entries belong to the same unit of work.
### Referential integrity
A transaction cannot validly reference an account that does not exist. Database foreign keys provide an additional layer of protection.
## Validation Rules
The following cases should be checked through Swagger or automated tests.
------------------------------------------------------------------------------------------- Input or condition                                       Expected behavior -------------------------------------------------------- ---------------------------------- Missing account name                                     Validation error
Empty/invalid account name                               Validation error
Client sends `balance` when extra fields are forbidden   Validation error
Malformed account UUID                                   Validation error
Well-formed UUID for missing account                     Not-found error
Invalid transaction type                                 Validation error
Amount equals zero                                       Validation error
Negative amount                                          Validation error
Missing reference ID                                     Validation error
Duplicate reference on same account                      Conflict
Debit greater than available balance                     Conflict
Transfer from an account to itself                       Validation error
Transfer with missing source or destination              Not-found error
Duplicate transfer reference                             Conflict
Transfer destination write fails                         Entire transfer rolls back -------------------------------------------------------------------------------------------
Always verify balances and history after a rejected request. A status code alone is not enough to prove that no side effects occurred.
## Security and Operational Notes
-   Never commit `.env` or expose database passwords.
-   Rotate credentials if a password is accidentally shared or committed.
-   URL-encode reserved characters in database connection strings.
-   Do not use production data for destructive testing.
-   Do not run migrations against a shared database without reviewing the migration.
-   Do not execute `drop_all()`, `TRUNCATE`, or database reset commands against the application schema.
-   Use least-privilege database credentials where practical.
-   Keep error responses informative but avoid exposing connection strings, stack traces, or secrets.
-   Use HTTPS and appropriate secret management when deploying publicly.
-   Configure database connectivity, timeouts, and pool sizing for the target deployment.
-   Avoid running the local development server with `--reload` in production.
-   Consider authentication, authorization, rate limiting, monitoring, and audit retention before exposing financial endpoints to real users.
## Troubleshooting
### Root URL displays nothing useful
Open `http://127.0.0.1:8000/docs`. The project is an API; a root homepage is not required for the API to work.
### Browser cannot connect
Check that Uvicorn is running and that the terminal has not exited. Start it from the project root:

``` bash
./.venv/bin/python -m uvicorn app.main:app --reload
```

### `404 ACCOUNT_NOT_FOUND`
Confirm you copied the real account ID from the `POST /api/v1/accounts` response and that the running API is connected to the database where that account was created.
### `409 INSUFFICIENT_BALANCE`
Check the source account balance first. A new account starts at zero. Credit it before attempting a debit or transfer.
### Duplicate reference conflict
Use a new reference ID for a new manual test, or inspect history to confirm whether the original request already succeeded. Do not blindly retry a request that may have completed.
### PostgreSQL tests are skipped
Run:

``` bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./.venv/bin/python -m pytest -v -m postgresql -rs
```

Read the skip reason. Verify the database URL is configured, the PostgreSQL server is reachable, credentials work, and the role can create the isolated test schema. Do not point a destructive test fixture at `public`.
### PostgreSQL connection failure
Check the connection details in the Supabase dashboard. Direct database connections may be affected by DNS, IPv6 support, network rules, or local network restrictions. Use the connection option supported by your environment and the connection string supplied by Supabase.
### `python` appears to use the wrong interpreter
Use the explicit virtual-environment interpreter:

``` bash
./.venv/bin/python --version
./.venv/bin/python -m pytest -v
```

This avoids shell aliases that may bypass `.venv`.
### Test-client deprecation warning
A deprecation warning is not itself a test failure. Review the installed FastAPI, Starlette, and HTTPX versions before changing dependencies. Upgrade a compatible set together and rerun the full suite.
## Assumptions and Design Decisions
1.  An account is created with a zero balance; funds are introduced through transactions.
2.  Monetary amounts must be positive.
3.  Credit and debit are represented as transaction types, while the amount itself is positive.
4.  Reference IDs are unique per account, not globally unique across all accounts.
5.  A transfer is represented by two transaction entries: source debit and destination credit.
6.  The transfer reference is checked against the source account and is stored on both entries.
7.  Balance-changing operations use database transactions.
8.  PostgreSQL row locks protect concurrent updates to the same account.
9.  History is returned newest first.
10. Pagination starts at page 1.
11. The API provides no transaction mutation endpoints.
12. The Swagger UI is the current interactive developer interface; a separate custom frontend is outside the current scope.
13. Unit tests use isolated SQLite databases for speed.
14. PostgreSQL concurrency tests use an isolated temporary schema.
15. Environment-specific credentials and deployment URLs are not stored in source control.
Refer to `ASSUMPTIONS.md` and `API_DOCUMENTATION.md` in the repository for any additional decisions documented in the codebase.
## Limitations and Future Improvements
Possible future enhancements include:
-   Add a custom frontend for account creation, balance display, history, and transfers.
-   Add authentication and account ownership authorization.
-   Add idempotency semantics that return the original result for safe retries, if required by the product contract.
-   Add explicit request correlation IDs and structured logging.
-   Add health/readiness probes that distinguish API health from database health.
-   Add monitoring and alerting for database errors and failed requests.
-   Add rate limiting and abuse prevention.
-   Add more property-based tests for transaction sequences and balance reconciliation.
-   Add more PostgreSQL tests for same-reference races, opposite-direction transfers, deadlocks, and rollback scenarios.
-   Add CI automation that runs unit tests and PostgreSQL integration tests in an isolated environment.
-   Add deployment instructions for a managed application host.
-   Add API authentication, authorization, and secure secret management before real-world use.
-   Define operational policies for reconciliation, backups, and data retention.
## Final Verification Checklist
Before submitting the project, verify:
-   [ ] Dependencies install in a clean virtual environment.
-   [ ] `.env` is ignored by Git.
-   [ ] The configured database URL points to the intended environment.
-   [ ] The application starts with Uvicorn.
-   [ ] `/health` responds.
-   [ ] `/docs` opens and lists all routes.
-   [ ] Account creation returns `201` and initializes the balance to zero.
-   [ ] Credit and debit update the balance correctly.
-   [ ] Insufficient funds are rejected without side effects.
-   [ ] Duplicate transaction references are rejected.
-   [ ] History filtering, ordering, and pagination work.
-   [ ] Transfers create both ledger entries atomically.
-   [ ] Failed transfers leave both balances unchanged.
-   [ ] The PostgreSQL concurrency tests execute and pass.
-   [ ] The full test suite passes.
-   [ ] The README and API documentation match the implemented endpoints.
-   [ ] No secrets or personal database credentials are committed.
------------------------------------------------------------------------
## License
Add the license appropriate for your project before publishing or distributing the repository.
