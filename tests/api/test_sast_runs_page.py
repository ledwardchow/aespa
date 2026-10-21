from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from aespa.models import SastRun
from aespa.services import sast_scanner


def test_sast_runs_page_sorts_and_limits_in_database(
    client, isolated_db_engine, monkeypatch
):
    started_at = datetime(2026, 10, 1, tzinfo=timezone.utc)
    with Session(isolated_db_engine) as session:
        for index in range(27):
            session.add(
                SastRun(
                    name="run 00" if index == 1 else f"Run {index:02d}",
                    status="failed" if index == 26 else "completed",
                    analysis_mode="light" if index % 2 else "deep",
                    leads_count=index // 2,
                    started_at=started_at + timedelta(days=index),
                )
            )
        session.commit()

    monkeypatch.setattr(
        sast_scanner,
        "is_sast_scan_running",
        lambda run_id, *, analysis_mode=None: run_id == 27,
    )

    first = client.get("/api/sast-runs/page?page=1&page_size=10")
    second = client.get("/api/sast-runs/page?page=2&page_size=10")
    assert first.status_code == second.status_code == 200, first.json()
    assert first.json()["total"] == second.json()["total"] == 27
    assert [run["id"] for run in first.json()["items"]] == list(range(27, 17, -1))
    assert [run["id"] for run in second.json()["items"]] == list(range(17, 7, -1))
    assert first.json()["items"][0]["status"] == "scanning"
    assert set(first.json()["items"][0]) == {
        "id",
        "name",
        "status",
        "analysis_mode",
        "leads_count",
        "started_at",
        "llm_profile_id",
    }

    by_leads = client.get(
        "/api/sast-runs/page",
        params={"page_size": 25, "sort_field": "leads_count", "sort_dir": "asc"},
    )
    assert by_leads.status_code == 200
    assert [run["id"] for run in by_leads.json()["items"][:4]] == [1, 2, 3, 4]
    assert [run["id"] for run in by_leads.json()["items"][-2:]] == [24, 25]

    by_name = client.get(
        "/api/sast-runs/page",
        params={"sort_field": "name", "sort_dir": "asc"},
    )
    assert [run["id"] for run in by_name.json()["items"][:3]] == [1, 2, 3]

    last = client.get("/api/sast-runs/page?page=3&page_size=10")
    assert [run["id"] for run in last.json()["items"]] == list(range(7, 0, -1))
    assert client.get("/api/sast-runs/page?page=4&page_size=10").json() == {
        "items": [],
        "total": 27,
    }


def test_sast_runs_page_rejects_invalid_paging_and_sort(client):
    for params in (
        {"page": 0},
        {"page_size": 11},
        {"sort_field": "created_at"},
        {"sort_dir": "sideways"},
    ):
        assert client.get("/api/sast-runs/page", params=params).status_code == 422


def test_sast_runs_page_uses_loaded_analysis_mode(
    client, isolated_db_engine, monkeypatch
):
    with Session(isolated_db_engine) as session:
        session.add(SastRun(name="Light scan", analysis_mode="light"))
        session.commit()

    def unexpected_lookup(_run_id):
        raise AssertionError("The list already loaded the analysis mode")

    monkeypatch.setattr(sast_scanner, "_is_light_run", unexpected_lookup)
    response = client.get("/api/sast-runs/page")

    assert response.status_code == 200
    assert response.json()["items"][0]["name"] == "Light scan"
