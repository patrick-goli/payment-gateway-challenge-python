from functools import lru_cache

from fastapi import Depends

from payment_gateway_api.external.acquiring_bank_service import AcquiringBankService
from payment_gateway_api.external.http_client import HttpClient
from payment_gateway_api.repositories.payments_repository import PaymentsRepository
from payment_gateway_api.services.payment_gateway_service import PaymentGatewayService


@lru_cache()
def get_payments_repository() -> PaymentsRepository:
    return PaymentsRepository()


@lru_cache()
def get_http_client() -> HttpClient:
    return HttpClient()


def get_acquiring_bank_service(
    http_client: HttpClient = Depends(get_http_client),
) -> AcquiringBankService:
    return AcquiringBankService(http_client)


def get_payment_gateway_service(
    payments_repository: PaymentsRepository = Depends(get_payments_repository),
    acquiring_bank_service: AcquiringBankService = Depends(get_acquiring_bank_service),
) -> PaymentGatewayService:
    return PaymentGatewayService(
        payments_repository=payments_repository,
        acquiring_bank_service=acquiring_bank_service,
    )
