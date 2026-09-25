from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.demo_seed import seed
from app.ml.demo_prepare import prepare_inference_history
from app.models.billing import Tariff
from app.models.energy import ChargingSession, EnergyReading, SolarReading
from app.models.infrastructure import Charger, ChargingStation
from app.models.prediction import SystemConfiguration
from app.models.user import User
from app.models.vehicle import Vehicle
from app.simulation.control import SimulationController


def test_demo_seed_is_idempotent(db_session: Session) -> None:
    seed(db_session, "admin-secret", "user-secret")
    db_session.commit()
    seed(db_session, "admin-secret", "user-secret")
    db_session.commit()
    for model, expected in ((User, 5), (Vehicle, 4), (ChargingStation, 1),
                            (Charger, 4), (Tariff, 1), (SystemConfiguration, 1)):
        assert db_session.scalar(select(func.count()).select_from(model)) == expected
    assert db_session.scalar(select(ChargingStation)).grid_limit_kw == 60
    assert db_session.scalar(select(Tariff)).is_active


def test_demo_seed_requires_passwords(db_session: Session) -> None:
    with pytest.raises(ValueError, match="at least 8"):
        seed(db_session, "short", "user-secret")


def test_ml_demo_history_is_causal_deterministic_and_idempotent(db_session: Session) -> None:
    seed(db_session, "admin-secret", "user-secret")
    demo_start = datetime(2026, 9, 18, 11, 58, tzinfo=UTC)

    first = prepare_inference_history(db_session, demo_start)
    db_session.commit()
    second = prepare_inference_history(db_session, demo_start)
    db_session.commit()

    assert first == second == datetime(2026, 9, 11, 12, 1, tzinfo=UTC)
    assert first < demo_start
    assert db_session.scalar(select(func.count()).select_from(EnergyReading)) == 4
    assert db_session.scalar(select(func.count()).select_from(SolarReading)) == 1
    assert db_session.scalar(select(func.count()).select_from(ChargingSession)) == 4
    assert db_session.scalar(select(func.sum(EnergyReading.allocated_power_kw))) == 80


def test_demo_clock_is_opt_in_and_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as env:
        env.setenv("APP_ENV", "demo")
        env.setenv("DEMO_SIMULATION_START_UTC", "2026-09-18T11:58:00Z")
        get_settings.cache_clear()
        assert SimulationController().clock.current_instant == datetime(
            2026, 9, 18, 11, 58, tzinfo=UTC
        )
        env.setenv("APP_ENV", "production")
        env.setenv("JWT_SECRET_KEY", "a" * 32)
        with pytest.raises(ValueError, match="demo or test"):
            Settings()
        env.setenv("APP_ENV", "demo")
        env.setenv("DEMO_SIMULATION_START_UTC", "2026-09-18T11:58:00")
        with pytest.raises(ValueError, match="explicit UTC"):
            Settings()
    get_settings.cache_clear()
    elapsed = SimulationController().clock.current_instant - datetime.now(UTC)
    assert abs(elapsed.total_seconds()) < 5


def test_demo_clock_is_rejected_in_regular_development(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DEMO_SIMULATION_START_UTC", "2026-09-18T11:58:00Z")

    with pytest.raises(ValueError, match="demo or test"):
        Settings()
