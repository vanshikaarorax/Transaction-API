import pytest
from tests.conftest import create_account
from tests.test_transactions import txn


def test_final_balance_reconciles(client):
    account = create_account(client)
    for kind, amount, ref in [("credit", "100", "a"), ("credit", "50", "b"), ("debit", "30", "c"), ("debit", "20", "d")]:
        assert txn(client, account["id"], kind, amount, ref).status_code == 201
    assert client.get(f"/api/v1/accounts/{account['id']}/balance").json()["balance"] == "100.00"


# @pytest.mark.skip(reason="Requires isolated PostgreSQL TEST_DATABASE_URL; SQLite cannot validate row locks/concurrent-write semantics.")
# def test_postgresql_concurrent_debits_cannot_overspend():
#     pass

from concurrent.futures import ThreadPoolExecutor


@pytest.mark.postgresql
def test_postgresql_concurrent_debits_cannot_overspend(postgres_client):
    client = postgres_client
    account = create_account(client, "Concurrent debit test")
    account_id = account["id"]

    # Fund the account with 100.
    assert txn(client, account_id, "credit", "100.00", "fund-concurrent").status_code == 201

    def debit(reference):
        return client.post(
            f"/api/v1/accounts/{account_id}/transactions",
            json={
                "type": "debit",
                "amount": "80.00",
                "description": "Concurrent debit test",
                "reference_id": reference,
            },
        )

    # Both requests attempt to debit 80 from the same 100 balance.
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(debit, "concurrent-debit-A"),
            executor.submit(debit, "concurrent-debit-B"),
        ]
        responses = [future.result(timeout=30) for future in futures]

    statuses = sorted(response.status_code for response in responses)

    # One debit succeeds; the other sees the updated balance and is rejected.
    assert statuses == [201, 409]
    assert next(response for response in responses if response.status_code == 409).json()["error"]["code"] == "INSUFFICIENT_BALANCE"

    balance_response = client.get(
        f"/api/v1/accounts/{account_id}/balance"
    )
    assert balance_response.status_code == 200
    assert balance_response.json()["balance"] == "20.00"

    history = client.get(
        f"/api/v1/accounts/{account_id}/transactions"
    ).json()

    # One funding credit plus exactly one successful debit.
    assert history["total_records"] == 2
