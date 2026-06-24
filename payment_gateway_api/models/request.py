from datetime import datetime, timezone
from typing import Any, Dict

from pydantic import BaseModel, Field, root_validator, validator

from payment_gateway_api.config import get_settings


def luhn_valid(number: str) -> bool:
    total = 0
    alt = False
    for ch in reversed(number):
        n = ord(ch) - ord("0")
        if alt:
            n *= 2
            if n > 9:
                n -= 9
        total += n
        alt = not alt
    return total % 10 == 0


class PostPaymentRequest(BaseModel):
    card_number: str = Field(
        ...,
        regex=r"^\d{14,19}$",
        description="Primary account number (PAN), 14 to 19 digits, validated with the Luhn algorithm.",
        example="370762578002484",
    )
    expiry_month: int = Field(
        ...,
        ge=1,
        le=12,
        description="Card expiry month, between 1 and 12.",
        example=12,
    )
    expiry_year: int = Field(
        ...,
        ge=1970,
        le=3099,
        description="Card expiry year in YYYY format.",
        example=2030,
    )
    currency: str = Field(
        ...,
        description="Three-letter ISO currency code. Supported values are configured at runtime.",
        example="USD",
    )
    amount: int = Field(
        ...,
        ge=1,
        description="Payment amount in minor units. Must be a positive integer.",
        example=100,
    )
    cvv: str = Field(
        ...,
        regex=r"^\d{3,4}$",
        description="Card verification value, 3 or 4 digits.",
        example="123",
    )

    class Config:
        anystr_strip_whitespace = True
        schema_extra = {
            "example": {
                "card_number": "346989009877447",
                "expiry_month": 12,
                "expiry_year": 2030,
                "currency": "USD",
                "amount": 100,
                "cvv": "123",
            }
        }

    @validator("card_number")
    def validate_card_number(cls, v: str) -> str:
        if not luhn_valid(v):
            raise ValueError("Card number is invalid")
        return v

    @validator("currency")
    def validate_currency(cls, v: str) -> str:
        settings = get_settings()
        if v.upper() not in settings.supported_currencies:
            allowed = ", ".join(settings.supported_currencies)
            raise ValueError(f"Currency must be one of: {allowed}")
        return v.upper()

    @root_validator
    def validate_expiry_date(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        month = values.get("expiry_month")
        year = values.get("expiry_year")
        if month is None or year is None:
            return values

        now = datetime.now(timezone.utc)
        if (year, month) < (now.year, now.month):
            raise ValueError("Card is expired")
        return values

    def card_number_last_four(self) -> str:
        return self.card_number[-4:]
