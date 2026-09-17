"""Solar source remains deterministic and bounded across the simulated day."""

import math
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.simulation.energy_data import EnergyDataProvider, SimulationEnergyDataProvider


@pytest.mark.parametrize(
    ("hour", "expected"),
    [
        (0, 0.0),  # midnight
        (5, 0.0),  # before sunrise
        (6, 0.0),  # sunrise
        (9, 5 * math.sqrt(2)),  # morning
        (12, 10.0),  # noon
        (15, 5 * math.sqrt(2)),  # afternoon
        (18, 0.0),  # sunset
        (21, 0.0),  # night
    ],
)
def test_solar_curve(hour: int, expected: float) -> None:
    provider: EnergyDataProvider = SimulationEnergyDataProvider()
    instant = datetime(2026, 9, 16, hour, tzinfo=UTC)
    assert provider.solar_available_kw(instant, 10.0) == pytest.approx(expected)


def test_zero_peak_and_reproducibility() -> None:
    provider = SimulationEnergyDataProvider()
    instant = datetime(2026, 9, 16, 11, 37, tzinfo=UTC)
    assert provider.solar_available_kw(instant, 0.0) == 0.0
    assert provider.solar_available_kw(instant, 10.0) == provider.solar_available_kw(
        instant, 10.0
    )
    assert provider.solar_available_kw(instant, 10.0) == provider.solar_available_kw(
        instant.astimezone(timezone(timedelta(hours=-3))), 10.0
    )


def test_solar_power_is_finite_and_bounded() -> None:
    provider = SimulationEnergyDataProvider()
    for minute in range(24 * 60):
        instant = datetime(2026, 9, 16, tzinfo=UTC) + timedelta(minutes=minute)
        power = provider.solar_available_kw(instant, 32.5)
        assert math.isfinite(power)
        assert 0 <= power <= 32.5


@pytest.mark.parametrize("peak", [-1.0, math.inf, -math.inf, math.nan])
def test_invalid_peak_is_rejected(peak: float) -> None:
    with pytest.raises(ValueError, match="station_peak_solar_kw"):
        SimulationEnergyDataProvider().solar_available_kw(datetime(2026, 9, 16, tzinfo=UTC), peak)


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        SimulationEnergyDataProvider().solar_available_kw(datetime(2026, 9, 16, 12), 10.0)
