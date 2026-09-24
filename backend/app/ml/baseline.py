"""Chronological evaluation of the hour/day-of-week demand baseline."""

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.ml.dataset import DemandDatasetRow


@dataclass(frozen=True, slots=True)
class RegressionMetrics:
    mae: float
    rmse: float
    r2: float


@dataclass(frozen=True, slots=True)
class BaselineEvaluation:
    strategy: str
    train_rows: int
    test_rows: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    metrics: RegressionMetrics


def chronological_split(
    rows: Sequence[DemandDatasetRow], test_fraction: float = 0.2
) -> tuple[Sequence[DemandDatasetRow], Sequence[DemandDatasetRow]]:
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between zero and one")
    if len(rows) < 2:
        raise ValueError("at least two rows are required")
    if any(
        current.timestamp <= previous.timestamp
        for previous, current in zip(rows, rows[1:], strict=False)
    ):
        raise ValueError("rows must be strictly ordered by timestamp")
    split_index = int(len(rows) * (1 - test_fraction))
    if split_index == 0 or split_index == len(rows):
        raise ValueError("split must leave rows in train and test")
    return rows[:split_index], rows[split_index:]


def regression_metrics(actual: Sequence[float], predicted: Sequence[float]) -> RegressionMetrics:
    if len(actual) != len(predicted) or not actual:
        raise ValueError("actual and predicted must have the same nonzero length")
    errors = [
        actual_value - predicted_value
        for actual_value, predicted_value in zip(actual, predicted, strict=True)
    ]
    mae = sum(abs(error) for error in errors) / len(errors)
    mse = sum(error**2 for error in errors) / len(errors)
    actual_mean = sum(actual) / len(actual)
    total_variance = sum((value - actual_mean) ** 2 for value in actual)
    residual_variance = sum(error**2 for error in errors)
    r2 = 1 - residual_variance / total_variance if total_variance else float(residual_variance == 0)
    return RegressionMetrics(mae=mae, rmse=math.sqrt(mse), r2=r2)


def evaluate_hour_weekday_baseline(
    rows: Sequence[DemandDatasetRow], test_fraction: float = 0.2
) -> BaselineEvaluation:
    train, test = chronological_split(rows, test_fraction)
    totals: defaultdict[tuple[int, int], float] = defaultdict(float)
    counts: defaultdict[tuple[int, int], int] = defaultdict(int)
    for row in train:
        bucket = (row.day_of_week, row.hour)
        totals[bucket] += row.demand_kw_next_60_minutes
        counts[bucket] += 1
    global_average = sum(row.demand_kw_next_60_minutes for row in train) / len(train)
    predictions = [
        totals[(row.day_of_week, row.hour)] / counts[(row.day_of_week, row.hour)]
        if counts[(row.day_of_week, row.hour)]
        else global_average
        for row in test
    ]
    metrics = regression_metrics(
        [row.demand_kw_next_60_minutes for row in test], predictions
    )
    return BaselineEvaluation(
        strategy="historical_mean_by_hour_and_day_of_week",
        train_rows=len(train),
        test_rows=len(test),
        train_start=train[0].timestamp,
        train_end=train[-1].timestamp,
        test_start=test[0].timestamp,
        test_end=test[-1].timestamp,
        metrics=metrics,
    )
