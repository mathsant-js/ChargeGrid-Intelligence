from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.schemas.common import Name, ORMResponse, PositivePower

Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]


class StationCreate(BaseModel):
    name: Name
    description: Description | None = None
    grid_limit_kw: PositivePower
    is_active: bool = True


class StationUpdate(BaseModel):
    name: Name | None = None
    description: Description | None = None
    grid_limit_kw: PositivePower | None = None
    is_active: bool | None = None


class StationResponse(ORMResponse):
    name: str
    description: str | None
    grid_limit_kw: float
    is_active: bool
