import uvicorn
from dotenv import load_dotenv

from payment_gateway_api.config import get_settings


def main():
    load_dotenv()
    settings = get_settings()

    if settings.is_dev:
        uvicorn.run(
            "payment_gateway_api.app:app",
            host="0.0.0.0",
            port=settings.server_port,
            reload=True,
        )
    else:
        uvicorn.run(
            "payment_gateway_api.app:app",
            host="0.0.0.0",
            port=settings.server_port,
            workers=2,
        )


if __name__ == "__main__":
    main()
