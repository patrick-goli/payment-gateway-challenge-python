# Checkout.com Payment Gateway Challenge (Python/FastAPI)

This project implements a simplified **payment gateway** in Python using FastAPI.
It exposes an API that allows a merchant to:

- process a card payment through the gateway
- retrieve the details of a previously processed payment

A **bank simulator** acts as the acquiring bank. The gateway validates requests, forwards valid ones to the simulator, and stores only non-sensitive payment data.

---

## Overview

## API documentation

The service exposes OpenAPI API documentation described in `payment-gateway-openapi.yaml` and at:

- Swagger UI: `http://localhost:8090/docs`
- ReDoc: `http://localhost:8090/redoc`

### Features

- `POST /api/v1/payments`
  - process a payment
  - validates card and payment data and forwards valid requests to the bank

- `GET /api/v1/payments/{id}`
  - returns stored payment details

Shopper             Merchant                 Gateway               Bank Simulator
   │                    │                        │                         │
   │─── Initiate ──────>│                        │                         │
   │                    │─── POST /payments ────>│                         │
   │                    │    (Schema Validation) │                         │
   │                    │                        │─── POST /payments ─────>│
   │                    │                        │    (Async HTTP Client)  │
   │                    │                        │                         │
   │                    │                        │<── [200 OK Authorized] ─│
   │                    │<── [210 Created] ──────│                         │
   │                    │    (Masked Response)   │                         │


### Data and Security

- Only **non-sensitive** data is stored and returned.
- Full card number and CVV are used only for validation and for the acquiring bank request.
- Stored/retrieved payment data contains only the last four digits of the card number.
- Errors are normalized into a consistent `ErrorResponse` model.

---

## Design Highlights

### Separation of concerns

The code is structured into focused layers:

- **API layer** (`payment_gateway_api.app`)
  - FastAPI routes
  - exception handlers
- **Service layer** (`PaymentGatewayService`)
  - orchestrates payment creation/retrieval
- **Integration layer**
  - `AcquiringBankService` maps internal request → bank request
  - `HttpClient` encapsulates HTTP behavior and upstream error mapping
- **Persistence layer**
  - `PaymentsRepository`
- **Validation/configuration layer**
  - Pydantic request models
  - environment-backed settings

### Validation

`PostPaymentRequest` uses:

- regex and numeric constraints
- Luhn validation for card numbers
- supported-currency validation from configuration
- cross-field expiry validation

### Error handling

The API centralizes exception handling and returns a consistent error contract for:

- validation failures
- payment not found
- upstream bank failures

### Observability

The service emits structured logs to both the console and a rotating log file (`LOGGING_FILE_NAME`):

- Incoming requests:
  - `POST /api/v1/payments`: logs currency, amount and last four card digits (never full PAN or CVV).
  - `GET /api/v1/payments/{id}`: logs lookup attempts and results.
- Payment lifecycle:
  - When a payment is processed, the gateway logs the generated payment ID, domain status, amount and currency.
- External integration:
  - Calls to the acquiring bank log the target URL, HTTP status codes, and whether the bank authorized the payment.
- Error handling:
  - Validation failures, upstream bank problems, and 4xx/5xx responses are logged with method, path, status code and a concise message.

These logs are intended to support troubleshooting and basic reporting while avoiding any storage of sensitive cardholder data.

---

## Configuration

Configuration is read from environment variables.

### Supported variables

```env
SERVER_PORT=8090
APP_ACQUIRING_BANK_API=http://localhost:8080/payments
APP_PAYMENT_SUPPORTED_CURRENCIES=USD,EUR,CAD
LOGGING_FILE_NAME=./log/application.log
```

An example local file is provided in `.env.example`.

---

## Running locally

### Requirements

- Python 3.11
- Poetry
- Docker

### 1. Start the bank simulator

```bash
docker compose up bank_simulator
```

### 2. Configure environment

```bash
cp .env.example .env
```

### 3. Install dependencies

```bash
poetry install
```

### 4. Run the application

```bash
poetry run python main.py
```

The API will be available on `http://localhost:8090`.

---

## Running with Docker

Build and run the service and simulator with Docker Compose:

```bash
docker compose up --build
```

If using a production-oriented env file, ensure the referenced file exists (`.env.production`).

---

## Running tests

```bash
poetry run pytest
```

---

## Project structure

```text
├── Dockerfile
├── docker-compose.yml
├── main.py
├── payment_gateway_api/
│   ├── app.py
│   ├── config.py
│   ├── exceptions.py
│   ├── status_enum.py
│   ├── external/
│   │   ├── acquiring_bank_service.py
│   │   └── http_client.py
│   ├── models/
│   │   ├── request.py
│   │   └── response.py
│   ├── repositories/
│   │   └── payments_repository.py
│   └── services/
│       └── payment_gateway_service.py
└── tests/
```

---

## Assumptions and trade-offs

- Repositories are in-memory for simplicity.
- Payment IDs are generated internally and exposed as strings.
- Only non-sensitive payment data is persisted.
- The bank simulator is treated as an external dependency and its failures are mapped into gateway errors.

---

## Possible next steps

- In-memory storage: `PaymentsRepository` keeps payments in memory only. A production system would use a durable data store (e.g. PostgreSQL) and proper migrations.
- No authentication/authorization: the API is intentionally open. In a real system, payments would be scoped to merchants and protected via API keys or OAuth2/JWT.
- No idempotency: repeated `POST /api/v1/payments` requests are treated as separate payments. A production gateway would implement idempotency keys and replay protection.
- Single acquiring bank: the integration layer targets one bank simulator. Extending this to multiple providers would involve introducing an abstraction for bank connectors and routing/selection logic.
- Correlation ID for full request traceability
- No metrics/traces: only logging is implemented. Metrics (e.g. authorized/declined/rejected counts, bank latency) and distributed tracing would be the next step for full observability.
- Pagination and filtering: Add `GET /payments?merchant_id=&status=` with pagination
