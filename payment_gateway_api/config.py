import os
from functools import lru_cache
from typing import List


class Settings:
    def __init__(self) -> None:
        self.environment: str = os.getenv("APP_ENV", "local")
        self.is_dev = self.environment in {"local", "dev"}
        self.server_port: int = int(os.getenv("SERVER_PORT", "8090"))
        self.acquiring_bank_api: str = os.getenv(
            "APP_ACQUIRING_BANK_API",
            "http://localhost:8080/payments",
        )
        currencies = os.getenv(
            "APP_PAYMENT_SUPPORTED_CURRENCIES",
            "USD,EUR,CAD",
        )
        self.supported_currencies: List[str] = [
            c.strip().upper() for c in currencies.split(",") if c.strip()
        ]
        self.logging_file_name: str = os.getenv(
            "LOGGING_FILE_NAME",
            "./log/application.log",
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
