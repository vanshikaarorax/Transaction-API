import pytest
from decimal import Decimal
from tests.conftest import create_account
from tests.test_transactions import txn

def transfer(client, source, destination, amount="30.00", reference="transfer-1"):
    return client.post("/api/v1/transfers", json={
        "source_account_id": source, "destination_account_id": destination,
        "amount": amount, "reference_id": reference, "description": "Payment",
    })


def balance(client, account_id):
    return client.get(f"/api/v1/accounts/{account_id}/balance").json()["balance"]


def test_successful_transfer_updates_both_ledgers_and_conserves_balance(client):
    source, destination = create_account(client, "source"), create_account(client, "destination")
    assert txn(client, source["id"], "credit", "100.00", "funding").status_code == 201
    response = transfer(client, source["id"], destination["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["source_transaction"]["type"] == "debit"
    assert body["destination_transaction"]["type"] == "credit"
    assert balance(client, source["id"]) == "70.00"
    assert balance(client, destination["id"]) == "30.00"
    assert client.get(f"/api/v1/accounts/{source['id']}/transactions").json()["total_records"] == 2
    assert client.get(f"/api/v1/accounts/{destination['id']}/transactions").json()["total_records"] == 1


def test_transfer_rejections_do_not_create_side_effects(client):
    source, destination = create_account(client, "source"), create_account(client, "destination")
    assert transfer(client, source["id"], destination["id"], "1.00").status_code == 409
    assert balance(client, source["id"]) == balance(client, destination["id"]) == "0.00"
    assert transfer(client, source["id"], source["id"]).status_code == 422
    assert transfer(client, source["id"], destination["id"], "0").status_code == 422
    assert transfer(client, "00000000-0000-0000-0000-000000000001", destination["id"]).status_code == 404
    assert transfer(client, source["id"], "00000000-0000-0000-0000-000000000001").status_code == 404


def test_duplicate_transfer_and_destination_insert_failure_roll_back(client):
    source, destination = create_account(client, "source"), create_account(client, "destination")
    assert txn(client, source["id"], "credit", "100.00", "fund").status_code == 201
    assert transfer(client, source["id"], destination["id"], "30.00", "once").status_code == 201
    assert transfer(client, source["id"], destination["id"], "30.00", "once").status_code == 409
    assert balance(client, source["id"]) == "70.00" and balance(client, destination["id"]) == "30.00"
    # A destination reference collision occurs after the source debit is staged;
    # the unit of work must roll every staged change back.
    assert txn(client, destination["id"], "credit", "1.00", "collision").status_code == 201
    assert transfer(client, source["id"], destination["id"], "10.00", "collision").status_code == 409
    assert balance(client, source["id"]) == "70.00" and balance(client, destination["id"]) == "31.00"
    history = client.get(f"/api/v1/accounts/{source['id']}/transactions").json()
    assert not any(item["reference_id"] == "collision" for item in history["items"])


# @pytest.mark.skip(reason="Requires isolated PostgreSQL TEST_DATABASE_URL to exercise locks and concurrent transfer requests.")
# def test_postgresql_concurrent_transfers_cannot_overspend_or_duplicate():
#     pass


from concurrent.futures import ThreadPoolExecutor


@pytest.mark.postgresql
def test_postgresql_concurrent_transfers_cannot_overspend_or_duplicate(
    postgres_client,
):
    client = postgres_client

    source = create_account(client, "Concurrent transfer source")
    destination_a = create_account(client, "Concurrent destination A")
    destination_b = create_account(client, "Concurrent destination B")

    source_id = source["id"]

    assert txn(
        client,
        source_id,
        "credit",
        "100.00",
        "fund-concurrent-transfer",
    ).status_code == 201

    def make_transfer(destination_id, reference):
        return client.post(
            "/api/v1/transfers",
            json={
                "source_account_id": source_id,
                "destination_account_id": destination_id,
                "amount": "80.00",
                "reference_id": reference,
                "description": "Concurrent transfer test",
            },
        )

    # Competing transfers have different references but the same source.
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                make_transfer,
                destination_a["id"],
                "concurrent-transfer-A",
            ),
            executor.submit(
                make_transfer,
                destination_b["id"],
                "concurrent-transfer-B",
            ),
        ]
        responses = [future.result(timeout=30) for future in futures]

    statuses = sorted(response.status_code for response in responses)
    assert statuses == [201, 409]
    assert next(response for response in responses if response.status_code == 409).json()["error"]["code"] == "INSUFFICIENT_BALANCE"

    # The source cannot be overspent.
    assert balance(client, source_id) == "20.00"

    # Exactly 80 was transferred, regardless of which destination won.
    destination_a_balance = balance(client, destination_a["id"])
    destination_b_balance = balance(client, destination_b["id"])

    assert Decimal(destination_a_balance) + Decimal(destination_b_balance) == Decimal("80.00")

    source_history = client.get(
        f"/api/v1/accounts/{source_id}/transactions"
    ).json()

    # One funding credit plus one successful transfer debit.
    assert source_history["total_records"] == 2

    successful_destinations = [
        destination_a["id"]
        if destination_a_balance == "80.00"
        else None,
        destination_b["id"]
        if destination_b_balance == "80.00"
        else None,
    ]
    assert sum(item is not None for item in successful_destinations) == 1

    # Same-reference racing requests must execute the transfer exactly once.
    duplicate_source = create_account(client, "Concurrent duplicate source")
    duplicate_destination = create_account(client, "Concurrent duplicate destination")
    assert txn(client, duplicate_source["id"], "credit", "100.00", "fund-duplicate-race").status_code == 201

    def duplicate_transfer():
        return client.post("/api/v1/transfers", json={
            "source_account_id": duplicate_source["id"],
            "destination_account_id": duplicate_destination["id"],
            "amount": "80.00", "reference_id": "duplicate-transfer-race", "description": "Duplicate race",
        })

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: duplicate_transfer(), range(2)))
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert next(response for response in responses if response.status_code == 409).json()["error"]["code"] == "DUPLICATE_TRANSFER_REFERENCE"
    assert balance(client, duplicate_source["id"]) == "20.00"
    assert balance(client, duplicate_destination["id"]) == "80.00"

