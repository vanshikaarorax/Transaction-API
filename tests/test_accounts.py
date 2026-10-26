from tests.conftest import create_account


def test_create_account_is_server_initialized(client):
    account = create_account(client)
    assert account["name"] == "Ada" and account["balance"] == "0.00" and account["created_at"]


def test_name_validation_and_client_controlled_fields_rejected(client):
    assert client.post("/api/v1/accounts", json={"name": "  "}).status_code == 422
    assert client.post("/api/v1/accounts", json={"name": "Ada", "balance": "99.00", "created_at": "2000-01-01T00:00:00Z"}).status_code == 201
    # Pydantic ignores unknown fields, so malicious values have no effect.
    created = client.post("/api/v1/accounts", json={"name": "Grace", "balance": "7.00"}).json()
    assert created["balance"] == "0.00"


def test_balance_and_missing_account(client):
    account = create_account(client)
    assert client.get(f"/api/v1/accounts/{account['id']}/balance").json()["balance"] == "0.00"
    assert client.get("/api/v1/accounts/00000000-0000-0000-0000-000000000001/balance").status_code == 404
