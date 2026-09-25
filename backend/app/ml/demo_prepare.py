"""Prepare the reproducible ML artifact and causal history for the official demo."""

import argparse
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.demo_seed import PREFIX
from app.ml.dataset import DatasetConfig
from app.ml.pipeline import run_pipeline
from app.models.billing import Tariff
from app.models.energy import ChargingSession, ChargingSessionStatus, EnergyReading, SolarReading
from app.models.infrastructure import Charger, ChargingStation
from app.models.vehicle import Vehicle

HISTORICAL_DEMAND_KW = 80.0
HISTORICAL_SOLAR_KW = 20.0
DEMO_PREDICTION_OFFSET = timedelta(minutes=3)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("demo start must be timezone-aware")
    return value.astimezone(UTC)


def prepare_inference_history(db: Session, demo_start: datetime) -> datetime:
    """Insert one explicit, physically valid past observation for inference.

    The official scenario predicts after three one-minute ticks. The fixture is
    exactly seven days before that instant, so weekday/hour historical features
    are available without inserting any observation in the scenario's future.
    """

    start = _as_utc(demo_start)
    historical_at = start + DEMO_PREDICTION_OFFSET - timedelta(days=7)
    station = db.scalar(select(ChargingStation).where(ChargingStation.name == PREFIX))
    if station is None:
        raise ValueError("run app.demo_seed before ML demo preparation")
    chargers = list(
        db.scalars(
            select(Charger)
            .where(Charger.station_id == station.id)
            .order_by(Charger.code)
        )
    )
    vehicles = list(
        db.scalars(select(Vehicle).where(Vehicle.license_plate.like("S3D-%")).order_by(Vehicle.license_plate))
    )
    tariff = db.scalar(select(Tariff).where(Tariff.name == PREFIX))
    if len(chargers) != 4 or len(vehicles) != 4 or tariff is None:
        raise ValueError("official demo domain seed is incomplete")

    existing_solar = db.scalar(
        select(SolarReading).where(
            SolarReading.station_id == station.id,
            SolarReading.timestamp == historical_at,
        )
    )
    if existing_solar is not None:
        total = db.scalar(
            select(func.sum(EnergyReading.allocated_power_kw))
            .join(ChargingSession, EnergyReading.session_id == ChargingSession.id)
            .join(Charger, ChargingSession.charger_id == Charger.id)
            .where(
                Charger.station_id == station.id,
                EnergyReading.timestamp == historical_at,
            )
        )
        if float(total or 0) != HISTORICAL_DEMAND_KW or existing_solar.available_power_kw != 20:
            raise ValueError("existing ML demo history conflicts with the deterministic fixture")
        return historical_at

    interval_hours = 5 / 60
    for charger, vehicle in zip(chargers, vehicles, strict=True):
        energy = 20 * interval_hours
        session = ChargingSession(
            user_id=vehicle.user_id,
            vehicle_id=vehicle.id,
            charger_id=charger.id,
            status=ChargingSessionStatus.COMPLETED,
            started_at=historical_at - timedelta(minutes=5),
            ended_at=historical_at,
            requested_power_kw=20,
            allocated_power_kw=0,
            energy_consumed_kwh=energy,
            solar_energy_kwh=HISTORICAL_SOLAR_KW / 4 * interval_hours,
            grid_energy_kwh=15 * interval_hours,
            tariff_per_kwh=tariff.price_per_kwh,
            total_cost=Decimal(str(energy * float(tariff.price_per_kwh))).quantize(
                Decimal("0.01")
            ),
        )
        db.add(session)
        db.flush()
        db.add(
            EnergyReading(
                session_id=session.id,
                timestamp=historical_at,
                requested_power_kw=20,
                allocated_power_kw=20,
                solar_power_kw=5,
                grid_power_kw=15,
                interval_energy_kwh=energy,
                solar_energy_kwh=5 * interval_hours,
                grid_energy_kwh=15 * interval_hours,
            )
        )
    db.add(
        SolarReading(
            station_id=station.id,
            timestamp=historical_at,
            available_power_kw=HISTORICAL_SOLAR_KW,
        )
    )
    return historical_at


def prepare(
    *,
    demo_start: datetime,
    dataset_path: Path,
    metadata_path: Path,
    artifact_path: Path,
    days: int = 90,
    seed: int = 42,
    test_fraction: float = 0.2,
) -> dict[str, Any]:
    metadata = run_pipeline(
        dataset_path=dataset_path,
        metadata_path=metadata_path,
        artifact_path=artifact_path,
        config=DatasetConfig(days=days, seed=seed),
        test_fraction=test_fraction,
    )
    with SessionLocal() as db, db.begin():
        historical_at = prepare_inference_history(db, demo_start)
    return {"training": metadata, "historical_observation_at": historical_at.isoformat()}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo-start", required=True, type=datetime.fromisoformat)
    parser.add_argument("--dataset", type=Path, default=Path("../data/processed/demand_90d.csv"))
    parser.add_argument(
        "--metadata", type=Path, default=Path("../data/processed/training_metrics.json")
    )
    parser.add_argument(
        "--artifact", type=Path, default=Path("../data/models/demand_forecast.joblib")
    )
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--test-fraction", type=float, default=0.2)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = prepare(
        demo_start=args.demo_start,
        dataset_path=args.dataset,
        metadata_path=args.metadata,
        artifact_path=args.artifact,
        days=args.days,
        seed=args.seed,
        test_fraction=args.test_fraction,
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
