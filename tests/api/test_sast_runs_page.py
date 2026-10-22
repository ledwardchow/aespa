from __future__ import annotations

import io
import zipfile
from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from aespa.models import ApiCollection, SastRun, Site
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
        "site_id",
        "collection_id",
        "associated_collection_id",
        "group_override",
        "associated_name",
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
        {"association": "other"},
    ):
        assert client.get("/api/sast-runs/page", params=params).status_code == 422


def test_sast_runs_page_filters_associations_before_paging(client, isolated_db_engine):
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.example")
        api = ApiCollection(name="Payments", base_url="https://api.example")
        session.add_all([site, api])
        session.commit()
        session.refresh(site)
        session.refresh(api)
        session.add_all(
            [
                SastRun(name="Site source", site_id=site.id),
                SastRun(name="API source", associated_collection_id=api.id),
                SastRun(name="Existing API source", collection_id=api.id),
                SastRun(name="Loose source"),
            ]
        )
        session.commit()

    assert client.get("/api/sast-runs/page").json()["total"] == 4
    for association, expected_names, target_name in (
        ("site", {"Site source"}, "Shop"),
        ("api", {"API source", "Existing API source"}, "Payments"),
        ("unassociated", {"Loose source"}, None),
    ):
        result = client.get(
            "/api/sast-runs/page", params={"association": association}
        ).json()
        assert result["total"] == len(expected_names)
        assert {item["name"] for item in result["items"]} == expected_names
        assert all(item["associated_name"] == target_name for item in result["items"])


def test_sast_runs_page_filters_target_and_sorts_target_names(
    client, isolated_db_engine
):
    with Session(isolated_db_engine) as session:
        bank = Site(name="Bank of Ed", base_url="https://bank.example")
        shop = Site(name="Shopped", base_url="https://shop.example")
        goose = ApiCollection(name="Goosecable API", base_url="https://goose.example")
        vampi = ApiCollection(name="Vampi", base_url="https://vampi.example")
        session.add_all([bank, shop, goose, vampi])
        session.commit()
        for target in (bank, shop, goose, vampi):
            session.refresh(target)
        session.add(SastRun(name="Shop scan", site_id=shop.id))
        for index in range(11):
            session.add(SastRun(name=f"Bank scan {index}", site_id=bank.id))
        session.add(SastRun(name="Goose scan", associated_collection_id=goose.id))
        session.add(SastRun(name="Vampi scan", collection_id=vampi.id))
        session.commit()
        bank_id = bank.id
        goose_id = goose.id

    site_names = client.get(
        "/api/sast-runs/page",
        params={"association": "site", "sort_field": "target", "sort_dir": "asc"},
    ).json()
    assert site_names["total"] == 12
    assert site_names["items"][0]["associated_name"] == "Bank of Ed"
    assert site_names["items"][-1]["associated_name"] == "Shopped"

    bank_page = client.get(
        "/api/sast-runs/page",
        params={
            "association": "site",
            "target_id": bank_id,
            "page": 2,
            "page_size": 10,
        },
    ).json()
    assert bank_page["total"] == 11
    assert len(bank_page["items"]) == 1
    assert bank_page["items"][0]["associated_name"] == "Bank of Ed"

    api_names = client.get(
        "/api/sast-runs/page",
        params={"association": "api", "sort_field": "target", "sort_dir": "desc"},
    ).json()
    assert [item["associated_name"] for item in api_names["items"]] == [
        "Vampi",
        "Goosecable API",
    ]
    goose_scans = client.get(
        "/api/sast-runs/page", params={"association": "api", "target_id": goose_id}
    ).json()
    assert [item["name"] for item in goose_scans["items"]] == ["Goose scan"]
    assert (
        client.get(
            "/api/sast-runs/page",
            params={"association": "unassociated", "target_id": bank_id},
        ).status_code
        == 422
    )


def test_sast_scan_name_and_group_can_be_changed_without_changing_source(
    client, isolated_db_engine
):
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.example")
        api = ApiCollection(name="Payments", base_url="https://api.example")
        session.add_all([site, api])
        session.commit()
        session.refresh(site)
        session.refresh(api)
        run = SastRun(name="Old name", collection_id=api.id, status="completed")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
        site_id = site.id
        api_id = api.id

    assert client.get("/api/sast-runs/page?association=api").json()["total"] == 1
    renamed = client.patch(f"/api/sast-runs/{run_id}", json={"name": "  New name  "})
    assert renamed.status_code == 200, renamed.json()
    assert renamed.json()["name"] == "New name"
    assert renamed.json()["collection_id"] == api_id

    moved = client.patch(
        f"/api/sast-runs/{run_id}",
        json={"site_id": site_id, "associated_collection_id": None},
    )
    assert moved.status_code == 200, moved.json()
    assert moved.json()["site_id"] == site_id
    assert moved.json()["collection_id"] == api_id
    assert client.get("/api/sast-runs/page?association=site").json()["total"] == 1
    assert client.get("/api/sast-runs/page?association=api").json()["total"] == 0

    cleared = client.patch(
        f"/api/sast-runs/{run_id}",
        json={"site_id": None, "associated_collection_id": None},
    )
    assert cleared.status_code == 200, cleared.json()
    assert cleared.json()["group_override"] is True
    assert (
        client.get("/api/sast-runs/page?association=unassociated").json()["total"] == 1
    )
    assert client.get("/api/sast-runs/page?association=api").json()["total"] == 0

    for payload, expected_status in (
        ({"name": " "}, 422),
        ({"site_id": site_id, "associated_collection_id": api_id}, 422),
        ({"site_id": 99999, "associated_collection_id": None}, 404),
    ):
        assert (
            client.patch(f"/api/sast-runs/{run_id}", json=payload).status_code
            == expected_status
        )
    assert client.get(f"/api/sast-runs/{run_id}").json()["name"] == "New name"


def test_uploaded_sast_scan_saves_association_and_validates_target(
    client, isolated_db_engine
):
    with Session(isolated_db_engine) as session:
        site = Site(name="Shop", base_url="https://shop.example")
        api = ApiCollection(name="Payments", base_url="https://api.example")
        session.add_all([site, api])
        session.commit()
        session.refresh(site)
        session.refresh(api)

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("app.py", "print('hello')\n")
    files = {"file": ("source.zip", archive.getvalue(), "application/zip")}

    result = client.post("/api/sast-runs", files=files, data={"site_id": site.id})
    assert result.status_code == 201, result.json()
    assert result.json()["site_id"] == site.id
    assert result.json()["collection_id"] is None
    assert client.get("/api/sast-runs/page?association=site").json()["total"] == 1

    api_result = client.post(
        "/api/sast-runs", files=files, data={"associated_collection_id": api.id}
    )
    assert api_result.status_code == 201, api_result.json()
    assert api_result.json()["associated_collection_id"] == api.id
    assert api_result.json()["collection_id"] is None
    assert api_result.json()["site_id"] is None
    assert client.get("/api/sast-runs/page?association=api").json()["total"] == 1

    invalid = client.post("/api/sast-runs", files=files, data={"site_id": 99999})
    assert invalid.status_code == 404
    assert (
        client.post(
            "/api/sast-runs",
            files=files,
            data={"site_id": site.id, "associated_collection_id": api.id},
        ).status_code
        == 422
    )

    assert client.delete(f"/api/sites/{site.id}").status_code == 204
    assert client.get(f"/api/sast-runs/{result.json()['id']}").json()["site_id"] is None
    assert (
        client.get("/api/sast-runs/page?association=unassociated").json()["total"] == 1
    )
    assert client.delete(f"/api/api-collections/{api.id}").status_code == 204
    assert (
        client.get(f"/api/sast-runs/{api_result.json()['id']}").json()[
            "associated_collection_id"
        ]
        is None
    )
    assert (
        client.get("/api/sast-runs/page?association=unassociated").json()["total"] == 2
    )


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
