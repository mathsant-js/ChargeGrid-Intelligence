from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select

from app.api.dependencies import AdminUser, CurrentUser
from app.api.routes.common import DbSession, commit_or_conflict, get_or_404
from app.models.infrastructure import ChargingStation
from app.schemas.station import StationCreate, StationResponse, StationUpdate

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=list[StationResponse])
async def list_stations(db: DbSession, _: CurrentUser) -> list[ChargingStation]:
    statement = select(ChargingStation).order_by(ChargingStation.created_at, ChargingStation.id)
    return list(db.scalars(statement).all())


@router.post("", response_model=StationResponse, status_code=status.HTTP_201_CREATED)
async def create_station(payload: StationCreate, db: DbSession, _: AdminUser) -> ChargingStation:
    station = ChargingStation(**payload.model_dump())
    db.add(station)
    commit_or_conflict(db, "Station could not be created")
    db.refresh(station)
    return station


@router.get("/{station_id}", response_model=StationResponse)
async def get_station(station_id: UUID, db: DbSession, _: CurrentUser) -> ChargingStation:
    return get_or_404(db, ChargingStation, station_id)


@router.patch("/{station_id}", response_model=StationResponse)
async def update_station(
    payload: StationUpdate, station_id: UUID, db: DbSession, _: AdminUser
) -> ChargingStation:
    station = get_or_404(db, ChargingStation, station_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(station, field, value)
    commit_or_conflict(db, "Station could not be updated")
    db.refresh(station)
    return station
