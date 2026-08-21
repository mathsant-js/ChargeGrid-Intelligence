from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models.billing import InvoiceStatus

MoneyRate = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=4)]
Currency = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=3, to_upper=True)
]
TariffName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class TariffFields(BaseModel):
    name: TariffName
    price_per_kwh: MoneyRate
    currency: Currency = "BRL"
    is_active: bool = True
    valid_from: datetime
    valid_until: datetime | None = None

    @model_validator(mode="after")
    def validate_period(self) -> "TariffFields":
        if self.valid_until is not None and self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be after valid_from")
        return self


class TariffCreate(TariffFields):
    pass


class TariffUpdate(BaseModel):
    name: TariffName | None = None
    price_per_kwh: MoneyRate | None = None
    currency: Currency | None = None
    is_active: bool | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class TariffResponse(TariffFields):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    session_id: UUID
    user_id: UUID
    energy_kwh: Decimal
    tariff_per_kwh: Decimal
    subtotal: Decimal
    total: Decimal
    status: InvoiceStatus
    created_at: datetime
    closed_at: datetime | None
