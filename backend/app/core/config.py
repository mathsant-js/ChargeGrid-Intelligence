from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ChargeGrid Intelligence"
    app_env: str = "development"
    app_log_level: str = "INFO"
    app_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://chargegrid:chargegrid@localhost:5432/chargegrid"


@lru_cache
def get_settings() -> Settings:
    return Settings()
