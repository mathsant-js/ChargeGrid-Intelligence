from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, field_validator

from app.schemas.common import Name, ORMResponse, PositivePower

Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
NonNegativePower = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class StationCreate(BaseModel):
    name: Name
    description: Description | None = None
    grid_limit_kw: PositivePower
    station_peak_solar_kw: NonNegativePower = 0.0
    is_active: bool = True


class StationUpdate(BaseModel):
    name: Name | None = None
    description: Description | None = None
    grid_limit_kw: PositivePower | None = None
    station_peak_solar_kw: NonNegativePower | None = None
    is_active: bool | None = None

    @field_validator("name", "grid_limit_kw", "station_peak_solar_kw", "is_active")
    @classmethod
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("field cannot be null")
        return value


class StationResponse(ORMResponse):
    name: str
    description: str | None
    grid_limit_kw: float
    station_peak_solar_kw: float
    is_active: bool
