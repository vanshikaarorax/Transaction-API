from tests.conftest import create_account


def txn(client, account_id, kind, amount, reference, description="test"):
    return client.post(f"/api/v1/accounts/{account_id}/transactions", json={"type": kind, "amount": amount, "description": description, "reference_id": reference})


def test_credit_debit_and_insufficient_rollback(client):
    account = create_account(client)
    assert txn(client, account["id"], "credit", "100.00", "c1").status_code == 201
    assert txn(client, account["id"], "debit", "30.00", "d1").status_code == 201
    failed = txn(client, account["id"], "debit", "100.00", "d2")
    assert failed.status_code == 409 and failed.json()["error"]["code"] == "INSUFFICIENT_BALANCE"
    assert client.get(f"/api/v1/accounts/{account['id']}/balance").json()["balance"] == "70.00"
    assert client.get(f"/api/v1/accounts/{account['id']}/transactions").json()["total_records"] == 2


def test_validation_duplicate_and_reference_scope(client):
    first, second = create_account(client, "one"), create_account(client, "two")
    assert txn(client, first["id"], "credit", "1.001", "precision").status_code == 422
    assert txn(client, first["id"], "credit", "0", "zero").status_code == 422
    assert txn(client, first["id"], "other", "1", "bad").status_code == 422
    assert txn(client, first["id"], "credit", "10", "same").status_code == 201
    assert txn(client, first["id"], "credit", "10", "same").status_code == 409
    assert txn(client, second["id"], "credit", "10", "same").status_code == 201
    assert txn(client, "00000000-0000-0000-0000-000000000001", "credit", "1", "x").status_code == 404


def test_history_filter_pagination_order_and_no_mutation_endpoints(client):
    account = create_account(client)
    for i, kind in enumerate(["credit", "debit", "credit"]):
        if kind == "debit":
            txn(client, account["id"], "credit", "10", "fund")
        assert txn(client, account["id"], kind, "1", f"r{i}").status_code == 201
    all_rows = client.get(f"/api/v1/accounts/{account['id']}/transactions", params={"page": 1, "limit": 2}).json()
    assert all_rows["total_records"] == 4 and all_rows["total_pages"] == 2 and len(all_rows["items"]) == 2
    assert client.get(f"/api/v1/accounts/{account['id']}/transactions?type=credit").json()["total_records"] == 3
    assert client.get(f"/api/v1/accounts/{account['id']}/transactions?type=debit").json()["total_records"] == 1
    assert client.get(f"/api/v1/accounts/{account['id']}/transactions?page=0").status_code == 422
    assert client.get(f"/api/v1/accounts/{account['id']}/transactions?type=wire").status_code == 422
    assert client.patch(f"/api/v1/accounts/{account['id']}/transactions/not-real").status_code == 404
    assert client.delete(f"/api/v1/accounts/{account['id']}/transactions/not-real").status_code == 404
