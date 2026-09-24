"""Deterministic temporal dataset generation for demand forecasting.

The generator deliberately produces station-level observations without calling
the production power allocator.  It is training-data scaffolding, not a second
implementation of the energy-management business rules.
"""

import csv
import math
import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass, fields
from datetime import UTC, datetime, timedelta
from pathlib import Path

INTERVAL_MINUTES = 5
FORECAST_HORIZON_MINUTES = 60
HORIZON_STEPS = FORECAST_HORIZON_MINUTES // INTERVAL_MINUTES


@dataclass(frozen=True, slots=True)
class DatasetConfig:
    days: int = 90
    seed: int = 42
    start: datetime = datetime(2026, 1, 1, tzinfo=UTC)
    grid_limit_kw: float = 180.0
    solar_peak_kw: float = 90.0


@dataclass(frozen=True, slots=True)
class DemandObservation:
    timestamp: datetime
    active_sessions: int
    requested_power_kw: float
    allocated_power_kw: float
    solar_available_kw: float
    solar_used_kw: float
    grid_power_kw: float
    total_demand_kw: float


@dataclass(frozen=True, slots=True)
class DemandDatasetRow:
    timestamp: datetime
    hour: int
    day_of_week: int
    is_weekend: bool
    active_sessions: int
    requested_power_kw: float
    allocated_power_kw: float
    solar_available_kw: float
    solar_used_kw: float
    grid_power_kw: float
    total_demand_kw: float
    current_demand_kw: float
    historical_avg_demand_kw: float
    demand_kw_next_60_minutes: float


DATASET_COLUMNS = tuple(field.name for field in fields(DemandDatasetRow))
FEATURE_COLUMNS = tuple(
    column for column in DATASET_COLUMNS if column != "demand_kw_next_60_minutes"
)


def _validate_config(config: DatasetConfig) -> None:
    if config.days <= 0:
        raise ValueError("days must be positive")
    if config.start.tzinfo is None or config.start.utcoffset() is None:
        raise ValueError("start must be timezone-aware")
    if config.grid_limit_kw <= 0 or config.solar_peak_kw < 0:
        raise ValueError("power limits must be valid")


def generate_observations(config: DatasetConfig) -> list[DemandObservation]:
    """Generate 90 days plus the look-ahead needed to label the final row."""

    _validate_config(config)
    rng = random.Random(config.seed)
    row_count = config.days * 24 * 60 // INTERVAL_MINUTES + HORIZON_STEPS
    observations: list[DemandObservation] = []

    for step in range(row_count):
        timestamp = config.start + timedelta(minutes=step * INTERVAL_MINUTES)
        fractional_hour = timestamp.hour + timestamp.minute / 60
        weekday_factor = 0.78 if timestamp.weekday() >= 5 else 1.0
        morning = math.exp(-((fractional_hour - 8.0) / 2.8) ** 2)
        evening = math.exp(-((fractional_hour - 18.0) / 3.4) ** 2)
        activity_level = weekday_factor * (1.6 + 8.2 * morning + 11.5 * evening)
        active_sessions = max(0, round(activity_level + rng.gauss(0, 1.15)))

        average_request_kw = max(3.6, 9.2 + rng.gauss(0, 1.1))
        requested_power_kw = active_sessions * average_request_kw

        daylight = 0.0
        if 6 < fractional_hour < 18:
            daylight = math.sin(math.pi * (fractional_hour - 6) / 12)
        seasonal_factor = 0.82 + 0.18 * math.sin(2 * math.pi * timestamp.timetuple().tm_yday / 365)
        cloud_factor = min(1.0, max(0.35, 0.84 + rng.gauss(0, 0.07)))
        solar_available_kw = config.solar_peak_kw * daylight * seasonal_factor * cloud_factor

        # Synthetic capacity is intentionally local to the data generator.  It
        # preserves physical consistency without owning production allocation.
        allocated_power_kw = min(requested_power_kw, config.grid_limit_kw + solar_available_kw)
        solar_used_kw = min(allocated_power_kw, solar_available_kw)
        grid_power_kw = allocated_power_kw - solar_used_kw
        observations.append(
            DemandObservation(
                timestamp=timestamp,
                active_sessions=active_sessions,
                requested_power_kw=round(requested_power_kw, 6),
                allocated_power_kw=round(allocated_power_kw, 6),
                solar_available_kw=round(solar_available_kw, 6),
                solar_used_kw=round(solar_used_kw, 6),
                grid_power_kw=round(grid_power_kw, 6),
                total_demand_kw=round(allocated_power_kw, 6),
            )
        )
    return observations


def build_supervised_dataset(
    observations: Sequence[DemandObservation],
    *,
    output_rows: int | None = None,
) -> list[DemandDatasetRow]:
    """Build causal features and a label exactly 60 minutes in the future.

    Historical averages are calculated from earlier observations only.  The
    current observation is added to the accumulator after its feature value is
    read, which makes the no-look-ahead property explicit.
    """

    if len(observations) <= HORIZON_STEPS:
        raise ValueError("observations must cover more than the forecast horizon")
    for previous, current in zip(observations, observations[1:], strict=False):
        if current.timestamp - previous.timestamp != timedelta(minutes=INTERVAL_MINUTES):
            raise ValueError("observations must be unique, ordered 5-minute intervals")

    available_rows = len(observations) - HORIZON_STEPS
    row_count = available_rows if output_rows is None else output_rows
    if not 0 < row_count <= available_rows:
        raise ValueError("output_rows exceeds observations with known targets")

    totals: defaultdict[tuple[int, int], float] = defaultdict(float)
    counts: defaultdict[tuple[int, int], int] = defaultdict(int)
    rows: list[DemandDatasetRow] = []
    for index, observation in enumerate(observations[:row_count]):
        bucket = (observation.timestamp.weekday(), observation.timestamp.hour)
        historical_average = totals[bucket] / counts[bucket] if counts[bucket] else 0.0
        target = observations[index + HORIZON_STEPS].total_demand_kw
        rows.append(
            DemandDatasetRow(
                timestamp=observation.timestamp,
                hour=observation.timestamp.hour,
                day_of_week=observation.timestamp.weekday(),
                is_weekend=observation.timestamp.weekday() >= 5,
                active_sessions=observation.active_sessions,
                requested_power_kw=observation.requested_power_kw,
                allocated_power_kw=observation.allocated_power_kw,
                solar_available_kw=observation.solar_available_kw,
                solar_used_kw=observation.solar_used_kw,
                grid_power_kw=observation.grid_power_kw,
                total_demand_kw=observation.total_demand_kw,
                current_demand_kw=observation.total_demand_kw,
                historical_avg_demand_kw=round(historical_average, 6),
                demand_kw_next_60_minutes=target,
            )
        )
        totals[bucket] += observation.total_demand_kw
        counts[bucket] += 1
    return rows


def generate_dataset(config: DatasetConfig | None = None) -> list[DemandDatasetRow]:
    config = config or DatasetConfig()
    expected_rows = config.days * 24 * 60 // INTERVAL_MINUTES
    return build_supervised_dataset(generate_observations(config), output_rows=expected_rows)


def write_dataset_csv(rows: Sequence[DemandDatasetRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=DATASET_COLUMNS)
        writer.writeheader()
        for row in rows:
            values = asdict(row)
            values["timestamp"] = row.timestamp.isoformat()
            writer.writerow(values)
