from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

from aespa.services import openrouter_provider


def test_discover_models_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": "openai/gpt-4o", "name": "GPT-4o"},
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
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
            assert url == "https://openrouter.ai/api/v1/models"
            return mock_response

    with patch("httpx.AsyncClient", _MockClient):
        models = asyncio.run(openrouter_provider.discover_models())
        assert models == ["openai/gpt-4o", "anthropic/claude-3.5-sonnet"]
