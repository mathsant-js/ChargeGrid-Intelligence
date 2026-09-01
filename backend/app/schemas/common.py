from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
ShortCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
LicensePlate = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
PositivePower = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class ErrorResponse(BaseModel):
    detail: str


class ORMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at")
    @classmethod
    def normalize_audit_timestamp_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
