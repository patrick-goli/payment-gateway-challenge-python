from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from payment_gateway_api.status_enum import PaymentStatus


class PostPaymentResponse(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique payment identifier.",
        example="8c71cc81-c970-420a-930c-91a34e31a94b",
    )
    status: PaymentStatus = Field(
        ...,
        description="Payment outcome returned by the gateway.",
        example="Authorized",
    )
    card_number_last_four: str = Field(
        ...,
        alias="card_number_last_four",
        description="Last four digits of the card number.",
        example="4242",
    )
    expiry_month: int = Field(
        ...,
        alias="expiry_month",
        description="Card expiry month.",
        example=12,
    )
    expiry_year: int = Field(
        ...,
        alias="expiry_year",
        description="Card expiry year.",
        example=2030,
    )
    currency: str = Field(
        ...,
        description="Three-letter ISO currency code.",
        example="USD",
    )
    amount: int = Field(
        ...,
        description="Payment amount in minor units.",
        example=100,
    )

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "id": "9d3cc1ad-8db0-4ec0-8f5a-cf1b27763c0d",
                "status": "Authorized",
                "card_number_last_four": "4242",
                "expiry_month": 12,
                "expiry_year": 2030,
                "currency": "EUR",
                "amount": 100,
            }
        }


class ErrorResponse(BaseModel):
    status: Optional[PaymentStatus] = Field(
        None,
        description="Domain-level payment status, usually Rejected for validation or upstream failures.",
        example="Rejected",
    )
    error: str = Field(
        ...,
        description="HTTP reason phrase.",
        example="Bad Request",
    )
    message: str = Field(
        ...,
        description="Human-readable error message.",
        example="Validation failed",
    )
    timestamp: datetime = Field(
        ...,
        description="UTC timestamp when the error was produced.",
        example="2026-06-21T19:30:00Z",
    )
    validation_errors: Optional[Dict[str, str]] = Field(
        None,
        description="Field-level validation messages when the request body is invalid.",
        example={"card_number": "Card number is invalid"},
    )
