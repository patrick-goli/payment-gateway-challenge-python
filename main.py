import uvicorn
from dotenv import load_dotenv

from payment_gateway_api.config import get_settings


def main():
    load_dotenv()

    settings = get_settings()

    uvicorn.run(
        app="payment_gateway_api.app:app",
        host="0.0.0.0",
        port=settings.server_port,
        reload=True,
        workers=1,
    )


if __name__ == "__main__":
    main()