from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
ShortCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
LicensePlate = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
PositivePower = Annotated[float, Field(gt=0, allow_inf_nan=False)]


class ORMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
