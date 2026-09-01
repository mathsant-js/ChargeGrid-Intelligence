from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_station_and_charger_crud(client: AsyncClient) -> None:
    station_response = await client.post(
        "/api/v1/stations",
        json={"name": "FIAP Station", "description": "Campus", "grid_limit_kw": 60},
    )
    assert station_response.status_code == 201
    station = station_response.json()
    assert station["is_active"] is True

    charger_response = await client.post(
        "/api/v1/chargers",
        json={
            "station_id": station["id"],
            "name": "Charger 1",
            "code": "CH-01",
            "max_power_kw": 22,
        },
    )
    assert charger_response.status_code == 201
    charger = charger_response.json()
    assert charger["status"] == "AVAILABLE"

    station_update = await client.patch(
        f"/api/v1/stations/{station['id']}",
        json={"grid_limit_kw": 55, "description": None},
    )
    charger_update = await client.patch(
        f"/api/v1/chargers/{charger['id']}",
        json={"status": "UNAVAILABLE", "is_active": False},
    )
    assert station_update.status_code == 200
    assert station_update.json()["description"] is None
    assert station_update.json()["grid_limit_kw"] == 55
    assert charger_update.status_code == 200
    assert charger_update.json()["status"] == "UNAVAILABLE"
    assert charger_update.json()["is_active"] is False

    assert (await client.get("/api/v1/stations")).json() == [station_update.json()]
    assert (await client.get("/api/v1/chargers")).json() == [charger_update.json()]
    assert (await client.get(f"/api/v1/stations/{station['id']}")).status_code == 200
    assert (await client.get(f"/api/v1/chargers/{charger['id']}")).status_code == 200


@pytest.mark.anyio
async def test_infrastructure_validates_references_enums_and_power(client: AsyncClient) -> None:
    station = await client.post("/api/v1/stations", json={"name": "Station", "grid_limit_kw": 60})
    station_id = station.json()["id"]

    invalid_station = {
        "station_id": str(uuid4()),
        "name": "Charger",
        "code": "CH-X",
        "max_power_kw": 22,
    }
    assert (await client.post("/api/v1/chargers", json=invalid_station)).status_code == 404

    invalid_status = {**invalid_station, "station_id": station_id, "status": "BROKEN"}
    assert (await client.post("/api/v1/chargers", json=invalid_status)).status_code == 422

    invalid_power = {**invalid_station, "station_id": station_id, "max_power_kw": -1}
    assert (await client.post("/api/v1/chargers", json=invalid_power)).status_code == 422
    assert (
        await client.post("/api/v1/stations", json={"name": "Invalid", "grid_limit_kw": 0})
    ).status_code == 422

    charger = await client.post(
        "/api/v1/chargers",
        json={
            "station_id": station_id,
            "name": "Valid charger",
            "code": "CH-VALID",
            "max_power_kw": 22,
        },
    )
    missing_reference = await client.patch(
        f"/api/v1/chargers/{charger.json()['id']}", json={"station_id": str(uuid4())}
    )
    assert missing_reference.status_code == 404


@pytest.mark.anyio
async def test_infrastructure_requires_identifiers_and_rejects_null_updates(
    client: AsyncClient,
) -> None:
    blank_station_name = await client.post(
        "/api/v1/stations", json={"name": "   ", "grid_limit_kw": 60}
    )
    station = (
        await client.post("/api/v1/stations", json={"name": "Station", "grid_limit_kw": 60})
    ).json()
    missing_code = await client.post(
        "/api/v1/chargers",
        json={"station_id": station["id"], "name": "Charger", "max_power_kw": 22},
    )
    charger = (
        await client.post(
            "/api/v1/chargers",
            json={
                "station_id": station["id"],
                "name": "Charger",
                "code": "CH-1",
                "max_power_kw": 22,
            },
        )
    ).json()

    assert blank_station_name.status_code == 422
    assert missing_code.status_code == 422
    assert (
        await client.patch(f"/api/v1/stations/{station['id']}", json={"is_active": None})
    ).status_code == 422
    assert (
        await client.patch(f"/api/v1/chargers/{charger['id']}", json={"status": None})
    ).status_code == 422
    assert (await client.get(f"/api/v1/stations/{uuid4()}")).status_code == 404
    assert (await client.get(f"/api/v1/chargers/{uuid4()}")).status_code == 404
