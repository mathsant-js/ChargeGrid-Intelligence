from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "development-only-change-me-minimum-32-bytes"
NON_LOCAL_ENVIRONMENTS = {"staging", "production"}


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
    jwt_secret_key: str = Field(default=DEFAULT_JWT_SECRET, min_length=32)
    jwt_expiration_minutes: int = Field(default=60, gt=0)
    jwt_algorithm: Literal["HS256"] = "HS256"

    @model_validator(mode="after")
    def reject_default_jwt_secret_outside_local_environments(self) -> "Settings":
        if (
            self.app_env.strip().lower() in NON_LOCAL_ENVIRONMENTS
            and self.jwt_secret_key == DEFAULT_JWT_SECRET
        ):
            raise ValueError(
                "JWT_SECRET_KEY must be changed from the development placeholder "
                "in staging and production"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
