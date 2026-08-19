from collections.abc import AsyncIterator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models as _models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app as api_app


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

    api_app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=api_app), base_url="http://test") as value:
        yield value
    api_app.dependency_overrides.clear()
