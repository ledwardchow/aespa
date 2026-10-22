"""SAST ALICE uses the retained archive and stays within its run."""

from __future__ import annotations

import asyncio
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

from sqlmodel import select

from aespa.models import AliceChatSession, SastRun


def _run_with_archive(db_session, tmp_path: Path) -> SastRun:
    archive = tmp_path / "snapshot.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(
            "src/orders.py", "def load_order(order_id):\n    return db.get(order_id)\n"
        )
    run = SastRun(
        name="Orders source",
        status="completed",
        source_provider="git",
        source_locator="example/orders",
        source_revision="abc123",
        source_archive_path=str(archive),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def test_sast_alice_routes_save_sessions_and_isolate_run(
    client, db_session, tmp_path, monkeypatch
):
    from aespa.services import alice_tasks

    run = _run_with_archive(db_session, tmp_path)
    other = SastRun(name="Other run", status="pending")
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    saved = client.put(
        f"/api/sast-runs/{run.id}/alice/sessions",
        json={
            "active_tab_id": "tab-1",
            "chats": [
                {
                    "id": "tab-1",
                    "title": "Review",
                    "messages": [
                        {
                            "id": "m1",
                            "sender": "user",
                            "type": "message",
                            "text": "Hi",
                            "ts": "12:00",
                        }
                    ],
                }
            ],
        },
    )
    assert saved.status_code == 200
    result = client.get(f"/api/sast-runs/{run.id}/alice/sessions").json()
    assert result["chats"][0]["messages"][0]["text"] == "Hi"
    assert result["run_created_at"] == run.created_at.isoformat()
    assert client.get(f"/api/sast-runs/{other.id}/alice/sessions").json()["chats"] == []

    calls = []

    async def fake_start(run_id, **kwargs):
        calls.append((run_id, kwargs["run_type"]))

    monkeypatch.setattr(alice_tasks, "start", fake_start)
    payload = {
        "message": "Explain this snapshot",
        "history": [],
        "tab_id": "tab-1",
        "think_msg_id": "think-1",
        "reply_msg_id": "reply-1",
    }
    assert (
        client.post(f"/api/sast-runs/{run.id}/alice/run", json=payload).status_code
        == 200
    )
    assert calls == [(run.id, "sast")]
    assert (
        client.post(f"/api/sast-runs/{other.id}/alice/run", json=payload).status_code
        == 409
    )
    run_id = run.id
    assert client.delete(f"/api/sast-runs/{run_id}").status_code == 204
    db_session.expire_all()
    assert not db_session.exec(
        select(AliceChatSession).where(AliceChatSession.test_run_id == run_id)
    ).all()


def test_sast_alice_reads_saved_snapshot_without_escaping_it(
    db_session, tmp_path, monkeypatch
):
    from aespa.services import alice_sast

    run = _run_with_archive(db_session, tmp_path)
    (tmp_path / "secret.txt").write_text("outside secret")
    monkeypatch.setattr(
        alice_sast,
        "get_llm_config_for_role",
        lambda *_: SimpleNamespace(provider="openai"),
    )
    monkeypatch.setattr("aespa.services.alice._apply_upstream_proxy", lambda *_: None)
    monkeypatch.setattr(alice_sast.llm, "set_run_context", lambda *args, **kwargs: None)
    monkeypatch.setattr(alice_sast.llm, "clear_run_context", lambda: None)
    monkeypatch.setattr(
        alice_sast.llm,
        "compact_messages_for_config",
        lambda _c, _s, m, tools: (m, None),
    )
    requested = []

    async def fake_stream(_config, _system, messages, tools):
        requested.append(messages)
        if len(requested) == 1:
            blocks = [
                {
                    "type": "tool_use",
                    "id": "t1",
                    "name": "read_file",
                    "input": {"path": "../secret.txt"},
                },
                {
                    "type": "tool_use",
                    "id": "t2",
                    "name": "read_file",
                    "input": {"path": "src/orders.py"},
                },
            ]
            yield {"type": "result", "result": (blocks, "tool_use", blocks)}
        else:
            yield {
                "type": "text_delta",
                "delta": "The saved order lookup is in src/orders.py.",
            }
            blocks = [
                {"type": "text", "text": "The saved order lookup is in src/orders.py."}
            ]
            yield {"type": "result", "result": (blocks, "end_turn", blocks)}

    monkeypatch.setattr(alice_sast.llm, "stream_tools_call", fake_stream)

    async def collect():
        return [
            json.loads(line[6:])
            async for line in alice_sast.run_sast_alice_turn_stream(
                run.id, "Show order lookup", []
            )
        ]

    events = asyncio.run(collect())
    results = [
        event["result"] for event in events if event["type"] == "step_tool_result"
    ]
    assert any("Path escape attempt" in result for result in results)
    assert any("return db.get(order_id)" in result for result in results)
    assert "outside secret" not in json.dumps(events)
    activity = "".join(
        event["delta"] for event in events if event["type"] == "thinking_chunk"
    )
    assert activity.count("Used tool: read_file\n") == 2
    assert "[Step" not in activity
    assert events[-1]["thought"] == activity
    assert events[-1]["type"] == "done"
