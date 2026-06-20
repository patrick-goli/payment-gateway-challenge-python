from uuid import uuid4
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from payment_gateway_api.exceptions import PaymentNotFoundException
from payment_gateway_api.external.acquiring_bank_service import BankResponse
from payment_gateway_api.models.request import PostPaymentRequest
from payment_gateway_api.repositories.payments_repository import PaymentsRepository
from payment_gateway_api.services.payment_gateway_service import PaymentGatewayService


def build_request(**overrides) -> PostPaymentRequest:
    now = datetime.now(timezone.utc)
    data = {
        "card_number": "2277497185963469",
        "expiry_month": 12,
        "expiry_year": now.year + 1,
        "currency": "USD",
        "amount": 100,
        "cvv": "123",
    }
    data.update(overrides)
    return PostPaymentRequest(**data)


def build_service(bank_authorized: bool = True):
    payments_repository = PaymentsRepository()
    acquiring_bank_service = Mock()
    acquiring_bank_service.process_payment.return_value = BankResponse(
        authorized=bank_authorized,
        authorization_code=uuid4(),
    )

    service = PaymentGatewayService(
        payments_repository=payments_repository,
        acquiring_bank_service=acquiring_bank_service,
    )
    return service, payments_repository, acquiring_bank_service


def test_get_payment_by_id_returns_existing_payment():
    service, payments_repository, _ = build_service()
    request = build_request()
    created = service.process_payment(request)

    found = service.get_payment_by_id(created.id)

    assert found == created
    assert payments_repository.get(created.id) == created


def test_get_payment_by_id_raises_when_missing():
    service, _, _ = build_service()

    with pytest.raises(PaymentNotFoundException) as exc:
        service.get_payment_by_id("missing-id")

    assert "Payment ID not found: missing-id" == str(exc.value)


def test_process_payment_returns_authorized_when_bank_authorizes():
    service, payments_repository, acquiring_bank_service = build_service(
        bank_authorized=True
    )
    request = build_request(card_number="2277497185963469")

    response = service.process_payment(request)

    assert response.status.value == "Authorized"
    assert response.card_number_last_four == "3469"
    assert response.expiry_month == request.expiry_month
    assert response.expiry_year == request.expiry_year
    assert response.currency == request.currency
    assert response.amount == request.amount
    assert payments_repository.get(response.id) == response
    acquiring_bank_service.process_payment.assert_called_once_with(request)


def test_process_payment_returns_declined_when_bank_declines():
    service, payments_repository, acquiring_bank_service = build_service(
        bank_authorized=False
    )
    request = build_request(card_number="4242424242424242")

    response = service.process_payment(request)

    assert response.status.value == "Declined"
    assert response.card_number_last_four == "4242"
    assert payments_repository.get(response.id) == response
    acquiring_bank_service.process_payment.assert_called_once_with(request)

