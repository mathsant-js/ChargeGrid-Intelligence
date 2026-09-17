"""Administrative simulation lifecycle and read API integration."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.main import app
from app.models.energy import ChargingSession, ChargingSessionStatus, EnergyReading, SolarReading
from app.models.infrastructure import Charger, ChargingStation
from app.models.prediction import SystemConfiguration
from app.models.user import User, UserRole
from app.models.vehicle import Vehicle
from app.services.energy_allocation import PowerBreakdown, SessionPowerRequest
from app.simulation.clock import SimulationClock
from app.simulation.control import SimulationController, get_simulation_controller

INSTANT = datetime(2026, 9, 16, 12, tzinfo=UTC)


@pytest.fixture
def control() -> SimulationController:
    value = SimulationController(SimulationClock(initial_instant=INSTANT))

    async def override() -> SimulationController:
        return value

    app.dependency_overrides[get_simulation_controller] = override
    yield value
    app.dependency_overrides.pop(get_simulation_controller, None)


def seed_charging_session(
    db: Session,
    *,
    station: ChargingStation | None = None,
    grid_limit_kw: float = 20,
    solar_peak_kw: float = 10,
    requested_power_kw: float = 11,
    max_power_kw: float = 11,
) -> tuple[UUID, UUID]:
    marker = str(uuid4())
    user = User(name="Driver", email=f"driver-{marker}@example.com", password_hash="hash")
    station = station or ChargingStation(
        name="Solar station", grid_limit_kw=grid_limit_kw, station_peak_solar_kw=solar_peak_kw
    )
    db.add_all([user, station])
    db.flush()
    charger = Charger(station_id=station.id, name="C1", code=marker, max_power_kw=max_power_kw)
    vehicle = Vehicle(
        user_id=user.id,
        name="EV",
        brand="B",
        model="M",
        license_plate=marker[:8],
        max_charge_power_kw=max_power_kw,
    )
    db.add_all([charger, vehicle])
    db.flush()
    charging = ChargingSession(
        user_id=user.id,
        vehicle_id=vehicle.id,
        charger_id=charger.id,
        status=ChargingSessionStatus.CHARGING,
        requested_power_kw=requested_power_kw,
        allocated_power_kw=0,
        energy_consumed_kwh=0,
        solar_energy_kwh=0,
        grid_energy_kwh=0,
        tariff_per_kwh=Decimal("1"),
        total_cost=Decimal("0"),
    )
    db.add(charging)
    db.commit()
    return station.id, charging.id


@pytest.mark.anyio
async def test_simulation_authentication_and_authorization(
    client: AsyncClient, db_session: Session, control: SimulationController
) -> None:
    user = User(
        name="Regular",
        email="regular-simulation@example.com",
        password_hash="hash",
        role=UserRole.USER,
    )
    db_session.add(user)
    db_session.commit()
    paths = [
        ("get", "/status"),
        ("post", "/start"),
        ("post", "/stop"),
        ("post", "/reset"),
        ("post", "/ticks"),
    ]
    for method, suffix in paths:
        path = f"/api/v1/simulation{suffix}"
        for header in (None, "Bearer invalid"):
            headers = {"Authorization": header} if header else {"Authorization": ""}
            response = await client.request(method, path, headers=headers)
            assert response.status_code == 401
        response = await client.request(
            method, path, headers={"Authorization": f"Bearer {create_access_token(user.id)}"}
        )
        assert response.status_code == 403
    assert control.clock.current_instant == INSTANT


@pytest.mark.anyio
async def test_simulation_lifecycle_readings_filters_and_reset(
    client: AsyncClient,
    db_session: Session,
    control: SimulationController,
    caplog: pytest.LogCaptureFixture,
) -> None:
    station_id, session_id = seed_charging_session(db_session)
    db_session.add(
        SystemConfiguration(
            simulation_speed=120,
            grid_emission_factor_kg_per_kwh=0.4,
            high_demand_threshold=0.8,
            medium_peak_threshold=0.5,
            high_peak_threshold=0.8,
        )
    )
    db_session.commit()
    base = "/api/v1/simulation"
    initial = (await client.get(f"{base}/status")).json()
    assert initial == {
        "state": "STOPPED",
        "current_instant": INSTANT.isoformat().replace("+00:00", "Z"),
        "tick_duration_seconds": 60,
        "simulation_speed": 60,
        "last_tick": None,
    }
    assert (await client.post(f"{base}/ticks")).status_code == 409
    with caplog.at_level("INFO"):
        started = await client.post(f"{base}/start")
        repeated_start = await client.post(f"{base}/start")
        assert started.status_code == repeated_start.status_code == 200
        assert started.json() == repeated_start.json()
        assert started.json()["state"] == "RUNNING"
        assert started.json()["simulation_speed"] == 120
        assert started.json()["tick_duration_seconds"] == 120
        assert (await client.post(f"{base}/reset")).status_code == 409
        tick = await client.post(f"{base}/ticks")
        assert tick.status_code == 200
        assert tick.json()["timestamp"] == initial["current_instant"]
        assert tick.json()["stations_processed"] == 1
        assert tick.json()["energy_readings_created"] == 1
        current = INSTANT + timedelta(minutes=2)
        assert datetime.fromisoformat(tick.json()["current_instant"]) == current
        status = (await client.get(f"{base}/status")).json()
        assert datetime.fromisoformat(status["current_instant"]) == current
        assert datetime.fromisoformat(status["last_tick"]) == INSTANT
        stopped = await client.post(f"{base}/stop")
        repeated_stop = await client.post(f"{base}/stop")
        assert stopped.status_code == repeated_stop.status_code == 200
        assert stopped.json() == repeated_stop.json()
        assert stopped.json()["state"] == "STOPPED"
        reset = await client.post(f"{base}/reset")
        assert reset.status_code == 200
        assert reset.json()["last_tick"] is None
        assert datetime.fromisoformat(reset.json()["current_instant"]) >= current
    assert {record.message for record in caplog.records} >= {
        "simulation_started",
        "simulation_stopped",
        "simulation_reset",
        "simulation_tick_completed",
    }
    db_session.rollback()
    assert db_session.scalar(select(func.count()).select_from(EnergyReading)) == 1
    assert db_session.scalar(select(func.count()).select_from(SolarReading)) == 1
    session = db_session.get(ChargingSession, session_id)
    assert session is not None
    assert session.energy_consumed_kwh == pytest.approx(11 * 2 / 60)
    for resource in ("energy", "solar"):
        current_response = await client.get(
            f"/api/v1/{resource}/current", params={"station_id": str(station_id)}
        )
        assert current_response.status_code == 200
        assert datetime.fromisoformat(current_response.json()["timestamp"]) == INSTANT
        history = await client.get(
            f"/api/v1/{resource}/history",
            params={
                "station_id": str(station_id),
                "from": INSTANT.isoformat(),
                "to": INSTANT.isoformat(),
            },
        )
        assert history.status_code == 200
        assert len(history.json()) == 1
        excluded = await client.get(
            f"/api/v1/{resource}/history",
            params={
                "station_id": str(uuid4()),
                "from": INSTANT.isoformat(),
                "to": INSTANT.isoformat(),
            },
        )
        assert excluded.json() == []
        after = await client.get(
            f"/api/v1/{resource}/history",
            params={"from": (INSTANT + timedelta(seconds=1)).isoformat()},
        )
        assert after.json() == []
    energy = (await client.get("/api/v1/energy/current")).json()
    assert energy["allocated_power_kw"] == 11
    assert energy["solar_power_kw"] == 10
    assert energy["grid_power_kw"] == 1
    assert (await client.get("/api/v1/solar/current")).json()["available_power_kw"] == 10


@pytest.mark.anyio
async def test_tick_allocates_each_station_and_records_energy_parts(
    client: AsyncClient, db_session: Session, control: SimulationController
) -> None:
    station_a_id, first_id = seed_charging_session(
        db_session,
        grid_limit_kw=10,
        solar_peak_kw=6,
        requested_power_kw=12,
        max_power_kw=12,
    )
    station_a = db_session.get(ChargingStation, station_a_id)
    assert station_a is not None
    _, second_id = seed_charging_session(
        db_session, station=station_a, requested_power_kw=12, max_power_kw=12
    )
    station_b_id, third_id = seed_charging_session(
        db_session,
        grid_limit_kw=5,
        solar_peak_kw=0,
        requested_power_kw=9,
        max_power_kw=9,
    )

    assert (await client.post("/api/v1/simulation/start")).status_code == 200
    response = await client.post("/api/v1/simulation/ticks")
    assert response.status_code == 200
    assert response.json()["stations_processed"] == 2
    assert response.json()["energy_readings_created"] == 3
    assert control.clock.current_instant == INSTANT + timedelta(minutes=1)

    db_session.rollback()
    readings = {
        reading.session_id: reading for reading in db_session.scalars(select(EnergyReading)).all()
    }
    assert set(readings) == {first_id, second_id, third_id}
    expected = {
        first_id: (12, 8, 3, 5),
        second_id: (12, 8, 3, 5),
        third_id: (9, 5, 0, 5),
    }
    for session_id, (requested, allocated, solar, grid) in expected.items():
        reading = readings[session_id]
        session = db_session.get(ChargingSession, session_id)
        assert session is not None
        assert reading.requested_power_kw == requested
        assert reading.allocated_power_kw == pytest.approx(allocated)
        assert reading.solar_power_kw == pytest.approx(solar)
        assert reading.grid_power_kw == pytest.approx(grid)
        assert reading.interval_energy_kwh == pytest.approx(allocated / 60)
        assert reading.solar_energy_kwh == pytest.approx(solar / 60)
        assert reading.grid_energy_kwh == pytest.approx(grid / 60)
        assert reading.interval_energy_kwh == pytest.approx(
            reading.solar_energy_kwh + reading.grid_energy_kwh
        )
        assert session.allocated_power_kw == pytest.approx(allocated)
        assert session.energy_consumed_kwh == pytest.approx(reading.interval_energy_kwh)
        assert session.solar_energy_kwh == pytest.approx(reading.solar_energy_kwh)
        assert session.grid_energy_kwh == pytest.approx(reading.grid_energy_kwh)

    solar_readings = db_session.scalars(select(SolarReading)).all()
    assert {row.station_id: row.available_power_kw for row in solar_readings} == {
        station_a_id: 6,
        station_b_id: 0,
    }
    assert sum(readings[id].grid_power_kw for id in (first_id, second_id)) == pytest.approx(10)
    assert readings[third_id].grid_power_kw == pytest.approx(5)


@pytest.mark.anyio
async def test_tick_rolls_back_all_stations_for_invalid_injected_resolver(
    client: AsyncClient,
    db_session: Session,
    control: SimulationController,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first_station, first_session = seed_charging_session(db_session)
    second_station, second_session = seed_charging_session(db_session)
    failing_station = max(first_station, second_station)

    class InvalidResolver:
        def resolve(
            self,
            *,
            station_id: UUID,
            grid_limit_kw: float,
            solar_available_kw: float,
            sessions: Sequence[SessionPowerRequest],
        ) -> dict[UUID, PowerBreakdown]:
            if station_id == failing_station:
                return {
                    item.session_id: PowerBreakdown(11, 0, grid_limit_kw + 1) for item in sessions
                }
            return {item.session_id: PowerBreakdown(11, 10, 1) for item in sessions}

    monkeypatch.setattr("app.simulation.control.EqualSharePowerResolver", InvalidResolver)
    assert (await client.post("/api/v1/simulation/start")).status_code == 200
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers=dict(client.headers)
    ) as safe_client:
        response = await safe_client.post("/api/v1/simulation/ticks")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert control.clock.current_instant == INSTANT
    assert control.last_tick is None
    db_session.rollback()
    assert db_session.scalar(select(func.count()).select_from(EnergyReading)) == 0
    assert db_session.scalar(select(func.count()).select_from(SolarReading)) == 0
    for session_id in (first_session, second_session):
        session = db_session.get(ChargingSession, session_id)
        assert session is not None
        db_session.refresh(session)
        assert session.allocated_power_kw == 0
        assert session.energy_consumed_kwh == 0
        assert session.solar_energy_kwh == 0
        assert session.grid_energy_kwh == 0


@pytest.mark.anyio
async def test_failed_tick_keeps_clock_and_hides_internal_error(
    client: AsyncClient,
    control: SimulationController,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_tick(*args: object, **kwargs: object) -> None:
        raise RuntimeError("private simulator traceback marker")

    monkeypatch.setattr("app.simulation.control.execute_tick", fail_tick)
    assert (await client.post("/api/v1/simulation/start")).status_code == 200
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    with caplog.at_level("ERROR"):
        async with AsyncClient(
            transport=transport, base_url="http://test", headers=dict(client.headers)
        ) as safe_client:
            response = await safe_client.post("/api/v1/simulation/ticks")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "private simulator" not in response.text
    assert control.clock.current_instant == INSTANT
    assert control.last_tick is None
    assert any(record.message == "simulation_control_tick_failed" for record in caplog.records)


@pytest.mark.anyio
async def test_simulation_openapi_contract(
    client: AsyncClient, control: SimulationController
) -> None:
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for suffix, method, schema in (
        ("status", "get", "SimulationStatusResponse"),
        ("start", "post", "SimulationStatusResponse"),
        ("stop", "post", "SimulationStatusResponse"),
        ("reset", "post", "SimulationStatusResponse"),
        ("ticks", "post", "SimulationTickResponse"),
    ):
        operation = paths[f"/api/v1/simulation/{suffix}"][method]
        assert operation["security"] == [{"HTTPBearer": []}]
        assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
            "$ref": f"#/components/schemas/{schema}"
        }
        assert {"401", "403"} <= operation["responses"].keys()
        if suffix in ("reset", "ticks"):
            assert "409" in operation["responses"]
