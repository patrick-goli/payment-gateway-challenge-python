from datetime import datetime, timezone

from payment_gateway_api.models.response import PostPaymentResponse
from payment_gateway_api.repositories.payments_repository import PaymentsRepository
from payment_gateway_api.status_enum import PaymentStatus


def build_response(payment_id: str = "payment-1") -> PostPaymentResponse:
    now = datetime.now(timezone.utc)
    return PostPaymentResponse(
        id=payment_id,
        status=PaymentStatus.AUTHORIZED,
        card_number_last_four="4242",
        expiry_month=12,
        expiry_year=now.year + 1,
        currency="USD",
        amount=100,
    )


def test_payments_repository_add_and_get():
    repository = PaymentsRepository()
    payment = build_response()

    repository.add(payment)

    assert repository.get(payment.id) == payment


def test_payments_repository_returns_none_for_missing_payment():
    repository = PaymentsRepository()

    assert repository.get("missing") is None
