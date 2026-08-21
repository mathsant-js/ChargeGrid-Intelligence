from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models as _models  # noqa: F401
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app as api_app
from app.models.user import User, UserRole

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin-password"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def test_engine() -> Iterator[Engine]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Iterator[Session]:
    session_factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    with session_factory() as session:
        yield session


@pytest.fixture
async def client(test_engine: Engine) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[Session]:
        with Session(test_engine, expire_on_commit=False) as session:
            yield session

    with Session(test_engine, expire_on_commit=False) as session:
        session.add(
            User(
                name="Test Admin",
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
            )
        )
        session.commit()

    api_app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as value:
        login = await value.post(
            "/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        value.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
        yield value
    api_app.dependency_overrides.clear()
