from datetime import datetime, timezone
from uuid import UUID

from fastapi.testclient import TestClient

from payment_gateway_api.app import app

client = TestClient(app)
now = datetime.now(timezone.utc)


def build_body(**overrides):
    body = {
        "card_number": "2277497185963469",
        "expiry_month": 12,
        "expiry_year": now.year + 1,
        "currency": "USD",
        "amount": 100,
        "cvv": "123",
    }
    body.update(overrides)
    return body


def test_create_and_retrieve_payment():
    body = build_body()

    response = client.post("/api/v1/payments", json=body)
    assert response.status_code == 201

    data = response.json()
    payment_id = data["id"]
    assert payment_id is not None
    UUID(payment_id)
    assert data["status"] == "Authorized"
    assert data["card_number_last_four"] == "3469"
    assert data["currency"] == "USD"
    assert data["amount"] == 100

    location = response.headers["Location"]
    assert location == f"/api/v1/payments/{payment_id}"

    get_resp = client.get(location)
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["id"] == payment_id
    assert get_data["status"] == "Authorized"
    assert get_data["card_number_last_four"] == "3469"


def test_get_payment_returns_404_when_missing():
    response = client.get("/api/v1/payments/3fa85f64-5717-4562-b3fc-2c963f66afa6")

    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "Not Found"
    assert data["message"] == "Payment ID not found"
    assert "timestamp" in data


def test_create_payment_validation_errors_when_required_field_missing():
    body = {
        "expiry_month": 12,
        "expiry_year": now.year + 1,
        "currency": "USD",
        "amount": 100,
        "cvv": "123",
    }

    response = client.post("/api/v1/payments", json=body)

    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Rejected"
    assert data["error"] == "Bad Request"
    assert data["message"] == "Validation failed"
    assert "validation_errors" in data
    assert "card_number" in data["validation_errors"]


def test_create_payment_validation_errors_for_invalid_currency_and_card():
    body = build_body(card_number="12345678901234", currency="GBP")

    response = client.post("/api/v1/payments", json=body)

    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Rejected"
    assert data["message"] == "Validation failed"
    assert "validation_errors" in data
    assert "card_number" in data["validation_errors"] or "__root__" in data["validation_errors"]
    assert "currency" in data["validation_errors"]


def test_create_payment_returns_400_for_malformed_json():
    response = client.post(
        "/api/v1/payments",
        content='{"card_number": "2277497185963469",',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "Rejected"
    assert data["error"] == "Bad Request"