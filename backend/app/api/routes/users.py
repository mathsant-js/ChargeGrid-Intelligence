from uuid import UUID

from fastapi import APIRouter, HTTPException, status
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
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "", response_model=list[UserResponse], responses=UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE
)
async def list_users(db: DbSession, _: AdminUser) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at, User.id)).all())


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses=UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | CONFLICT_RESPONSE,
)
async def create_user(payload: UserCreate, db: DbSession, _: AdminUser) -> User:
    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password.get_secret_value()),
        role=payload.role,
        is_active=payload.is_active,
    )
    db.add(user)
    commit_or_conflict(db, "A user with this email already exists")
    db.refresh(user)
    return user


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    responses=UNAUTHORIZED_RESPONSE | NOT_FOUND_RESPONSE,
)
async def get_user(user_id: UUID, db: DbSession, current_user: CurrentUser) -> User:
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return get_or_404(db, User, user_id)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    responses=(
        UNAUTHORIZED_RESPONSE | FORBIDDEN_RESPONSE | NOT_FOUND_RESPONSE | CONFLICT_RESPONSE
    ),
)
async def update_user(
    payload: UserUpdate, user_id: UUID, db: DbSession, current_user: CurrentUser
) -> User:
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    if current_user.role != UserRole.ADMIN and "role" in payload.model_fields_set:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role cannot be changed")
    user = get_or_404(db, User, user_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"password"})
    for field, value in changes.items():
        setattr(user, field, value)
    if "password" in payload.model_fields_set and payload.password is not None:
        user.password_hash = hash_password(payload.password.get_secret_value())
    commit_or_conflict(db, "A user with this email already exists")
    db.refresh(user)
    return user
