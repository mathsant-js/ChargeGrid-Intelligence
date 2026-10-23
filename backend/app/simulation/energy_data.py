"""Deterministic, replaceable energy data supplied to the simulator."""

import csv
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class EnergyDataSource(StrEnum):
    CURVE = "curve"
    TELEMETRY_REPLAY = "telemetry_replay"


class DataQuality(StrEnum):
    SYNTHETIC = "SYNTHETIC"
    GOOD = "GOOD"
    ESTIMATED = "ESTIMATED"
    MISSING = "MISSING"


@dataclass(frozen=True, slots=True)
class EnergyDataSample:
    solar_available_kw: float
    source: EnergyDataSource
    quality: DataQuality


class EnergyDataProvider(Protocol):
    """Source of available solar power for a station at a simulated instant."""

    source: EnergyDataSource

    def sample(
        self,
        timestamp: datetime,
        station_code: str,
        station_peak_solar_kw: float,
    ) -> EnergyDataSample:
        """Return a validated sample for one station and instant."""


def _validate_request(timestamp: datetime, station_peak_solar_kw: float) -> datetime:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    if not math.isfinite(station_peak_solar_kw) or station_peak_solar_kw < 0:
        raise ValueError("station_peak_solar_kw must be finite and nonnegative")
    return timestamp.astimezone(UTC)


class SimulationEnergyDataProvider:
    """Daily solar curve evaluated against UTC clock time."""

    source = EnergyDataSource.CURVE

    def sample(
        self,
        timestamp: datetime,
        station_code: str,
        station_peak_solar_kw: float,
    ) -> EnergyDataSample:
        utc_time = _validate_request(timestamp, station_peak_solar_kw)
        hour = (
            utc_time.hour
            + utc_time.minute / 60
            + utc_time.second / 3600
            + utc_time.microsecond / 3_600_000_000
        )
        if hour <= 6 or hour >= 18 or station_peak_solar_kw == 0:
            power = 0.0
        else:
            power = station_peak_solar_kw * math.sin(math.pi * (hour - 6) / 12)
            power = min(station_peak_solar_kw, max(0.0, power))
        return EnergyDataSample(power, self.source, DataQuality.SYNTHETIC)

    def solar_available_kw(self, timestamp: datetime, station_peak_solar_kw: float) -> float:
        """Compatibility helper for callers interested only in the curve value."""
        return self.sample(timestamp, "", station_peak_solar_kw).solar_available_kw


class TelemetryReplayEnergyDataProvider:
    """Replay validated synthetic gateway telemetry from a versioned CSV file.

    Samples use an exact UTC timestamp and station code match. Missing samples
    safely produce zero generation with ``MISSING`` quality.
    """

    source = EnergyDataSource.TELEMETRY_REPLAY
    required_columns = {
        "timestamp",
        "station_code",
        "pv_power_kw",
        "grid_power_kw",
        "load_power_kw",
        "inverter_status",
        "temperature_c",
        "data_quality",
    }

    def __init__(self, path: Path) -> None:
        self.path = path
        self._samples = self._load(path)

    @classmethod
    def _load(cls, path: Path) -> dict[tuple[str, datetime], tuple[float, DataQuality]]:
        samples: dict[tuple[str, datetime], tuple[float, DataQuality]] = {}
        try:
            handle = path.open(encoding="utf-8", newline="")
        except OSError as exc:
            raise ValueError(f"cannot read telemetry replay file: {path}") from exc
        with handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or not cls.required_columns.issubset(reader.fieldnames):
                raise ValueError("telemetry replay file has missing required columns")
            for line_number, row in enumerate(reader, start=2):
                try:
                    try:
                        timestamp = datetime.fromisoformat(
                            row["timestamp"].replace("Z", "+00:00")
                        )
                    except ValueError as exc:
                        raise ValueError("timestamp must be valid ISO 8601") from exc
                    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                        raise ValueError("timestamp must include timezone")
                    timestamp = timestamp.astimezone(UTC)
                    station_code = row["station_code"].strip()
                    if not station_code:
                        raise ValueError("station_code is empty")
                    power = float(row["pv_power_kw"])
                    if not math.isfinite(power) or power < 0:
                        raise ValueError("pv_power_kw must be finite and nonnegative")
                    for field in ("grid_power_kw", "load_power_kw"):
                        field_value = float(row[field])
                        if not math.isfinite(field_value) or field_value < 0:
                            raise ValueError(f"{field} must be finite and nonnegative")
                    temperature = float(row["temperature_c"])
                    if not math.isfinite(temperature):
                        raise ValueError("temperature_c must be finite")
                    if not row["inverter_status"].strip():
                        raise ValueError("inverter_status is empty")
                    quality = DataQuality(row["data_quality"].strip().upper())
                    if quality is DataQuality.MISSING:
                        raise ValueError("persisted samples cannot have MISSING quality")
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError(
                        f"invalid telemetry replay sample at line {line_number}: {exc}"
                    ) from exc
                key = (station_code, timestamp)
                if key in samples:
                    raise ValueError(f"duplicate telemetry replay sample at line {line_number}")
                samples[key] = (power, quality)
        return samples

    def sample(
        self,
        timestamp: datetime,
        station_code: str,
        station_peak_solar_kw: float,
    ) -> EnergyDataSample:
        utc_time = _validate_request(timestamp, station_peak_solar_kw)
        stored = self._samples.get((station_code, utc_time))
        if stored is None:
            return EnergyDataSample(0.0, self.source, DataQuality.MISSING)
        power, quality = stored
        return EnergyDataSample(min(power, station_peak_solar_kw), self.source, quality)
