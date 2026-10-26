import pytest
from tests.conftest import create_account
from tests.test_transactions import txn


def test_final_balance_reconciles(client):
    account = create_account(client)
    for kind, amount, ref in [("credit", "100", "a"), ("credit", "50", "b"), ("debit", "30", "c"), ("debit", "20", "d")]:
        assert txn(client, account["id"], kind, amount, ref).status_code == 201
    assert client.get(f"/api/v1/accounts/{account['id']}/balance").json()["balance"] == "100.00"


@pytest.mark.skip(reason="Requires isolated PostgreSQL DATABASE_URL; SQLite cannot validate row locks/concurrent-write semantics.")
def test_postgresql_concurrent_debits_cannot_overspend():
    pass
