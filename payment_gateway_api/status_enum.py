from enum import Enum


class PaymentStatus(str, Enum):
    AUTHORIZED = "Authorized"
    DECLINED = "Declined"
    REJECTED = "Rejected"
