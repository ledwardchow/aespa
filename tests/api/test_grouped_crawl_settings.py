from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session

from aespa.models import TestRun


def _site(client: TestClient) -> int:
    result = client.post(
        "/api/sites",
        json={"name": "Shop", "base_url": "https://shop.test", "requires_auth": False},
    )
    assert result.status_code == 201
    return result.json()["id"]


def test_grouped_mode_is_opt_in_and_spa_cannot_use_it(client: TestClient) -> None:
    site_id = _site(client)
    default = client.post(
        f"/api/sites/{site_id}/test-runs", json={"max_depth": 2, "max_pages": 50}
    )
    assert default.status_code == 201
    assert default.json()["page_selection"] == "each_url"
    grouped = client.post(
        f"/api/sites/{site_id}/test-runs",
        json={"max_depth": 2, "max_pages": 50, "page_selection": "group_similar"},
    )
    assert grouped.status_code == 201
    assert grouped.json()["page_selection"] == "group_similar"
    invalid = client.post(
        f"/api/sites/{site_id}/test-runs",
        json={
            "max_depth": 2,
            "max_pages": 50,
            "crawler_mode": "interactive",
            "page_selection": "group_similar",
        },
    )
    assert invalid.status_code == 422


def test_mode_choices_lock_after_crawl_starts(
    client: TestClient, db_session: Session
) -> None:
    site_id = _site(client)
    created = client.post(
        f"/api/sites/{site_id}/test-runs", json={"max_depth": 2, "max_pages": 50}
    ).json()
    run_id = created["id"]
    before = client.patch(
        f"/api/test-runs/{run_id}",
        json={"max_depth": 2, "max_pages": 50, "page_selection": "group_similar"},
    )
    assert before.status_code == 200
    run = db_session.get(TestRun, run_id)
    run.crawl_started_once = True
    db_session.add(run)
    db_session.commit()
    after = client.patch(
        f"/api/test-runs/{run_id}",
        json={"max_depth": 2, "max_pages": 50, "page_selection": "each_url"},
    )
    assert after.status_code == 409
    assert (
        client.get(f"/api/test-runs/{run_id}").json()["page_selection"]
        == "group_similar"
    )
