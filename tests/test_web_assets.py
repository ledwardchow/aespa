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
