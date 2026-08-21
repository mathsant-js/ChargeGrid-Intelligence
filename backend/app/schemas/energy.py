from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.energy import ChargingSessionStatus
from app.schemas.common import ORMResponse

NonNegativePower = Annotated[float, Field(ge=0, allow_inf_nan=False)]
NonNegativeMoney = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=4)]


class ChargingSessionStart(BaseModel):
    vehicle_id: UUID
    charger_id: UUID
    tariff_per_kwh: NonNegativeMoney


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
