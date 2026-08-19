from uuid import UUID

from fastapi import APIRouter, Response, status
from sqlalchemy import select

from app.api.routes.common import DbSession, commit_or_conflict, get_or_404
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleResponse])
async def list_vehicles(db: DbSession) -> list[Vehicle]:
    return list(db.scalars(select(Vehicle).order_by(Vehicle.created_at, Vehicle.id)).all())


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(payload: VehicleCreate, db: DbSession) -> Vehicle:
    get_or_404(db, User, payload.user_id)
    vehicle = Vehicle(**payload.model_dump())
    db.add(vehicle)
    commit_or_conflict(db, "Vehicle could not be created")
    db.refresh(vehicle)
    return vehicle


@router.get("/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(vehicle_id: UUID, db: DbSession) -> Vehicle:
    return get_or_404(db, Vehicle, vehicle_id)


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(payload: VehicleUpdate, vehicle_id: UUID, db: DbSession) -> Vehicle:
    vehicle = get_or_404(db, Vehicle, vehicle_id)
    changes = payload.model_dump(exclude_unset=True)
    if "user_id" in changes:
        get_or_404(db, User, changes["user_id"])
    for field, value in changes.items():
        setattr(vehicle, field, value)
    commit_or_conflict(db, "Vehicle could not be updated")
    db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(vehicle_id: UUID, db: DbSession) -> Response:
    vehicle = get_or_404(db, Vehicle, vehicle_id)
    db.delete(vehicle)
    commit_or_conflict(db, "Vehicle cannot be deleted")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
