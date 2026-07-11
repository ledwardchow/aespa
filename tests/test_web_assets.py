import re

from fastapi.testclient import TestClient


def _javascript_bundle(client: TestClient) -> str:
    """Return the entry module plus every recursively referenced JS chunk."""
    pending = ["/app.js"]
    seen: set[str] = set()
    sources: list[str] = []
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        response = client.get(path)
        assert response.status_code == 200
        if path != "/app.js":
            # The HTML versions app.js with a query string. Importing it from a
            # chunk would create a second module identity (and a second React).
            assert not re.search(r'from["\'](?:\.\./|/)app\.js["\']', response.text)
        sources.append(response.text)
        for asset in re.findall(r'["\'](?:\./)?(assets/[^"\']+\.js)["\']', response.text):
            pending.append(f"/{asset}")
    return "\n".join(sources)


def test_index_uses_versioned_no_cache_assets(client: TestClient):
    response = client.get("/")

    assert response.status_code == 200
    assert "no-store" in response.headers["cache-control"]
    assert "__AESPA_ASSET_VERSION__" not in response.text
    assert '/app.js?v=' in response.text
    assert '/styles.css?v=' in response.text


def test_static_assets_are_no_cache(client: TestClient):
    response = client.get("/app.js")

    assert response.status_code == 200
    assert "no-store" in response.headers["cache-control"]


def test_scan_buttons_are_available_after_failed_scan(client: TestClient):
    source = _javascript_bundle(client)

    assert '"failed"' in source
    assert "Source" in source
    assert "source-badge" in source


def test_run_topbar_has_clear_only_crawl_action(client: TestClient):
    source = _javascript_bundle(client)

    assert "Clear crawl" in source
    assert "Clear & restart" not in source
    assert "clearCrawl" in source
    assert 'btn sm secondary" title=${!graph||graph.nodes.length===0 ? "No site map yet' not in source


def test_external_integrations_content_can_scroll(client: TestClient):
    source = _javascript_bundle(client)

    assert "External Integrations" in source
    assert "paddingLeft:16,paddingRight:0" in source
    assert 'minHeight:0,overflowY:"auto"' in source
