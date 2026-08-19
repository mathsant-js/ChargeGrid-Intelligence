import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, Float, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class ChargingSessionStatus(StrEnum):
    CREATED = "CREATED"
    CHARGING = "CHARGING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ChargingSession(TimestampMixin, Base):
    __tablename__ = "charging_sessions"
    __table_args__ = (
        CheckConstraint("requested_power_kw >= 0", name="ck_sessions_requested_power_nonnegative"),
        CheckConstraint("allocated_power_kw >= 0", name="ck_sessions_allocated_power_nonnegative"),
        CheckConstraint(
            "allocated_power_kw <= requested_power_kw", name="ck_sessions_allocation_within_request"
        ),
        CheckConstraint("energy_consumed_kwh >= 0", name="ck_sessions_energy_nonnegative"),
        CheckConstraint("solar_energy_kwh >= 0", name="ck_sessions_solar_energy_nonnegative"),
        CheckConstraint("grid_energy_kwh >= 0", name="ck_sessions_grid_energy_nonnegative"),
        CheckConstraint("tariff_per_kwh >= 0", name="ck_sessions_tariff_nonnegative"),
        CheckConstraint("total_cost >= 0", name="ck_sessions_total_cost_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    charger_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chargers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[ChargingSessionStatus] = mapped_column(
        Enum(ChargingSessionStatus, name="charging_session_status", native_enum=False),
        default=ChargingSessionStatus.CREATED,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    requested_power_kw: Mapped[float] = mapped_column(Float, nullable=False)
    allocated_power_kw: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    energy_consumed_kwh: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    solar_energy_kwh: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    grid_energy_kwh: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    tariff_per_kwh: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0"), nullable=False
    )

    readings: Mapped[list["EnergyReading"]] = relationship(back_populates="session")


class EnergyReading(Base):
    __tablename__ = "energy_readings"
    __table_args__ = (
        CheckConstraint("requested_power_kw >= 0", name="ck_energy_readings_requested_nonnegative"),
        CheckConstraint("allocated_power_kw >= 0", name="ck_energy_readings_allocated_nonnegative"),
        CheckConstraint(
            "allocated_power_kw <= requested_power_kw",
            name="ck_energy_readings_allocation_within_request",
        ),
        CheckConstraint("solar_power_kw >= 0", name="ck_energy_readings_solar_power_nonnegative"),
        CheckConstraint("grid_power_kw >= 0", name="ck_energy_readings_grid_power_nonnegative"),
        CheckConstraint("interval_energy_kwh >= 0", name="ck_energy_readings_energy_nonnegative"),
        CheckConstraint("solar_energy_kwh >= 0", name="ck_energy_readings_solar_nonnegative"),
        CheckConstraint("grid_energy_kwh >= 0", name="ck_energy_readings_grid_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("charging_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    requested_power_kw: Mapped[float] = mapped_column(Float, nullable=False)
    allocated_power_kw: Mapped[float] = mapped_column(Float, nullable=False)
    solar_power_kw: Mapped[float] = mapped_column(Float, nullable=False)
    grid_power_kw: Mapped[float] = mapped_column(Float, nullable=False)
    interval_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    solar_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    grid_energy_kwh: Mapped[float] = mapped_column(Float, nullable=False)

    session: Mapped[ChargingSession] = relationship(back_populates="readings")


class SolarReading(Base):
    __tablename__ = "solar_readings"
    __table_args__ = (
        CheckConstraint("available_power_kw >= 0", name="ck_solar_readings_power_nonnegative"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    station_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("charging_stations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    available_power_kw: Mapped[float] = mapped_column(Float, nullable=False)
