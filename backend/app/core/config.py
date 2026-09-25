from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
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
    demand_model_path: Path = Path("../data/models/demand_forecast.joblib")
    demo_simulation_start_utc: datetime | None = None
    database_url: str = "postgresql+psycopg://chargegrid:chargegrid@localhost:5432/chargegrid"
    jwt_secret_key: str = Field(default=DEFAULT_JWT_SECRET, min_length=32)
    jwt_expiration_minutes: int = Field(default=60, gt=0)
    jwt_algorithm: Literal["HS256"] = "HS256"

    @field_validator("demo_simulation_start_utc", mode="before")
    @classmethod
    def empty_demo_start_is_unset(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def reject_default_jwt_secret_outside_local_environments(self) -> "Settings":
        if self.demo_simulation_start_utc is not None:
            instant = self.demo_simulation_start_utc
            if self.app_env.strip().lower() not in {"demo", "test"}:
                raise ValueError(
                    "DEMO_SIMULATION_START_UTC is allowed only in demo or test environments"
                )
            if instant.tzinfo is None or instant.utcoffset() != UTC.utcoffset(instant):
                raise ValueError("DEMO_SIMULATION_START_UTC must be an explicit UTC instant")
            self.demo_simulation_start_utc = instant.astimezone(UTC)
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
