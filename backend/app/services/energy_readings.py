"""Pure interval energy calculations and data for an EnergyReading."""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

# Float power and energy match the existing SQLAlchemy columns. Allow only
# rounding error when comparing independently supplied power and energy parts.
RELATIVE_TOLERANCE = 1e-9
ABSOLUTE_TOLERANCE = 1e-12


@dataclass(frozen=True, slots=True)
class EnergyReadingData:
    session_id: UUID
    timestamp: datetime
    requested_power_kw: float
    allocated_power_kw: float
    solar_power_kw: float
    grid_power_kw: float
    interval_energy_kwh: float
    solar_energy_kwh: float
    grid_energy_kwh: float


def _validate_power(name: str, power_kw: float) -> None:
    if not math.isfinite(power_kw) or power_kw < 0:
        raise ValueError(f"{name} must be finite and nonnegative")


def calculate_energy_kwh(power_kw: float, interval: timedelta) -> float:
    """Convert a nonnegative power over an explicit duration into kWh."""

    _validate_power("power_kw", power_kw)
    if interval < timedelta(0):
        raise ValueError("interval must be nonnegative")
    energy_kwh = power_kw * (interval.total_seconds() / 3600)
    if not math.isfinite(energy_kwh):
        raise ValueError("interval energy must be finite")
    return energy_kwh


def build_energy_reading_data(
    *,
    session_id: UUID,
    timestamp: datetime,
    requested_power_kw: float,
    allocated_power_kw: float,
    solar_power_kw: float,
    grid_power_kw: float,
    interval: timedelta,
) -> EnergyReadingData:
    """Build reading fields from power values already chosen by the allocator.

    Power and energy conservation use 1e-9 relative and 1e-12 absolute
    tolerance for floating point rounding. Zero allocation requires zero
    solar and grid power exactly.
    """

    for name, power in (
        ("requested_power_kw", requested_power_kw),
        ("allocated_power_kw", allocated_power_kw),
        ("solar_power_kw", solar_power_kw),
        ("grid_power_kw", grid_power_kw),
    ):
        _validate_power(name, power)
    if allocated_power_kw > requested_power_kw:
        raise ValueError("allocated_power_kw must not exceed requested_power_kw")
    if allocated_power_kw == 0 and (solar_power_kw != 0 or grid_power_kw != 0):
        raise ValueError("zero allocation requires zero solar and grid power")
    if not math.isclose(
        solar_power_kw + grid_power_kw,
        allocated_power_kw,
        rel_tol=RELATIVE_TOLERANCE,
        abs_tol=ABSOLUTE_TOLERANCE,
    ):
        raise ValueError("solar and grid power must sum to allocated_power_kw")

    interval_energy_kwh = calculate_energy_kwh(allocated_power_kw, interval)
    solar_energy_kwh = calculate_energy_kwh(solar_power_kw, interval)
    grid_energy_kwh = calculate_energy_kwh(grid_power_kw, interval)
    if not math.isclose(
        solar_energy_kwh + grid_energy_kwh,
        interval_energy_kwh,
        rel_tol=RELATIVE_TOLERANCE,
        abs_tol=ABSOLUTE_TOLERANCE,
    ):
        raise ValueError("solar and grid energy must sum to interval_energy_kwh")

    return EnergyReadingData(
        session_id=session_id,
        timestamp=timestamp,
        requested_power_kw=requested_power_kw,
        allocated_power_kw=allocated_power_kw,
        solar_power_kw=solar_power_kw,
        grid_power_kw=grid_power_kw,
        interval_energy_kwh=interval_energy_kwh,
        solar_energy_kwh=solar_energy_kwh,
        grid_energy_kwh=grid_energy_kwh,
    )
