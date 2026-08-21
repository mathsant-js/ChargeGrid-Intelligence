import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import TimestampMixin


class DemandRiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DemandPrediction(Base):
    __tablename__ = "demand_predictions"
    __table_args__ = (
        CheckConstraint("predicted_demand_kw >= 0", name="ck_predictions_demand_nonnegative"),
        CheckConstraint("capacity_kw > 0", name="ck_predictions_capacity_positive"),
        CheckConstraint("prediction_for > generated_at", name="ck_predictions_future_target"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    station_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("charging_stations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    prediction_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    predicted_demand_kw: Mapped[float] = mapped_column(Float, nullable=False)
    capacity_kw: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[DemandRiskLevel] = mapped_column(
        Enum(DemandRiskLevel, name="demand_risk_level", native_enum=False), nullable=False
    )
    model_version: Mapped[str] = mapped_column(String(120), nullable=False)

    @property
    def prediction_horizon_minutes(self) -> int:
        generated_at = self.generated_at
        prediction_for = self.prediction_for
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=UTC)
        if prediction_for.tzinfo is None:
            prediction_for = prediction_for.replace(tzinfo=UTC)
        return round((prediction_for - generated_at).total_seconds() / 60)


class SystemConfiguration(TimestampMixin, Base):
    __tablename__ = "system_configurations"
    __table_args__ = (
        CheckConstraint("simulation_speed > 0", name="ck_config_simulation_speed_positive"),
        CheckConstraint(
            "grid_emission_factor_kg_per_kwh >= 0", name="ck_config_emission_nonnegative"
        ),
        CheckConstraint(
            "high_demand_threshold > 0 AND high_demand_threshold <= 1",
            name="ck_config_high_demand_range",
        ),
        CheckConstraint(
            "medium_peak_threshold > 0 AND medium_peak_threshold < high_peak_threshold "
            "AND high_peak_threshold <= 1",
            name="ck_config_peak_threshold_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    singleton_key: Mapped[bool] = mapped_column(default=True, unique=True, nullable=False)
    simulation_speed: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_emission_factor_kg_per_kwh: Mapped[float] = mapped_column(Float, nullable=False)
    high_demand_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    medium_peak_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    high_peak_threshold: Mapped[float] = mapped_column(Float, nullable=False)
