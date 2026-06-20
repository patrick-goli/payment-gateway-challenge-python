from typing import Dict, Optional

from payment_gateway_api.models.response import PostPaymentResponse


class PaymentsRepository:
    def __init__(self) -> None:
        self._payments: Dict[str, PostPaymentResponse] = {}

    def add(self, payment: PostPaymentResponse) -> None:
        self._payments[payment.id] = payment

    def get(self, payment_id: str) -> Optional[PostPaymentResponse]:
        return self._payments.get(payment_id)