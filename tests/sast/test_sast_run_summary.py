from __future__ import annotations

from sqlmodel import Session

from aespa.models import SastRun


def test_sast_run_summary_includes_source_archive_path(client, isolated_db_engine):
    with Session(isolated_db_engine) as session:
        ready = SastRun(
            name="ready",
            status="cancelled",
            source_provider="git",
            source_archive_path="aespa_data/sast_uploads/ready.zip",
        )
        missing = SastRun(name="missing", status="failed", source_provider="git")
        session.add(ready)
        session.add(missing)
        session.commit()
        ready_id, missing_id = ready.id, missing.id

    response = client.get(f"/api/sast-runs/{ready_id}")
    assert response.status_code == 200
    assert response.json()["source_archive_path"] == "aespa_data/sast_uploads/ready.zip"
    assert (
        client.get(f"/api/sast-runs/{missing_id}").json()["source_archive_path"] is None
    )
