"""Deterministic ComponentFact extraction, and the standalone-SAST regression
check that hooking fact extraction into ``sast_scanner`` does not change
standalone (non-campaign) SAST behavior.
"""

from __future__ import annotations

from sqlmodel import Session, select

from aespa.models import CampaignSourceMember, ComponentFact
from aespa.services.component_facts import (
    extract_component_facts,
    interface_fact_fingerprint,
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


def test_extracts_path_aware_spring_security_rules(tmp_path):
    (tmp_path / "SecurityConfig.java").write_text(
        'http.securityMatcher("/api/customer/**")\n'
        '.requestMatchers(HttpMethod.POST, "/api/customer/auth").permitAll()\n'
        ".anyRequest().authenticated();\n"
    )
    facts = extract_component_facts(tmp_path)
    auth_facts = [fact for fact in facts if fact["fact_type"] == "auth_boundary"]

    public = next(fact for fact in auth_facts if fact["name"] == "permitAll")
    assert public["detail"] == {
        "scope": "path",
        "public_paths": ["/api/customer/auth"],
        "public_methods": ["POST"],
    }
    global_rule = next(
        fact for fact in auth_facts if fact["detail"].get("scope") == "global"
    )
    assert global_rule["detail"]["protected_paths"] == ["/api/customer/**"]


def test_interface_fingerprint_ignores_mapper_labels_and_host_explanations():
    first = interface_fact_fingerprint(
        fact_type="http_call",
        method="GET",
        path="/api/customer/profile/",
        host="http://192.168.3.104 (default)",
        name="Customer profile API",
    )
    second = interface_fact_fingerprint(
        fact_type="http_call",
        method="get",
        path="/api/customer/profile",
        host="http://192.168.3.104",
        name="Profile endpoint",
    )
    assert first == second


def test_extracts_framework_marker_from_package_json(tmp_path):
    (tmp_path / "package.json").write_text('{"dependencies": {"express": "^4.0.0"}}')
    facts = extract_component_facts(tmp_path)
    frameworks = [f for f in facts if f["fact_type"] == "framework"]
    assert any(f["name"] == "Express" for f in frameworks)


def test_extracts_frontend_routes_actions_and_axios_calls(tmp_path):
    (tmp_path / "src" / "app" / "checkout").mkdir(parents=True)
    (tmp_path / "src" / "app" / "checkout" / "page.tsx").write_text(
        "<button onClick={submitOrder}>Place order</button>\n"
        'axios.post("/api/orders", { price })\n'
    )
    (tmp_path / "router.tsx").write_text(
        '<Route path="/checkout" element={<Checkout />} />\n'
    )

    facts = extract_component_facts(tmp_path)
    ui_routes = [fact for fact in facts if fact["fact_type"] == "ui_route"]
    actions = [fact for fact in facts if fact["fact_type"] == "ui_action"]
    calls = [fact for fact in facts if fact["fact_type"] == "http_call"]

    assert {fact["path"] for fact in ui_routes} == {"/checkout"}
    assert actions[0]["detail"]["handler"] == "submitOrder"
    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/api/orders"


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


def test_persist_component_facts_reuses_legacy_semantic_llm_fact(
    isolated_db_engine, tmp_path
):
    (tmp_path / "app.py").write_text("@app.route('/orders')\ndef v():\n    pass\n")
    with Session(isolated_db_engine) as s:
        s.add(
            ComponentFact(
                sast_run_id=654,
                fact_type="route",
                method="GET",
                path="/orders",
                name=None,
                detail_json='{"origin":"llm"}',
                evidence_location="app.py:1",
                fingerprint="legacy-label-dependent-fingerprint",
            )
        )
        s.commit()

    persist_component_facts(654, tmp_path)
    with Session(isolated_db_engine) as s:
        facts = s.exec(
            select(ComponentFact).where(ComponentFact.sast_run_id == 654)
        ).all()
    assert len(facts) == 1
    assert facts[0].detail_json == '{"origin":"llm"}'
    assert facts[0].fingerprint == interface_fact_fingerprint(
        fact_type="route",
        method="GET",
        path="/orders",
        host=None,
        name=None,
    )
