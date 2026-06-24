import logging

from uuid import uuid4

from payment_gateway_api.status_enum import PaymentStatus
from payment_gateway_api.external.acquiring_bank_service import AcquiringBankService
from payment_gateway_api.models.request import PostPaymentRequest
from payment_gateway_api.models.response import PostPaymentResponse
from payment_gateway_api.repositories.payments_repository import PaymentsRepository
from payment_gateway_api.exceptions import PaymentNotFoundException

logger = logging.getLogger(__name__)


class PaymentGatewayService:
    def __init__(
        self,
        payments_repository: PaymentsRepository,
        acquiring_bank_service: AcquiringBankService,
    ) -> None:
        self._payments_repository = payments_repository
        self._acquiring_bank_service = acquiring_bank_service

    def get_payment_by_id(self, payment_id: str) -> PostPaymentResponse:
        logger.info("payment_lookup payment_id=%s", payment_id)
        payment = self._payments_repository.get(payment_id)
        if payment is None:
            logger.warning("payment_not_found payment_id=%s", payment_id)
            raise PaymentNotFoundException(str(payment_id))
        logger.info("payment_lookup_hit payment_id=%s status=%s", payment.id, payment.status)
        return payment

    def process_payment(
        self,
        request: PostPaymentRequest,
    ) -> PostPaymentResponse:

        logger.info(
                "payment_processing_started amount=%s currency=%s card_last_four=%s",
                request.amount,
                request.currency,
                request.card_number_last_four(),
            )

        bank_response = self._acquiring_bank_service.process_payment(request)

        status = (
            PaymentStatus.AUTHORIZED if bank_response.authorized else PaymentStatus.DECLINED
        )

        response = PostPaymentResponse(
            id=str(uuid4()),
            status=status,
            card_number_last_four=request.card_number_last_four(),
            expiry_month=request.expiry_month,
            expiry_year=request.expiry_year,
            currency=request.currency,
            amount=request.amount,
        )

        self._payments_repository.add(response)

        logger.info(
            "payment_processing_completed payment_id=%s status=%s amount=%s currency=%s",
            response.id,
            response.status,
            response.amount,
            response.currency,
        )

        return response
