# Architecture

This document describes the internal architecture of the Python/FastAPI implementation of the Payment Gateway challenge, its main components, request flows, and key design trade-offs.

---

## High-Level View

The system is a single FastAPI service that acts as a payment gateway between a merchant-facing API and an acquiring bank simulator.

Main responsibilities:

1. Validate incoming payment requests.
2. Translate valid requests into the acquiring bank’s expected payload.
3. Call the bank simulator and interpret its response.
4. Persist and expose non-sensitive payment details for later retrieval.

Key components:

- **API layer**: FastAPI routes and exception handlers.
- **Application layer**: payment orchestration service.
- **Integration layer**: HTTP client and acquiring bank adapter.
- **Persistence layer**:
  - `PaymentsRepository` – stores payments in memory by string ID.
- **Validation & configuration**: Pydantic models, validators, and environment-backed settings.
- **Observability**: file + console logging via Python `logging` and `RotatingFileHandler`.

---

## Package Structure

Simplified:

- `payment_gateway_api.app`
  - FastAPI app, route definitions, exception handlers, logging setup
- `payment_gateway_api.services`
  - `PaymentGatewayService`
- `payment_gateway_api.external`
  - `HttpClient`
  - `AcquiringBankService`
- `payment_gateway_api.models`
  - `PostPaymentRequest`
  - `PostPaymentResponse`
  - `ErrorResponse`
- `payment_gateway_api.repositories`
  - `PaymentsRepository`
- `payment_gateway_api.config`
  - `Settings`
  - `get_settings()`
- `payment_gateway_api.exceptions`
  - `PaymentNotFoundException`
  - `BankProcessingException`
- `payment_gateway_api.status_enum`
  - `PaymentStatus`

---

## Domain Model

The core business concept is a **payment**.

### Payment status

The gateway uses a domain-level payment status distinct from HTTP status codes:

- `Authorized` – the bank authorized the payment.
- `Declined` – the bank received the request and declined it.
- `Rejected` – the gateway rejected the request because of validation or upstream processing problems.

### Inbound model

`PostPaymentRequest` captures merchant input:

- `card_number`
- `expiry_month`
- `expiry_year`
- `currency`
- `amount`
- `cvv`

Validation is performed with Pydantic field constraints plus custom validators:

- card number length + regex + Luhn check
- month/year numeric ranges
- currency against configured supported currencies
- CVV length/format
- expiry date cross-field validation

### Outbound model

`PostPaymentResponse` contains only non-sensitive data:

- `id`
- `status`
- `card_number_last_four`
- `expiry_month`
- `expiry_year`
- `currency`
- `amount`

Sensitive values such as full PAN and CVV are never stored.

### Error model

`ErrorResponse` is used for consistent API errors:

- `status`
- `error`
- `message`
- `timestamp`
- `validation_errors`

---

## Request Flow: Process Payment

`POST /api/v1/payments`

1. **API layer**
   - FastAPI binds the JSON body to `PostPaymentRequest`.
   - FastAPI/Pydantic validation runs before application code.

2. **Validation**
   - Field-level and custom Pydantic validators run.
   - Validation failures are intercepted by a global `RequestValidationError` handler.
   - The response is normalized into a domain-style `ErrorResponse` with `status=Rejected` and a `validation_errors` map.


3. **Integration layer**
   - `AcquiringBankService` maps `PostPaymentRequest` to `BankRequest`.
   - It formats `expiry_date` as `MM/YYYY`.
   - It delegates the HTTP POST to `HttpClient`.
   - `HttpClient` handles transport and maps upstream HTTP failures to `BankProcessingException`.

4. **Bank response interpretation**
   - `PaymentGatewayService` maps:
     - `authorized = true` → `Authorized`
     - `authorized = false` → `Declined`
   - It generates a new string payment ID.
   - It builds `PostPaymentResponse` with masked/non-sensitive data only.
   - It persists the payment in `PaymentsRepository`.

5. **HTTP response**
   - The route returns `201 Created`.
   - A `Location` header points to `/api/v1/payments/{id}`.

---

## Request Flow: Retrieve Payment

`GET /api/v1/payments/{payment_id}`

1. API layer forwards the payment ID to `PaymentGatewayService.get_payment_by_id`.
2. The service reads from `PaymentsRepository`.
3. If found, the stored `PostPaymentResponse` is returned.
4. If not found, `PaymentNotFoundException` is raised and converted to `404 Not Found`.

---

## External Integration

### `HttpClient`

`HttpClient` is a thin wrapper around `httpx.post(...)`.

Responsibilities:

- send JSON to the bank endpoint
- enforce request timeout
- convert network failures into `503 Service Unavailable`
- convert upstream `400` into `BankProcessingException(400, ...)`
- convert upstream `503` into `BankProcessingException(503, ...)`
- convert other upstream errors into a generic `BankProcessingException`

### `AcquiringBankService`

This layer isolates bank-specific payload mapping from the rest of the application.

Responsibilities:

- build the bank request payload
- call the configured bank URL
- deserialize the response into `BankResponse`

This keeps the application service independent of HTTP and external schema details.

---

## Persistence Model

Both repositories are intentionally in-memory for challenge simplicity.

### `PaymentsRepository`

- stores `PostPaymentResponse` in a Python dictionary keyed by string payment ID
- supports `add(...)` and `get(...)`


### Trade-off

This is suitable for a coding challenge and single-instance deployment, but not durable across restarts or horizontally scaled instances. In production, both repositories should move to persistent/shared storage.

---

## Validation Strategy

Validation is intentionally split between schema-level constraints and business rules:

- field constraints via `Field(...)` for regex/range validation
- custom validator for Luhn check
- custom validator for supported currency
- root validator for expiry consistency and expiry-in-the-past checks

This keeps the route layer clean and pushes request correctness close to the model boundary.

---

## Error Handling Strategy

The application uses centralized FastAPI exception handlers to ensure a uniform JSON error contract.

### Covered cases

- `RequestValidationError`
  - returns `400 Bad Request`
  - `status=Rejected`
  - includes `validation_errors`
- `BankProcessingException`
  - returns upstream-derived HTTP code
  - `status=Rejected`
  - returns `409 Conflict`
  - `status=Rejected`
- `HTTPException`
  - used as a generic fallback for explicitly raised route-level HTTP errors

### Design intent

The API separates domain outcome (`Authorized`, `Declined`, `Rejected`) from transport outcome (200/201/400/404/409/503). This makes the contract easier for clients to consume.

---

## Configuration

Configuration is environment-driven through `Settings` in `config.py`.

Supported settings:

- `SERVER_PORT`
- `APP_ACQUIRING_BANK_API`
- `APP_PAYMENT_SUPPORTED_CURRENCIES`
- `LOGGING_FILE_NAME`

`get_settings()` is cached via `lru_cache()` to avoid repeated parsing.

This gives the service a simple local-development story (`.env`) while remaining container-friendly.

---

## Observability

The application configures:

- console logging
- rotating file logging

Current strengths:

- logs are persisted to file
- logs are available on stdout for containers

Current limitations:

- no correlation/request ID in logs
- no structured JSON logging
- no metrics or tracing
- limited explicit logging in service and client layers compared with the Java version

These are acceptable for the exercise but would be the first observability improvements in production.

---

## Testing Strategy

The test suite currently combines API-level and service-level tests.

Recommended test categories for this architecture:

- **Service tests**
  - payment authorized/declined mapping
  - payment retrieval success/not found
- **HTTP client tests**
  - success path
  - upstream 400/503
  - transport exception
  - malformed JSON / unexpected payloads
- **API tests**
  - create payment
  - retrieve payment
  - validation errors
  - error handler formatting

---

## Production Evolution

If this service were moved beyond challenge scope, the next improvements would be:

1. Replace in-memory repositories with persistent/shared storage.
2. Add authentication and merchant scoping.
3. Add structured logging, correlation IDs, metrics, and tracing.
4. Harden upstream handling with retries, circuit breakers, and response contract validation.
5. Expand tests, especially around repositories, HTTP client behavior, and error paths.
6. Add OpenAPI metadata/examples directly on routes and models.