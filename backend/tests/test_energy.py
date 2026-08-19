from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.models.energy import ChargingSession, EnergyReading, SolarReading


async def create_session_dependencies(client: AsyncClient) -> tuple[dict[str, object], ...]:
    user = (
        await client.post(
            "/api/v1/users",
            json={"name": "Driver", "email": "driver@example.com", "password": "secret123"},
        )
    ).json()
    vehicle = (
        await client.post(
            "/api/v1/vehicles",
            json={
                "user_id": user["id"],
                "name": "Daily EV",
                "brand": "GoodCar",
                "model": "E1",
                "license_plate": "EV-2026",
                "max_charge_power_kw": 11,
            },
        )
    ).json()
    station = (
        await client.post("/api/v1/stations", json={"name": "Station", "grid_limit_kw": 60})
    ).json()
    charger = (
        await client.post(
            "/api/v1/chargers",
            json={
                "station_id": station["id"],
                "name": "Charger",
                "code": "CH-01",
                "max_power_kw": 22,
            },
        )
    ).json()
    return user, vehicle, station, charger


@pytest.mark.anyio
async def test_start_and_stop_charging_session(client: AsyncClient) -> None:
    user, vehicle, _, charger = await create_session_dependencies(client)
    start = await client.post(
        "/api/v1/sessions/start",
        json={
            "user_id": user["id"],
            "vehicle_id": vehicle["id"],
            "charger_id": charger["id"],
            "tariff_per_kwh": "0.9200",
        },
    )

    assert start.status_code == 201
    session = start.json()
    assert session["status"] == "CHARGING"
    assert session["requested_power_kw"] == 11
    assert session["allocated_power_kw"] == 0
    assert session["started_at"] is not None
    assert (await client.get(f"/api/v1/chargers/{charger['id']}")).json()["status"] == "CHARGING"

    duplicate = await client.post(
        "/api/v1/sessions/start",
        json={
            "user_id": user["id"],
            "vehicle_id": vehicle["id"],
            "charger_id": charger["id"],
            "tariff_per_kwh": "0.92",
        },
    )
    assert duplicate.status_code == 409

    stop = await client.post(f"/api/v1/sessions/{session['id']}/stop")
    assert stop.status_code == 200
    assert stop.json()["status"] == "COMPLETED"
    assert stop.json()["ended_at"] is not None
    assert (await client.get(f"/api/v1/chargers/{charger['id']}")).json()["status"] == "AVAILABLE"
    assert (await client.post(f"/api/v1/sessions/{session['id']}/stop")).status_code == 409


@pytest.mark.anyio
async def test_session_rejects_vehicle_from_another_user(client: AsyncClient) -> None:
    _, vehicle, _, charger = await create_session_dependencies(client)
    other_user = (
        await client.post(
            "/api/v1/users",
            json={"name": "Other", "email": "other@example.com", "password": "secret123"},
        )
    ).json()
    response = await client.post(
        "/api/v1/sessions/start",
        json={
            "user_id": other_user["id"],
            "vehicle_id": vehicle["id"],
            "charger_id": charger["id"],
            "tariff_per_kwh": "0.92",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Vehicle does not belong to user"


@pytest.mark.anyio
async def test_energy_and_solar_current_history_filters(
    client: AsyncClient, db_session: Session
) -> None:
    user, vehicle, station, charger = await create_session_dependencies(client)
    session_response = await client.post(
        "/api/v1/sessions/start",
        json={
            "user_id": user["id"],
            "vehicle_id": vehicle["id"],
            "charger_id": charger["id"],
            "tariff_per_kwh": "0.92",
        },
    )
    session = db_session.get(ChargingSession, UUID(session_response.json()["id"]))
    assert session is not None
    earlier = datetime(2026, 8, 18, 12, tzinfo=UTC)
    later = earlier + timedelta(minutes=5)
    db_session.add_all(
        [
            EnergyReading(
                session_id=session.id,
                timestamp=earlier,
                requested_power_kw=11,
                allocated_power_kw=10,
                solar_power_kw=4,
                grid_power_kw=6,
                interval_energy_kwh=0.5,
                solar_energy_kwh=0.2,
                grid_energy_kwh=0.3,
            ),
            EnergyReading(
                session_id=session.id,
                timestamp=later,
                requested_power_kw=11,
                allocated_power_kw=8,
                solar_power_kw=3,
                grid_power_kw=5,
                interval_energy_kwh=0.4,
                solar_energy_kwh=0.15,
                grid_energy_kwh=0.25,
            ),
            SolarReading(
                station_id=UUID(str(station["id"])), timestamp=earlier, available_power_kw=12
            ),
            SolarReading(
                station_id=UUID(str(station["id"])), timestamp=later, available_power_kw=9
            ),
        ]
    )
    db_session.commit()

    energy_current = await client.get(
        "/api/v1/energy/current", params={"station_id": station["id"]}
    )
    assert energy_current.status_code == 200
    assert energy_current.json()["allocated_power_kw"] == 8
    energy_history = await client.get(
        "/api/v1/energy/history",
        params={"station_id": station["id"], "from": later.isoformat()},
    )
    assert [reading["allocated_power_kw"] for reading in energy_history.json()] == [8]

    solar_current = await client.get("/api/v1/solar/current", params={"station_id": station["id"]})
    assert solar_current.status_code == 200
    assert solar_current.json()["available_power_kw"] == 9
    solar_history = await client.get("/api/v1/solar/history", params={"to": earlier.isoformat()})
    assert [reading["available_power_kw"] for reading in solar_history.json()] == [12]
