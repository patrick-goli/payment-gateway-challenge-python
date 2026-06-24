from typing import Optional


class PaymentNotFoundException(Exception):
    def __init__(self, payment_id: str) -> None:
        self.payment_id = payment_id
        super().__init__(f"Payment ID not found: {payment_id}")


class BankProcessingException(Exception):
    def __init__(self, status_code: int, message: str, cause: Optional[Exception] = None):
        self.status_code = status_code
        self.message = message
        self.cause = cause
        super().__init__(message)
