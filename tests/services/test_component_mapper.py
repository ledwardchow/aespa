from __future__ import annotations

import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlmodel import Session, select

from aespa.models import (
    Application,
    ApplicationComponent,
    AssessmentCampaign,
    CampaignSourceMember,
    ComponentFact,
    ComponentSnapshot,
    SastRun,
)
from aespa.services import component_mapper
from aespa.services.component_facts import extract_component_facts


def _seed_member(engine, archive: Path) -> tuple[int, int]:
    with Session(engine) as session:
        app = Application(name="Mapper test")
        session.add(app)
        session.flush()
        component = ApplicationComponent(application_id=app.id, name="service")
        session.add(component)
        session.flush()
        snapshot = ComponentSnapshot(
            component_id=component.id,
            filename="service.zip",
            stored_path=str(archive),
            size_bytes=archive.stat().st_size,
            sha256="a" * 64,
        )
        run = SastRun(name="service scan", status="completed")
        session.add(snapshot)
        session.add(run)
        session.flush()
        campaign = AssessmentCampaign(application_id=app.id, name="mapping")
        session.add(campaign)
        session.flush()
        member = CampaignSourceMember(
            campaign_id=campaign.id,
            component_id=component.id,
            snapshot_id=snapshot.id,
            sast_run_id=run.id,
            status="completed",
        )
        session.add(member)
        session.commit()
        return campaign.id, member.id


def _archive(tmp_path: Path) -> Path:
    archive = tmp_path / "service.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("src/routes.py", "BASE = '/api'\n@get('/orders')\n")
    return archive


@pytest.mark.anyio
async def test_mapper_persists_read_evidenced_fact_and_cleans_workspace(
    isolated_db_engine, tmp_path, monkeypatch
):
    archive = _archive(tmp_path)
    campaign_id, member_id = _seed_member(isolated_db_engine, archive)
    monkeypatch.setattr(
        component_mapper,
        "get_settings",
        lambda: SimpleNamespace(data_dir=tmp_path / "data"),
    )

    async def fake_loop(_config, **kwargs):
        executor = kwargs["tool_executor"]
        await executor("read_file", {"path": "src/routes.py"}, 1)
        await executor(
            "record_interface_fact",
            {
                "fact_type": "route",
                "method": "GET",
                "path": "/api/orders",
                "host": None,
                "name": None,
                "confidence": 0.92,
                "evidence_location": "src/routes.py:2",
                "supporting_locations": [],
                "reasoning": "The decorator exposes the composed route.",
            },
            2,
        )
        return "mapped"

    from aespa.services import llm

    monkeypatch.setattr(llm, "thinking_agentic_loop", fake_loop)
    result = await component_mapper.map_campaign_component(
        campaign_id, member_id, llm_config=object()
    )

    assert result.facts_recorded == 1
    assert result.facts_rejected == 0
    assert not (
        tmp_path / "data" / "campaign_correlation" / str(campaign_id) / str(member_id)
    ).exists()
    with Session(isolated_db_engine) as session:
        fact = session.exec(select(ComponentFact)).one()
        assert fact.fact_type == "route"
        assert fact.detail_json.find('"origin": "llm"') >= 0


@pytest.mark.anyio
async def test_mapper_stops_cleanly_at_configured_fact_budget(
    isolated_db_engine, tmp_path, monkeypatch
):
    archive = _archive(tmp_path)
    campaign_id, member_id = _seed_member(isolated_db_engine, archive)
    monkeypatch.setattr(
        component_mapper,
        "get_settings",
        lambda: SimpleNamespace(data_dir=tmp_path / "data"),
    )
    monkeypatch.setattr(
        component_mapper.settings_svc,
        "get_component_mapper_config",
        lambda _session: SimpleNamespace(
            max_tool_calls=10,
            max_source_files=10,
            max_source_bytes=1024 * 1024,
            max_facts=1,
            max_concurrent=1,
        ),
    )

    async def fake_loop(_config, **kwargs):
        executor = kwargs["tool_executor"]
        await executor("read_file", {"path": "src/routes.py"}, 1)
        fact = {
            "fact_type": "route",
            "method": "GET",
            "path": "/api/orders",
            "host": None,
            "name": None,
            "confidence": 0.92,
            "evidence_location": "src/routes.py:2",
            "supporting_locations": [],
            "reasoning": "The decorator exposes the composed route.",
        }
        await executor("record_interface_fact", fact, 2)
        response = await executor("record_interface_fact", fact, 3)
        assert "fact budget exhausted" in response
        assert kwargs["termination_check"]()
        return ""

    from aespa.services import llm

    monkeypatch.setattr(llm, "thinking_agentic_loop", fake_loop)
    result = await component_mapper.map_campaign_component(
        campaign_id, member_id, llm_config=object()
    )

    assert result.facts_recorded == 1
    assert "fact budget exhausted" in result.summary


@pytest.mark.anyio
async def test_mapper_rejects_unread_and_traversal_evidence(
    isolated_db_engine, tmp_path, monkeypatch
):
    archive = _archive(tmp_path)
    campaign_id, member_id = _seed_member(isolated_db_engine, archive)
    monkeypatch.setattr(
        component_mapper,
        "get_settings",
        lambda: SimpleNamespace(data_dir=tmp_path / "data"),
    )

    async def fake_loop(_config, **kwargs):
        executor = kwargs["tool_executor"]
        for line, path in ((2, "src/routes.py"), (1, "../outside.py")):
            await executor(
                "record_interface_fact",
                {
                    "fact_type": "route",
                    "method": "GET",
                    "path": "/orders",
                    "confidence": 0.8,
                    "evidence_location": f"{path}:{line}",
                    "supporting_locations": [],
                    "reasoning": "invalid evidence",
                },
                1,
            )
        return "done"

    from aespa.services import llm

    monkeypatch.setattr(llm, "thinking_agentic_loop", fake_loop)
    result = await component_mapper.map_campaign_component(
        campaign_id, member_id, llm_config=object()
    )

    assert result.facts_recorded == 0
    assert result.facts_rejected == 2
    with Session(isolated_db_engine) as session:
        assert session.exec(select(ComponentFact)).all() == []


def test_mapper_fact_validation_rejects_unsupported_method(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "route.py").write_text("route()\n")
    with pytest.raises(ValueError, match="unsupported HTTP method"):
        component_mapper._validate_fact(
            root,
            {
                "fact_type": "route",
                "method": "TRACE",
                "path": "/orders",
                "confidence": 0.8,
                "evidence_location": "route.py:1",
            },
            {"route.py": [(1, 1)]},
        )


def test_deterministic_request_roles_separate_browser_and_server_hops(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "ui.ts").write_text("fetch('/api/quotes/motor', {method: 'POST'})\n")
    (root / "server.py").write_text(
        "@app.post('/api/customer/quotes/motor')\n"
        "requests.post('/api/customer/quotes/motor')\n"
    )

    facts = extract_component_facts(root)
    roles = {
        (fact["fact_type"], fact["path"]): fact["detail"].get("request_role")
        for fact in facts
        if fact["fact_type"] in {"route", "http_call"}
    }
    assert roles[("http_call", "/api/quotes/motor")] == "browser_request"
    assert roles[("http_call", "/api/customer/quotes/motor")] == "server_egress"
    assert roles[("route", "/api/customer/quotes/motor")] == "server_ingress"


def test_mapper_fact_validation_rejects_invalid_request_role(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "route.py").write_text("route('/orders')\n")
    with pytest.raises(ValueError, match="request_role"):
        component_mapper._validate_fact(
            root,
            {
                "fact_type": "http_call",
                "method": "POST",
                "path": "/orders",
                "confidence": 0.8,
                "evidence_location": "route.py:1",
                "detail": {"request_role": "unknown"},
            },
            {"route.py": [(1, 1)]},
        )


def test_mapper_validates_evidence_backed_auth_flow(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    (root / "client.py").write_text(
        "token = authenticate()\nheaders = bearer(token)\nrequest(headers=headers)\n"
    )

    fact = component_mapper._validate_fact(
        root,
        {
            "fact_type": "auth_flow",
            "method": "POST",
            "path": "/session",
            "name": "bearer token",
            "confidence": 0.9,
            "evidence_location": "client.py:1",
            "supporting_locations": ["client.py:2", "client.py:3"],
            "reasoning": "The response token is attached to later requests.",
            "detail": {
                "credential_kind": "bearer",
                "acquisition_call_locations": ["client.py:1"],
                "credential_use_locations": ["client.py:3"],
            },
        },
        {"client.py": [(1, 3)]},
    )

    assert fact["fact_type"] == "auth_flow"
    assert fact["detail"]["acquisition_call_locations"] == ["client.py:1"]
    assert fact["detail"]["credential_use_locations"] == ["client.py:3"]


@pytest.mark.anyio
async def test_mapper_merges_deterministic_fact_by_semantic_fingerprint(
    isolated_db_engine, tmp_path, monkeypatch
):
    archive = _archive(tmp_path)
    campaign_id, member_id = _seed_member(isolated_db_engine, archive)
    with Session(isolated_db_engine) as session:
        member = session.get(CampaignSourceMember, member_id)
        session.add(
            ComponentFact(
                sast_run_id=member.sast_run_id,
                component_id=member.component_id,
                fact_type="route",
                method="GET",
                path="/api/orders",
                evidence_location="src/routes.py:2",
                fingerprint=component_mapper.interface_fact_fingerprint(
                    fact_type="route",
                    method="GET",
                    path="/api/orders",
                    host=None,
                    name=None,
                ),
            )
        )
        session.commit()
    monkeypatch.setattr(
        component_mapper,
        "get_settings",
        lambda: SimpleNamespace(data_dir=tmp_path / "data"),
    )

    async def fake_loop(_config, **kwargs):
        executor = kwargs["tool_executor"]
        await executor("read_file", {"path": "src/routes.py"}, 1)
        await executor(
            "record_interface_fact",
            {
                "fact_type": "route",
                "method": "GET",
                "path": "/api/orders",
                "confidence": 0.9,
                "evidence_location": "src/routes.py:2",
                "supporting_locations": [],
                "reasoning": "same semantic route",
            },
            2,
        )
        return ""

    from aespa.services import llm

    monkeypatch.setattr(llm, "thinking_agentic_loop", fake_loop)
    await component_mapper.map_campaign_component(
        campaign_id, member_id, llm_config=object()
    )
    with Session(isolated_db_engine) as session:
        facts = session.exec(select(ComponentFact)).all()
        assert len(facts) == 1
        assert '"origin": "deterministic+llm"' in facts[0].detail_json
