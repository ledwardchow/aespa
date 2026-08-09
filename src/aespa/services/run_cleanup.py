"""Reusable cascade-delete helpers for scan runs.

Run ids are globally unique now, but explicit cleanup still matters because it
removes the run's stored evidence, logs, sessions, and temporary lead copies.
The identity anchor is deleted last so the database foreign keys can cascade
anything a new child table adds in the future.

Each table is scoped to the run kind: findings/traffic key on the dedicated
``api_test_run_id`` column; coverage cells FK to ``api_test_run``; logs, scanner
sessions, and alice chats share the ``test_run_id`` column with web runs and are
disambiguated by ``run_kind`` / ``producer_run_type``.

The helpers ``session.delete`` rows but do not commit — the caller commits once,
so a collection delete can cascade many runs atomically.

**Campaign child runs** can also be changed or deleted from their ordinary
run screens. Deleting one detaches its campaign member and returns that member
to ``pending`` so the campaign can resume the action without a stale run id.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, text
from sqlmodel import Session, select

from aespa.models import (
    AgentLog,
    AliceChatMessage,
    AliceChatSession,
    ApiEndpointTest,
    ApiTestRun,
    AssessmentCampaign,
    CampaignSourceMember,
    CampaignTargetMember,
    ComponentConnection,
    ComponentFact,
    ComponentSnapshot,
    CoverageEvidence,
    CrawledPage,
    LeadTargetMapping,
    PageCredentialView,
    PageLink,
    PageOwaspTest,
    PhaseCheckpoint,
    ProbeExecution,
    RunIdentity,
    SastRun,
    ScanCheckpoint,
    ScanFinding,
    ScanLead,
    ScanLeadComponentProvenance,
    ScanLog,
    ScannerSession,
    ScanObligation,
    TargetIntelItem,
    TestRun,
    TrafficEntry,
)


def _delete_run_identity(session: Session, run_id: int, run) -> None:
    """Remove the identity anchor after its type-specific row is gone.

    Child run records point to ``run_identity`` with database-level cascade
    rules.  The explicit flush makes deletion safe on SQLite with foreign-key
    enforcement enabled, while the direct child cleanup below remains usable
    on older databases that have not been migrated yet.
    """
    if run is not None:
        session.delete(run)
        session.flush()
    session.execute(delete(RunIdentity).where(RunIdentity.id == run_id))


def cascade_delete_web_run(session: Session, run_id: int) -> None:
    """Delete a web ``TestRun`` and every row owned by it.

    Web run ids can be reused by SQLite after the parent row is deleted.  The
    cleanup therefore covers both the original crawl tables and the newer scan
    workprogram/evidence tables.  Rows shared with API runs are filtered by
    ``run_kind`` or the dedicated API run column so a colliding API id is not
    removed accidentally.
    """
    for member in session.exec(
        select(CampaignTargetMember).where(CampaignTargetMember.test_run_id == run_id)
    ).all():
        member.test_run_id = None
        member.status = "pending"
        member.updated_at = datetime.now(timezone.utc)
        session.add(member)

    # Capture IDs before deleting their parents so dependent rows can be removed
    # in a foreign-key-safe order.
    pages = session.exec(
        select(CrawledPage).where(CrawledPage.test_run_id == run_id)
    ).all()
    findings = session.exec(
        select(ScanFinding)
        .where(ScanFinding.test_run_id == run_id)
        .where(ScanFinding.api_test_run_id == None)  # noqa: E711
    ).all()
    finding_ids = [finding.id for finding in findings if finding.id is not None]

    executions = session.exec(
        select(ProbeExecution)
        .where(ProbeExecution.run_kind == "web")
        .where(ProbeExecution.run_id == run_id)
    ).all()
    execution_ids = [
        execution.id for execution in executions if execution.id is not None
    ]

    for lead in session.exec(
        select(ScanLead)
        .where(ScanLead.imported_into_run_type == "web")
        .where(ScanLead.imported_into_run_id == run_id)
    ).all():
        session.delete(lead)
    for lead in session.exec(
        select(ScanLead)
        .where(ScanLead.investigated_by_run_type == "web")
        .where(ScanLead.investigated_by_run_id == run_id)
    ).all():
        lead.investigated_by_run_type = None
        lead.investigated_by_run_id = None
        session.add(lead)
    if finding_ids:
        for lead in session.exec(
            select(ScanLead).where(ScanLead.linked_finding_id.in_(finding_ids))
        ).all():
            lead.linked_finding_id = None
            session.add(lead)

    # Messages depend on chat sessions.  Evidence depends on probe executions,
    # which depend on obligations and may reference captured traffic.
    for chat in session.exec(
        select(AliceChatSession)
        .where(AliceChatSession.test_run_id == run_id)
        .where(AliceChatSession.run_kind == "web")
    ).all():
        for message in session.exec(
            select(AliceChatMessage).where(AliceChatMessage.session_id == chat.id)
        ).all():
            session.delete(message)
        session.delete(chat)

    if execution_ids:
        for evidence in session.exec(
            select(CoverageEvidence).where(
                CoverageEvidence.execution_id.in_(execution_ids)
            )
        ).all():
            session.delete(evidence)
    for execution in executions:
        session.delete(execution)

    # Findings and page workprogram cells must go before crawled pages because
    # both carry page references.
    for finding in findings:
        session.delete(finding)
    for cell in session.exec(
        select(PageOwaspTest).where(PageOwaspTest.test_run_id == run_id)
    ).all():
        session.delete(cell)
    for link in session.exec(
        select(PageLink).where(PageLink.test_run_id == run_id)
    ).all():
        session.delete(link)
    for view in session.exec(
        select(PageCredentialView).where(PageCredentialView.test_run_id == run_id)
    ).all():
        session.delete(view)
    for item in session.exec(
        select(TargetIntelItem).where(TargetIntelItem.test_run_id == run_id)
    ).all():
        session.delete(item)
    for entry in session.exec(
        select(TrafficEntry)
        .where(TrafficEntry.test_run_id == run_id)
        .where(TrafficEntry.api_test_run_id == None)  # noqa: E711
    ).all():
        session.delete(entry)
    for page in pages:
        session.delete(page)

    # These tables retain a surface marker for compatibility and presentation.
    for model in (ScannerSession, ScanLog, AgentLog):
        for row in session.exec(
            select(model)
            .where(model.test_run_id == run_id)
            .where(model.run_kind == "web")
        ).all():
            session.delete(row)
    for checkpoint in session.exec(
        select(ScanCheckpoint).where(ScanCheckpoint.test_run_id == run_id)
    ).all():
        session.delete(checkpoint)
    for checkpoint in session.exec(
        select(PhaseCheckpoint)
        .where(PhaseCheckpoint.run_kind == "web")
        .where(PhaseCheckpoint.run_id == run_id)
    ).all():
        session.delete(checkpoint)
    for obligation in session.exec(
        select(ScanObligation)
        .where(ScanObligation.run_kind == "web")
        .where(ScanObligation.run_id == run_id)
    ).all():
        session.delete(obligation)

    # Retired task-queue tables may still exist in upgraded databases even
    # though their ORM models are no longer part of the application.
    # Query through this Session.  Inspecting the Engine would borrow the same
    # StaticPool connection in tests and can roll back the uncommitted deletes.
    table_names = {
        row[0]
        for row in session.exec(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        ).all()
    }
    if "pentest_task" in table_names:
        session.exec(
            text("DELETE FROM pentest_task WHERE test_run_id = :run_id").bindparams(
                run_id=run_id
            )
        )
    if "pentest_hypothesis" in table_names:
        session.exec(
            text(
                "DELETE FROM pentest_hypothesis WHERE test_run_id = :run_id"
            ).bindparams(run_id=run_id)
        )

    # A SAST run explicitly linked as being spawned by this web run is also a
    # child.  Its own helper removes its original leads and activity rows.
    for sast_run in session.exec(
        select(SastRun)
        .where(SastRun.triggered_by_run_type == "web")
        .where(SastRun.triggered_by_run_id == run_id)
    ).all():
        if sast_run.id is not None:
            cascade_delete_sast_run(session, sast_run.id)

    run = session.get(TestRun, run_id)
    _delete_run_identity(session, run_id, run)


def cascade_delete_api_run(session: Session, run_id: int) -> None:
    """Delete an ``ApiTestRun`` and every row that keys on it."""
    for member in session.exec(
        select(CampaignTargetMember).where(
            CampaignTargetMember.api_test_run_id == run_id
        )
    ).all():
        member.api_test_run_id = None
        member.status = "pending"
        member.updated_at = datetime.now(timezone.utc)
        session.add(member)

    for finding in session.exec(
        select(ScanFinding).where(ScanFinding.api_test_run_id == run_id)
    ).all():
        session.delete(finding)
    for entry in session.exec(
        select(TrafficEntry).where(TrafficEntry.api_test_run_id == run_id)
    ).all():
        session.delete(entry)
    for cell in session.exec(
        select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == run_id)
    ).all():
        session.delete(cell)
    for lead in session.exec(
        select(ScanLead)
        .where(ScanLead.imported_into_run_type == "api")
        .where(ScanLead.imported_into_run_id == run_id)
    ).all():
        session.delete(lead)
    for ss in session.exec(
        select(ScannerSession)
        .where(ScannerSession.test_run_id == run_id)
        .where(ScannerSession.run_kind == "api")
    ).all():
        session.delete(ss)
    for slog in session.exec(
        select(ScanLog)
        .where(ScanLog.test_run_id == run_id)
        .where(ScanLog.run_kind == "api")
    ).all():
        session.delete(slog)
    for sess in session.exec(
        select(AliceChatSession)
        .where(AliceChatSession.test_run_id == run_id)
        .where(AliceChatSession.run_kind == "api")
    ).all():
        for msg in session.exec(
            select(AliceChatMessage).where(AliceChatMessage.session_id == sess.id)
        ).all():
            session.delete(msg)
        session.delete(sess)
    for log in session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == run_id)
        .where(AgentLog.run_kind == "api")
    ).all():
        session.delete(log)
    run = session.get(ApiTestRun, run_id)
    _delete_run_identity(session, run_id, run)


def cascade_delete_sast_run(session: Session, run_id: int) -> None:
    """Delete a ``SastRun`` and every row that keys on it.

    Only the *original* leads are removed (``imported_into_run_id IS NULL``):
    copies imported into a dynamic run keep ``producer_run_id`` pointing here but
    belong to that run and are cleaned up when the run is deleted instead.
    """
    for member in session.exec(
        select(CampaignSourceMember).where(CampaignSourceMember.sast_run_id == run_id)
    ).all():
        member.sast_run_id = None
        member.status = "pending"
        member.updated_at = datetime.now(timezone.utc)
        session.add(member)

    for lead in session.exec(
        select(ScanLead)
        .where(ScanLead.producer_run_id == run_id)
        .where(ScanLead.producer_run_type == "sast")
        .where(ScanLead.imported_into_run_id == None)  # noqa: E711
    ).all():
        session.delete(lead)
    for slog in session.exec(
        select(ScanLog)
        .where(ScanLog.test_run_id == run_id)
        .where(ScanLog.run_kind == "sast")
    ).all():
        session.delete(slog)
    for log in session.exec(
        select(AgentLog)
        .where(AgentLog.test_run_id == run_id)
        .where(AgentLog.run_kind == "sast")
    ).all():
        session.delete(log)
    for fact in session.exec(
        select(ComponentFact).where(ComponentFact.sast_run_id == run_id)
    ).all():
        session.delete(fact)
    run = session.get(SastRun, run_id)
    if run is not None:
        # Remove the stored archive only when this run owns it exclusively.
        # A campaign-created run's ``source_archive_path`` points at a shared,
        # immutable ``ComponentSnapshot`` file that other campaigns may still
        # reference — deleting a run must never delete that file out from
        # under the snapshot row. Only a run whose archive path is NOT a
        # known snapshot (i.e. a standalone upload under sast_uploads/) is
        # safe to remove here.
        if run.source_archive_path:
            is_shared_snapshot = (
                session.exec(
                    select(ComponentSnapshot.id).where(
                        ComponentSnapshot.stored_path == run.source_archive_path
                    )
                ).first()
                is not None
            )
            if not is_shared_snapshot:
                try:
                    import os

                    if os.path.isfile(run.source_archive_path):
                        os.remove(run.source_archive_path)
                except OSError:
                    pass
        _delete_run_identity(session, run_id, run)


def cascade_delete_campaign(session: Session, campaign_id: int) -> None:
    """Delete an ``AssessmentCampaign`` and every row/child run it owns.

    A campaign wholly owns the child SAST/web/API runs it created (they exist
    only because the campaign asked for them), so deleting it cascades into
    those runs' own cascade helpers instead of leaving them orphaned. Original
    cross-repository leads it authored (``producer_run_type == "campaign"``)
    are removed directly; their imported copies are already covered by the
    child dynamic-run cascades below.

    FK-safe order matters here (verified with SQLite foreign-key enforcement
    on): every row that references a ``ScanLead``/``ComponentFact`` —
    ``LeadTargetMapping``, ``ComponentConnection``, and
    ``ScanLeadComponentProvenance`` — is deleted and flushed *before* the
    child-run cascades remove the leads/facts they point to. Deleting a
    ``ComponentFact`` while a ``ComponentConnection`` still references it (or
    a ``ScanLead`` while a ``LeadTargetMapping``/``ScanLeadComponentProvenance``
    still references it) would otherwise violate their foreign keys.
    """
    for connection in session.exec(
        select(ComponentConnection).where(
            ComponentConnection.campaign_id == campaign_id
        )
    ).all():
        session.delete(connection)

    for mapping in session.exec(
        select(LeadTargetMapping).where(LeadTargetMapping.campaign_id == campaign_id)
    ).all():
        session.delete(mapping)

    campaign_leads = session.exec(
        select(ScanLead)
        .where(ScanLead.producer_run_type == "campaign")
        .where(ScanLead.producer_run_id == campaign_id)
        .where(ScanLead.imported_into_run_id == None)  # noqa: E711
    ).all()
    campaign_lead_ids = [lead.id for lead in campaign_leads if lead.id is not None]
    if campaign_lead_ids:
        for provenance in session.exec(
            select(ScanLeadComponentProvenance).where(
                ScanLeadComponentProvenance.scan_lead_id.in_(campaign_lead_ids)
            )
        ).all():
            session.delete(provenance)

    # Flush now: the rows referencing facts/leads are gone from the session's
    # pending state, so the child-run cascades below can safely delete the
    # ComponentFact/ScanLead rows those references pointed to.
    session.flush()

    for source in session.exec(
        select(CampaignSourceMember).where(
            CampaignSourceMember.campaign_id == campaign_id
        )
    ).all():
        if source.sast_run_id is not None:
            cascade_delete_sast_run(session, source.sast_run_id)
        session.delete(source)

    for target in session.exec(
        select(CampaignTargetMember).where(
            CampaignTargetMember.campaign_id == campaign_id
        )
    ).all():
        if target.test_run_id is not None:
            cascade_delete_web_run(session, target.test_run_id)
        if target.api_test_run_id is not None:
            cascade_delete_api_run(session, target.api_test_run_id)
        session.delete(target)

    # The campaign-owned cross-repo leads themselves can now go — their
    # provenance rows were already removed above.
    for lead in campaign_leads:
        session.delete(lead)
    session.flush()

    campaign = session.get(AssessmentCampaign, campaign_id)
    _delete_run_identity(session, campaign_id, campaign)
