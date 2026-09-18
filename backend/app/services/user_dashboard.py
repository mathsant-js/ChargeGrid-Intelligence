from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.billing import Invoice, InvoiceStatus
from app.models.energy import ChargingSession, ChargingSessionStatus
from app.models.infrastructure import Charger
from app.models.vehicle import Vehicle
from app.schemas.billing import InvoiceResponse
from app.schemas.user_dashboard import UserDashboardResponse, UserSessionSummary
from app.services.billing import calculate_pay_per_use_total

ACTIVE = {
    ChargingSessionStatus.CREATED,
    ChargingSessionStatus.CHARGING,
    ChargingSessionStatus.PAUSED,
}


def get_user_dashboard(
    db: Session, user_id: UUID, now: datetime | None = None
) -> UserDashboardResponse:
    now = now or datetime.now(UTC)
    sessions = db.execute(
        select(ChargingSession, Vehicle.name, Charger.name)
        .join(Vehicle, ChargingSession.vehicle_id == Vehicle.id)
        .join(Charger, ChargingSession.charger_id == Charger.id)
        .where(ChargingSession.user_id == user_id, Vehicle.user_id == user_id)
        .order_by(ChargingSession.created_at.desc(), ChargingSession.id.desc())
    ).all()
    invoices = list(
        db.scalars(
            select(Invoice)
            .where(Invoice.user_id == user_id)
            .order_by(Invoice.created_at.desc(), Invoice.id.desc())
        ).all()
    )
    closed = {
        invoice.session_id: invoice
        for invoice in invoices
        if invoice.status == InvoiceStatus.CLOSED
    }

    def summarize(
        session: ChargingSession, vehicle_name: str, charger_name: str
    ) -> UserSessionSummary:
        start = session.started_at
        end = session.ended_at or now
        if start is not None and start.tzinfo is None:
            start = start.replace(tzinfo=UTC)
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        invoice = closed.get(session.id)
        return UserSessionSummary(
            id=session.id,
            status=session.status,
            vehicle_name=vehicle_name,
            charger_name=charger_name,
            started_at=start,
            ended_at=session.ended_at,
            duration_seconds=max(0, int((end - start).total_seconds())) if start else 0,
            allocated_power_kw=session.allocated_power_kw,
            energy_consumed_kwh=session.energy_consumed_kwh,
            solar_percentage=(
                100 * session.solar_energy_kwh / session.energy_consumed_kwh
                if session.energy_consumed_kwh > 0
                else 0
            ),
            estimated_cost=(
                calculate_pay_per_use_total(session.energy_consumed_kwh, session.tariff_per_kwh)
                if session.status in ACTIVE
                else None
            ),
            invoice_total=invoice.total if invoice else None,
        )

    summaries = [summarize(session, vehicle, charger) for session, vehicle, charger in sessions]
    current = next((item for item in summaries if item.status in ACTIVE), None)
    history = [item for item in summaries if item.status not in ACTIVE]
    return UserDashboardResponse(
        current_session=current,
        session_history=history,
        invoices=[InvoiceResponse.model_validate(invoice) for invoice in invoices],
    )
