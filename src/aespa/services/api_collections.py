"""Service-layer CRUD for API Collections.

Pure functions taking a SQLModel ``Session``, mirroring ``services.sites``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlmodel import Session, select

from aespa.models import ApiCollection
from aespa.schemas import ApiCollectionCreate, ApiCollectionUpdate


class ApiCollectionServiceError(Exception):
    """Base class for service-layer errors."""


class ApiCollectionNotFound(ApiCollectionServiceError):
    pass


class DuplicateApiCollectionName(ApiCollectionServiceError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# API-scan traffic has no real TestRun row; traffic._write stores this sentinel
# in the NOT NULL test_run_id column and keys the real run on api_test_run_id.
_API_TRAFFIC_SENTINEL_RUN_ID = 0


def list_collections(session: Session) -> list[ApiCollection]:
    return list(session.exec(select(ApiCollection).order_by(ApiCollection.name)).all())


def get_collection(session: Session, collection_id: int) -> ApiCollection:
    collection = session.get(ApiCollection, collection_id)
    if collection is None:
        raise ApiCollectionNotFound(f"API collection id={collection_id} does not exist")
    return collection


def get_collection_by_name(session: Session, name: str) -> ApiCollection | None:
    return session.exec(select(ApiCollection).where(ApiCollection.name == name)).first()


def _ensure_unique_name(
    session: Session, name: str, *, ignore_id: int | None = None
) -> None:
    existing = get_collection_by_name(session, name)
    if existing is None:
        return
    if ignore_id is not None and existing.id == ignore_id:
        return
    raise DuplicateApiCollectionName(f"An API collection named {name!r} already exists")


def create_collection(session: Session, payload: ApiCollectionCreate) -> ApiCollection:
    _ensure_unique_name(session, payload.name)

    collection = ApiCollection(
        name=payload.name,
        base_url=str(payload.base_url),
        description=payload.description,
        servers=json.dumps([str(s) for s in payload.servers]),
        scope_hosts=json.dumps(payload.scope_hosts),
    )
    session.add(collection)
    session.commit()
    session.refresh(collection)
    return collection


def update_collection(
    session: Session, collection_id: int, payload: ApiCollectionUpdate
) -> ApiCollection:
    collection = get_collection(session, collection_id)
    _ensure_unique_name(session, payload.name, ignore_id=collection.id)

    collection.name = payload.name
    collection.base_url = str(payload.base_url)
    collection.description = payload.description
    collection.servers = json.dumps([str(s) for s in payload.servers])
    collection.scope_hosts = json.dumps(payload.scope_hosts)
    collection.updated_at = _utcnow()

    session.add(collection)
    session.commit()
    session.refresh(collection)
    return collection


def delete_collection(session: Session, collection_id: int) -> None:
    """Delete a collection and every row that hangs off it.

    Like the run ids, ``ApiCollection`` ids are reused by SQLite, so any child
    left behind (runs, findings, endpoints, uploaded docs, …) would resurface
    under a newly created collection that reuses the freed id.  Cascade through
    every child: API/SAST runs go via the shared ``run_cleanup`` helpers so their
    findings/traffic/logs are cleaned too.
    """
    from pathlib import Path

    from aespa.models import (
        ApiCredential,
        ApiDocument,
        ApiEndpoint,
        ApiTestRun,
        SastRun,
        ScanLead,
    )
    from aespa.services import run_cleanup

    collection = get_collection(session, collection_id)

    for run in session.exec(
        select(ApiTestRun).where(ApiTestRun.collection_id == collection_id)
    ).all():
        run_cleanup.cascade_delete_api_run(session, run.id)
    for run in session.exec(
        select(SastRun).where(SastRun.collection_id == collection_id)
    ).all():
        run_cleanup.cascade_delete_sast_run(session, run.id)
    # Leads carry a collection_id of their own; sweep any not tied to a SAST run.
    for lead in session.exec(
        select(ScanLead).where(ScanLead.collection_id == collection_id)
    ).all():
        session.delete(lead)
    for ep in session.exec(
        select(ApiEndpoint).where(ApiEndpoint.collection_id == collection_id)
    ).all():
        session.delete(ep)
    for cred in session.exec(
        select(ApiCredential).where(ApiCredential.collection_id == collection_id)
    ).all():
        session.delete(cred)
    for doc in session.exec(
        select(ApiDocument).where(ApiDocument.collection_id == collection_id)
    ).all():
        try:
            path = Path(doc.stored_path)
            if path.is_file():
                path.unlink()
        except OSError:
            pass
        session.delete(doc)

    session.delete(collection)
    session.commit()


# ── Export / Import ──────────────────────────────────────────────────────────
# Parallel to services.sites.export_site/import_site, but for an ApiCollection:
# its documents, endpoints, credentials, API test runs (+ findings/traffic/
# workprogram/logs/ALICE), and SAST runs + leads (+ SAST logs). source_zip bytes
# are dropped — leads are self-contained text; only re-running SAST needs them.


def export_collection(session: Session, collection_id: int) -> dict:
    """Return a portable, self-contained dict for a collection and all its data.

    Uploaded document bytes are inlined as base64 so the bundle re-parses on a
    fresh installation. Primary keys are preserved so import_collection() can
    remap them.
    """
    import base64
    from pathlib import Path

    from aespa.models import (
        AgentLog,
        AliceChatMessage,
        AliceChatSession,
        ApiCredential,
        ApiDocument,
        ApiEndpoint,
        ApiEndpointTest,
        ApiTestRun,
        SastRun,
        ScanFinding,
        ScanLead,
        ScanLog,
        ScannerSession,
        TrafficEntry,
    )

    collection = get_collection(session, collection_id)

    def _row(obj) -> dict:
        return obj.model_dump(mode="json")

    def _doc_row(doc: ApiDocument) -> dict:
        row = _row(doc)
        # source_zip archives can be 25 MiB; SAST leads are self-contained, so we
        # skip the bytes. Other docs (specs) inline their bytes for re-parse.
        if doc.doc_type == "source_zip":
            row["content_b64"] = None
        else:
            try:
                row["content_b64"] = base64.b64encode(
                    Path(doc.stored_path).read_bytes()
                ).decode("ascii")
            except OSError:
                row["content_b64"] = None  # file gone — metadata still travels
        row.pop("stored_path", None)  # rewritten on import
        return row

    docs = list(
        session.exec(
            select(ApiDocument).where(ApiDocument.collection_id == collection_id)
        ).all()
    )
    endpoints = list(
        session.exec(
            select(ApiEndpoint).where(ApiEndpoint.collection_id == collection_id)
        ).all()
    )
    creds = list(
        session.exec(
            select(ApiCredential).where(ApiCredential.collection_id == collection_id)
        ).all()
    )
    runs = list(
        session.exec(
            select(ApiTestRun).where(ApiTestRun.collection_id == collection_id)
        ).all()
    )
    sast_runs = list(
        session.exec(
            select(SastRun).where(SastRun.collection_id == collection_id)
        ).all()
    )
    leads = list(
        session.exec(
            select(ScanLead).where(ScanLead.collection_id == collection_id)
        ).all()
    )

    sast_bundles = []
    for sr in sast_runs:
        srid = sr.id
        sast_bundles.append(
            {
                "sast_run": _row(sr),
                "scan_logs": [
                    _row(sl)
                    for sl in session.exec(
                        select(ScanLog)
                        .where(ScanLog.test_run_id == srid)
                        .where(ScanLog.run_kind == "sast")
                    ).all()
                ],
                "agent_logs": [
                    _row(a)
                    for a in session.exec(
                        select(AgentLog)
                        .where(AgentLog.test_run_id == srid)
                        .where(AgentLog.run_kind == "sast")
                    ).all()
                ],
            }
        )

    run_bundles = []
    for run in runs:
        rid = run.id
        findings = list(
            session.exec(
                select(ScanFinding).where(ScanFinding.api_test_run_id == rid)
            ).all()
        )
        traffic = list(
            session.exec(
                select(TrafficEntry).where(TrafficEntry.api_test_run_id == rid)
            ).all()
        )
        cells = list(
            session.exec(
                select(ApiEndpointTest).where(ApiEndpointTest.api_test_run_id == rid)
            ).all()
        )
        sessions_ = list(
            session.exec(
                select(ScannerSession)
                .where(ScannerSession.test_run_id == rid)
                .where(ScannerSession.run_kind == "api")
            ).all()
        )
        logs = list(
            session.exec(
                select(ScanLog)
                .where(ScanLog.test_run_id == rid)
                .where(ScanLog.run_kind == "api")
            ).all()
        )
        agent_logs = list(
            session.exec(
                select(AgentLog)
                .where(AgentLog.test_run_id == rid)
                .where(AgentLog.run_kind == "api")
            ).all()
        )
        alice_sessions = list(
            session.exec(
                select(AliceChatSession)
                .where(AliceChatSession.test_run_id == rid)
                .where(AliceChatSession.run_kind == "api")
            ).all()
        )
        alice_sess_ids = [s.id for s in alice_sessions]
        alice_messages = (
            list(
                session.exec(
                    select(AliceChatMessage).where(
                        AliceChatMessage.session_id.in_(alice_sess_ids)
                    )
                ).all()
            )
            if alice_sess_ids
            else []
        )

        run_bundles.append(
            {
                "api_test_run": _row(run),
                "scan_findings": [_row(f) for f in findings],
                "traffic_entries": [_row(t) for t in traffic],
                "endpoint_tests": [_row(c) for c in cells],
                "scanner_sessions": [_row(s) for s in sessions_],
                "scan_logs": [_row(sl) for sl in logs],
                "agent_logs": [_row(a) for a in agent_logs],
                "alice_chat_sessions": [_row(s) for s in alice_sessions],
                "alice_chat_messages": [_row(m) for m in alice_messages],
            }
        )

    return {
        "export_version": 1,
        "kind": "api-collection",
        "exported_at": _utcnow().isoformat(),
        "collection": _row(collection),
        "documents": [_doc_row(d) for d in docs],
        "endpoints": [_row(e) for e in endpoints],
        "credentials": [_row(c) for c in creds],
        "test_runs": run_bundles,
        "sast_runs": sast_bundles,
        "scan_leads": [_row(ld) for ld in leads],
    }


def import_collection(session: Session, bundle: dict) -> ApiCollection:
    """Create a new collection from a bundle produced by export_collection().

    All primary keys are remapped to avoid colliding with existing rows; the
    collection name gets a numeric suffix if taken. llm_config_id / sast_run_id
    are dropped because they cannot be mapped across installations.
    """
    import base64
    from pathlib import Path

    from aespa.models import (
        AgentLog,
        AliceChatMessage,
        AliceChatSession,
        ApiCredential,
        ApiDocument,
        ApiEndpoint,
        ApiEndpointTest,
        ApiTestRun,
        SastRun,
        ScanFinding,
        ScanLead,
        ScanLog,
        ScannerSession,
        TrafficEntry,
    )
    from aespa.services.api_documents import _storage_dir
    from aespa.services.sites import _parse_datetimes

    if bundle.get("export_version") != 1 or bundle.get("kind") != "api-collection":
        raise ApiCollectionServiceError(
            f"Unsupported or non-API export bundle: version={bundle.get('export_version')!r} kind={bundle.get('kind')!r}"
        )

    # ── Collection ─────────────────────────────────────────────────────────────
    col_data = {
        k: v
        for k, v in bundle["collection"].items()
        if k not in ("id", "created_at", "updated_at")
    }
    name = col_data["name"]
    candidate, counter = name, 2
    while get_collection_by_name(session, candidate) is not None:
        candidate = f"{name} ({counter})"
        counter += 1
    col_data["name"] = candidate

    collection = ApiCollection(**col_data)
    session.add(collection)
    session.flush()
    new_cid: int = collection.id  # type: ignore[assignment]

    # ── Documents (write inlined bytes to new storage) ──────────────────────────
    doc_id_map: dict[int, int] = {}
    for d in bundle.get("documents", []):
        d = dict(d)
        old_id = d.pop("id")
        content_b64 = d.pop("content_b64", None)
        d["collection_id"] = new_cid
        if content_b64:
            ext = Path(d.get("filename", "")).suffix
            import uuid

            path = _storage_dir(new_cid) / f"{uuid.uuid4().hex}{ext}"
            path.write_bytes(base64.b64decode(content_b64))
            d["stored_path"] = str(path)
        else:
            d["stored_path"] = ""  # bytes were missing at export time
        _parse_datetimes(d, "created_at")
        doc = ApiDocument(**d)
        session.add(doc)
        session.flush()
        doc_id_map[old_id] = doc.id  # type: ignore[index]

    # ── Endpoints ────────────────────────────────────────────────────────────────
    endpoint_id_map: dict[int, int] = {}
    for e in bundle.get("endpoints", []):
        e = dict(e)
        old_id = e.pop("id")
        e["collection_id"] = new_cid
        old_doc = e.get("source_doc_id")
        if old_doc is not None:
            e["source_doc_id"] = doc_id_map.get(old_doc)
        _parse_datetimes(e, "created_at")
        ep = ApiEndpoint(**e)
        session.add(ep)
        session.flush()
        endpoint_id_map[old_id] = ep.id  # type: ignore[index]

    # ── Credentials ──────────────────────────────────────────────────────────────
    for c in bundle.get("credentials", []):
        c = dict(c)
        c.pop("id")
        c["collection_id"] = new_cid
        old_ep = c.get("endpoint_id")
        if old_ep is not None:
            c["endpoint_id"] = endpoint_id_map.get(old_ep)
        _parse_datetimes(c, "created_at")
        session.add(ApiCredential(**c))

    # ── Test runs + children ──────────────────────────────────────────────────────
    # Maps kept collection-wide: leads' linked_finding_id can point at any run's
    # finding, and SAST runs' triggered_by_run_id at any api run.
    api_run_id_map: dict[int, int] = {}
    finding_id_map: dict[int, int] = {}
    sast_backpatch: list = []  # (ApiTestRun, old_sast_run_id) — patched after SAST import
    for rb in bundle.get("test_runs", []):
        src = rb["api_test_run"]
        old_run_id = src["id"]
        old_sast_id = src.get("sast_run_id")
        run_data = {k: v for k, v in src.items() if k != "id"}
        run_data["collection_id"] = new_cid
        run_data["llm_config_id"] = None  # cannot map across installations
        run_data["sast_run_id"] = None  # back-patched once SAST runs are imported
        _parse_datetimes(
            run_data, "created_at", "updated_at", "started_at", "completed_at"
        )
        run = ApiTestRun(**run_data)
        session.add(run)
        session.flush()
        new_run_id: int = run.id  # type: ignore[assignment]
        api_run_id_map[old_run_id] = new_run_id
        if old_sast_id is not None:
            sast_backpatch.append((run, old_sast_id))

        # Findings first — endpoint-test cells reference finding ids.
        for f in rb.get("scan_findings", []):
            f = dict(f)
            old_fid = f.pop("id")
            f["api_test_run_id"] = new_run_id
            f["test_run_id"] = None  # API findings never key on a web run
            f["page_id"] = None
            _parse_datetimes(f, "created_at")
            finding = ScanFinding(**f)
            session.add(finding)
            session.flush()
            finding_id_map[old_fid] = finding.id  # type: ignore[index]

        for t in rb.get("traffic_entries", []):
            t = dict(t)
            t.pop("id")
            t["api_test_run_id"] = new_run_id
            # API traffic has no real TestRun; test_run_id is NOT NULL, so it
            # carries the sentinel 0 the scanner writes (see traffic._write).
            t["test_run_id"] = _API_TRAFFIC_SENTINEL_RUN_ID
            _parse_datetimes(t, "created_at")
            session.add(TrafficEntry(**t))

        for cell in rb.get("endpoint_tests", []):
            cell = dict(cell)
            cell.pop("id")
            cell["api_test_run_id"] = new_run_id
            old_ep = cell.get("endpoint_id")
            if old_ep is not None:
                cell["endpoint_id"] = endpoint_id_map.get(old_ep, old_ep)
            try:
                old_fids = json.loads(cell.get("finding_ids_json") or "[]")
                cell["finding_ids_json"] = json.dumps(
                    [finding_id_map[fid] for fid in old_fids if fid in finding_id_map]
                )
            except Exception:
                cell["finding_ids_json"] = "[]"
            _parse_datetimes(cell, "last_updated")
            session.add(ApiEndpointTest(**cell))

        for s in rb.get("scanner_sessions", []):
            s = dict(s)
            s.pop("id")
            s["test_run_id"] = new_run_id
            s["credential_id"] = (
                None  # web-credential FK; not meaningful for API import
            )
            _parse_datetimes(s, "created_at", "updated_at")
            session.add(ScannerSession(**s))

        for sl in rb.get("scan_logs", []):
            sl = dict(sl)
            sl.pop("id")
            sl["test_run_id"] = new_run_id
            _parse_datetimes(sl, "created_at")
            session.add(ScanLog(**sl))

        for a in rb.get("agent_logs", []):
            a = dict(a)
            a.pop("id")
            a["test_run_id"] = new_run_id
            _parse_datetimes(a, "created_at")
            session.add(AgentLog(**a))

        alice_sess_id_map: dict[int, int] = {}
        for s in rb.get("alice_chat_sessions", []):
            s = dict(s)
            old_sid = s.pop("id")
            s["test_run_id"] = new_run_id
            _parse_datetimes(s, "created_at", "updated_at")
            sess = AliceChatSession(**s)
            session.add(sess)
            session.flush()
            alice_sess_id_map[old_sid] = sess.id  # type: ignore[index]

        for m in rb.get("alice_chat_messages", []):
            m = dict(m)
            m.pop("id")
            new_sid = alice_sess_id_map.get(m.get("session_id"))
            if new_sid is None:
                continue
            m["session_id"] = new_sid
            _parse_datetimes(m, "updated_at")
            session.add(AliceChatMessage(**m))

    # ── SAST runs (+ their scan/agent logs) ─────────────────────────────────────
    sast_run_id_map: dict[int, int] = {}
    for sb in bundle.get("sast_runs", []):
        sr = dict(sb["sast_run"])
        old_id = sr.pop("id")
        sr["collection_id"] = new_cid
        sr["llm_config_id"] = None
        old_doc = sr.get("document_id")
        if old_doc is not None:
            sr["document_id"] = doc_id_map.get(old_doc)
        # Only api runs are in this bundle; a web trigger can't be mapped.
        if sr.get("triggered_by_run_type") == "api":
            sr["triggered_by_run_id"] = api_run_id_map.get(
                sr.get("triggered_by_run_id")
            )
        else:
            sr["triggered_by_run_type"] = None
            sr["triggered_by_run_id"] = None
        _parse_datetimes(sr, "created_at", "updated_at", "started_at", "completed_at")
        obj = SastRun(**sr)
        session.add(obj)
        session.flush()
        new_sast_id: int = obj.id  # type: ignore[assignment]
        sast_run_id_map[old_id] = new_sast_id

        # SAST logs key on test_run_id == the SAST run id (run_kind="sast").
        for sl in sb.get("scan_logs", []):
            sl = dict(sl)
            sl.pop("id")
            sl["test_run_id"] = new_sast_id
            _parse_datetimes(sl, "created_at")
            session.add(ScanLog(**sl))
        for a in sb.get("agent_logs", []):
            a = dict(a)
            a.pop("id")
            a["test_run_id"] = new_sast_id
            _parse_datetimes(a, "created_at")
            session.add(AgentLog(**a))

    # ── Scan leads ───────────────────────────────────────────────────────────────
    for ld in bundle.get("scan_leads", []):
        ld = dict(ld)
        ld.pop("id")
        ld["collection_id"] = new_cid
        old_prod = ld.get("producer_run_id")
        if old_prod is not None:
            ld["producer_run_id"] = sast_run_id_map.get(old_prod, old_prod)
        if ld.get("investigated_by_run_type") == "api":
            ld["investigated_by_run_id"] = api_run_id_map.get(
                ld.get("investigated_by_run_id")
            )
        else:
            ld["investigated_by_run_type"] = None
            ld["investigated_by_run_id"] = None
        old_link = ld.get("linked_finding_id")
        if old_link is not None:
            ld["linked_finding_id"] = finding_id_map.get(
                old_link
            )  # None if cross-bundle
        _parse_datetimes(ld, "created_at", "updated_at")
        session.add(ScanLead(**ld))

    # ── Back-patch ApiTestRun.sast_run_id now that SAST ids are known ──────────────
    for run, old_sast_id in sast_backpatch:
        run.sast_run_id = sast_run_id_map.get(old_sast_id)
        session.add(run)

    session.commit()
    session.refresh(collection)
    return collection
