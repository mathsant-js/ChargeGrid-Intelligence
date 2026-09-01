import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.dependencies import CurrentUser, RegularUser
from app.api.routes.common import (
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    DbSession,
    commit_or_conflict,
    get_or_404,
)
from app.models.energy import ChargingSession
from app.models.infrastructure import Charger
from app.models.user import UserRole
from app.models.vehicle import Vehicle
from app.schemas.energy import ChargingSessionResponse, ChargingSessionStart
from app.services.charging_sessions import (
    ensure_session_access,
    start_charging_session,
    stop_charging_session,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[ChargingSessionResponse], responses=UNAUTHORIZED_RESPONSE)
async def list_sessions(db: DbSession, current_user: CurrentUser) -> list[ChargingSession]:
    statement = select(ChargingSession)
    if current_user.role != UserRole.ADMIN:
        statement = statement.where(ChargingSession.user_id == current_user.id)
    return list(
        db.scalars(statement.order_by(ChargingSession.created_at, ChargingSession.id))
    )


@router.get(
    "/{session_id}",
    response_model=ChargingSessionResponse,
    responses=UNAUTHORIZED_RESPONSE | NOT_FOUND_RESPONSE,
)
async def get_session(
    session_id: UUID, db: DbSession, current_user: CurrentUser
) -> ChargingSession:
    session = get_or_404(db, ChargingSession, session_id)
    if current_user.role != UserRole.ADMIN:
        ensure_session_access(session, current_user)
    return session


@router.post(
    "/start",
    response_model=ChargingSessionResponse,
    status_code=status.HTTP_201_CREATED,
    responses=(
        UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | NOT_FOUND_RESPONSE | CONFLICT_RESPONSE
    ),
)
async def start_session(
    payload: ChargingSessionStart, db: DbSession, current_user: RegularUser
) -> ChargingSession:
    vehicle = get_or_404(db, Vehicle, payload.vehicle_id)
    if vehicle.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    session = start_charging_session(
        db,
        user=current_user,
        vehicle=vehicle,
        charger=get_or_404(db, Charger, payload.charger_id),
    )
    commit_or_conflict(db, "Charging session could not be started")
    db.refresh(session)
    logger.info(
        "charging_session_started",
        extra={
            "charging_session_id": str(session.id),
            "user_id": str(session.user_id),
            "vehicle_id": str(session.vehicle_id),
            "charger_id": str(session.charger_id),
        },
    )
    return session


@router.post(
    "/{session_id}/stop",
    response_model=ChargingSessionResponse,
    responses=(
        UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | NOT_FOUND_RESPONSE | CONFLICT_RESPONSE
    ),
)
async def stop_session(
    session_id: UUID, db: DbSession, current_user: RegularUser
) -> ChargingSession:
    session = get_or_404(db, ChargingSession, session_id)
    ensure_session_access(session, current_user)
    charger = get_or_404(db, Charger, session.charger_id)
    stop_charging_session(db, session, charger)
    commit_or_conflict(db, "Charging session could not be stopped")
    db.refresh(session)
    logger.info(
        "charging_session_finished",
        extra={
            "charging_session_id": str(session.id),
            "user_id": str(session.user_id),
            "vehicle_id": str(session.vehicle_id),
            "charger_id": str(session.charger_id),
        },
    )
    return session
