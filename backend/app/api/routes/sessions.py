from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.routes.common import DbSession, commit_or_conflict, get_or_404
from app.models.energy import ChargingSession
from app.models.infrastructure import Charger
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.energy import ChargingSessionResponse, ChargingSessionStart
from app.services.charging_sessions import start_charging_session, stop_charging_session

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[ChargingSessionResponse])
async def list_sessions(db: DbSession) -> list[ChargingSession]:
    return list(
        db.scalars(select(ChargingSession).order_by(ChargingSession.created_at, ChargingSession.id))
    )


@router.get("/{session_id}", response_model=ChargingSessionResponse)
async def get_session(session_id: UUID, db: DbSession) -> ChargingSession:
    return get_or_404(db, ChargingSession, session_id)


@router.post("/start", response_model=ChargingSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(payload: ChargingSessionStart, db: DbSession) -> ChargingSession:
    session = start_charging_session(
        db,
        user=get_or_404(db, User, payload.user_id),
        vehicle=get_or_404(db, Vehicle, payload.vehicle_id),
        charger=get_or_404(db, Charger, payload.charger_id),
        tariff_per_kwh=payload.tariff_per_kwh,
    )
    commit_or_conflict(db, "Charging session could not be started")
    db.refresh(session)
    return session


@router.post("/{session_id}/stop", response_model=ChargingSessionResponse)
async def stop_session(session_id: UUID, db: DbSession) -> ChargingSession:
    session = get_or_404(db, ChargingSession, session_id)
    charger = get_or_404(db, Charger, session.charger_id)
    stop_charging_session(db, session, charger)
    commit_or_conflict(db, "Charging session could not be stopped")
    db.refresh(session)
    return session
