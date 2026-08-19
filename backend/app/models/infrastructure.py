import uuid
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ChargerStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    CHARGING = "CHARGING"
    UNAVAILABLE = "UNAVAILABLE"


class ChargingStation(TimestampMixin, Base):
    __tablename__ = "charging_stations"
    __table_args__ = (CheckConstraint("grid_limit_kw > 0", name="ck_stations_grid_limit_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    grid_limit_kw: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    chargers: Mapped[list["Charger"]] = relationship(back_populates="station")


class Charger(TimestampMixin, Base):
    __tablename__ = "chargers"
    __table_args__ = (CheckConstraint("max_power_kw > 0", name="ck_chargers_max_power_positive"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    station_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("charging_stations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False)
    max_power_kw: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[ChargerStatus] = mapped_column(
        Enum(ChargerStatus, name="charger_status", native_enum=False),
        default=ChargerStatus.AVAILABLE,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    station: Mapped[ChargingStation] = relationship(back_populates="chargers")
