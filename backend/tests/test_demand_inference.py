from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.alert import Alert, AlertType
from app.models.energy import ChargingSession, ChargingSessionStatus, EnergyReading, SolarReading
from app.models.infrastructure import Charger, ChargerStatus, ChargingStation
from app.models.prediction import DemandPrediction, DemandRiskLevel, SystemConfiguration
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle
from app.services.demand_predictions import (
    build_inference_features,
    classify_risk,
    run_demand_prediction,
)


class FixedModel:
    def __init__(self, prediction: float) -> None:
        self.prediction = prediction
        self.metadata = SimpleNamespace(model_version="test-model")

    def predict(self, rows: object) -> list[float]:
        return [self.prediction]


def seed_inference_context(db: Session) -> tuple[ChargingStation, ChargingSession, datetime]:
    instant = datetime.now(UTC).replace(microsecond=0)
    admin = db.scalar(select(User).limit(1))
    if admin is None:
        admin = User(
            name="Inference admin",
            email="inference-admin@example.com",
            password_hash=hash_password("password-123"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.flush()
    station = ChargingStation(
        name="Inference station", grid_limit_kw=60, station_peak_solar_kw=20, is_active=True
    )
    db.add(station)
    db.flush()
    charger = Charger(
        station_id=station.id,
        name="Inference charger",
        code=f"INF-{station.id}",
        max_power_kw=22,
        status=ChargerStatus.CHARGING,
        is_active=True,
    )
    vehicle = Vehicle(
        user_id=admin.id,
        name="Inference EV",
        brand="Test",
        model="EV",
        license_plate=f"INF-{str(station.id)[:8]}",
        max_charge_power_kw=20,
    )
    db.add_all([charger, vehicle])
    db.flush()
    session = ChargingSession(
        user_id=admin.id,
        vehicle_id=vehicle.id,
        charger_id=charger.id,
        status=ChargingSessionStatus.CHARGING,
        started_at=instant - timedelta(days=8),
        requested_power_kw=20,
        allocated_power_kw=12,
        tariff_per_kwh=Decimal("0.9200"),
    )
    db.add(session)
    db.flush()
    for timestamp, demand in (
        (instant - timedelta(days=7), 10.0),
        (instant - timedelta(minutes=5), 12.0),
    ):
        db.add(
            EnergyReading(
                session_id=session.id,
                timestamp=timestamp,
                requested_power_kw=20,
                allocated_power_kw=demand,
                solar_power_kw=2,
                grid_power_kw=demand - 2,
                interval_energy_kwh=1,
                solar_energy_kwh=0.2,
                grid_energy_kwh=0.8,
            )
        )
    db.add(
        SolarReading(
            station_id=station.id,
            timestamp=instant - timedelta(minutes=1),
            available_power_kw=20,
        )
    )
    db.add(
        SystemConfiguration(
            simulation_speed=60,
            grid_emission_factor_kg_per_kwh=0.084,
            high_demand_threshold=0.85,
            medium_peak_threshold=0.7,
            high_peak_threshold=0.9,
        )
    )
    db.commit()
    return station, session, instant


@pytest.mark.parametrize(
    ("demand", "expected"),
    [
        (69.999, DemandRiskLevel.LOW),
        (70, DemandRiskLevel.MEDIUM),
        (89.999, DemandRiskLevel.MEDIUM),
        (90, DemandRiskLevel.HIGH),
    ],
)
def test_risk_classification_exact_boundaries(
    demand: float, expected: DemandRiskLevel
) -> None:
    assert (
        classify_risk(demand, 100, medium_threshold=0.7, high_threshold=0.9) == expected
    )


def test_inference_features_ignore_future_energy_and_solar_readings(
    db_session: Session,
) -> None:
    station, session, instant = seed_inference_context(db_session)
    future = instant + timedelta(minutes=5)
    db_session.add_all(
        [
            EnergyReading(
                session_id=session.id,
                timestamp=future,
                requested_power_kw=999,
                allocated_power_kw=999,
                solar_power_kw=999,
                grid_power_kw=0,
                interval_energy_kwh=1,
                solar_energy_kwh=1,
                grid_energy_kwh=0,
            ),
            SolarReading(station_id=station.id, timestamp=future, available_power_kw=999),
        ]
    )
    db_session.commit()

    features, solar_available = build_inference_features(db_session, station.id, instant)

    assert features.current_demand_kw == 12
    assert features.historical_avg_demand_kw == 10
    assert features.solar_available_kw == solar_available == 20


def test_inference_persists_sixty_minute_forecast_and_does_not_change_allocation(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    station, session, instant = seed_inference_context(db_session)
    monkeypatch.setattr(
        "app.services.demand_predictions.load_model_artifact", lambda _: FixedModel(72)
    )
    configuration = db_session.scalar(select(SystemConfiguration))
    assert configuration is not None

    prediction = run_demand_prediction(
        db_session,
        station=station,
        configuration=configuration,
        artifact_path=Path("unused.joblib"),
        generated_at=instant,
    )
    db_session.commit()

    persisted = db_session.get(DemandPrediction, prediction.id)
    assert persisted is not None
    assert persisted.prediction_horizon_minutes == 60
    assert persisted.capacity_kw == 80
    assert persisted.risk_level == DemandRiskLevel.HIGH
    assert persisted.model_version == "test-model"
    assert db_session.get(ChargingSession, session.id).allocated_power_kw == 12  # type: ignore[union-attr]


def test_peak_risk_alert_is_deduplicated_within_same_episode(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    station, _, instant = seed_inference_context(db_session)
    monkeypatch.setattr(
        "app.services.demand_predictions.load_model_artifact", lambda _: FixedModel(72)
    )
    configuration = db_session.scalar(select(SystemConfiguration))
    assert configuration is not None
    for offset in (0, 1):
        run_demand_prediction(
            db_session,
            station=station,
            configuration=configuration,
            artifact_path=Path("unused.joblib"),
            generated_at=instant + timedelta(minutes=offset),
        )
        db_session.commit()

    count = db_session.scalar(
        select(func.count(Alert.id)).where(
            Alert.station_id == station.id, Alert.type == AlertType.PEAK_RISK
        )
    )
    assert count == 1


@pytest.mark.anyio
async def test_run_endpoint_reports_missing_model(
    client: AsyncClient, db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    station, _, _ = seed_inference_context(db_session)
    monkeypatch.setattr(get_settings(), "demand_model_path", tmp_path / "missing.joblib")

    response = await client.post(
        "/api/v1/predictions/demand/run", json={"station_id": str(station.id)}
    )

    assert response.status_code == 503
    assert "not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_run_endpoint_rejects_insufficient_features(
    client: AsyncClient,
) -> None:
    station = await client.post(
        "/api/v1/stations", json={"name": "Empty prediction station", "grid_limit_kw": 60}
    )
    configuration = {
        "simulation_speed": 60,
        "grid_emission_factor_kg_per_kwh": 0.084,
        "high_demand_threshold": 0.85,
        "medium_peak_threshold": 0.7,
        "high_peak_threshold": 0.9,
    }
    created_configuration = await client.post(
        "/api/v1/system-configuration", json=configuration
    )
    assert created_configuration.status_code == 201

    response = await client.post(
        "/api/v1/predictions/demand/run", json={"station_id": station.json()["id"]}
    )

    assert response.status_code == 422
    assert "insufficient features" in response.json()["detail"]
