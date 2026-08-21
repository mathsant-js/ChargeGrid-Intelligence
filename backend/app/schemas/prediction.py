from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.prediction import DemandRiskLevel
from app.schemas.common import ORMResponse


class DemandPredictionCreate(BaseModel):
    station_id: UUID
    prediction_for: datetime
    predicted_demand_kw: float = Field(ge=0, allow_inf_nan=False)
    capacity_kw: float = Field(gt=0, allow_inf_nan=False)
    risk_level: DemandRiskLevel
    model_version: str = Field(min_length=1, max_length=120)


class DemandPredictionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    station_id: UUID
    generated_at: datetime
    prediction_for: datetime
    predicted_demand_kw: float
    capacity_kw: float
    risk_level: DemandRiskLevel
    model_version: str
    prediction_horizon_minutes: int


class SystemConfigurationValues(BaseModel):
    simulation_speed: int = Field(gt=0)
    grid_emission_factor_kg_per_kwh: float = Field(ge=0, allow_inf_nan=False)
    high_demand_threshold: float = Field(gt=0, le=1, allow_inf_nan=False)
    medium_peak_threshold: float = Field(gt=0, lt=1, allow_inf_nan=False)
    high_peak_threshold: float = Field(gt=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_peak_thresholds(self) -> Self:
        if self.medium_peak_threshold >= self.high_peak_threshold:
            raise ValueError("medium_peak_threshold must be lower than high_peak_threshold")
        return self


class SystemConfigurationCreate(SystemConfigurationValues):
    pass


class SystemConfigurationUpdate(BaseModel):
    simulation_speed: int | None = Field(default=None, gt=0)
    grid_emission_factor_kg_per_kwh: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )
    high_demand_threshold: float | None = Field(default=None, gt=0, le=1, allow_inf_nan=False)
    medium_peak_threshold: float | None = Field(default=None, gt=0, lt=1, allow_inf_nan=False)
    high_peak_threshold: float | None = Field(default=None, gt=0, le=1, allow_inf_nan=False)


class SystemConfigurationResponse(ORMResponse, SystemConfigurationValues):
    pass
