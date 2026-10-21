"""Solar source remains deterministic and bounded across the simulated day."""

import math
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.simulation.energy_data import (
    DataQuality,
    EnergyDataProvider,
    EnergyDataSource,
    SimulationEnergyDataProvider,
    TelemetryReplayEnergyDataProvider,
)


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


def write_replay(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "telemetry.csv"
    header = (
        "timestamp,station_code,pv_power_kw,grid_power_kw,load_power_kw,"
        "inverter_status,temperature_c,data_quality\n"
    )
    path.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_telemetry_replay_reads_exact_sample_caps_peak_and_is_deterministic(
    tmp_path: Path,
) -> None:
    path = write_replay(
        tmp_path,
        ["2026-09-18T12:00:00Z,ST-01,25,10,35,ONLINE,36.5,estimated"],
    )
    provider: EnergyDataProvider = TelemetryReplayEnergyDataProvider(path)
    instant = datetime(2026, 9, 18, 9, tzinfo=timezone(timedelta(hours=-3)))

    first = provider.sample(instant, "ST-01", 20)
    second = provider.sample(instant, "ST-01", 20)

    assert first == second
    assert first.solar_available_kw == 20
    assert first.source is EnergyDataSource.TELEMETRY_REPLAY
    assert first.quality is DataQuality.ESTIMATED


def test_telemetry_replay_missing_sample_is_explicit_and_safe(tmp_path: Path) -> None:
    provider = TelemetryReplayEnergyDataProvider(
        write_replay(
            tmp_path,
            ["2026-09-18T12:00:00Z,ST-01,10,5,15,ONLINE,32,GOOD"],
        )
    )

    sample = provider.sample(datetime(2026, 9, 18, 12, 1, tzinfo=UTC), "ST-01", 20)

    assert sample.solar_available_kw == 0
    assert sample.quality is DataQuality.MISSING


@pytest.mark.parametrize(
    ("timestamp", "power", "grid", "load", "temperature", "match"),
    [
        ("invalid", "10", "5", "15", "32", "timestamp"),
        ("2026-09-18T12:00:00", "10", "5", "15", "32", "timezone"),
        ("2026-09-18T12:00:00Z", "-1", "5", "15", "32", "pv_power_kw"),
        ("2026-09-18T12:00:00Z", "nan", "5", "15", "32", "pv_power_kw"),
        ("2026-09-18T12:00:00Z", "10", "inf", "15", "32", "grid_power_kw"),
        ("2026-09-18T12:00:00Z", "10", "5", "-1", "32", "load_power_kw"),
        ("2026-09-18T12:00:00Z", "10", "5", "15", "nan", "temperature_c"),
    ],
)
def test_telemetry_replay_rejects_invalid_values(
    tmp_path: Path,
    timestamp: str,
    power: str,
    grid: str,
    load: str,
    temperature: str,
    match: str,
) -> None:
    path = write_replay(
        tmp_path,
        [f"{timestamp},ST-01,{power},{grid},{load},ONLINE,{temperature},GOOD"],
    )

    with pytest.raises(ValueError, match=match):
        TelemetryReplayEnergyDataProvider(path)


def test_telemetry_replay_rejects_duplicate_station_timestamp(tmp_path: Path) -> None:
    row = "2026-09-18T12:00:00Z,ST-01,10,5,15,ONLINE,32,GOOD"
    with pytest.raises(ValueError, match="duplicate"):
        TelemetryReplayEnergyDataProvider(write_replay(tmp_path, [row, row]))
