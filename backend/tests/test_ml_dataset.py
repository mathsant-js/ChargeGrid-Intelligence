from dataclasses import fields, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.ml.baseline import (
    chronological_split,
    evaluate_hour_weekday_baseline,
    regression_metrics,
)
from app.ml.dataset import (
    DATASET_COLUMNS,
    FEATURE_COLUMNS,
    HORIZON_STEPS,
    DatasetConfig,
    DemandDatasetRow,
    build_supervised_dataset,
    generate_dataset,
    generate_observations,
)
from app.ml.pipeline import run_pipeline


@pytest.fixture(scope="module")
def dataset() -> list[DemandDatasetRow]:
    return generate_dataset(DatasetConfig(days=2, seed=17))


def test_dataset_schema_contains_required_and_causal_columns(
    dataset: list[DemandDatasetRow],
) -> None:
    required = {
        "timestamp",
        "hour",
        "day_of_week",
        "is_weekend",
        "active_sessions",
        "requested_power_kw",
        "allocated_power_kw",
        "solar_available_kw",
        "solar_used_kw",
        "grid_power_kw",
        "total_demand_kw",
        "demand_kw_next_60_minutes",
    }
    assert required <= set(DATASET_COLUMNS)
    assert "demand_kw_next_60_minutes" not in FEATURE_COLUMNS
    assert tuple(field.name for field in fields(dataset[0])) == DATASET_COLUMNS


def test_dataset_is_strictly_ordered_in_five_minute_intervals(
    dataset: list[DemandDatasetRow],
) -> None:
    assert len(dataset) == 2 * 24 * 12
    assert all(
        current.timestamp - previous.timestamp == timedelta(minutes=5)
        for previous, current in zip(dataset, dataset[1:], strict=False)
    )


def test_target_is_demand_exactly_sixty_minutes_ahead() -> None:
    observations = generate_observations(DatasetConfig(days=1, seed=3))
    rows = build_supervised_dataset(observations)
    for index, row in enumerate(rows):
        assert row.demand_kw_next_60_minutes == observations[index + HORIZON_STEPS].total_demand_kw


def test_future_changes_do_not_change_past_features() -> None:
    observations = generate_observations(DatasetConfig(days=1, seed=5))
    cutoff = 80
    changed = list(observations)
    changed[cutoff] = replace(
        changed[cutoff], total_demand_kw=changed[cutoff].total_demand_kw + 999
    )
    original_rows = build_supervised_dataset(observations)
    changed_rows = build_supervised_dataset(changed)
    for original, modified in zip(original_rows[:cutoff], changed_rows[:cutoff], strict=True):
        assert tuple(getattr(original, name) for name in FEATURE_COLUMNS) == tuple(
            getattr(modified, name) for name in FEATURE_COLUMNS
        )


def test_generation_is_reproducible_and_seed_configurable() -> None:
    config = DatasetConfig(days=1, seed=101, start=datetime(2026, 2, 1, tzinfo=UTC))
    assert generate_dataset(config) == generate_dataset(config)
    assert generate_dataset(config) != generate_dataset(replace(config, seed=102))


def test_chronological_split_has_no_overlap(dataset: list[DemandDatasetRow]) -> None:
    train, test = chronological_split(dataset, test_fraction=0.25)
    assert train[-1].timestamp < test[0].timestamp
    assert len(train) + len(test) == len(dataset)


def test_baseline_metrics_are_calculated_correctly() -> None:
    metrics = regression_metrics([1.0, 2.0, 3.0], [1.0, 2.0, 4.0])
    assert metrics.mae == pytest.approx(1 / 3)
    assert metrics.rmse == pytest.approx((1 / 3) ** 0.5)
    assert metrics.r2 == pytest.approx(0.5)


def test_hour_weekday_baseline_reports_finite_metrics_and_periods(
    dataset: list[DemandDatasetRow],
) -> None:
    evaluation = evaluate_hour_weekday_baseline(dataset)
    assert evaluation.strategy == "historical_mean_by_hour_and_day_of_week"
    assert evaluation.train_end < evaluation.test_start
    assert evaluation.train_rows + evaluation.test_rows == len(dataset)
    assert evaluation.metrics.mae >= 0
    assert evaluation.metrics.rmse >= 0
    assert all(
        value == pytest.approx(value)
        for value in (
            evaluation.metrics.mae,
            evaluation.metrics.rmse,
            evaluation.metrics.r2,
        )
    )


def test_pipeline_writes_dataset_and_training_metadata(tmp_path: Path) -> None:
    dataset_path = tmp_path / "dataset.csv"
    metadata_path = tmp_path / "metadata.json"
    metadata = run_pipeline(
        dataset_path=dataset_path,
        metadata_path=metadata_path,
        artifact_path=tmp_path / "model.joblib",
        config=DatasetConfig(days=1, seed=9),
        test_fraction=0.2,
    )
    assert dataset_path.read_text(encoding="utf-8").splitlines()[0] == ",".join(
        DATASET_COLUMNS
    )
    assert metadata_path.is_file()
    assert metadata["dataset"]["rows"] == 24 * 12
    assert metadata["baseline"]["train_end"] < metadata["baseline"]["test_start"]
