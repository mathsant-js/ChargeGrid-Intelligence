from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.billing import Invoice, InvoiceStatus
from app.models.energy import ChargingSession, ChargingSessionStatus, EnergyReading
from app.models.infrastructure import Charger
from app.schemas.analytics import DashboardResponse, SustainabilityResponse


@dataclass(frozen=True)
class AnalyticsFilters:
    station_id: UUID | None = None
    user_id: UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


def _sessions(db: Session, filters: AnalyticsFilters) -> list[ChargingSession]:
    statement = select(ChargingSession).join(Charger)
    if filters.station_id is not None:
        statement = statement.where(Charger.station_id == filters.station_id)
    if filters.user_id is not None:
        statement = statement.where(ChargingSession.user_id == filters.user_id)
    return list(db.scalars(statement).all())


def _in_period(value: datetime | None, filters: AnalyticsFilters) -> bool:
    if value is None:
        return False
    # SQLite test fixtures can return naive UTC timestamps.
    if value.tzinfo is None:
        from datetime import UTC

        value = value.replace(tzinfo=UTC)
    return (filters.date_from is None or value >= filters.date_from) and (
        filters.date_to is None or value <= filters.date_to
    )


def _readings(
    db: Session, session_ids: list[UUID], filters: AnalyticsFilters
) -> list[EnergyReading]:
    if not session_ids:
        return []
    statement = select(EnergyReading).where(EnergyReading.session_id.in_(session_ids))
    if filters.date_from is not None:
        statement = statement.where(EnergyReading.timestamp >= filters.date_from)
    if filters.date_to is not None:
        statement = statement.where(EnergyReading.timestamp <= filters.date_to)
    return list(db.scalars(statement).all())


def dashboard(db: Session, filters: AnalyticsFilters) -> DashboardResponse:
    sessions = _sessions(db, filters)
    ids = [item.id for item in sessions]
    readings = _readings(db, ids, filters)
    invoices = []
    if ids:
        invoices = list(
            db.scalars(
                select(Invoice).where(
                    Invoice.session_id.in_(ids), Invoice.status == InvoiceStatus.CLOSED
                )
            ).all()
        )
    return DashboardResponse(
        station_id=filters.station_id,
        user_id=filters.user_id,
        session_count=sum(
            item.started_at is not None and _in_period(item.started_at, filters)
            for item in sessions
        ),
        completed_session_count=sum(
            item.status == ChargingSessionStatus.COMPLETED and _in_period(item.ended_at, filters)
            for item in sessions
        ),
        energy_consumed_kwh=sum(item.interval_energy_kwh for item in readings),
        solar_energy_kwh=sum(item.solar_energy_kwh for item in readings),
        grid_energy_kwh=sum(item.grid_energy_kwh for item in readings),
        billed_total=sum(
            (item.total for item in invoices if _in_period(item.closed_at, filters)),
            Decimal("0.00"),
        ),
    )


def sustainability(
    db: Session, filters: AnalyticsFilters, emission_factor: float
) -> SustainabilityResponse:
    sessions = _sessions(db, filters)
    by_id = {item.id: item for item in sessions}
    readings = _readings(db, list(by_id), filters)
    consumed = sum(item.interval_energy_kwh for item in readings)
    solar = sum(item.solar_energy_kwh for item in readings)
    grid = sum(item.grid_energy_kwh for item in readings)
    savings = sum(
        (
            Decimal(str(item.solar_energy_kwh)) * by_id[item.session_id].tariff_per_kwh
            for item in readings
        ),
        Decimal("0"),
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return SustainabilityResponse(
        station_id=filters.station_id,
        user_id=filters.user_id,
        energy_consumed_kwh=consumed,
        solar_energy_kwh=solar,
        grid_energy_kwh=grid,
        solar_percentage=solar / consumed * 100 if consumed else 0,
        avoided_co2_kg=solar * emission_factor,
        grid_emission_factor_kg_per_kwh=emission_factor,
        estimated_solar_savings=savings,
    )
