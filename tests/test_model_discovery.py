from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from aespa.services import model_discovery


def test_discover_openai_models():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": "gpt-4o"},
            {"id": "gpt-4o-mini"},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    class _MockClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            assert "models" in url
            return mock_response

    with patch("httpx.AsyncClient", _MockClient):
        models = asyncio.run(
            model_discovery.discover_openai_models(api_key="test-key")
        )
        assert models == ["gpt-4o", "gpt-4o-mini"]


def test_discover_anthropic_models():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": "claude-3-7-sonnet-20250219"},
            {"id": "claude-3-5-haiku-20241022"},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    class _MockClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            assert "v1/models" in url
            return mock_response

    with patch("httpx.AsyncClient", _MockClient):
        models = asyncio.run(
            model_discovery.discover_anthropic_models(api_key="test-key")
        )
        assert models == ["claude-3-7-sonnet-20250219", "claude-3-5-haiku-20241022"]


def test_discover_google_models():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "models": [
            {"name": "models/gemini-2.0-flash-exp", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-1.5-pro", "supportedGenerationMethods": ["generateContent"]},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    class _MockClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            assert "v1beta/models" in url
            return mock_response

    with patch("httpx.AsyncClient", _MockClient):
        models = asyncio.run(
            model_discovery.discover_google_models(api_key="test-key")
        )
        assert models == ["gemini-2.0-flash-exp", "gemini-1.5-pro"]
