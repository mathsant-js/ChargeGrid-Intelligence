from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertSeverity, AlertType
from app.models.billing import Invoice, InvoiceStatus, Tariff
from app.models.energy import ChargingSession, ChargingSessionStatus
from app.models.infrastructure import Charger, ChargerStatus
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.errors import DomainConflictError, DomainResourceNotFoundError

ACTIVE_SESSION_STATUSES = (
    ChargingSessionStatus.CREATED,
    ChargingSessionStatus.CHARGING,
    ChargingSessionStatus.PAUSED,
)

VALID_SESSION_TRANSITIONS = {
    ChargingSessionStatus.CREATED: {
        ChargingSessionStatus.CHARGING,
        ChargingSessionStatus.CANCELLED,
    },
    ChargingSessionStatus.CHARGING: {
        ChargingSessionStatus.PAUSED,
        ChargingSessionStatus.COMPLETED,
        ChargingSessionStatus.CANCELLED,
    },
    ChargingSessionStatus.PAUSED: {
        ChargingSessionStatus.CHARGING,
        ChargingSessionStatus.COMPLETED,
        ChargingSessionStatus.CANCELLED,
    },
    ChargingSessionStatus.COMPLETED: set(),
    ChargingSessionStatus.CANCELLED: set(),
}


def ensure_session_access(session: ChargingSession, user: User) -> None:
    if session.user_id != user.id:
        raise DomainResourceNotFoundError("Resource not found")


def transition_session(
    session: ChargingSession, target_status: ChargingSessionStatus
) -> None:
    if target_status not in VALID_SESSION_TRANSITIONS[session.status]:
        raise DomainConflictError(
            f"Session cannot transition from {session.status} to {target_status}"
        )
    session.status = target_status


def start_charging_session(
    db: Session,
    *,
    user: User,
    vehicle: Vehicle,
    charger: Charger,
) -> ChargingSession:
    if not user.is_active:
        raise DomainConflictError("User is inactive")
    if vehicle.user_id != user.id:
        raise DomainConflictError("Vehicle does not belong to user")
    if not charger.is_active:
        raise DomainConflictError("Charger is unavailable")

    charger_session = db.scalar(
        select(ChargingSession.id).where(
            ChargingSession.status.in_(ACTIVE_SESSION_STATUSES),
            ChargingSession.charger_id == charger.id,
        )
    )
    if charger_session is not None:
        raise DomainConflictError("Charger already has an active session")
    if charger.status != ChargerStatus.AVAILABLE:
        raise DomainConflictError("Charger is unavailable")
    vehicle_session = db.scalar(
        select(ChargingSession.id).where(
            ChargingSession.status.in_(ACTIVE_SESSION_STATUSES),
            ChargingSession.vehicle_id == vehicle.id,
        )
    )
    if vehicle_session is not None:
        raise DomainConflictError("Vehicle already has an active session")

    started_at = datetime.now(UTC)
    tariff = db.scalar(
        select(Tariff)
        .where(
            Tariff.is_active.is_(True),
            Tariff.valid_from <= started_at,
            or_(Tariff.valid_until.is_(None), Tariff.valid_until > started_at),
        )
    )
    if tariff is None:
        raise DomainConflictError("No active tariff is valid for the session start time")

    requested_power_kw = min(charger.max_power_kw, vehicle.max_charge_power_kw)
    session = ChargingSession(
        user_id=user.id,
        vehicle_id=vehicle.id,
        charger_id=charger.id,
        status=ChargingSessionStatus.CHARGING,
        started_at=started_at,
        requested_power_kw=requested_power_kw,
        allocated_power_kw=0,
        energy_consumed_kwh=0,
        solar_energy_kwh=0,
        grid_energy_kwh=0,
        tariff_per_kwh=tariff.price_per_kwh,
        total_cost=Decimal("0"),
    )
    charger.status = ChargerStatus.CHARGING
    db.add(session)
    return session


def stop_charging_session(db: Session, session: ChargingSession, charger: Charger) -> None:
    transition_session(session, ChargingSessionStatus.COMPLETED)
    closed_at = datetime.now(UTC)
    session.ended_at = closed_at
    session.allocated_power_kw = 0
    subtotal = (Decimal(str(session.energy_consumed_kwh)) * session.tariff_per_kwh).quantize(
        Decimal("0.01")
    )
    session.total_cost = subtotal
    charger.status = ChargerStatus.AVAILABLE
    db.add(
        Invoice(
            session_id=session.id,
            user_id=session.user_id,
            energy_kwh=Decimal(str(session.energy_consumed_kwh)),
            tariff_per_kwh=session.tariff_per_kwh,
            subtotal=subtotal,
            total=subtotal,
            status=InvoiceStatus.CLOSED,
            closed_at=closed_at,
        )
    )
    db.add(
        Alert(
            station_id=charger.station_id,
            type=AlertType.SESSION_FINISHED,
            severity=AlertSeverity.INFO,
            title="Charging session finished",
            message=f"Charging session {session.id} finished successfully.",
        )
    )
