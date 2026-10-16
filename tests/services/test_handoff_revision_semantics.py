from __future__ import annotations

from sqlmodel import select

from aespa.models import (
    Credential,
    Site,
    TargetAccessObservation,
    TestRun,
    TrafficEntry,
)
from aespa.services.specialist_handoffs import create_or_get_handoff
from aespa.services.target_catalog import (
    DiscoverySource,
    record_discoveries,
    record_traffic_response,
)


def test_response_nonce_does_not_reopen_handoff_but_access_change_does(db_session) -> None:
    site = Site(name="Handoff", base_url="https://shop.test")
    db_session.add(site)
    db_session.flush()
    run = TestRun(site_id=site.id, name="Handoff")
    credential = Credential(site_id=site.id, username="owner", password="x")
    db_session.add_all([run, credential])
    db_session.commit()
    url = "https://shop.test/orders/101"
    record_discoveries(
        run.id, [url], source=DiscoverySource(None, None, "anonymous", "dom_link"),
    )

    def observation(status: int, body: str) -> int:
        traffic = TrafficEntry(
            test_run_id=run.id, source="httpx", method="GET", url=url,
            username="owner", status=status, response_body=body,
        )
        db_session.add(traffic)
        db_session.commit()
        record_traffic_response(
            run.id, traffic.id, actor=f"credential:{credential.id}",
            verified_credential_id=credential.id,
        )
        return db_session.exec(
            select(TargetAccessObservation).where(
                TargetAccessObservation.test_run_id == run.id,
                TargetAccessObservation.source_id == traffic.id,
            )
        ).one().id

    def claim(evidence_id: int):
        return create_or_get_handoff(
            run_id=run.id, run_kind="web", attack_class="idor", target_url=url,
            page_id=None, parameter="id", session_label=None, priority=8,
            rationale="Compare this order", dispatch_source="test_lead",
            agent_id="specialist", actor_key=f"credential:{credential.id}",
            evidence_observation_ids=(evidence_id,),
        )

    first, created = claim(observation(200, "order nonce=one"))
    assert created is True
    same, created = claim(observation(200, "order nonce=two"))
    assert (same.id, created) == (first.id, False)
    changed, created = claim(observation(403, "denied"))
    assert changed.id != first.id
    assert (changed.status, created) == ("deferred", False)
    owner_one, created = claim(observation(200, '{"owner_id":1,"nonce":"one"}'))
    assert created is False
    assert owner_one.id != first.id
    same_owner, created = claim(observation(200, '{"owner_id":1,"nonce":"two"}'))
    assert (same_owner.id, created) == (owner_one.id, False)
    changed_owner, created = claim(observation(200, '{"owner_id":2,"nonce":"three"}'))
    assert created is False
    assert changed_owner.id != owner_one.id
