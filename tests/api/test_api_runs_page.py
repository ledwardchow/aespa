from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from aespa.models import ApiCollection, ApiTestRun


def test_api_runs_page_limits_and_scopes_rows(client, isolated_db_engine):
    created_at = datetime(2026, 10, 1, tzinfo=timezone.utc)
    with Session(isolated_db_engine) as session:
        first = ApiCollection(name="First", base_url="https://first.example")
        second = ApiCollection(name="Second", base_url="https://second.example")
        session.add(first)
        session.add(second)
        session.flush()
        for index in range(27):
            session.add(
                ApiTestRun(
                    collection_id=first.id,
                    name=f"Run {index:02d}",
                    created_at=created_at + timedelta(days=index),
                )
            )
        session.add(ApiTestRun(collection_id=second.id, name="Other run"))
        session.commit()
        collection_id = first.id

    url = f"/api/api-collections/{collection_id}/test-runs/page"
    first_page = client.get(url, params={"page": 1, "page_size": 10})
    second_page = client.get(url, params={"page": 2, "page_size": 10})
    assert first_page.status_code == second_page.status_code == 200, first_page.json()
    assert first_page.json()["total"] == second_page.json()["total"] == 27
    assert [row["name"] for row in first_page.json()["items"]] == [
        f"Run {index:02d}" for index in range(26, 16, -1)
    ]
    assert [row["name"] for row in second_page.json()["items"]] == [
        f"Run {index:02d}" for index in range(16, 6, -1)
    ]
    assert set(first_page.json()["items"][0]) == {
        "id",
        "name",
        "status",
        "coverage_mode",
        "created_at",
    }
    assert [
        row["name"]
        for row in client.get(url, params={"page": 3, "page_size": 10}).json()["items"]
    ] == [f"Run {index:02d}" for index in range(6, -1, -1)]
    assert client.get(url, params={"page": 4, "page_size": 10}).json() == {
        "items": [],
        "total": 27,
    }


def test_api_runs_page_sorts_case_insensitively_with_stable_ties(
    client, isolated_db_engine
):
    with Session(isolated_db_engine) as session:
        collection = ApiCollection(name="Sorted", base_url="https://sorted.example")
        session.add(collection)
        session.flush()
        for name, status, mode in (
            ("zebra", "running", "track"),
            ("Alpha", "pending", "enforce"),
            ("alpha", "pending", "track"),
        ):
            session.add(
                ApiTestRun(
                    collection_id=collection.id,
                    name=name,
                    status=status,
                    coverage_mode=mode,
                )
            )
        session.commit()
        collection_id = collection.id

    url = f"/api/api-collections/{collection_id}/test-runs/page"
    by_name = client.get(url, params={"sort_field": "name", "sort_dir": "asc"})
    assert [row["name"] for row in by_name.json()["items"]] == [
        "Alpha",
        "alpha",
        "zebra",
    ]
    by_status = client.get(url, params={"sort_field": "status", "sort_dir": "desc"})
    assert [row["name"] for row in by_status.json()["items"]] == [
        "zebra",
        "alpha",
        "Alpha",
    ]
    by_mode = client.get(url, params={"sort_field": "coverage_mode", "sort_dir": "asc"})
    assert [row["name"] for row in by_mode.json()["items"]] == [
        "Alpha",
        "zebra",
        "alpha",
    ]


def test_api_runs_page_validates_query_and_collection(client):
    assert client.get("/api/api-collections/9999/test-runs/page").status_code == 404
    response = client.post(
        "/api/api-collections",
        json={"name": "Validation", "base_url": "https://validation.example"},
    )
    assert response.status_code == 201
    url = f"/api/api-collections/{response.json()['id']}/test-runs/page"
    for params in (
        {"page": 0},
        {"page_size": 11},
        {"sort_field": "not_a_field"},
        {"sort_dir": "sideways"},
    ):
        assert client.get(url, params=params).status_code == 422
