from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.dependencies import AdminUser, CurrentUser
from app.api.routes.common import (
    CONFLICT_RESPONSE,
    FORBIDDEN_RESPONSE,
    NOT_FOUND_RESPONSE,
    UNAUTHORIZED_RESPONSE,
    DbSession,
    commit_or_conflict,
    get_or_404,
)
from app.models.infrastructure import Charger, ChargingStation
from app.schemas.charger import ChargerCreate, ChargerResponse, ChargerUpdate

router = APIRouter(prefix="/chargers", tags=["chargers"])


@router.get("", response_model=list[ChargerResponse], responses=UNAUTHORIZED_RESPONSE)
async def list_chargers(db: DbSession, _: CurrentUser) -> list[Charger]:
    return list(db.scalars(select(Charger).order_by(Charger.created_at, Charger.id)).all())


@router.post(
    "",
    response_model=ChargerResponse,
    status_code=status.HTTP_201_CREATED,
    responses=(
        UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | NOT_FOUND_RESPONSE | CONFLICT_RESPONSE
    ),
)
async def create_charger(payload: ChargerCreate, db: DbSession, _: AdminUser) -> Charger:
    get_or_404(db, ChargingStation, payload.station_id)
    charger = Charger(**payload.model_dump())
    db.add(charger)
    commit_or_conflict(db)
    db.refresh(charger)
    return charger


@router.get(
    "/{charger_id}",
    response_model=ChargerResponse,
    responses=UNAUTHORIZED_RESPONSE | NOT_FOUND_RESPONSE,
)
async def get_charger(charger_id: UUID, db: DbSession, _: CurrentUser) -> Charger:
    return get_or_404(db, Charger, charger_id)


@router.patch(
    "/{charger_id}",
    response_model=ChargerResponse,
    responses=(
        UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | NOT_FOUND_RESPONSE | CONFLICT_RESPONSE
    ),
)
async def update_charger(
    payload: ChargerUpdate, charger_id: UUID, db: DbSession, _: AdminUser
) -> Charger:
    charger = get_or_404(db, Charger, charger_id)
    changes = payload.model_dump(exclude_unset=True)
    if "station_id" in changes:
        get_or_404(db, ChargingStation, changes["station_id"])
    for field, value in changes.items():
        setattr(charger, field, value)
    commit_or_conflict(db)
    db.refresh(charger)
    return charger
