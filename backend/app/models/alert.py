import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AlertType(StrEnum):
    HIGH_DEMAND = "HIGH_DEMAND"
    PEAK_RISK = "PEAK_RISK"
    HIGH_SOLAR_AVAILABILITY = "HIGH_SOLAR_AVAILABILITY"
    SESSION_FINISHED = "SESSION_FINISHED"


class AlertSeverity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    station_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("charging_stations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, name="alert_type", native_enum=False), nullable=False, index=True
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity", native_enum=False), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
