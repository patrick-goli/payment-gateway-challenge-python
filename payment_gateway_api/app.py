import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict
from http import HTTPStatus

from fastapi import FastAPI,  HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError

from payment_gateway_api.config import get_settings
from payment_gateway_api.status_enum import PaymentStatus
from payment_gateway_api.exceptions import PaymentNotFoundException, BankProcessingException
from payment_gateway_api.dependencies import get_payment_gateway_service
from payment_gateway_api.models.request import PostPaymentRequest
from payment_gateway_api.models.response import PostPaymentResponse, ErrorResponse
from payment_gateway_api.services.payment_gateway_service import PaymentGatewayService

from fastapi import Depends, FastAPI, HTTPException, Request, status


app = FastAPI(
    title="Payment Gateway API",
    description=(
        "A simplified payment gateway that validates card payments, forwards valid "
        "requests to an acquiring bank simulator, stores non-sensitive payment data, "
        "and exposes retrieval endpoints for previously processed payments."
    ),
    version="0.2.0",
    contact={
        "name": "Patrick Goli",
        "url": "https://github.com/patrick-goli/payment-gateway-challenge-python",
    },
    openapi_tags=[
        {
            "name": "Health",
            "description": "Service health and readiness endpoints.",
        },
        {
            "name": "Payments",
            "description": "Create and retrieve card payments.",
        },
    ],
)

settings = get_settings()
logger = logging.getLogger(__name__)
log_path = Path(settings.logging_file_name)
log_path.parent.mkdir(parents=True, exist_ok=True)

handler = RotatingFileHandler(
    log_path,
    maxBytes=5_000_000,
    backupCount=3,
)
logging.basicConfig(
    level=logging.INFO,
    handlers=[handler, logging.StreamHandler()],
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

logger.info("RUNNING IN MODE : %s", settings.environment)


@app.get(
    "/",
    tags=["Health"],
    summary="Health check",
    description="Returns the service health status.",
)
async def health() -> Dict[str, str]:
    logger.debug("health_check")
    return {"status": "UP"}



@app.get(
    "/api/v1/payments/{payment_id}",
    tags=["Payments"],
    summary="Retrieve a payment",
    description="Retrieve the non-sensitive details of a previously processed payment by its ID.",
    response_model=PostPaymentResponse,
    response_description="Stored payment details.",
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Payment not found.",
            "content": {
                "application/json": {
                    "example": {
                        "error": "Not Found",
                        "message": "Payment ID not found",
                        "timestamp": "2026-06-21T19:30:00Z",
                    }
                }
            },
        }
    },
)
async def get_payment(
    payment_id: str,
    payment_gateway_service: PaymentGatewayService = Depends(get_payment_gateway_service),
) -> PostPaymentResponse:
    logger.info("get_payment request payment_id=%s", payment_id)
    try:
        return payment_gateway_service.get_payment_by_id(payment_id)
    except PaymentNotFoundException:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment ID not found",
        )


@app.post(
    "/api/v1/payments",
    tags=["Payments"],
    summary="Create a payment",
    description=(
        "Validate a card payment request, forward it to the acquiring bank simulator, "
        "and return the created payment resource."
    ),
    response_model=PostPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    response_description="Created payment.",
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Validation failed or malformed request body.",
            "content": {
                "application/json": {
                    "examples": {
                        "validation": {
                            "summary": "Validation failure",
                            "value": {
                                "status": "Rejected",
                                "error": "Bad Request",
                                "message": "Validation failed",
                                "timestamp": "2026-06-21T19:30:00Z",
                                "validation_errors": {
                                    "card_number": "Card number is invalid",
                                    "currency": "Currency must be one of: USD, EUR, CAD",
                                },
                            },
                        }
                    }
                }
            },
        },
        503: {
            "model": ErrorResponse,
            "description": "Acquiring bank unavailable.",
            "content": {
                "application/json": {
                    "example": {
                        "status": "Rejected",
                        "error": "Service Unavailable",
                        "message": "Acquiring bank is temporarily unavailable",
                        "timestamp": "2026-06-21T19:30:00Z",
                    }
                }
            },
        },
    },
)
async def create_payment(
    request: PostPaymentRequest,
    payment_gateway_service: PaymentGatewayService = Depends(get_payment_gateway_service),
):
    logger.info(
        "create_payment request currency=%s amount=%s card_last_four=%s",
        request.currency,
        request.amount,
        request.card_number_last_four(),
    )
    response = payment_gateway_service.process_payment(request)

    logger.info(
        "create_payment success payment_id=%s status=%s amount=%s currency=%s",
        response.id,
        response.status,
        response.amount,
        response.currency,
    )
    location = f"/api/v1/payments/{response.id}"
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=jsonable_encoder(response.dict(by_alias=True), exclude_none=True),
        headers={"Location": location},
    )


# --- Error handlers ---


@app.exception_handler(BankProcessingException)
async def bank_processing_exception_handler(
    request: Request, exc: BankProcessingException
) -> JSONResponse:
    
    logger.warning(
        "bank_processing_exception method=%s path=%s status_code=%s message=%s",
        request.method,
        request.url.path,
        exc.status_code,
        exc.message,
    )

    error = ErrorResponse(
        status=PaymentStatus.REJECTED,
        error=HTTPStatus(exc.status_code).phrase,
        message=exc.message,
        timestamp=datetime.now(timezone.utc),
        validation_errors=None,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(error, exclude_none=True),
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:

    logger.warning(
        "request_validation_failed method=%s path=%s errors=%s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    
    validation_errors: dict[str, str] = {}

    for err in exc.errors():
        loc = err.get("loc", [])
        msg = err.get("msg", "Invalid value")

        if len(loc) >= 2 and loc[0] == "body":
            field_name = loc[1]
        else:
            field_name = ".".join(str(x) for x in loc) if loc else "body"

        validation_errors[str(field_name)] = msg

    error = ErrorResponse(
        status=PaymentStatus.REJECTED,
        error=HTTPStatus(status.HTTP_400_BAD_REQUEST).phrase,
        message="Validation failed",
        timestamp=datetime.now(timezone.utc),
        validation_errors=validation_errors,
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(error, exclude_none=True),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    # Explicit HTTPExceptions

    logger.warning(
        "http_exception method=%s path=%s status_code=%s detail=%s",
        request.method,
        request.url.path,
        exc.status_code,
        exc.detail,
    )

    status_code = exc.status_code
    error = ErrorResponse(
        status=PaymentStatus.REJECTED
        if status_code == status.HTTP_400_BAD_REQUEST
        else None,
        error=HTTPStatus(status_code).phrase,
        message=str("An unexpected error occurred"),
        timestamp=datetime.now(timezone.utc),
        validation_errors=None,
    )
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(error, exclude_none=True),
    )
