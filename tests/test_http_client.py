from unittest.mock import Mock, patch

import httpx
import pytest
from fastapi import status

from payment_gateway_api.exceptions import BankProcessingException
from payment_gateway_api.external.http_client import HttpClient


def make_response(status_code: int, json_data=None):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data if json_data is not None else {}
    return response


def test_post_json_returns_json_for_successful_2xx_response():
    client = HttpClient(timeout_seconds=3.5)
    payload = {"amount": 100}
    expected = {"authorized": True, "authorization_code": "auth-123"}

    with patch("payment_gateway_api.external.http_client.httpx.post") as mock_post:
        mock_post.return_value = make_response(200, expected)

        result = client.post_json("http://bank/payments", payload)

    assert result == expected
    mock_post.assert_called_once_with(
        "http://bank/payments", json=payload, timeout=3.5
    )


def test_post_json_raises_bad_request_for_400_response():
    client = HttpClient()

    with patch("payment_gateway_api.external.http_client.httpx.post") as mock_post:
        mock_post.return_value = make_response(status.HTTP_400_BAD_REQUEST)

        with pytest.raises(BankProcessingException) as exc:
            client.post_json("http://bank/payments", {"amount": 100})

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.value.message == "Invalid request sent to acquiring bank"


def test_post_json_raises_service_unavailable_for_503_response():
    client = HttpClient()

    with patch("payment_gateway_api.external.http_client.httpx.post") as mock_post:
        mock_post.return_value = make_response(status.HTTP_503_SERVICE_UNAVAILABLE)

        with pytest.raises(BankProcessingException) as exc:
            client.post_json("http://bank/payments", {"amount": 100})

    assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc.value.message == "Acquiring bank is temporarily unavailable"


def test_post_json_raises_service_unavailable_on_transport_exception():
    client = HttpClient()

    with patch("payment_gateway_api.external.http_client.httpx.post") as mock_post:
        mock_post.side_effect = httpx.ConnectError("boom")

        with pytest.raises(BankProcessingException) as exc:
            client.post_json("http://bank/payments", {"amount": 100})

    assert exc.value.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert exc.value.message == "Error while contacting acquiring bank"


def test_post_json_raises_generic_exception_for_unexpected_upstream_status():
    client = HttpClient()

    with patch("payment_gateway_api.external.http_client.httpx.post") as mock_post:
        mock_post.return_value = make_response(502)

        with pytest.raises(BankProcessingException) as exc:
            client.post_json("http://bank/payments", {"amount": 100})

    assert exc.value.status_code == 502
    assert exc.value.message == "Unexpected response from acquiring bank: 502"