from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class DashboardResponse(BaseModel):
    station_id: UUID | None
    user_id: UUID | None
    session_count: int
    completed_session_count: int
    energy_consumed_kwh: float
    solar_energy_kwh: float
    grid_energy_kwh: float
    billed_total: Decimal
    currency: str = "BRL"


class SustainabilityResponse(BaseModel):
    station_id: UUID | None
    user_id: UUID | None
    energy_consumed_kwh: float
    solar_energy_kwh: float
    grid_energy_kwh: float
    solar_percentage: float
    avoided_co2_kg: float
    grid_emission_factor_kg_per_kwh: float
    estimated_solar_savings: Decimal
    currency: str = "BRL"
