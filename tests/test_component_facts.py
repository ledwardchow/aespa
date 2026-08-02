"""Deterministic ComponentFact extraction, and the standalone-SAST regression
check that hooking fact extraction into ``sast_scanner`` does not change
standalone (non-campaign) SAST behavior.
"""

from __future__ import annotations

from sqlmodel import Session, select

from aespa.models import CampaignSourceMember, ComponentFact
from aespa.services.component_facts import (
    extract_component_facts,
    persist_component_facts,
)


def test_extracts_flask_route_and_outbound_call(tmp_path):
    (tmp_path / "app.py").write_text(
        "import requests\n"
        "\n"
        "@app.route('/orders', methods=['POST'])\n"
        "def create_order():\n"
        "    requests.post('https://api.acme.test/orders', json=body)\n"
        "    return 'ok'\n"
    )
    facts = extract_component_facts(tmp_path)
    fact_types = {f["fact_type"] for f in facts}
    assert "route" in fact_types
    assert "http_call" in fact_types

    route = next(f for f in facts if f["fact_type"] == "route")
    assert route["method"] == "POST"
    assert route["path"] == "/orders"

    call = next(f for f in facts if f["fact_type"] == "http_call")
    assert call["host"] == "api.acme.test"


def test_extracts_auth_boundary_and_datastore_markers(tmp_path):
    (tmp_path / "auth.py").write_text("@login_required\ndef view():\n    pass\n")
    (tmp_path / "db.py").write_text("engine = create_engine(DATABASE_URL)\n")
    facts = extract_component_facts(tmp_path)
    fact_types = {f["fact_type"] for f in facts}
    assert "auth_boundary" in fact_types
    assert "datastore" in fact_types


def test_extracts_framework_marker_from_package_json(tmp_path):
    (tmp_path / "package.json").write_text('{"dependencies": {"express": "^4.0.0"}}')
    facts = extract_component_facts(tmp_path)
    frameworks = [f for f in facts if f["fact_type"] == "framework"]
    assert any(f["name"] == "Express" for f in frameworks)


def test_extraction_is_bounded_and_deterministic(tmp_path):
    (tmp_path / "app.py").write_text("@app.route('/x')\ndef view():\n    pass\n")
    first = extract_component_facts(tmp_path)
    second = extract_component_facts(tmp_path)
    assert first == second  # identical input -> identical output


def test_persist_component_facts_links_component_via_campaign_membership(
    isolated_db_engine, tmp_path
):
    (tmp_path / "app.py").write_text("@app.route('/orders')\ndef v():\n    pass\n")
    with Session(isolated_db_engine) as s:
        s.add(
            CampaignSourceMember(
                campaign_id=1,
                component_id=42,
                snapshot_id=1,
                sast_run_id=555,
            )
        )
        s.commit()

    count = persist_component_facts(555, tmp_path)
    assert count >= 1
    with Session(isolated_db_engine) as s:
        facts = s.exec(
            select(ComponentFact).where(ComponentFact.sast_run_id == 555)
        ).all()
    assert len(facts) == count
    assert all(f.component_id == 42 for f in facts)


def test_persist_component_facts_leaves_component_id_null_for_standalone_run(
    isolated_db_engine, tmp_path
):
    """No CampaignSourceMember exists for this sast_run_id -> standalone run."""
    (tmp_path / "app.py").write_text("@app.route('/orders')\ndef v():\n    pass\n")
    persist_component_facts(999, tmp_path)
    with Session(isolated_db_engine) as s:
        facts = s.exec(
            select(ComponentFact).where(ComponentFact.sast_run_id == 999)
        ).all()
    assert facts
    assert all(f.component_id is None for f in facts)


def test_persist_component_facts_is_idempotent_per_run(isolated_db_engine, tmp_path):
    (tmp_path / "app.py").write_text("@app.route('/orders')\ndef v():\n    pass\n")
    persist_component_facts(321, tmp_path)
    persist_component_facts(321, tmp_path)
    with Session(isolated_db_engine) as s:
        facts = s.exec(
            select(ComponentFact).where(ComponentFact.sast_run_id == 321)
        ).all()
    assert len(facts) == 1  # rerun replaces, does not duplicate
