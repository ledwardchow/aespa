import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import aespa.db
from aespa.db import _migrate, get_session, set_engine
from aespa.main import create_app


@pytest.fixture(scope="function", autouse=True)
def isolated_db_engine():
    prev_engine = aespa.db._engine
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # ensure models are registered with metadata before create_all
    from aespa import models as _models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _migrate(engine)
    set_engine(engine)

    yield engine

    set_engine(prev_engine)
    SQLModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def client(isolated_db_engine):
    def _override_session():
        with Session(isolated_db_engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_session

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="function")
def fk_engine():
    """A fresh in-memory engine with SQLite foreign-key enforcement genuinely
    ON — mirrors ``db._build_engine``'s "connect" pragma, which the plain
    ``isolated_db_engine`` fixture above does not set. Use this whenever a
    test needs to prove a deletion helper is FK-safe (ordering bugs are
    silent when foreign_keys is off, SQLite's default).

    Overrides the autouse ``isolated_db_engine`` for tests that request it
    explicitly, matching the pattern already used by other test files with
    their own local ``engine`` fixture.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enforce_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    from aespa import models as _models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _migrate(engine)

    prev_engine = aespa.db._engine
    set_engine(engine)

    yield engine

    set_engine(prev_engine)
    SQLModel.metadata.drop_all(engine)
    engine.dispose()
