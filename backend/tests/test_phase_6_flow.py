"""Golden Path integration through the public API, without ML training."""

from decimal import Decimal
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.infrastructure import ChargingStation
from app.models.prediction import SystemConfiguration
from app.simulation.clock import SimulationClock
from app.simulation.control import SimulationController, get_simulation_controller
from tests.test_charging_session_domain import (
    create_user_and_headers,
    create_vehicle,
    start_session,
)
from tests.test_simulation_api import INSTANT


@pytest.fixture
async def control() -> SimulationController:
    value = SimulationController(SimulationClock(initial_instant=INSTANT))

    async def override() -> SimulationController:
        return value

    app.dependency_overrides[get_simulation_controller] = override
    yield value
    await value.shutdown()
    app.dependency_overrides.pop(get_simulation_controller, None)


@pytest.mark.anyio
async def test_phase_6_golden_path(
    client: AsyncClient, db_session: Session, control: SimulationController,
) -> None:
    station = (await client.post(
        "/api/v1/stations",
        json={"name": "Golden Path", "grid_limit_kw": 60, "station_peak_solar_kw": 0},
    )).json()
    db_session.add(SystemConfiguration(
        simulation_speed=60,
        grid_emission_factor_kg_per_kwh=0.4,
        high_demand_threshold=0.85,
        medium_peak_threshold=0.7,
        high_peak_threshold=0.9,
    ))
    db_session.commit()
    for index in range(4):
        suffix = f"golden-{index}"
        user, headers = await create_user_and_headers(client, suffix=suffix)
        vehicle = await create_vehicle(client, headers, suffix=suffix, max_power_kw=20)
        charger = (await client.post("/api/v1/chargers", json={
            "station_id": station["id"], "name": f"CH-0{index + 1}",
            "code": f"GOLDEN-0{index + 1}", "max_power_kw": 22,
        })).json()
        if index == 3:
            fourth = (user, headers, vehicle, charger)
            break
        started = await start_session(client, headers, vehicle, charger)
        assert started.status_code == 201

    assert (await client.post("/api/v1/simulation/start")).status_code == 200
    assert (await client.post("/api/v1/simulation/ticks")).json()["energy_readings_created"] == 3
    first_readings = (await client.get("/api/v1/energy/history", params={
        "station_id": station["id"],
    })).json()
    assert len(first_readings) == 3
    assert all(
        row["allocated_power_kw"] == 20 and row["grid_power_kw"] == 20
        for row in first_readings
    )
    alerts = (await client.get("/api/v1/alerts", params={"station_id": station["id"]})).json()
    assert len([item for item in alerts if item["type"] == "HIGH_DEMAND"]) == 1

    user, headers, vehicle, charger = fourth
    started = await start_session(client, headers, vehicle, charger)
    assert started.status_code == 201
    fourth_id = started.json()["id"]
    assert (await client.post("/api/v1/simulation/ticks")).json()["energy_readings_created"] == 4
    redistributed = (await client.get("/api/v1/energy/history", params={
        "station_id": station["id"],
    })).json()[3:]
    assert len(redistributed) == 4
    assert all(row["allocated_power_kw"] == pytest.approx(15) for row in redistributed)
    assert sum(row["grid_power_kw"] for row in redistributed) == pytest.approx(60)
    db_session.rollback()
    station_model = db_session.get(ChargingStation, UUID(station["id"]))
    assert station_model is not None
    station_model.station_peak_solar_kw = 20
    db_session.commit()
    assert (await client.post("/api/v1/simulation/ticks")).json()["energy_readings_created"] == 4
    readings = (await client.get("/api/v1/energy/history", params={
        "station_id": station["id"],
    })).json()
    latest = readings[7:]
    assert len(latest) == 4
    assert sum(row["allocated_power_kw"] for row in latest) == pytest.approx(80, abs=0.01)
    assert sum(row["solar_power_kw"] for row in latest) == pytest.approx(20, abs=0.01)
    assert sum(row["grid_power_kw"] for row in latest) == pytest.approx(60, abs=0.01)
    assert all(row["allocated_power_kw"] <= 20 for row in latest)

    before = (await client.get("/api/v1/analytics/dashboard", params={
        "station_id": station["id"],
    })).json()
    assert before["session_count"] == 4
    assert before["completed_session_count"] == 0
    assert before["billed_total"] == "0.00"
    assert before["energy_consumed_kwh"] == pytest.approx(200 / 60, abs=0.0001)
    assert before["solar_energy_kwh"] == pytest.approx(20 / 60, abs=0.001)
    assert before["grid_energy_kwh"] == pytest.approx(180 / 60, abs=0.001)

    user_current = (await client.get("/api/v1/user/dashboard", headers=headers)).json()
    assert user_current["current_session"]["id"] == fourth_id
    assert user_current["current_session"]["energy_consumed_kwh"] > 0
    stopped = await client.post(f"/api/v1/sessions/{fourth_id}/stop", headers=headers)
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "COMPLETED"
    assert (await client.get(f"/api/v1/chargers/{charger['id']}")).json()["status"] == "AVAILABLE"
    invoices = (await client.get("/api/v1/billing/invoices", headers=headers)).json()
    assert len(invoices) == 1
    assert invoices[0]["status"] == "CLOSED"
    assert Decimal(invoices[0]["total"]) == Decimal("0.54")
    user_after = (await client.get("/api/v1/user/dashboard", headers=headers)).json()
    assert user_after["current_session"] is None
    assert user_after["session_history"][0]["invoice_total"] == invoices[0]["total"]
    assert user_after["invoices"][0]["id"] == invoices[0]["id"]
    after = (await client.get("/api/v1/analytics/dashboard", params={
        "station_id": station["id"],
    })).json()
    assert after["completed_session_count"] == 1
    assert after["billed_total"] == invoices[0]["total"]
    sustainability = (await client.get("/api/v1/analytics/sustainability", params={
        "station_id": station["id"],
    })).json()
    assert sustainability["avoided_co2_kg"] == pytest.approx(20 / 60 * 0.4, abs=0.001)
    assert sustainability["solar_percentage"] == pytest.approx(10, abs=0.01)
    assert len((await client.get("/api/v1/alerts", params={
        "station_id": station["id"],
    })).json()) >= 2
