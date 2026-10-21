from __future__ import annotations

from sqlmodel import Session

from aespa.models import Credential, Site


def test_site_header_returns_only_display_fields(client, isolated_db_engine):
    with Session(isolated_db_engine) as session:
        site = Site(
            name="Example",
            base_url="https://example.test",
            requires_auth=True,
            workflow_data_json='[{"name":"saved workflow"}]',
        )
        session.add(site)
        session.flush()
        session.add(Credential(site_id=site.id, username="admin", password="secret"))
        session.commit()
        site_id = site.id

    response = client.get(f"/api/sites/{site_id}/header")
    assert response.status_code == 200
    assert response.json() == {
        "id": site_id,
        "name": "Example",
        "base_url": "https://example.test",
        "requires_auth": True,
        "credential_count": 1,
    }
    assert client.get("/api/sites/999999/header").status_code == 404
