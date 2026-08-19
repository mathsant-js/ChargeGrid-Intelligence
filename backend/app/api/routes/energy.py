from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import Select, select

from app.api.routes.common import DbSession
from app.models.energy import ChargingSession, EnergyReading
from app.models.infrastructure import Charger
from app.schemas.energy import EnergyReadingResponse

router = APIRouter(prefix="/energy", tags=["energy"])
DateFrom = Annotated[datetime | None, Query(alias="from")]
DateTo = Annotated[datetime | None, Query(alias="to")]


def _filtered_readings(
    station_id: UUID | None, date_from: datetime | None, date_to: datetime | None
) -> Select[tuple[EnergyReading]]:
    query = select(EnergyReading)
    if station_id is not None:
        query = query.join(ChargingSession).join(Charger).where(Charger.station_id == station_id)
    if date_from is not None:
        query = query.where(EnergyReading.timestamp >= date_from)
    if date_to is not None:
        query = query.where(EnergyReading.timestamp <= date_to)
    return query


@router.get("/current", response_model=EnergyReadingResponse | None)
async def current_energy(db: DbSession, station_id: UUID | None = None) -> EnergyReading | None:
    query = _filtered_readings(station_id, None, None).order_by(
        EnergyReading.timestamp.desc(), EnergyReading.id.desc()
    )
    return db.scalar(query.limit(1))


@router.get("/history", response_model=list[EnergyReadingResponse])
async def energy_history(
    db: DbSession,
    date_from: DateFrom = None,
    date_to: DateTo = None,
    station_id: UUID | None = None,
) -> list[EnergyReading]:
    query = _filtered_readings(station_id, date_from, date_to).order_by(
        EnergyReading.timestamp, EnergyReading.id
    )
    return list(db.scalars(query).all())
