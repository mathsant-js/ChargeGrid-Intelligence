from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.energy import ChargingSession, ChargingSessionStatus
from app.models.infrastructure import Charger, ChargerStatus
from app.models.user import User
from app.models.vehicle import Vehicle

ACTIVE_SESSION_STATUSES = (
    ChargingSessionStatus.CREATED,
    ChargingSessionStatus.CHARGING,
    ChargingSessionStatus.PAUSED,
)


def start_charging_session(
    db: Session,
    *,
    user: User,
    vehicle: Vehicle,
    charger: Charger,
    tariff_per_kwh: Decimal,
) -> ChargingSession:
    if not user.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is inactive")
    if vehicle.user_id != user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Vehicle does not belong to user")
    if not charger.is_active or charger.status != ChargerStatus.AVAILABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Charger is unavailable")

    existing = db.scalar(
        select(ChargingSession.id).where(
            ChargingSession.status.in_(ACTIVE_SESSION_STATUSES),
            or_(
                ChargingSession.charger_id == charger.id,
                ChargingSession.vehicle_id == vehicle.id,
            ),
        )
    )
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Charger or vehicle already has an active session"
        )

    requested_power_kw = min(charger.max_power_kw, vehicle.max_charge_power_kw)
    session = ChargingSession(
        user_id=user.id,
        vehicle_id=vehicle.id,
        charger_id=charger.id,
        status=ChargingSessionStatus.CHARGING,
        started_at=datetime.now(UTC),
        requested_power_kw=requested_power_kw,
        allocated_power_kw=0,
        energy_consumed_kwh=0,
        solar_energy_kwh=0,
        grid_energy_kwh=0,
        tariff_per_kwh=tariff_per_kwh,
        total_cost=Decimal("0"),
    )
    charger.status = ChargerStatus.CHARGING
    db.add(session)
    return session


def stop_charging_session(session: ChargingSession, charger: Charger) -> None:
    if session.status not in (ChargingSessionStatus.CHARGING, ChargingSessionStatus.PAUSED):
        raise HTTPException(status.HTTP_409_CONFLICT, "Session cannot be stopped")
    session.status = ChargingSessionStatus.COMPLETED
    session.ended_at = datetime.now(UTC)
    session.allocated_power_kw = 0
    session.total_cost = Decimal(str(session.energy_consumed_kwh)) * session.tariff_per_kwh
    charger.status = ChargerStatus.AVAILABLE
