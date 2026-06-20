import logging

from uuid import UUID
from pydantic import BaseModel, validator

from payment_gateway_api.config import get_settings
from payment_gateway_api.external.http_client import HttpClient
from payment_gateway_api.models.request import PostPaymentRequest


logger = logging.getLogger(__name__)

class BankRequest(BaseModel):
    card_number: str
    expiry_date: str
    currency: str
    amount: int
    cvv: str


class BankResponse(BaseModel):
    authorized: bool
    authorization_code: UUID | None = None

    @validator("authorization_code", pre=True)
    def empty_string_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

class AcquiringBankService:
    def __init__(self, http_client: HttpClient) -> None:
        self._http_client = http_client
        self._settings = get_settings()

    def process_payment(self, request: PostPaymentRequest) -> BankResponse:
        logger.info(
            "acquiring_bank_request amount=%s currency=%s card_last_four=%s endpoint=%s",
            request.amount,
            request.currency,
            request.card_number_last_four(),
            self._settings.acquiring_bank_api,
        )
        
        bank_request = BankRequest(
            card_number=request.card_number,
            expiry_date=f"{request.expiry_month:02d}/{request.expiry_year}",
            currency=request.currency,
            amount=request.amount,
            cvv=request.cvv,
        )
        response_json = self._http_client.post_json(
            self._settings.acquiring_bank_api,
            bank_request.dict(),
        )

        logger.info(
            "acquiring_bank_response authorized=%s authorization_code_present=%s",
            response_json["authorized"],
            response_json["authorization_code"] is not None,
        )
        
        return BankResponse(**response_json)