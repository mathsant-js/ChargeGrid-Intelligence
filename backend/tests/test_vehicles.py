from uuid import uuid4

import pytest
from httpx import AsyncClient


async def create_user(client: AsyncClient) -> str:
    response = await client.post(
        "/api/v1/users",
        json={"name": "Owner", "email": "owner@example.com", "password": "password-123"},
    )
    return str(response.json()["id"])


async def authenticate_owner(client: AsyncClient) -> str:
    user_id = await create_user(client)
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@example.com", "password": "password-123"},
    )
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    return user_id


@pytest.mark.anyio
async def test_vehicle_crud(client: AsyncClient) -> None:
    user_id = await authenticate_owner(client)
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
async def test_vehicle_ignores_body_owner_and_validates_positive_power(
    client: AsyncClient,
) -> None:
    user_id = await authenticate_owner(client)
    payload: dict[str, object] = {
        "user_id": str(uuid4()),
        "name": "EV",
        "brand": "Brand",
        "model": "Model",
        "license_plate": "ABC-1234",
        "max_charge_power_kw": 22,
    }
    created = await client.post("/api/v1/vehicles", json=payload)
    assert created.status_code == 201
    assert created.json()["user_id"] == user_id

    payload["license_plate"] = "ABC-9999"
    payload["max_charge_power_kw"] = 0
    assert (await client.post("/api/v1/vehicles", json=payload)).status_code == 422


@pytest.mark.anyio
async def test_vehicle_requires_fields_and_rejects_null_partial_update(
    client: AsyncClient,
) -> None:
    await authenticate_owner(client)
    missing_name = await client.post(
        "/api/v1/vehicles",
        json={
            "brand": "Brand",
            "model": "Model",
            "license_plate": "ABC-1234",
            "max_charge_power_kw": 11,
        },
    )
    created = await client.post(
        "/api/v1/vehicles",
        json={
            "name": "EV",
            "brand": "Brand",
            "model": "Model",
            "license_plate": "ABC-1234",
            "max_charge_power_kw": 11,
        },
    )
    null_power = await client.patch(
        f"/api/v1/vehicles/{created.json()['id']}", json={"max_charge_power_kw": None}
    )

    assert missing_name.status_code == 422
    assert null_power.status_code == 422
    assert (await client.get(f"/api/v1/vehicles/{uuid4()}")).status_code == 404
