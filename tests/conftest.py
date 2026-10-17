from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import aespa.db
from aespa.db import _migrate, get_session, set_engine
from aespa.main import create_app


def _memory_engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(scope="session")
def _template_db_engine():
    """Build and migrate the schema once per test process.

    Creating 90-odd tables and running every migration costs far more than the
    average test, so each test gets a copy of this database instead.
    """
    # ensure models are registered with metadata before create_all
    from aespa import models as _models  # noqa: F401

    engine = _memory_engine()
    SQLModel.metadata.create_all(engine)
    _migrate(engine)
    yield engine
    engine.dispose()


def _copy_template_into(template, engine) -> None:
    """Copy the migrated template into ``engine`` with SQLite's backup API."""
    source = template.raw_connection()
    target = engine.raw_connection()
    try:
        source.driver_connection.backup(target.driver_connection)
    finally:
        # StaticPool keeps the single underlying connection open on close().
        source.close()
        target.close()


@pytest.fixture(scope="function", autouse=True)
def isolated_db_engine(_template_db_engine):
    """Keep every test, including mocked provider calls, off the local database."""
    prev_engine = aespa.db._engine
    engine = _memory_engine()
    _copy_template_into(_template_db_engine, engine)
    set_engine(engine)

    yield engine

    set_engine(prev_engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(isolated_db_engine):
    """Provide a session backed by the shared isolated test database."""
    with Session(isolated_db_engine) as session:
        yield session


@pytest.fixture(scope="function")
def db_engine(isolated_db_engine):
    """Compatibility alias for tests that use the shared engine directly."""
    return isolated_db_engine


@pytest.fixture(scope="function")
def engine(isolated_db_engine):
    """The shared isolated engine; ``get_engine()`` already returns it."""
    return isolated_db_engine


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Isolate uploaded-file storage to a temp dir for the test."""
    monkeypatch.setenv("AESPA_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture(scope="function")
def isolated_client(isolated_db_engine):
    def _override_session():
        with Session(isolated_db_engine) as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = _override_session

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="function")
def client(isolated_client):
    return isolated_client


@pytest.fixture(scope="function")
def fk_engine(_template_db_engine):
    """A fresh in-memory engine with SQLite foreign-key enforcement genuinely
    ON — mirrors ``db._build_engine``'s "connect" pragma, which the plain
    ``isolated_db_engine`` fixture above does not set. Use this whenever a
    test needs to prove a deletion helper is FK-safe (ordering bugs are
    silent when foreign_keys is off, SQLite's default).

    Overrides the autouse ``isolated_db_engine`` for tests that request it
    explicitly, matching the pattern already used by other test files with
    their own local ``engine`` fixture.
    """
    engine = _memory_engine()

    @event.listens_for(engine, "connect")
    def _enforce_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    _copy_template_into(_template_db_engine, engine)

    prev_engine = aespa.db._engine
    set_engine(engine)

    yield engine

    set_engine(prev_engine)
    engine.dispose()


@pytest.fixture
def fake_ssl_context(monkeypatch):
    """Turn CA bundle paths into comparable stand-ins instead of loading them.

    Returns a function giving the value ``httpx_verify`` produces for a path,
    so tests can check which bundle reached a client without a real file.
    """
    from aespa.services import tls

    def _context(cafile=None, capath=None):
        return ("ssl-context", cafile or capath)

    monkeypatch.setattr(tls, "ssl", SimpleNamespace(create_default_context=_context))
    return lambda path: ("ssl-context", path)


@pytest.fixture(autouse=True)
def offline_retire_list(monkeypatch, tmp_path_factory):
    """Keep tests off the network and away from a downloaded Retire.js copy.

    Scans use the Retire.js list shipped with AESPA. Tests of the download
    itself import ``ensure_fresh`` directly, before this patch applies.
    """
    from aespa.services import retire_repository

    cache = tmp_path_factory.mktemp("retire-cache")
    monkeypatch.setattr(retire_repository, "cache_dir", lambda: cache)

    async def _no_download(**_kwargs):
        return {**retire_repository.info(), "status": "disabled"}

    monkeypatch.setattr(retire_repository, "ensure_fresh", _no_download)
    return cache


@pytest.fixture(autouse=True)
def instant_llm_network_retries(monkeypatch):
    """Retry temporary LLM errors without real backoff waits in tests."""
    from aespa.services import llm

    monkeypatch.setattr(
        llm,
        "AGENTIC_NETWORK_RETRY_DELAYS",
        tuple(0.0 for _ in llm.AGENTIC_NETWORK_RETRY_DELAYS),
    )
