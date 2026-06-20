import logging

from typing import Any, Dict

import httpx
from fastapi import status

from payment_gateway_api.exceptions import BankProcessingException


logger = logging.getLogger(__name__)

class HttpClient:
    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout = timeout_seconds

    def post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("http_post_json url=%s", url)
        try:
            response = httpx.post(url, json=payload, timeout=self._timeout)
        except Exception as exc:
            logger.exception("http_post_failed url=%s", url)
            raise BankProcessingException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Error while contacting acquiring bank",
            ) from exc
        logger.info("http_post_response url=%s status_code=%s", url, response.status_code)
        if 200 <= response.status_code < 300:
            return response.json()

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            logger.warning("http_post_bad_request url=%s", url)
            raise BankProcessingException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Invalid request sent to acquiring bank",
            )

        if response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            logger.warning("http_post_service_unavailable url=%s", url)
            raise BankProcessingException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Acquiring bank is temporarily unavailable",
            )

        logger.warning(
                "http_post_unexpected_status url=%s status_code=%s",
                url,
                response.status_code,
            )

        raise BankProcessingException(
            status_code=response.status_code,
            message=f"Unexpected response from acquiring bank: {response.status_code}",
        )