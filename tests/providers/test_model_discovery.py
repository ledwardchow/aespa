from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from aespa.services import model_discovery, settings


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
        models = asyncio.run(model_discovery.discover_openai_models(api_key="test-key"))
        assert models == ["gpt-4o", "gpt-4o-mini"]


def test_discover_bedrock_mantle_models_uses_v1_models_route():
    captured: dict[str, object] = {}
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": "openai.gpt-5.5"},
            {"id": "openai.gpt-oss-120b"},
        ]
    }

    class _MockClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            captured["url"] = url
            return mock_response

    with patch("httpx.AsyncClient", _MockClient):
        records = asyncio.run(
            model_discovery.discover_bedrock_mantle_model_options(
                api_key="mantle-key",
                base_url="https://bedrock-mantle.ap-southeast-2.api.aws/openai/v1",
            )
        )

    assert captured["url"] == (
        "https://bedrock-mantle.ap-southeast-2.api.aws/v1/models"
    )
    assert captured["client"]["headers"]["Authorization"] == "Bearer mantle-key"
    assert [record["id"] for record in records] == [
        "openai.gpt-5.5",
        "openai.gpt-oss-120b",
    ]


def test_discover_bedrock_mantle_models_uses_sigv4_without_api_key(monkeypatch):
    captured: dict[str, object] = {}
    signer = object()
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": []}

    class _MockSigner:
        def __new__(cls, *, region, profile):
            captured["signer"] = {"region": region, "profile": profile}
            return signer

    class _MockClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            return mock_response

    monkeypatch.setenv("AWS_PROFILE", "mantle-dev")
    monkeypatch.setattr("aespa.services.llm._BedrockMantleSigV4Auth", _MockSigner)
    with patch("httpx.AsyncClient", _MockClient):
        asyncio.run(
            model_discovery.discover_bedrock_mantle_model_options(
                base_url="https://bedrock-mantle.eu-west-1.api.aws",
            )
        )

    assert captured["signer"] == {"region": "eu-west-1", "profile": "mantle-dev"}
    assert captured["client"]["auth"] is signer


def test_provider_model_discovery_sorts_and_deduplicates_all_formats(monkeypatch):
    async def fake_discovery(**kwargs):
        return [
            {"id": "Zulu", "supported_efforts": []},
            {"id": "alpha", "supported_efforts": []},
            {"id": "Zulu", "supported_efforts": []},
        ]

    monkeypatch.setattr(
        model_discovery, "discover_bedrock_mantle_model_options", fake_discovery
    )

    result = asyncio.run(
        settings.discover_model_options_for_format(
            api_format="bedrock_mantle",
            api_key="mantle-key",
            base_url="https://bedrock-mantle.ap-southeast-2.api.aws",
        )
    )

    assert result["models"] == ["alpha", "Zulu"]


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
            {
                "name": "models/gemini-2.0-flash-exp",
                "supportedGenerationMethods": ["generateContent"],
            },
            {
                "name": "models/gemini-1.5-pro",
                "supportedGenerationMethods": ["generateContent"],
            },
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
        models = asyncio.run(model_discovery.discover_google_models(api_key="test-key"))
        assert models == ["gemini-2.0-flash-exp", "gemini-1.5-pro"]


def test_discover_google_vertex_models_uses_adc_and_filters_publishers(monkeypatch):
    captured: dict[str, object] = {}

    class _Pager:
        def __init__(self):
            self._items = iter(
                [
                    SimpleNamespace(
                        name="publishers/google/models/gemini-2.5-flash",
                        input_token_limit=1_048_576,
                        output_token_limit=65_536,
                        supported_actions=["generateContent"],
                    ),
                    SimpleNamespace(
                        name="projects/p/locations/us-central1/endpoints/123",
                        input_token_limit=None,
                        output_token_limit=None,
                        supported_actions=["predict"],
                    ),
                    SimpleNamespace(
                        name="publishers/google/models/text-embedding-005",
                        input_token_limit=None,
                        output_token_limit=None,
                        supported_actions=["embedContent"],
                    ),
                ]
            )

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self._items)
            except StopIteration as exc:
                raise StopAsyncIteration from exc

    class _Models:
        async def list(self, *, config):
            captured["list_config"] = config
            return _Pager()

    class _AsyncClient:
        models = _Models()

        async def aclose(self):
            captured["closed"] = True

    class _Client:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.aio = _AsyncClient()

    monkeypatch.setattr("google.genai.Client", _Client)

    records = asyncio.run(
        model_discovery.discover_google_vertex_model_options(
            project_id="example-project", location="us-central1"
        )
    )

    assert [record["id"] for record in records] == ["gemini-2.5-flash"]
    assert records[0]["input_token_limit"] == 1_048_576
    assert captured["client"]["vertexai"] is True
    assert captured["client"]["project"] == "example-project"
    assert captured["client"]["location"] == "us-central1"
    assert captured["list_config"] == {"query_base": True}
    assert captured["closed"] is True
