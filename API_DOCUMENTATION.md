# API documentation

FastAPI OpenAPI is available at `/docs` and `/openapi.json`.

All application errors use `{ "error": { "code": "...", "message": "..." } }`. Validation errors return `422` with `VALIDATION_ERROR`; unknown accounts return `404 ACCOUNT_NOT_FOUND`.

## Create account

`POST /api/v1/accounts` — body: `{ "name": "Ada Lovelace" }`. Returns `201` and `{id,name,balance:"0.00",created_at}`. Initial balance and timestamp are server controlled; extra client fields cannot override them.

## Balance

`GET /api/v1/accounts/{account_id}/balance` returns `{ "account_id": "...", "balance": "100.00" }`.

## Add transaction

`POST /api/v1/accounts/{account_id}/transactions` — body:

```json
{"type":"credit","amount":"100.00","description":"Opening funding","reference_id":"deposit-001"}
```

Returns `201` with server-generated id, account id and timestamp. Amounts must be positive and have at most two decimal places. `debit` returns `409 INSUFFICIENT_BALANCE` if it cannot be covered. A duplicate `(account_id, reference_id)` returns `409 DUPLICATE_REFERENCE`; the same reference is allowed on another account.

## History

`GET /api/v1/accounts/{account_id}/transactions?type=credit&page=1&limit=20`

`type` is optional (`credit` or `debit`); `page` starts at 1 and `limit` is 1–100 (default 20). Response contains `items`, `current_page`, `page_size`, `total_records`, and `total_pages`. Results are filtered before totals/pagination and sorted newest-first by `created_at`, then ID.

## Transfer money

`POST /api/v1/transfers` transfers money between two distinct accounts:

```json
{
  "source_account_id": "b4b8de0e-348d-4e3d-b3c0-8c8bc31ff814",
  "destination_account_id": "8bcf99ad-f4bb-46dd-86f7-4afc370a7e4c",
  "amount": "30.00",
  "reference_id": "transfer-001",
  "description": "Invoice settlement"
}
```

It returns `201` with `reference_id`, `source_transaction` (a debit), and `destination_transaction` (a credit). Both ledger records use the supplied reference and remain subject to existing per-account reference uniqueness. The transfer reference is idempotent within its source account: a repeat returns `409 DUPLICATE_TRANSFER_REFERENCE` and does not execute again. A missing account returns `404`, insufficient source funds return `409 INSUFFICIENT_BALANCE`, and same-account or invalid amounts return `422`.

## Integrity and immutability

There are no PUT, PATCH, or DELETE transaction routes. On PostgreSQL, each write locks the target account (`SELECT ... FOR UPDATE`), checks funds, inserts the transaction and updates balance inside one database transaction. Transfers lock both accounts in sorted UUID order before making either change, then insert both ledger records and commit once. The database constraints and unique index remain the final protection against invalid or concurrent writes.
