# Assumptions

- Money is a single implicit currency represented with `Decimal` and PostgreSQL `NUMERIC(18,2)`; more than two decimal places is rejected.
- Accounts always start at `0.00`. IDs and UTC-capable timestamps are server generated.
- A reference is idempotent only within one account. A duplicate is a `409`, makes no balance change, and creates no new entry.
- History defaults to page 1, 20 records; maximum limit is 100. Ties are ordered by transaction ID after timestamp.
- Errors use `{error:{code,message}}`; validation errors are deliberately summarized to avoid leaking internals.
- Ledger entries are API-immutable. Corrections are represented by a new compensating entry, never a rewrite.
- PostgreSQL account-row locking plus a single transaction makes the stored balance and successfully inserted ledger records atomic. Database checks additionally forbid negative balances/amounts and illegal types.
- Transfers reuse the ledger table rather than adding a transfer table. They create a source debit and destination credit with the same supplied reference. Transfer idempotency is scoped to the source account, and each corresponding ledger entry remains subject to the existing per-account reference uniqueness constraint.
