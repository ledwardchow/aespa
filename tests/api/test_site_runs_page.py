from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from aespa.models import Site, TestRun
from aespa.services import scanner


def test_site_runs_page_limits_and_sorts_in_database(
    client, isolated_db_engine, monkeypatch
):
    started_at = datetime(2026, 10, 1, tzinfo=timezone.utc)
    with Session(isolated_db_engine) as session:
        first_site = Site(name="First", base_url="https://first.example")
        second_site = Site(name="Second", base_url="https://second.example")
        session.add_all([first_site, second_site])
        session.flush()
        for index in range(27):
            session.add(
                TestRun(
                    site_id=first_site.id,
                    name="run 00" if index == 1 else f"Run {index:02d}",
                    status="paused" if index == 26 else "complete",
                    pages_discovered=index // 2,
                    created_at=started_at + timedelta(days=index),
                )
            )
        session.add(TestRun(site_id=second_site.id, name="Other site"))
        session.commit()
        site_id = first_site.id

    def unexpected_lookup(_run_id):
        raise AssertionError("Paged list must not load scan findings per row")

    monkeypatch.setattr(scanner, "get_thinking_scan_status", unexpected_lookup)
    first = client.get(f"/api/sites/{site_id}/test-runs/page?page=1&page_size=10")
    second = client.get(f"/api/sites/{site_id}/test-runs/page?page=2&page_size=10")
    assert first.status_code == second.status_code == 200, first.json()
    assert first.json()["total"] == second.json()["total"] == 27
    assert [run["id"] for run in first.json()["items"]] == list(range(27, 17, -1))
    assert [run["id"] for run in second.json()["items"]] == list(range(17, 7, -1))
    assert first.json()["items"][0]["thinking_status"] == "paused"
    assert set(first.json()["items"][0]) == {
        "id",
        "name",
        "status",
        "phase",
        "thinking_status",
        "coverage_mode",
        "pages_discovered",
        "created_at",
        "llm_profile_id",
        "max_depth",
        "max_pages",
        "crawler_mode",
        "page_selection",
        "crawl_started_once",
        "llm_budget_usd",
    }

    by_pages = client.get(
        f"/api/sites/{site_id}/test-runs/page",
        params={"page_size": 25, "sort_field": "pages_discovered", "sort_dir": "asc"},
    )
    assert [run["id"] for run in by_pages.json()["items"][:4]] == [1, 2, 3, 4]
    by_name = client.get(
        f"/api/sites/{site_id}/test-runs/page",
        params={"sort_field": "name", "sort_dir": "asc"},
    )
    assert [run["id"] for run in by_name.json()["items"][:3]] == [1, 2, 3]
    assert [
        run["id"]
        for run in client.get(
            f"/api/sites/{site_id}/test-runs/page?page=3&page_size=10"
        ).json()["items"]
    ] == list(range(7, 0, -1))
    assert client.get(
        f"/api/sites/{site_id}/test-runs/page?page=4&page_size=10"
    ).json() == {
        "items": [],
        "total": 27,
    }


def test_site_runs_page_rejects_invalid_query_and_missing_site(client):
    for params in (
        {"page": 0},
        {"page_size": 11},
        {"sort_field": "llm_budget_usd"},
        {"sort_dir": "sideways"},
    ):
        assert (
            client.get("/api/sites/1/test-runs/page", params=params).status_code == 422
        )
    assert client.get("/api/sites/1/test-runs/page").status_code == 404
