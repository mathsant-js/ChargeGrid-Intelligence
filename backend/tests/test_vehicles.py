from uuid import uuid4

import pytest
from httpx import AsyncClient


async def create_user(client: AsyncClient) -> str:
    response = await client.post(
        "/api/v1/users",
        json={"name": "Owner", "email": "owner@example.com", "password": "password-123"},
    )
    return str(response.json()["id"])


@pytest.mark.anyio
async def test_vehicle_crud(client: AsyncClient) -> None:
    user_id = await create_user(client)
    response = await client.post(
        "/api/v1/vehicles",
        json={
            "user_id": user_id,
            "name": "Daily EV",
            "brand": "GoodCar",
            "model": "E1",
            "license_plate": "EV-2026",
            "max_charge_power_kw": 22,
        },
    )

    assert response.status_code == 201
    vehicle = response.json()
    assert vehicle["user_id"] == user_id
    assert vehicle["max_charge_power_kw"] == 22

    update = await client.patch(
        f"/api/v1/vehicles/{vehicle['id']}",
        json={"name": "Weekend EV", "max_charge_power_kw": 11},
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Weekend EV"
    assert (await client.get("/api/v1/vehicles")).json() == [update.json()]

    assert (await client.delete(f"/api/v1/vehicles/{vehicle['id']}")).status_code == 204
    assert (await client.get(f"/api/v1/vehicles/{vehicle['id']}")).status_code == 404


@pytest.mark.anyio
async def test_vehicle_validates_owner_and_positive_power(client: AsyncClient) -> None:
    payload: dict[str, object] = {
        "user_id": str(uuid4()),
        "name": "EV",
        "brand": "Brand",
        "model": "Model",
        "license_plate": "ABC-1234",
        "max_charge_power_kw": 22,
    }
    assert (await client.post("/api/v1/vehicles", json=payload)).status_code == 404

    payload["user_id"] = await create_user(client)
    payload["max_charge_power_kw"] = 0
    assert (await client.post("/api/v1/vehicles", json=payload)).status_code == 422
