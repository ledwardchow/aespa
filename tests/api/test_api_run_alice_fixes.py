"""API-run A.L.I.C.E. context tool, goal steering, and session edits."""

from __future__ import annotations

import json

from sqlmodel import Session

from aespa.models import ApiCollection, ApiTestRun, ScannerSession
from aespa.services import alice as alice_svc
from aespa.services import alice_tasks
from aespa.services.api_scanner import _make_api_context_tool_fn


def _api_run(engine) -> tuple[int, int]:
    with Session(engine) as s:
        collection = ApiCollection(name="API", base_url="http://api.local")
        s.add(collection)
        s.flush()
        run = ApiTestRun(collection_id=collection.id, name="API run")
        s.add(run)
        s.commit()
        return collection.id, run.id


def test_context_tool_accepts_api_run_id_for_api_adapter(engine):
    collection_id, api_run_id = _api_run(engine)
    callback = _make_api_context_tool_fn(collection_id, api_run_id)

    output = alice_svc._invoke_context_tool(
        callback,
        "endpoint_list",
        {},
        pages_snapshot=[],
        findings_snapshot=[],
        history=[],
        run_id=api_run_id,
        base_url="http://api.local",
        api_run_id=api_run_id,
    )

    # Before the fix this call raised TypeError for the unexpected api_run_id.
    assert isinstance(output, dict)


def test_context_tool_forwards_api_run_id_when_adapter_declares_it():
    seen = {}

    def callback(
        tool_name,
        args,
        *,
        pages_snapshot,
        findings_snapshot,
        history,
        run_id,
        base_url,
        api_run_id,
    ):
        seen["api_run_id"] = api_run_id
        return {"ok": True}

    alice_svc._invoke_context_tool(
        callback,
        "endpoint_list",
        {},
        pages_snapshot=[],
        findings_snapshot=[],
        history=[],
        run_id=7,
        base_url="",
        api_run_id=7,
    )

    assert seen == {"api_run_id": 7}


def test_api_goal_steer_passes_tab_id(client, engine, monkeypatch):
    _, api_run_id = _api_run(engine)
    calls = []

    async def fake_steer(run_id, message, run_type="site", tab_id=None):
        calls.append((run_id, message, run_type, tab_id))
        return True

    monkeypatch.setattr(alice_tasks, "steer_goal", fake_steer)

    res = client.post(
        f"/api/api-test-runs/{api_run_id}/alice/goal/steer",
        json={"message": "check the admin routes", "tab_id": "tab-2"},
    )

    assert res.status_code == 200
    assert calls == [(api_run_id, "check the admin routes", "api", "tab-2")]


def test_api_goal_steer_without_tab_id(client, engine, monkeypatch):
    _, api_run_id = _api_run(engine)

    async def fake_steer(run_id, message, run_type="site", tab_id=None):
        return tab_id is None

    monkeypatch.setattr(alice_tasks, "steer_goal", fake_steer)

    res = client.post(
        f"/api/api-test-runs/{api_run_id}/alice/goal/steer",
        json={"message": "keep going"},
    )

    assert res.status_code == 200


def test_api_scanner_session_patch_returns_redacted_session(client, engine):
    _, api_run_id = _api_run(engine)
    with Session(engine) as s:
        record = ScannerSession(
            test_run_id=api_run_id,
            run_kind="api",
            label="admin",
            kind="bearer",
            cookies_json=json.dumps({"sid": "secret-cookie"}),
            extra_headers_json=json.dumps({"Authorization": "Bearer secret"}),
            session_metadata=json.dumps({"refresh_token": "secret", "note": "ok"}),
        )
        s.add(record)
        s.commit()
        session_id = record.id

    res = client.patch(
        f"/api/api-test-runs/{api_run_id}/scanner-sessions/{session_id}",
        json={"label": "admin-2"},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["label"] == "admin_2"
    assert body["cookie_names"] == ["sid"]
    assert body["header_names"] == ["Authorization"]
    assert body["session_metadata"] == {"refresh_token": "[REDACTED]", "note": "ok"}
    assert "secret" not in json.dumps(body)
