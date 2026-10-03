from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from sqlmodel import Session, select

from aespa.db import _get_alembic_config
from aespa.extensions import get_extension_manager
from aespa.models import ScanFinding, Site, TestRun
from aespa.services import external_scans
from alembic import command


@pytest.fixture(autouse=True)
def clear_external_scan_state():
    external_scans._targets.clear()
    external_scans._tasks.clear()
    yield
    external_scans._targets.clear()
    external_scans._tasks.clear()


def test_existing_burp_configuration_migrates_to_extension(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    config = _get_alembic_config(engine)
    command.upgrade(config, "465996cd1ec3")
    now = datetime.now(timezone.utc)
    old_config = sa.Table("burp_rest_api_config", sa.MetaData(), autoload_with=engine)
    specialist = sa.Table(
        "specialist_agent_config", sa.MetaData(), autoload_with=engine
    )
    old_values = {
        "id": 1,
        "enabled": True,
        "api_url": "http://127.0.0.1:9999",
        "api_key": "migrated-secret",
        "scan_configuration_name": "Fast audit",
        "scan_sqli": False,
        "scan_xss": True,
        "scan_command_injection": True,
        "scan_path_traversal": True,
        "scan_ssrf": True,
        "scan_xxe": True,
        "scan_ssti": True,
        "updated_at": now,
    }
    specialist_values = {}
    for column in specialist.columns:
        if column.name == "id":
            specialist_values[column.name] = 1
        elif column.name == "updated_at":
            specialist_values[column.name] = now
        elif column.name == "trigger_specialist_on_burp":
            specialist_values[column.name] = True
        elif isinstance(column.type, sa.Boolean):
            specialist_values[column.name] = True
        elif isinstance(column.type, sa.Integer):
            specialist_values[column.name] = 5
        elif (
            not column.nullable
            and column.default is None
            and column.server_default is None
        ):
            specialist_values[column.name] = "test"
    with engine.begin() as connection:
        connection.execute(old_config.insert().values(**old_values))
        connection.execute(specialist.insert().values(**specialist_values))
        connection.execute(
            sa.text(
                "INSERT INTO extension_setting "
                "(extension_id, enabled, schema_version, settings_json, updated_at) "
                "VALUES ('github.repository', 0, 1, '{\"git_executable\": \"/usr/bin/git\"}', :now)"
            ),
            {"now": now},
        )
        connection.execute(
            sa.text(
                "INSERT INTO sast_run "
                "(id, name, status, leads_count, completion_status, source_provider, "
                "created_at, updated_at) "
                "VALUES (999, 'Existing GitHub run', 'completed', 0, 'full', "
                "'github.repository', :now, :now)"
            ),
            {"now": now},
        )
    command.upgrade(config, "head")

    with engine.connect() as connection:
        row = (
            connection.execute(
                sa.text(
                    "SELECT enabled, settings_json FROM extension_setting WHERE extension_id = 'aespa.burpsuite'"
                )
            )
            .mappings()
            .one()
        )
        secret = connection.execute(
            sa.text(
                "SELECT value FROM extension_secret WHERE namespace = 'aespa.burpsuite' AND key = 'api_key'"
            )
        ).scalar_one()
        github = (
            connection.execute(
                sa.text(
                    "SELECT enabled, settings_json FROM extension_setting "
                    "WHERE extension_id = 'aespa.githubrepository'"
                )
            )
            .mappings()
            .one()
        )
        source_provider = connection.execute(
            sa.text("SELECT source_provider FROM sast_run WHERE id = 999")
        ).scalar_one()
    assert row["enabled"] == 1
    settings = json.loads(row["settings_json"])
    assert settings["api_url"] == "http://127.0.0.1:9999"
    assert settings["scan_sqli"] is False
    assert settings["trigger_specialist"] is True
    assert "migrated-secret" not in row["settings_json"]
    assert secret == "migrated-secret"
    assert github["enabled"] == 0
    assert json.loads(github["settings_json"])["git_executable"] == "/usr/bin/git"
    assert source_provider == "aespa.githubrepository"
    assert "burp_rest_api_config" not in sa.inspect(engine).get_table_names()
    engine.dispose()


@pytest.mark.anyio
async def test_burp_extension_scans_in_scope_and_saves_findings(
    db_session: Session, monkeypatch
):
    manager = get_extension_manager()
    manager.load_extensions()
    manager.set_enabled("aespa.burpsuite", True)
    manager.save_settings("aespa.burpsuite", {"scan_sqli": True})
    burp_client = manager.web_scanners["aespa.burpsuite"].scanner.scan.__globals__[
        "client"
    ]
    site = Site(name="target", base_url="https://target.local")
    db_session.add(site)
    db_session.flush()
    run = TestRun(site_id=site.id, name="Burp extension test")
    db_session.add(run)
    db_session.commit()

    launched = []

    async def launch(config, url, **kwargs):
        launched.append((config, url, kwargs))
        return 17

    async def wait(_config, _task_id):
        return [
            {
                "name": "SQL injection",
                "affected_url": "https://target.local/search?q=1",
                "severity": "high",
                "confidence": "certain",
                "description": "The search input is injectable.",
                "remediation": "Use parameterized queries.",
            }
        ]

    monkeypatch.setattr(burp_client, "launch_active_scan", launch)
    monkeypatch.setattr(burp_client, "wait_for_scan", wait)
    candidate = SimpleNamespace(
        id=3,
        page_id=None,
        title="SQL injection in search",
        description="Search query is injectable",
        owasp_category="A03",
        affected_url="https://target.local/search?q=1",
    )
    vault = {
        1: {
            "kind": "credential",
            "cookies": {"session": "test"},
            "extra_headers": {"Authorization": "Bearer test"},
        }
    }
    external_scans.schedule_finding(run.id, candidate, vault)
    await asyncio.gather(*external_scans._tasks[(run.id, "aespa.burpsuite")])

    assert len(launched) == 1
    assert launched[0][1] == candidate.affected_url
    assert launched[0][2]["cookies"] == {"session": "test"}
    assert launched[0][2]["extra_headers"] == {"Authorization": "Bearer test"}
    findings = db_session.exec(
        select(ScanFinding).where(ScanFinding.test_run_id == run.id)
    ).all()
    assert len(findings) == 1
    assert findings[0].finding_source == "burp_active_scan"
    assert findings[0].severity == "high"

    external_scans.schedule_finding(run.id, candidate, vault)
    assert len(launched) == 1
    candidate.affected_url = "https://outside.local/search?q=1"
    external_scans.schedule_finding(run.id, candidate, vault)
    assert len(launched) == 1


@pytest.mark.anyio
async def test_burp_extension_disable_cancels_scan(db_session: Session, monkeypatch):
    manager = get_extension_manager()
    manager.load_extensions()
    manager.set_enabled("aespa.burpsuite", True)
    scanner = manager.web_scanners["aespa.burpsuite"].scanner
    site = Site(name="target", base_url="https://target.local")
    db_session.add(site)
    db_session.flush()
    run = TestRun(site_id=site.id, name="Cancellation test")
    db_session.add(run)
    db_session.commit()

    started = asyncio.Event()

    async def scan(_candidate, context):
        context.on_started("18")
        started.set()
        await asyncio.Future()

    monkeypatch.setattr(scanner, "scan", scan)
    external_scans.schedule_investigation(
        run.id,
        {"url": "https://target.local/search", "hypothesis": "SQL injection"},
        "Investigate search",
        {},
    )
    await asyncio.wait_for(started.wait(), timeout=2)
    tasks = list(external_scans._tasks[(run.id, "aespa.burpsuite")])
    manager.set_enabled("aespa.burpsuite", False)
    await asyncio.gather(*tasks, return_exceptions=True)
    assert all(task.cancelled() for task in tasks)
