"""Interval energy is deterministic and conserved across solar and grid."""

import math
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.services.energy_readings import (
    ABSOLUTE_TOLERANCE,
    RELATIVE_TOLERANCE,
    build_energy_reading_data,
    calculate_energy_kwh,
)

SESSION_ID = UUID("00000000-0000-0000-0000-000000000001")
INSTANT = datetime(2026, 9, 16, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    ("power_kw", "interval", "expected_kwh"),
    [
        (15.0, timedelta(minutes=5), 1.25),
        (0.0, timedelta(minutes=5), 0.0),
        (15.0, timedelta(0), 0.0),
    ],
)
def test_calculate_energy_kwh(
    power_kw: float, interval: timedelta, expected_kwh: float
) -> None:
    assert calculate_energy_kwh(power_kw, interval) == pytest.approx(expected_kwh)


@pytest.mark.parametrize(
    ("allocated", "solar", "grid", "total_kwh", "solar_kwh", "grid_kwh"),
    [
        (15.0, 15.0, 0.0, 1.25, 1.25, 0.0),
        (15.0, 0.0, 15.0, 1.25, 0.0, 1.25),
        (15.0, 6.0, 9.0, 1.25, 0.5, 0.75),
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    ],
)
def test_build_energy_reading_data(
    allocated: float,
    solar: float,
    grid: float,
    total_kwh: float,
    solar_kwh: float,
    grid_kwh: float,
) -> None:
    reading = build_energy_reading_data(
        session_id=SESSION_ID,
        timestamp=INSTANT,
        requested_power_kw=15.0,
        allocated_power_kw=allocated,
        solar_power_kw=solar,
        grid_power_kw=grid,
        interval=timedelta(minutes=5),
    )

    assert reading.interval_energy_kwh == pytest.approx(total_kwh)
    assert reading.solar_energy_kwh == pytest.approx(solar_kwh)
    assert reading.grid_energy_kwh == pytest.approx(grid_kwh)
    assert reading.interval_energy_kwh == pytest.approx(
        reading.solar_energy_kwh + reading.grid_energy_kwh
    )
    assert asdict(reading) == {
        "session_id": SESSION_ID,
        "timestamp": INSTANT,
        "requested_power_kw": 15.0,
        "allocated_power_kw": allocated,
        "solar_power_kw": solar,
        "grid_power_kw": grid,
        "interval_energy_kwh": reading.interval_energy_kwh,
        "solar_energy_kwh": reading.solar_energy_kwh,
        "grid_energy_kwh": reading.grid_energy_kwh,
    }


def test_zero_interval_builds_zero_energy_with_nonzero_power() -> None:
    reading = build_energy_reading_data(
        session_id=SESSION_ID,
        timestamp=INSTANT,
        requested_power_kw=15,
        allocated_power_kw=15,
        solar_power_kw=6,
        grid_power_kw=9,
        interval=timedelta(0),
    )
    assert (reading.interval_energy_kwh, reading.solar_energy_kwh, reading.grid_energy_kwh) == (
        0,
        0,
        0,
    )


@pytest.mark.parametrize("power_kw", [-1.0, -math.inf, math.inf, math.nan])
def test_calculation_rejects_invalid_power(power_kw: float) -> None:
    with pytest.raises(ValueError, match="power_kw must be finite and nonnegative"):
        calculate_energy_kwh(power_kw, timedelta(minutes=5))


def test_calculation_rejects_negative_interval() -> None:
    with pytest.raises(ValueError, match="interval must be nonnegative"):
        calculate_energy_kwh(15, timedelta(microseconds=-1))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("requested_power_kw", -1.0),
        ("allocated_power_kw", -1.0),
        ("solar_power_kw", -1.0),
        ("grid_power_kw", -1.0),
        ("solar_power_kw", math.nan),
    ],
)
def test_reading_rejects_invalid_power(field: str, value: float) -> None:
    powers = dict(requested_power_kw=15.0, allocated_power_kw=15.0,
                  solar_power_kw=6.0, grid_power_kw=9.0)
    powers[field] = value
    with pytest.raises(ValueError, match=f"{field} must be finite and nonnegative"):
        build_energy_reading_data(
            session_id=SESSION_ID, timestamp=INSTANT, interval=timedelta(minutes=5), **powers
        )


@pytest.mark.parametrize(
    ("allocated", "solar", "grid"),
    [(15.0, 6.0, 8.0), (0.0, 1e-13, 0.0)],
)
def test_reading_rejects_inconsistent_power(
    allocated: float, solar: float, grid: float
) -> None:
    with pytest.raises(ValueError, match="power"):
        build_energy_reading_data(
            session_id=SESSION_ID,
            timestamp=INSTANT,
            requested_power_kw=15,
            allocated_power_kw=allocated,
            solar_power_kw=solar,
            grid_power_kw=grid,
            interval=timedelta(minutes=5),
        )


def test_reading_rejects_negative_interval_and_excess_allocation() -> None:
    with pytest.raises(ValueError, match="interval must be nonnegative"):
        build_energy_reading_data(
            session_id=SESSION_ID,
            timestamp=INSTANT,
            requested_power_kw=15,
            allocated_power_kw=15,
            solar_power_kw=6,
            grid_power_kw=9,
            interval=timedelta(seconds=-1),
        )
    with pytest.raises(ValueError, match="must not exceed"):
        build_energy_reading_data(
            session_id=SESSION_ID,
            timestamp=INSTANT,
            requested_power_kw=14,
            allocated_power_kw=15,
            solar_power_kw=6,
            grid_power_kw=9,
            interval=timedelta(minutes=5),
        )


def test_float_rounding_is_accepted_and_energy_is_conserved_within_tolerance() -> None:
    reading = build_energy_reading_data(
        session_id=SESSION_ID,
        timestamp=INSTANT,
        requested_power_kw=0.3,
        allocated_power_kw=0.3,
        solar_power_kw=0.1,
        grid_power_kw=0.2,
        interval=timedelta(minutes=5),
    )
    assert math.isclose(
        reading.interval_energy_kwh,
        reading.solar_energy_kwh + reading.grid_energy_kwh,
        rel_tol=RELATIVE_TOLERANCE,
        abs_tol=ABSOLUTE_TOLERANCE,
    )
