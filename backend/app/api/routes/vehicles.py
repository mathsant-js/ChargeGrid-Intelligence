from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
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
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=list[VehicleResponse], responses=UNAUTHORIZED_RESPONSE)
async def list_vehicles(db: DbSession, current_user: CurrentUser) -> list[Vehicle]:
    statement = select(Vehicle)
    if current_user.role != UserRole.ADMIN:
        statement = statement.where(Vehicle.user_id == current_user.id)
    return list(db.scalars(statement.order_by(Vehicle.created_at, Vehicle.id)).all())


@router.post(
    "",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    responses=UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | CONFLICT_RESPONSE,
)
async def create_vehicle(
    payload: VehicleCreate, db: DbSession, current_user: RegularUser
) -> Vehicle:
    vehicle = Vehicle(**payload.model_dump(exclude={"user_id"}), user_id=current_user.id)
    db.add(vehicle)
    commit_or_conflict(db)
    db.refresh(vehicle)
    return vehicle


@router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    responses=UNAUTHORIZED_RESPONSE | NOT_FOUND_RESPONSE,
)
async def get_vehicle(vehicle_id: UUID, db: DbSession, current_user: CurrentUser) -> Vehicle:
    vehicle = get_or_404(db, Vehicle, vehicle_id)
    ensure_vehicle_access(vehicle, current_user)
    return vehicle


@router.patch(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    responses=(
        UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | NOT_FOUND_RESPONSE | CONFLICT_RESPONSE
    ),
)
async def update_vehicle(
    payload: VehicleUpdate, vehicle_id: UUID, db: DbSession, current_user: RegularUser
) -> Vehicle:
    vehicle = get_or_404(db, Vehicle, vehicle_id)
    ensure_vehicle_access(vehicle, current_user)
    changes = payload.model_dump(exclude_unset=True)
    if "user_id" in changes:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner cannot be changed")
    for field, value in changes.items():
        setattr(vehicle, field, value)
    commit_or_conflict(db)
    db.refresh(vehicle)
    return vehicle


@router.delete(
    "/{vehicle_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=(
        UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | NOT_FOUND_RESPONSE | CONFLICT_RESPONSE
    ),
)
async def delete_vehicle(vehicle_id: UUID, db: DbSession, current_user: RegularUser) -> Response:
    vehicle = get_or_404(db, Vehicle, vehicle_id)
    ensure_vehicle_access(vehicle, current_user)
    db.delete(vehicle)
    commit_or_conflict(db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def ensure_vehicle_access(vehicle: Vehicle, current_user: User) -> None:
    if current_user.role != UserRole.ADMIN and vehicle.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
