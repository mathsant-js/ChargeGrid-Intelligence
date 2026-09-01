from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User


@pytest.mark.anyio
async def test_user_crud_hashes_password_and_never_exposes_it(
    client: AsyncClient, db_session: Session
) -> None:
    response = await client.post(
        "/api/v1/users",
        json={
            "name": "Ana Silva",
            "email": " ANA@EXAMPLE.COM ",
            "password": "strong-password",
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["email"] == "ana@example.com"
    assert created["role"] == "USER"
    assert created["is_active"] is True
    assert "password" not in created
    assert "password_hash" not in created
    UUID(created["id"])

    stored = db_session.scalar(select(User).where(User.id == UUID(created["id"])))
    assert stored is not None
    assert stored.password_hash != "strong-password"
    assert verify_password("strong-password", stored.password_hash)

    update = await client.patch(
        f"/api/v1/users/{created['id']}",
        json={"name": "Ana Souza", "role": "ADMIN", "password": "new-password"},
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Ana Souza"
    assert update.json()["role"] == "ADMIN"
    db_session.refresh(stored)
    assert verify_password("new-password", stored.password_hash)

    detail = await client.get(f"/api/v1/users/{created['id']}")
    listing = await client.get("/api/v1/users")
    assert detail.status_code == 200
    assert detail.json() in listing.json()


@pytest.mark.anyio
async def test_user_rejects_duplicate_email_and_invalid_input(client: AsyncClient) -> None:
    payload = {"name": "User", "email": "user@example.com", "password": "password-123"}
    assert (await client.post("/api/v1/users", json=payload)).status_code == 201
    assert (await client.post("/api/v1/users", json=payload)).status_code == 409

    invalid_password = {**payload, "email": "other@example.com", "password": "short"}
    assert (await client.post("/api/v1/users", json=invalid_password)).status_code == 422
    assert (await client.get(f"/api/v1/users/{uuid4()}")).status_code == 404


@pytest.mark.anyio
async def test_user_update_rejects_null_and_duplicate_email(client: AsyncClient) -> None:
    first = (
        await client.post(
            "/api/v1/users",
            json={"name": "First", "email": "first@example.com", "password": "password-123"},
        )
    ).json()
    second = (
        await client.post(
            "/api/v1/users",
            json={"name": "Second", "email": "second@example.com", "password": "password-123"},
        )
    ).json()

    duplicate = await client.patch(
        f"/api/v1/users/{second['id']}", json={"email": " FIRST@EXAMPLE.COM "}
    )
    null_name = await client.patch(f"/api/v1/users/{first['id']}", json={"name": None})

    assert duplicate.status_code == 409
    assert null_name.status_code == 422


@pytest.mark.anyio
async def test_user_response_has_only_public_fields_and_utc_timestamps(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users",
        json={"name": "Public", "email": "public@example.com", "password": "password-123"},
    )

    assert response.status_code == 201
    assert set(response.json()) == {
        "id",
        "name",
        "email",
        "role",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert response.json()["created_at"].endswith("Z")
    assert response.json()["updated_at"].endswith("Z")
