from uuid import UUID

from pydantic import BaseModel, field_validator

from app.models.infrastructure import ChargerStatus
from app.schemas.common import Name, ORMResponse, PositivePower, ShortCode


class ChargerCreate(BaseModel):
    station_id: UUID
    name: Name
    code: ShortCode
    max_power_kw: PositivePower
    status: ChargerStatus = ChargerStatus.AVAILABLE
    is_active: bool = True


class ChargerUpdate(BaseModel):
    station_id: UUID | None = None
    name: Name | None = None
    code: ShortCode | None = None
    max_power_kw: PositivePower | None = None
    status: ChargerStatus | None = None
    is_active: bool | None = None

    @field_validator("station_id", "name", "code", "max_power_kw", "status", "is_active")
    @classmethod
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class ChargerResponse(ORMResponse):
    station_id: UUID
    name: str
    code: str
    max_power_kw: float
    status: ChargerStatus
    is_active: bool
