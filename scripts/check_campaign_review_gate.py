"""Check the campaign review gate on the real service functions.

The check drives ``submit_review``, ``continue_to_live_testing``, and
``compile_runnable_cases``. It does not start a crawl or a live scan: the
live-testing task is replaced with a no-op after the status commit.

Exit 1 when a promise that currently holds is broken, or when a known
finding reproduces. The finding text is the result, not a checker failure.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from aespa.db import _migrate, get_engine, set_engine
from aespa.models import (
    AssessmentCampaign,
    CampaignTargetMember,
    LeadTargetMapping,
    SastRun,
    ScanLead,
    Site,
    System,
    SystemTarget,
    TestRun,
)
from aespa.services import campaign_validation_cases as cases_svc
from aespa.services import campaigns
from aespa.services import correlation as correlation_svc

SYNC_COMMIT = "06d48d23"
COVERED = (
    "src/aespa/services/campaigns.py submit_review",
    "src/aespa/services/campaigns.py continue_to_live_testing",
    "src/aespa/services/correlation.py apply_review_decisions",
    "src/aespa/services/correlation.py count_pending_mappings",
    "src/aespa/services/campaign_validation_cases.py compile_runnable_cases",
)


@dataclass
class Seed:
    campaign_id: int
    mapping_ids: list[int]
    member_id: int | None = None
    run_id: int | None = None


@dataclass
class Report:
    holds: list[tuple[str, bool, str]] = field(default_factory=list)
    findings: list[tuple[str, str]] = field(default_factory=list)

    def hold(self, name: str, ok: bool, detail: str = "") -> None:
        self.holds.append((name, ok, detail))

    def finding(self, name: str, detail: str) -> None:
        self.findings.append((name, detail))


def _engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _prepare_database() -> None:
    from aespa import models as _models  # noqa: F401

    engine = _engine()
    SQLModel.metadata.create_all(engine)
    _migrate(engine)
    set_engine(engine)


def _seed(
    *,
    name: str,
    status: str = "awaiting_review",
    proposals: int = 1,
    stamped: bool = False,
    mapping_status: str = "proposed",
    with_child_run: bool = False,
) -> Seed:
    with Session(get_engine()) as session:
        system = System(name=name)
        session.add(system)
        session.flush()
        campaign = AssessmentCampaign(system_id=system.id, name=name, status=status)
        if stamped:
            campaign.review_submitted_at = datetime.now(timezone.utc)
        session.add(campaign)
        session.flush()
        mapping_ids: list[int] = []
        member_id = None
        run_id = None
        if proposals or with_child_run:
            site = Site(name=name, base_url="https://app.example.test")
            sast_run = SastRun(name=name, status="completed")
            session.add(site)
            session.add(sast_run)
            session.flush()
            target = SystemTarget(
                system_id=system.id, target_type="site", target_id=site.id
            )
            session.add(target)
            session.flush()
            if with_child_run:
                run = TestRun(site_id=site.id, name=name)
                session.add(run)
                session.flush()
                member = CampaignTargetMember(
                    campaign_id=campaign.id,
                    target_id=target.id,
                    target_type="site",
                    test_run_id=run.id,
                )
                session.add(member)
                session.flush()
                member_id = member.id
                run_id = run.id
            for index in range(proposals):
                lead = ScanLead(
                    producer_run_type="sast",
                    producer_run_id=sast_run.id,
                    title=f"{name} lead {index}",
                    description="A proposed path onto the live site.",
                    fingerprint=f"{name}-{index}",
                    reportable=True,
                    location="app.py:1",
                )
                session.add(lead)
                session.flush()
                mapping = LeadTargetMapping(
                    campaign_id=campaign.id,
                    lead_id=lead.id,
                    target_id=target.id,
                    target_type="site",
                    status=mapping_status,
                    path_json="{}",
                )
                session.add(mapping)
                session.flush()
                mapping_ids.append(mapping.id)
        session.commit()
        return Seed(campaign.id, mapping_ids, member_id, run_id)


def _state(campaign_id: int) -> tuple[str, bool, dict[int, str]]:
    with Session(get_engine()) as session:
        campaign = session.get(AssessmentCampaign, campaign_id)
        mappings = session.exec(
            select(LeadTargetMapping).where(
                LeadTargetMapping.campaign_id == campaign_id
            )
        ).all()
        assert campaign is not None
        return (
            campaign.status,
            campaign.review_submitted_at is not None,
            {mapping.id: mapping.status for mapping in mappings},
        )


def _quiet_live_start(campaign_id: int) -> None:
    original = campaigns._run_dast_wrapper

    async def _quiet(_campaign_id: int) -> None:
        return None

    async def _run() -> None:
        campaigns._run_dast_wrapper = _quiet
        try:
            await campaigns.continue_to_live_testing(campaign_id)
            task = campaigns._campaign_tasks.get(campaign_id)
            if task is not None:
                await task
        finally:
            campaigns._run_dast_wrapper = original
            campaigns._campaign_tasks.pop(campaign_id, None)

    asyncio.run(_run())


def _raises(func, exc_type: type[BaseException]) -> str | None:
    try:
        func()
    except exc_type as exc:
        return str(exc)
    except Exception as exc:
        return f"unexpected {type(exc).__name__}: {exc}"
    return None


def check_sequential(report: Report) -> None:
    pending = _seed(name="empty-while-pending", proposals=1)
    message = _raises(
        lambda: campaigns.submit_review(pending.campaign_id, []),
        campaigns.InvalidReviewDecision,
    )
    status, stamped, mappings = _state(pending.campaign_id)
    report.hold(
        "empty review is refused while a proposal is undecided",
        message is not None and status == "awaiting_review" and not stamped,
        message or f"status={status} stamped={stamped} mappings={mappings}",
    )

    host = _seed(name="foreign-decision", proposals=1)
    other = _seed(name="foreign-decision-other", proposals=1)
    before = _state(host.campaign_id)
    message = _raises(
        lambda: campaigns.submit_review(host.campaign_id, [(other.mapping_ids[0], True)]),
        campaigns.InvalidReviewDecision,
    )
    report.hold(
        "a decision for another campaign is refused and changes nothing",
        message is not None and _state(host.campaign_id) == before,
        message or "state changed",
    )

    partial = _seed(name="partial-review", proposals=2)
    campaigns.submit_review(partial.campaign_id, [(partial.mapping_ids[0], True)])
    status, stamped, mappings = _state(partial.campaign_id)
    report.hold(
        "a partial review records the decision and does not stamp the gate",
        status == "awaiting_review"
        and not stamped
        and mappings[partial.mapping_ids[0]] == "approved"
        and mappings[partial.mapping_ids[1]] == "proposed",
        f"status={status} stamped={stamped} mappings={mappings}",
    )

    complete = _seed(name="complete-review", proposals=1)
    campaigns.submit_review(complete.campaign_id, [(complete.mapping_ids[0], True)])
    status, stamped, mappings = _state(complete.campaign_id)
    report.hold(
        "deciding the last proposal stamps the review and stays in awaiting review",
        status == "awaiting_review" and stamped and mappings[complete.mapping_ids[0]] == "approved",
        f"status={status} stamped={stamped} mappings={mappings}",
    )

    vacant = _seed(name="no-proposals", proposals=0)
    campaigns.submit_review(vacant.campaign_id, [])
    status, stamped, _mappings = _state(vacant.campaign_id)
    report.hold(
        "an empty review stamps the gate only when nothing was proposed",
        status == "awaiting_review" and stamped,
        f"status={status} stamped={stamped}",
    )

    unstamped = _seed(name="start-without-review", proposals=1, stamped=False)
    message = _raises(
        lambda: _quiet_live_start(unstamped.campaign_id),
        campaigns.InvalidCampaignState,
    )
    status, stamped, _mappings = _state(unstamped.campaign_id)
    report.hold(
        "live testing refuses to start before the review is stamped",
        message is not None and "review" in message.lower() and status == "awaiting_review",
        message or f"status={status} stamped={stamped}",
    )

    blocked_statuses = (
        "draft",
        "sast_running",
        "correlating",
        "dast_running",
        "completed",
        "incomplete",
        "stopped",
        "failed",
        "interrupted",
    )
    blocked_ok = True
    blocked_detail: list[str] = []
    for blocked in blocked_statuses:
        seeded = _seed(name=f"start-from-{blocked}", proposals=0, status=blocked, stamped=True)
        message = _raises(
            lambda seeded=seeded: _quiet_live_start(seeded.campaign_id),
            campaigns.InvalidCampaignState,
        )
        status, _stamped, _mappings = _state(seeded.campaign_id)
        ok = message is not None and status == blocked
        blocked_ok = blocked_ok and ok
        if not ok:
            blocked_detail.append(f"{blocked}: {message or status}")
    report.hold(
        "live testing starts only from awaiting review",
        blocked_ok,
        "; ".join(blocked_detail),
    )

    ready = _seed(name="start-after-review", proposals=1, mapping_status="approved", stamped=True)
    _quiet_live_start(ready.campaign_id)
    status, stamped, mappings = _state(ready.campaign_id)
    report.hold(
        "a stamped awaiting-review campaign enters live testing",
        status == "dast_running" and stamped and mappings[ready.mapping_ids[0]] == "approved",
        f"status={status} stamped={stamped} mappings={mappings}",
    )

    message = _raises(
        lambda: campaigns.submit_review(ready.campaign_id, [(ready.mapping_ids[0], False)]),
        campaigns.InvalidCampaignState,
    )
    status, _stamped, mappings = _state(ready.campaign_id)
    report.hold(
        "a review that starts after live testing does not change the mapping",
        message is not None
        and status == "dast_running"
        and mappings[ready.mapping_ids[0]] == "approved",
        message or f"status={status} mappings={mappings}",
    )


def check_review_races_live_start(report: Report) -> None:
    """Park inside the gap between the status read and the decision write."""
    seeded = _seed(
        name="race-review-start",
        proposals=1,
        mapping_status="approved",
        stamped=True,
    )
    entered = threading.Event()
    release = threading.Event()
    real_apply = correlation_svc.apply_review_decisions
    error: list[BaseException] = []

    def _park(campaign_id: int, decisions: list[tuple[int, bool]]) -> dict:
        entered.set()
        if not release.wait(timeout=5):
            raise TimeoutError("live testing did not run during the review gap")
        return real_apply(campaign_id, decisions)

    def _review() -> None:
        try:
            campaigns.submit_review(seeded.campaign_id, [(seeded.mapping_ids[0], False)])
        except BaseException as exc:
            error.append(exc)

    correlation_svc.apply_review_decisions = _park
    worker = threading.Thread(target=_review)
    worker.start()
    try:
        if not entered.wait(timeout=5):
            report.finding(
                "review decision commits after live testing starts",
                "the checker did not reach apply_review_decisions",
            )
            return
        _quiet_live_start(seeded.campaign_id)
        release.set()
        worker.join(timeout=5)
    finally:
        correlation_svc.apply_review_decisions = real_apply
        release.set()
        worker.join(timeout=5)

    status, _stamped, mappings = _state(seeded.campaign_id)
    mapping_status = mappings.get(seeded.mapping_ids[0])
    if error:
        report.hold(
            "the review gap can be exercised",
            False,
            f"{type(error[0]).__name__}: {error[0]}",
        )
        return
    if status == "dast_running" and mapping_status == "rejected":
        report.finding(
            "review decision commits after live testing starts",
            "submit_review passed its awaiting_review check, "
            "continue_to_live_testing then committed dast_running, "
            "and apply_review_decisions still rejected the mapping. "
            f"Campaign {seeded.campaign_id} is {status}; "
            f"mapping {seeded.mapping_ids[0]} is {mapping_status}.",
        )
        return
    report.hold(
        "a review already past its status check cannot change a mapping after live testing starts",
        status == "dast_running" and mapping_status == "approved",
        f"status={status} mapping={mapping_status}",
    )


def check_rejected_case_is_not_queued(report: Report) -> None:
    seeded = _seed(
        name="rejected-resolved-case",
        proposals=1,
        mapping_status="approved",
        stamped=True,
        status="dast_running",
        with_child_run=True,
    )
    assert seeded.member_id is not None
    with Session(get_engine()) as session:
        mapping = session.get(LeadTargetMapping, seeded.mapping_ids[0])
        member = session.get(CampaignTargetMember, seeded.member_id)
        assert mapping is not None and member is not None
        cases_svc.upsert_validation_case(
            session,
            mapping,
            member,
            readiness_status=cases_svc.READINESS_RESOLVED,
            static_path={"schema_version": 3, "perspective": "frontend"},
        )
        mapping.status = "rejected"
        session.add(mapping)
        session.commit()
    compiled = cases_svc.compile_runnable_cases(seeded.campaign_id, seeded.member_id)
    if compiled.copied_lead_ids:
        report.finding(
            "compile queues a resolved case after its mapping was rejected",
            "compile_runnable_cases copied lead "
            f"{compiled.copied_lead_ids} for mapping {seeded.mapping_ids[0]} "
            "while that mapping's status was rejected. "
            "The copy query filters on readiness_status == resolved and does not "
            "read LeadTargetMapping.status.",
        )
        return
    report.hold(
        "compile does not queue a resolved case whose mapping is rejected",
        True,
        f"warnings={compiled.warnings}",
    )


def _head_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def main() -> int:
    os.environ.setdefault("AESPA_DATA_DIR", tempfile.mkdtemp(prefix="aespa-review-gate-"))
    _prepare_database()
    report = Report()
    check_sequential(report)
    check_review_races_live_start(report)
    check_rejected_case_is_not_queued(report)

    head = _head_commit()
    print("campaign review gate")
    print(f"recorded sync commit: {SYNC_COMMIT}")
    print(f"HEAD: {head}")
    if not head.startswith(SYNC_COMMIT):
        print(
            "HEAD is not the recorded sync commit. Re-read the covered functions "
            "before trusting this result, and move the sync commit only after "
            "the check still describes them."
        )
    print("covers:")
    for item in COVERED:
        print(f"  {item}")
    print("holds:")
    failed = False
    for name, ok, detail in report.holds:
        print(f"  {'PASS' if ok else 'FAIL'} {name}")
        if detail and not ok:
            print(f"    {detail}")
        failed = failed or not ok
    print("findings:")
    if not report.findings:
        print("  none")
    for name, detail in report.findings:
        print(f"  FINDING {name}")
        print(f"    {detail}")
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
