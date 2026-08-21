from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import LicensePlate, Name, ORMResponse, PositivePower


class VehicleCreate(BaseModel):
    user_id: UUID | None = None
    name: Name
    brand: Name
    model: Name
    license_plate: LicensePlate
    max_charge_power_kw: PositivePower


class VehicleUpdate(BaseModel):
    user_id: UUID | None = None
    name: Name | None = None
    brand: Name | None = None
    model: Name | None = None
    license_plate: LicensePlate | None = None
    max_charge_power_kw: PositivePower | None = None


class VehicleResponse(ORMResponse):
    user_id: UUID
    name: str
    brand: str
    model: str
    license_plate: str
    max_charge_power_kw: float
