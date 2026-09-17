"""Deterministic energy data supplied to the simulator."""

import math
from datetime import UTC, datetime
from typing import Protocol


class EnergyDataProvider(Protocol):
    """Source of available solar power for a station at a simulated instant."""

    def solar_available_kw(self, timestamp: datetime, station_peak_solar_kw: float) -> float:
        """Return available solar power in kW."""


class SimulationEnergyDataProvider:
    """Daily solar curve evaluated against UTC clock time.

    Generation runs from 06:00 to 18:00 UTC. A half sine wave reaches the
    configured station peak at 12:00 UTC. No state or randomness is involved.
    """

    def solar_available_kw(self, timestamp: datetime, station_peak_solar_kw: float) -> float:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        if not math.isfinite(station_peak_solar_kw) or station_peak_solar_kw < 0:
            raise ValueError("station_peak_solar_kw must be finite and nonnegative")

        utc_time = timestamp.astimezone(UTC)
        hour = (
            utc_time.hour
            + utc_time.minute / 60
            + utc_time.second / 3600
            + utc_time.microsecond / 3_600_000_000
        )
        if hour <= 6 or hour >= 18 or station_peak_solar_kw == 0:
            return 0.0

        power = station_peak_solar_kw * math.sin(math.pi * (hour - 6) / 12)
        return min(station_peak_solar_kw, max(0.0, power))
