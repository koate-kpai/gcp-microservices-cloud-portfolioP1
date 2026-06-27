# inventory-service/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Inventory Service"
    ENVIRONMENT: str = "production"
    PORT: int = 8001

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
