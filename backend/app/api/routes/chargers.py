from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.routes.common import DbSession, commit_or_conflict, get_or_404
from app.models.infrastructure import Charger, ChargingStation
from app.schemas.charger import ChargerCreate, ChargerResponse, ChargerUpdate

router = APIRouter(prefix="/chargers", tags=["chargers"])


@router.get("", response_model=list[ChargerResponse])
async def list_chargers(db: DbSession) -> list[Charger]:
    return list(db.scalars(select(Charger).order_by(Charger.created_at, Charger.id)).all())


@router.post("", response_model=ChargerResponse, status_code=status.HTTP_201_CREATED)
async def create_charger(payload: ChargerCreate, db: DbSession) -> Charger:
    get_or_404(db, ChargingStation, payload.station_id)
    charger = Charger(**payload.model_dump())
    db.add(charger)
    commit_or_conflict(db, "Charger could not be created")
    db.refresh(charger)
    return charger


@router.get("/{charger_id}", response_model=ChargerResponse)
async def get_charger(charger_id: UUID, db: DbSession) -> Charger:
    return get_or_404(db, Charger, charger_id)


@router.patch("/{charger_id}", response_model=ChargerResponse)
async def update_charger(payload: ChargerUpdate, charger_id: UUID, db: DbSession) -> Charger:
    charger = get_or_404(db, Charger, charger_id)
    changes = payload.model_dump(exclude_unset=True)
    if "station_id" in changes:
        get_or_404(db, ChargingStation, changes["station_id"])
    for field, value in changes.items():
        setattr(charger, field, value)
    commit_or_conflict(db, "Charger could not be updated")
    db.refresh(charger)
    return charger
