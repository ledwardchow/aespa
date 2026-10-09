from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlmodel import select

from aespa.models import SavedCrawl


def _make_site(client: TestClient, **kw):
    defaults = {
        "name": "Target",
        "base_url": "https://target.local",
        "requires_auth": False,
    }
    return client.post("/api/sites", json={**defaults, **kw}).json()


def _make_run(client: TestClient, site_id: int):
    return client.post(
        f"/api/sites/{site_id}/test-runs", json={"max_depth": 2, "max_pages": 10}
    ).json()


def _seed_crawled_run(client: TestClient, site_id: int) -> dict:
    run = _make_run(client, site_id)
    # The finding-import endpoint creates a crawled page without Playwright.
    created = client.post(
        f"/api/test-runs/{run['id']}/findings/import",
        json=[
            {"title": "Seed one", "affected_url": "https://target.local/account"},
            {"title": "Seed two", "affected_url": "https://target.local/orders"},
        ],
    )
    assert created.status_code == 200
    return run


def _save(client: TestClient, run_id: int, name: str = "Baseline crawl"):
    return client.post(
        f"/api/test-runs/{run_id}/crawl/save",
        json={"name": name, "notes": "for benchmarks"},
    )


def test_save_list_and_load_saved_crawl(client: TestClient):
    site = _make_site(client)
    source = _seed_crawled_run(client, site["id"])

    saved = _save(client, source["id"])
    assert saved.status_code == 201
    body = saved.json()
    assert body["name"] == "Baseline crawl"
    assert body["notes"] == "for benchmarks"
    assert body["page_count"] == 2
    assert body["size_bytes"] > 0
    assert body["source_run_id"] == source["id"]
    assert "archive_gz" not in body

    listed = client.get(f"/api/sites/{site['id']}/saved-crawls").json()
    assert [item["id"] for item in listed] == [body["id"]]
    assert listed[0]["source_run_exists"] is True
    assert "archive_gz" not in listed[0]

    target = _make_run(client, site["id"])
    loaded = client.post(f"/api/test-runs/{target['id']}/crawl/load/{body['id']}")
    assert loaded.status_code == 200
    assert loaded.json()["status"] == "complete"
    assert loaded.json()["pages_discovered"] == 2
    pages = client.get(f"/api/test-runs/{target['id']}/pages").json()
    assert {page["url"] for page in pages} == {
        "https://target.local/account",
        "https://target.local/orders",
    }

    # Loading again into the now-populated run is refused.
    again = client.post(f"/api/test-runs/{target['id']}/crawl/load/{body['id']}")
    assert again.status_code == 409


def test_saved_crawl_survives_source_run_deletion(client: TestClient):
    site = _make_site(client)
    source = _seed_crawled_run(client, site["id"])
    saved_id = _save(client, source["id"]).json()["id"]

    assert client.delete(f"/api/test-runs/{source['id']}").status_code == 204
    listed = client.get(f"/api/sites/{site['id']}/saved-crawls").json()
    assert listed[0]["id"] == saved_id
    assert listed[0]["source_run_exists"] is False

    target = _make_run(client, site["id"])
    loaded = client.post(f"/api/test-runs/{target['id']}/crawl/load/{saved_id}")
    assert loaded.status_code == 200


def test_save_requires_crawl_data(client: TestClient):
    site = _make_site(client)
    run = _make_run(client, site["id"])
    response = _save(client, run["id"])
    assert response.status_code == 400


def test_load_rejects_another_sites_crawl(client: TestClient):
    site = _make_site(client)
    other = _make_site(client, name="Other", base_url="https://other.local")
    saved_id = _save(client, _seed_crawled_run(client, site["id"])["id"]).json()["id"]
    target = _make_run(client, other["id"])
    response = client.post(f"/api/test-runs/{target['id']}/crawl/load/{saved_id}")
    assert response.status_code == 404


def test_rename_download_and_delete(client: TestClient):
    site = _make_site(client)
    saved_id = _save(client, _seed_crawled_run(client, site["id"])["id"]).json()["id"]
    base = f"/api/sites/{site['id']}/saved-crawls/{saved_id}"

    renamed = client.patch(base, json={"name": "Renamed", "notes": ""})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Renamed"
    assert renamed.json()["notes"] is None

    exported = client.get(f"{base}/export")
    assert exported.status_code == 200
    assert exported.json()["format"] == "aespa-crawl-export"
    assert len(exported.json()["crawl"]["pages"]) == 2

    assert client.delete(base).status_code == 204
    assert client.get(f"/api/sites/{site['id']}/saved-crawls").json() == []
    assert client.delete(base).status_code == 404


def test_upload_export_file_as_saved_crawl(client: TestClient):
    site = _make_site(client)
    source = _seed_crawled_run(client, site["id"])
    archive = client.get(f"/api/test-runs/{source['id']}/crawl/export").content

    uploaded = client.post(
        f"/api/sites/{site['id']}/saved-crawls/upload",
        files={"file": ("crawl.json", archive, "application/json")},
        data={"name": "From file"},
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["name"] == "From file"
    assert uploaded.json()["page_count"] == 2
    assert uploaded.json()["source_run_id"] is None

    other = _make_site(client, name="Other", base_url="https://other.local")
    rejected = client.post(
        f"/api/sites/{other['id']}/saved-crawls/upload",
        files={"file": ("crawl.json", archive, "application/json")},
    )
    assert rejected.status_code == 400
    bad = client.post(
        f"/api/sites/{site['id']}/saved-crawls/upload",
        files={"file": ("crawl.json", json.dumps({"x": 1}), "application/json")},
    )
    assert bad.status_code == 400


def test_deleting_site_removes_saved_crawls(client: TestClient, db_session):
    site = _make_site(client)
    _save(client, _seed_crawled_run(client, site["id"])["id"])
    assert client.delete(f"/api/sites/{site['id']}").status_code == 204
    assert db_session.exec(select(SavedCrawl)).all() == []
