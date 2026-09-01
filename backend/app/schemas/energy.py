from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.energy import ChargingSessionStatus
from app.schemas.common import ORMResponse

NonNegativePower = Annotated[float, Field(ge=0, allow_inf_nan=False)]
class ChargingSessionStart(BaseModel):
    vehicle_id: UUID
    charger_id: UUID

    @model_validator(mode="before")
    @classmethod
    def reject_user_supplied_tariff(cls, value: object) -> object:
        if isinstance(value, dict) and "tariff_per_kwh" in value:
            raise ValueError("tariff_per_kwh is selected by the backend")
        return value


class ChargingSessionResponse(ORMResponse):
    user_id: UUID
    vehicle_id: UUID
    charger_id: UUID
    status: ChargingSessionStatus
    started_at: datetime | None
    ended_at: datetime | None
    requested_power_kw: float
    allocated_power_kw: float
    energy_consumed_kwh: float
    solar_energy_kwh: float
    grid_energy_kwh: float
    tariff_per_kwh: Decimal
    total_cost: Decimal

    @field_validator("started_at", "ended_at")
    @classmethod
    def normalize_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC) if value is not None else None


class ReadingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    timestamp: datetime


class EnergyReadingResponse(ReadingResponse):
    session_id: UUID
    requested_power_kw: float
    allocated_power_kw: float
    solar_power_kw: float
    grid_power_kw: float
    interval_energy_kwh: float
    solar_energy_kwh: float
    grid_energy_kwh: float


class SolarReadingResponse(ReadingResponse):
    station_id: UUID
    available_power_kw: float
