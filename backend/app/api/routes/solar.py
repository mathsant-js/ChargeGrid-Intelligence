from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import Select, select

from app.api.routes.common import DbSession
from app.models.energy import SolarReading
from app.schemas.energy import SolarReadingResponse

router = APIRouter(prefix="/solar", tags=["solar"])
DateFrom = Annotated[datetime | None, Query(alias="from")]
DateTo = Annotated[datetime | None, Query(alias="to")]


def _filtered_readings(
    station_id: UUID | None, date_from: datetime | None, date_to: datetime | None
) -> Select[tuple[SolarReading]]:
    query = select(SolarReading)
    if station_id is not None:
        query = query.where(SolarReading.station_id == station_id)
    if date_from is not None:
        query = query.where(SolarReading.timestamp >= date_from)
    if date_to is not None:
        query = query.where(SolarReading.timestamp <= date_to)
    return query


@router.get("/current", response_model=SolarReadingResponse | None)
async def current_solar(db: DbSession, station_id: UUID | None = None) -> SolarReading | None:
    query = _filtered_readings(station_id, None, None).order_by(
        SolarReading.timestamp.desc(), SolarReading.id.desc()
    )
    return db.scalar(query.limit(1))


@router.get("/history", response_model=list[SolarReadingResponse])
async def solar_history(
    db: DbSession,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    station_id: UUID | None = None,
) -> list[SolarReading]:
    query = _filtered_readings(station_id, date_from, date_to).order_by(
        SolarReading.timestamp, SolarReading.id
    )
    return list(db.scalars(query).all())
