# order-service/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Order Service"
    ENVIRONMENT: str = "production"
    PORT: int = 8000
    INVENTORY_SERVICE_URL: str = (
        "http://inventory-service.default.svc.cluster.local:8001"
    )
    ORDER_SERVICE_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
