import asyncio

import pytest

from aespa.models import LLMConfig
from aespa.services import reporting_debug


def test_prompt_versions_can_be_created_updated_and_deleted(tmp_path, monkeypatch):
    monkeypatch.setattr(
        reporting_debug,
        "debug_db_path",
        lambda: tmp_path / "reporting_debug.db",
    )

    defaults = reporting_debug.list_prompt_versions(reporting_debug.PROMPT_KEY_ANALYSE)
    assert defaults[0]["is_builtin"] is True
    assert defaults[0]["name"] == "Default"

    version = reporting_debug.create_prompt_version(
        key=reporting_debug.PROMPT_KEY_ANALYSE,
        name="Strict report",
        prompt_text="custom prompt",
    )
    assert version["is_builtin"] is False
    assert version["prompt_text"] == "custom prompt"

    updated = reporting_debug.update_prompt_version(
        version["id"],
        name="Strict report v2",
        prompt_text="custom prompt v2",
    )
    assert updated["name"] == "Strict report v2"
    assert updated["prompt_text"] == "custom prompt v2"

    reporting_debug.delete_prompt_version(version["id"])
    assert reporting_debug.get_prompt_version(version["id"]) is None

    with pytest.raises(PermissionError):
        reporting_debug.delete_prompt_version(defaults[0]["id"])


def test_replay_persists_findings_against_prompt_version(tmp_path, monkeypatch):
    monkeypatch.setattr(
        reporting_debug,
        "debug_db_path",
        lambda: tmp_path / "reporting_debug.db",
    )
    version = reporting_debug.create_prompt_version(
        key=reporting_debug.PROMPT_KEY_ANALYSE,
        name="Concise",
        prompt_text="Version prompt\n{url}\n{results}\n{severity_calibration}",
    )
    capture_id = reporting_debug.capture_reporting_batch(
        run_id=1,
        url="https://target.local",
        result_texts=["probe result"],
        prompt="original prompt",
        prompt_sha256="abc",
        llm={"provider": "openai_compatible", "model": "local"},
        raw_response="[]",
        findings=[],
    )
    replay = reporting_debug.create_replay(capture_id, prompt_version_id=version["id"])
    assert replay["prompt_version_id"] == version["id"]
    assert replay["prompt_version_name"] == "Concise"

    async def fake_replay(config, capture, prompt_template=None):  # noqa: ARG001
        return {
            "prompt": "rendered prompt",
            "prompt_sha256": "def",
            "raw_response": "{}",
            "findings": [{"title": "Debug finding", "severity": "medium"}],
        }

    from aespa.services import llm

    monkeypatch.setattr(llm, "replay_reporting_capture", fake_replay)
    asyncio.run(
        reporting_debug.run_replay(
            replay["id"],
            LLMConfig(provider="openai_compatible", model="local"),
        )
    )

    completed = reporting_debug.get_replay(replay["id"])
    assert completed["status"] == "complete"
    assert completed["prompt_version_name"] == "Concise"
    assert completed["findings"] == [{"title": "Debug finding", "severity": "medium"}]
