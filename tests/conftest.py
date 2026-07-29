import pytest
from fastapi.testclient import TestClient
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
