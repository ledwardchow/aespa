from fastapi.testclient import TestClient


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
    response = client.get("/app.js")

    assert response.status_code == 200
    assert '"failed"' in response.text
    assert "canShowScanStartButtons" in response.text
    assert "Start Structured Scan" in response.text
    assert "Source" in response.text
    assert "source-badge" in response.text


def test_run_topbar_has_clear_only_crawl_action(client: TestClient):
    response = client.get("/app.js")

    assert response.status_code == 200
    assert "Clear crawl" in response.text
    assert "Clear & restart" not in response.text
    assert "clearCrawl" in response.text
    assert 'btn sm secondary" title=${!graph||graph.nodes.length===0 ? "No site map yet' not in response.text


def test_external_integrations_content_can_scroll(client: TestClient):
    response = client.get("/app.js")

    assert response.status_code == 200
    assert "ExternalIntegrationsPage" in response.text
    assert "paddingLeft:16,paddingRight:0" in response.text
    assert 'minHeight:0,overflowY:"auto"' in response.text
