"""Command-line entry point for Phase 7 dataset and baseline generation."""

import argparse
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.ml.baseline import evaluate_hour_weekday_baseline
from app.ml.dataset import (
    FORECAST_HORIZON_MINUTES,
    INTERVAL_MINUTES,
    DatasetConfig,
    generate_dataset,
    write_dataset_csv,
)


def _isoformat_datetimes(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def run_pipeline(
    *,
    dataset_path: Path,
    metadata_path: Path,
    config: DatasetConfig,
    test_fraction: float,
) -> dict[str, Any]:
    rows = generate_dataset(config)
    evaluation = evaluate_hour_weekday_baseline(rows, test_fraction)
    write_dataset_csv(rows, dataset_path)
    metadata: dict[str, Any] = {
        "dataset": {
            "rows": len(rows),
            "seed": config.seed,
            "interval_minutes": INTERVAL_MINUTES,
            "forecast_horizon_minutes": FORECAST_HORIZON_MINUTES,
            "period_start": rows[0].timestamp,
            "period_end": rows[-1].timestamp,
        },
        "baseline": asdict(evaluation),
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(metadata, default=_isoformat_datetimes, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metadata


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("../data/processed/demand_90d.csv"))
    parser.add_argument(
        "--metadata", type=Path, default=Path("../data/processed/baseline_metrics.json")
    )
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    metadata = run_pipeline(
        dataset_path=args.dataset,
        metadata_path=args.metadata,
        config=DatasetConfig(days=args.days, seed=args.seed),
        test_fraction=args.test_fraction,
    )
    print(json.dumps(metadata, default=_isoformat_datetimes, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
