from __future__ import annotations

import sqlite3

from sqlalchemy import func
from sqlmodel import Session, SQLModel, select

from aespa.models import (
    ApiCollection,
    ApiTestRun,
    Application,
    AssessmentCampaign,
    LLMProviderConfig,
    PublicReferenceNamespace,
    SastRun,
    ScannerPolicy,
    Site,
    TestRun,
)
from aespa.services import database_operations


def _count(session: Session, model) -> int:
    return session.exec(select(func.count()).select_from(model)).one()


def test_backup_database_creates_readable_complete_sqlite_copy(
    isolated_db_engine, tmp_path
):
    with Session(isolated_db_engine) as session:
        session.add(Site(name="Backup target", base_url="https://example.test"))
        session.commit()

    destination = tmp_path / "aespa-backup.db"
    saved = database_operations.backup_database(destination)

    assert saved == destination
    with sqlite3.connect(destination) as backup:
        assert backup.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert backup.execute("SELECT name FROM site").fetchall() == [
            ("Backup target",)
        ]
        assert backup.execute("SELECT version_num FROM alembic_version").fetchone()


def test_clear_scans_keeps_targets_llm_and_settings(fk_engine, monkeypatch):
    monkeypatch.setattr(database_operations, "_has_active_jobs", lambda session: False)
    with Session(fk_engine) as session:
        provider = LLMProviderConfig(name="Kept provider")
        policy = ScannerPolicy(scan_mode="safe_active")
        site = Site(name="Kept site", base_url="https://example.test")
        collection = ApiCollection(name="Kept API", base_url="https://api.example.test")
        application = Application(name="Kept application")
        session.add(provider)
        session.add(policy)
        session.add(site)
        session.add(collection)
        session.add(application)
        session.commit()
        session.refresh(site)
        session.refresh(collection)
        session.refresh(application)

        web_run = TestRun(site_id=site.id, name="Web scan")
        api_run = ApiTestRun(collection_id=collection.id, name="API scan")
        sast_run = SastRun(name="SAST scan")
        campaign = AssessmentCampaign(
            application_id=application.id, name="Campaign scan"
        )
        session.add(web_run)
        session.add(api_run)
        session.add(sast_run)
        session.add(campaign)
        session.commit()
        for owner_type, owner_id in (
            ("web", web_run.id),
            ("api", api_run.id),
            ("sast", sast_run.id),
            ("campaign", campaign.id),
        ):
            session.add(
                PublicReferenceNamespace(
                    owner_type=owner_type,
                    owner_id=owner_id,
                    prefix=f"{owner_type[:1].upper()}{owner_id:03d}",
                )
            )
        session.commit()

    assert database_operations.clear_scans() == 4

    with Session(fk_engine) as session:
        assert _count(session, TestRun) == 0
        assert _count(session, ApiTestRun) == 0
        assert _count(session, SastRun) == 0
        assert _count(session, AssessmentCampaign) == 0
        assert _count(session, PublicReferenceNamespace) == 0
        assert _count(session, Site) == 1
        assert _count(session, ApiCollection) == 1
        assert _count(session, LLMProviderConfig) == 1
        assert _count(session, ScannerPolicy) == 1
        assert _count(session, Application) == 1


def test_reset_database_removes_all_application_rows(fk_engine, monkeypatch):
    monkeypatch.setattr(database_operations, "_has_active_jobs", lambda session: False)
    with Session(fk_engine) as session:
        session.add(LLMProviderConfig(name="Removed provider"))
        session.add(ScannerPolicy())
        session.add(Site(name="Removed site", base_url="https://example.test"))
        session.commit()

    database_operations.reset_database()

    with Session(fk_engine) as session:
        for table in SQLModel.metadata.sorted_tables:
            count = session.execute(
                select(func.count()).select_from(table)
            ).scalar_one()
            assert count == 0, table.name


def test_destructive_database_operations_refuse_active_jobs(
    isolated_db_engine, monkeypatch
):
    monkeypatch.setattr(database_operations, "_has_active_jobs", lambda session: True)

    for operation in (
        database_operations.clear_scans,
        database_operations.reset_database,
    ):
        try:
            operation()
        except database_operations.DatabaseOperationError as exc:
            assert "Stop all active scans" in str(exc)
        else:
            raise AssertionError("Destructive operation ran while a job was active")
