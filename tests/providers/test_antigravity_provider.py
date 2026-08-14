from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from aespa.models import LLMConfig
from aespa.services import antigravity_provider, llm


def test_workspace_isolation(monkeypatch, tmp_path):
    monkeypatch.setattr(
        antigravity_provider.tempfile, "gettempdir", lambda: str(tmp_path)
    )

    first = antigravity_provider._workspace_directory()
    second = antigravity_provider._workspace_directory()

    assert first == second == tmp_path / "aespa-antigravity-workspace"
    assert first.is_dir()


def test_child_environment_does_not_forward_secrets(monkeypatch):
    monkeypatch.setenv("HOME", "/tmp/test-home")
    monkeypatch.setenv("PATH", "/usr/local/bin:/usr/bin")
    monkeypatch.setenv("AESPA_SECRET_KEY", "do-not-forward")

    env = antigravity_provider._child_env("http://proxy.local:8080")

    assert env["HOME"] == "/tmp/test-home"
    assert env["PATH"] == "/usr/local/bin:/usr/bin"
    assert env["HTTPS_PROXY"] == "http://proxy.local:8080"
    assert "AESPA_SECRET_KEY" not in env


def test_model_alias_resolution():
    assert antigravity_provider._resolve_model("auto") == "Gemini 3.7 Flash (High)"
    assert (
        antigravity_provider._resolve_model("gemini-3.7-flash")
        == "Gemini 3.7 Flash (High)"
    )
    assert (
        antigravity_provider._resolve_model("gemini-2.5-pro") == "Gemini 3.1 Pro (High)"
    )
    assert antigravity_provider._resolve_model("custom-model") == "custom-model"
    assert antigravity_provider._resolve_model("") == "Gemini 3.7 Flash (High)"


def test_plain_completion_success():
    async def run():
        fake_output = {
            "conversation_id": "test-conv-id",
            "status": "SUCCESS",
            "response": "Test response content",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 25,
                "thinking_tokens": 10,
                "cache_read_tokens": 0,
                "total_tokens": 125,
            },
        }

        recorded = []

        def fake_usage_callback(**kwargs):
            recorded.append(kwargs)

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (json.dumps(fake_output).encode(), b"")
        mock_proc.returncode = 0

        with (
            patch(
                "aespa.services.antigravity_provider._find_agy_executable",
                return_value="/bin/agy",
            ),
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        ):
            config = LLMConfig(provider="google_antigravity", model="gemini-3.7-flash")
            res = await antigravity_provider.plain_completion(
                config=config,
                prompt="Hello",
                usage_callback=fake_usage_callback,
            )

            assert res == "Test response content"
            assert len(recorded) == 1
            assert recorded[0]["input_tokens"] == 100
            assert recorded[0]["output_tokens"] == 25
            assert recorded[0]["thinking_tokens"] == 10

    asyncio.run(run())


def test_plain_completion_quota_error():
    async def run():
        fake_error_output = {
            "status": "ERROR",
            "error": "RESOURCE_EXHAUSTED: rate limit exceeded, 429 too many requests",
        }

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (
            json.dumps(fake_error_output).encode(),
            b"",
        )
        mock_proc.returncode = 0

        with (
            patch(
                "aespa.services.antigravity_provider._find_agy_executable",
                return_value="/bin/agy",
            ),
            patch("asyncio.create_subprocess_exec", return_value=mock_proc),
        ):
            config = LLMConfig(provider="google_antigravity", model="auto")
            with pytest.raises(antigravity_provider.AntigravityQuotaError):
                await antigravity_provider.plain_completion(
                    config=config, prompt="Hello"
                )

    asyncio.run(run())


def test_llm_service_dispatch_google_antigravity():
    async def run():
        with patch(
            "aespa.services.antigravity_provider.plain_completion",
            new=AsyncMock(return_value="Antigravity response"),
        ):
            config = LLMConfig(provider="google_antigravity", model="auto")
            result = await llm.plain_completion(config, "test prompt")
            assert result == "Antigravity response"

    asyncio.run(run())


def test_discover_models():
    async def run():
        models = await antigravity_provider.discover_models()
        assert "auto" in models
        assert "Gemini 3.7 Flash (High)" in models

    asyncio.run(run())
