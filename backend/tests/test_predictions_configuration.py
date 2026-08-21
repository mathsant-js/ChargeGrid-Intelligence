from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient


async def create_station(
    client: AsyncClient, name: str = "Prediction station"
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/stations",
        json={"name": name, "grid_limit_kw": 60},
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.anyio
async def test_create_and_get_latest_demand_prediction(client: AsyncClient) -> None:
    station = await create_station(client)
    target = datetime.now(UTC) + timedelta(minutes=60)
    created = await client.post(
        "/api/v1/predictions/demand",
        json={
            "station_id": station["id"],
            "prediction_for": target.isoformat(),
            "predicted_demand_kw": 58.2,
            "capacity_kw": 60,
            "risk_level": "HIGH",
            "model_version": "baseline-1",
        },
    )
    assert created.status_code == 201
    assert created.json()["prediction_horizon_minutes"] == 60

    latest = await client.get(
        "/api/v1/predictions/demand", params={"station_id": station["id"]}
    )
    assert latest.status_code == 200
    assert latest.json()["id"] == created.json()["id"]
    assert latest.json()["risk_level"] == "HIGH"

    missing = await client.get(
        "/api/v1/predictions/demand",
        params={"station_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert missing.status_code == 404


@pytest.mark.anyio
async def test_prediction_validation_and_station_fk(client: AsyncClient) -> None:
    payload = {
        "station_id": "00000000-0000-0000-0000-000000000000",
        "prediction_for": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        "predicted_demand_kw": -1,
        "capacity_kw": 0,
        "risk_level": "INVALID",
        "model_version": "v1",
    }
    assert (await client.post("/api/v1/predictions/demand", json=payload)).status_code == 422

    payload.update(predicted_demand_kw=10, capacity_kw=60, risk_level="LOW")
    assert (await client.post("/api/v1/predictions/demand", json=payload)).status_code == 404


@pytest.mark.anyio
async def test_system_configuration_singleton_crud_and_thresholds(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/system-configuration")).status_code == 404
    payload = {
        "simulation_speed": 60,
        "grid_emission_factor_kg_per_kwh": 0.084,
        "high_demand_threshold": 0.8,
        "medium_peak_threshold": 0.7,
        "high_peak_threshold": 0.9,
    }
    created = await client.post("/api/v1/system-configuration", json=payload)
    assert created.status_code == 201
    assert created.json()["simulation_speed"] == 60
    assert (await client.post("/api/v1/system-configuration", json=payload)).status_code == 409

    updated = await client.patch(
        "/api/v1/system-configuration",
        json={"simulation_speed": 120, "high_peak_threshold": 0.95},
    )
    assert updated.status_code == 200
    assert updated.json()["simulation_speed"] == 120
    assert updated.json()["high_peak_threshold"] == 0.95

    invalid = await client.patch(
        "/api/v1/system-configuration", json={"medium_peak_threshold": 0.99}
    )
    assert invalid.status_code == 422
    assert (await client.get("/api/v1/system-configuration")).json()["simulation_speed"] == 120
