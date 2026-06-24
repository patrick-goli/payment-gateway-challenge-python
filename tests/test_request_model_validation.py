from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from payment_gateway_api.models.request import PostPaymentRequest


def build_payload(**overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "card_number": "4242424242424242",
        "expiry_month": 12,
        "expiry_year": now.year + 1,
        "currency": "USD",
        "amount": 100,
        "cvv": "123",
    }
    payload.update(overrides)
    return payload


def test_valid_request_is_accepted_and_currency_is_normalized():
    request = PostPaymentRequest(**build_payload(currency=" usd "))

    assert request.card_number == "4242424242424242"
    assert request.currency == "USD"
    assert request.amount == 100
    assert request.cvv == "123"


def test_card_number_must_pass_luhn_validation():
    with pytest.raises(ValidationError) as exc:
        PostPaymentRequest(**build_payload(card_number="12345678901234"))

    assert "Card number is invalid" in str(exc.value)


def test_card_number_must_match_digit_length_constraints():
    with pytest.raises(ValidationError) as exc:
        PostPaymentRequest(**build_payload(card_number="411111111111"))

    assert "string does not match regex" in str(exc.value)


def test_currency_must_be_in_supported_list():
    with pytest.raises(ValidationError) as exc:
        PostPaymentRequest(**build_payload(currency="GBP"))

    assert "Currency must be one of" in str(exc.value)


def test_expiry_month_must_be_between_1_and_12():
    with pytest.raises(ValidationError) as exc:
        PostPaymentRequest(**build_payload(expiry_month=13))

    assert "ensure this value is less than or equal to 12" in str(exc.value)


def test_expiry_date_must_not_be_in_the_past():
    now = datetime.now(timezone.utc)

    with pytest.raises(ValidationError) as exc:
        PostPaymentRequest(
            **build_payload(expiry_month=now.month, expiry_year=now.year - 1)
        )

    assert "Card is expired" in str(exc.value)


def test_amount_must_be_positive():
    with pytest.raises(ValidationError) as exc:
        PostPaymentRequest(**build_payload(amount=0))

    assert "ensure this value is greater than or equal to 1" in str(exc.value)


def test_cvv_must_be_three_or_four_digits():
    with pytest.raises(ValidationError) as exc:
        PostPaymentRequest(**build_payload(cvv="12"))

    assert "string does not match regex" in str(exc.value)


def test_card_number_last_four_returns_last_four_digits():
    request = PostPaymentRequest(**build_payload(card_number="5555555555554444"))

    assert request.card_number_last_four() == "4444"
