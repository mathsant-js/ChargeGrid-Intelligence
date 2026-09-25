from datetime import datetime
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import Select, select

from app.api.dependencies import CurrentUser
from app.api.routes.common import UNAUTHORIZED_RESPONSE, DbSession
from app.models.energy import ChargingSession, EnergyReading
from app.models.infrastructure import Charger
from app.models.user import UserRole
from app.schemas.energy import EnergyReadingResponse

router = APIRouter(prefix="/energy", tags=["energy"])
DateFrom = Annotated[datetime | None, Query(alias="from")]
DateTo = Annotated[datetime | None, Query(alias="to")]


def _filtered_readings(
    station_id: UUID | None,
    date_from: datetime | None,
    date_to: datetime | None,
    user_id: UUID | None = None,
) -> Select[Any]:
    query = select(EnergyReading)
    if station_id is not None or user_id is not None:
        query = query.join(ChargingSession)
    if station_id is not None:
        query = query.join(Charger).where(Charger.station_id == station_id)
    if user_id is not None:
        query = query.where(ChargingSession.user_id == user_id)
    if date_from is not None:
        query = query.where(EnergyReading.timestamp >= date_from)
    if date_to is not None:
        query = query.where(EnergyReading.timestamp <= date_to)
    return query


@router.get(
    "/current", response_model=EnergyReadingResponse | None, responses=UNAUTHORIZED_RESPONSE
)
async def current_energy(
    db: DbSession, current_user: CurrentUser, station_id: UUID | None = None
) -> EnergyReading | None:
    user_id = current_user.id if current_user.role != UserRole.ADMIN else None
    query = _filtered_readings(station_id, None, None, user_id).order_by(
        EnergyReading.timestamp.desc(), EnergyReading.id.desc()
    )
    return cast(EnergyReading | None, db.scalar(query.limit(1)))


@router.get(
    "/history", response_model=list[EnergyReadingResponse], responses=UNAUTHORIZED_RESPONSE
)
async def energy_history(
    db: DbSession,
    current_user: CurrentUser,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    station_id: UUID | None = None,
) -> list[EnergyReading]:
    user_id = current_user.id if current_user.role != UserRole.ADMIN else None
    query = _filtered_readings(station_id, date_from, date_to, user_id).order_by(
        EnergyReading.timestamp, EnergyReading.id
    )
    return list(db.scalars(query).all())
