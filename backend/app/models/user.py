import uuid
from enum import StrEnum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    USER = "USER"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="user")


from app.models.vehicle import Vehicle  # noqa: E402
