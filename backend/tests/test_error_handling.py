from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.api.routes.common import commit_or_conflict
from app.main import app


async def _raise_unexpected_error() -> None:
    raise RuntimeError("database password=super-secret\nprivate traceback marker")


app.add_api_route("/__tests__/unexpected-error", _raise_unexpected_error)


@pytest.mark.anyio
async def test_unexpected_exception_does_not_expose_internal_details() -> None:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/__tests__/unexpected-error")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "super-secret" not in response.text
    assert "traceback" not in response.text.lower()


def test_commit_maps_only_an_expected_integrity_constraint_to_conflict() -> None:
    db = Mock()
    db.commit.side_effect = IntegrityError(
        "insert", {}, Exception("UNIQUE constraint failed: users.email")
    )

    with pytest.raises(HTTPException) as captured:
        commit_or_conflict(db, {"users.email": "A user with this email already exists"})

    assert captured.value.status_code == 409
    assert captured.value.detail == "A user with this email already exists"
    db.rollback.assert_called_once_with()


def test_commit_preserves_unexpected_integrity_error() -> None:
    error = IntegrityError("insert", {}, Exception("CHECK constraint failed: unrelated_rule"))
    db = Mock()
    db.commit.side_effect = error

    with pytest.raises(IntegrityError) as captured:
        commit_or_conflict(db, {"users.email": "A user with this email already exists"})

    assert captured.value is error
    db.rollback.assert_called_once_with()
