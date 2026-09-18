from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.models.energy import ChargingSessionStatus
from app.schemas.billing import InvoiceResponse


class UserSessionSummary(BaseModel):
    id: UUID
    status: ChargingSessionStatus
    vehicle_name: str
    charger_name: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int
    allocated_power_kw: float
    energy_consumed_kwh: float
    solar_percentage: float
    estimated_cost: Decimal | None
    invoice_total: Decimal | None


class UserDashboardResponse(BaseModel):
    current_session: UserSessionSummary | None
    session_history: list[UserSessionSummary]
    invoices: list[InvoiceResponse]
