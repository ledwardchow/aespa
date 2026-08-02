"""Service-layer CRUD for Applications: components, ZIP snapshots, targets,
and connection hints.

Pure functions taking a SQLModel ``Session``, mirroring ``services.sites`` /
``services.api_collections``. Campaign orchestration lives in
``services.campaigns``; this module only manages the application's static
setup (the "Application setup" screens in the plan).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from aespa.models import (
    ApiCollection,
    Application,
    ApplicationComponent,
    ApplicationTarget,
    CampaignSourceMember,
    CampaignTargetMember,
    ComponentSnapshot,
    ComponentTargetHint,
    Site,
)
from aespa.schemas import (
    ApplicationComponentCreate,
    ApplicationComponentUpdate,
    ApplicationCreate,
    ApplicationTargetCreate,
    ApplicationUpdate,
    ComponentTargetHintCreate,
)


class ApplicationServiceError(Exception):
    """Base class for service-layer errors."""


class ApplicationNotFound(ApplicationServiceError):
    pass


class ComponentNotFound(ApplicationServiceError):
    pass


class SnapshotNotFound(ApplicationServiceError):
    pass


class TargetNotFound(ApplicationServiceError):
    pass


class HintNotFound(ApplicationServiceError):
    pass


class DuplicateApplicationName(ApplicationServiceError):
    pass


class DuplicateComponentName(ApplicationServiceError):
    pass


class ReferencedByCampaign(ApplicationServiceError):
    """Raised when deleting/detaching something a campaign still refers to."""


class CrossApplicationReference(ApplicationServiceError):
    """Raised when a referenced id belongs to a different Application."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Application ───────────────────────────────────────────────────────────────


def list_applications(session: Session) -> list[Application]:
    return list(session.exec(select(Application).order_by(Application.name)).all())


def get_application(session: Session, application_id: int) -> Application:
    app = session.get(Application, application_id)
    if app is None:
        raise ApplicationNotFound(f"Application id={application_id} does not exist")
    return app


def create_application(session: Session, payload: ApplicationCreate) -> Application:
    existing = session.exec(
        select(Application).where(Application.name == payload.name)
    ).first()
    if existing is not None:
        raise DuplicateApplicationName(f"An application named {payload.name!r} exists")
    app = Application(name=payload.name, description=payload.description)
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


def update_application(
    session: Session, application_id: int, payload: ApplicationUpdate
) -> Application:
    app = get_application(session, application_id)
    if payload.name is not None and payload.name != app.name:
        existing = session.exec(
            select(Application).where(Application.name == payload.name)
        ).first()
        if existing is not None and existing.id != app.id:
            raise DuplicateApplicationName(
                f"An application named {payload.name!r} exists"
            )
        app.name = payload.name
    if payload.description is not None:
        app.description = payload.description
    app.updated_at = _utcnow()
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


def delete_application(session: Session, application_id: int) -> None:
    from aespa.models import AssessmentCampaign

    app = get_application(session, application_id)
    has_campaign = session.exec(
        select(AssessmentCampaign.id).where(
            AssessmentCampaign.application_id == application_id
        )
    ).first()
    if has_campaign is not None:
        raise ReferencedByCampaign(
            "Delete this application's campaigns first — an application "
            "cannot be deleted while it still owns campaign history."
        )
    for hint in session.exec(
        select(ComponentTargetHint).where(
            ComponentTargetHint.application_id == application_id
        )
    ).all():
        session.delete(hint)
    for target in session.exec(
        select(ApplicationTarget).where(
            ApplicationTarget.application_id == application_id
        )
    ).all():
        session.delete(target)
    for component in session.exec(
        select(ApplicationComponent).where(
            ApplicationComponent.application_id == application_id
        )
    ).all():
        _delete_component_snapshots(session, component.id)
        session.delete(component)
    session.delete(app)
    session.commit()


# ── Components ────────────────────────────────────────────────────────────────


def list_components(
    session: Session, application_id: int
) -> list[ApplicationComponent]:
    get_application(session, application_id)  # 404 if missing
    return list(
        session.exec(
            select(ApplicationComponent)
            .where(ApplicationComponent.application_id == application_id)
            .order_by(ApplicationComponent.name)
        ).all()
    )


def get_component(
    session: Session, application_id: int, component_id: int
) -> ApplicationComponent:
    component = session.get(ApplicationComponent, component_id)
    if component is None or component.application_id != application_id:
        raise ComponentNotFound(
            f"Component id={component_id} does not exist for this application"
        )
    return component


def create_component(
    session: Session, application_id: int, payload: ApplicationComponentCreate
) -> ApplicationComponent:
    get_application(session, application_id)
    existing = session.exec(
        select(ApplicationComponent)
        .where(ApplicationComponent.application_id == application_id)
        .where(ApplicationComponent.name == payload.name)
    ).first()
    if existing is not None:
        raise DuplicateComponentName(
            f"A component named {payload.name!r} already exists in this application"
        )
    component = ApplicationComponent(
        application_id=application_id,
        name=payload.name,
        role=payload.role,
        description=payload.description,
    )
    session.add(component)
    session.commit()
    session.refresh(component)
    return component


def update_component(
    session: Session,
    application_id: int,
    component_id: int,
    payload: ApplicationComponentUpdate,
) -> ApplicationComponent:
    component = get_component(session, application_id, component_id)
    if payload.role is not None:
        component.role = payload.role
    if payload.description is not None:
        component.description = payload.description
    component.updated_at = _utcnow()
    session.add(component)
    session.commit()
    session.refresh(component)
    return component


def _delete_component_snapshots(session: Session, component_id: int) -> None:
    for snapshot in session.exec(
        select(ComponentSnapshot).where(ComponentSnapshot.component_id == component_id)
    ).all():
        _remove_snapshot_row(session, snapshot, check_referenced=False)


def delete_component(session: Session, application_id: int, component_id: int) -> None:
    component = get_component(session, application_id, component_id)
    referenced = session.exec(
        select(CampaignSourceMember)
        .join(
            ComponentSnapshot,
            CampaignSourceMember.snapshot_id == ComponentSnapshot.id,
        )
        .where(ComponentSnapshot.component_id == component_id)
    ).first()
    if referenced is not None:
        raise ReferencedByCampaign(
            "A campaign still references a snapshot of this component."
        )
    _delete_component_snapshots(session, component_id)
    for hint in session.exec(
        select(ComponentTargetHint).where(
            ComponentTargetHint.component_id == component_id
        )
    ).all():
        session.delete(hint)
    session.delete(component)
    session.commit()


# ── ZIP Snapshots ──────────────────────────────────────────────────────────────


def list_snapshots(
    session: Session, application_id: int, component_id: int
) -> list[ComponentSnapshot]:
    get_component(session, application_id, component_id)
    return list(
        session.exec(
            select(ComponentSnapshot)
            .where(ComponentSnapshot.component_id == component_id)
            .order_by(ComponentSnapshot.id.desc())  # type: ignore[attr-defined]
        ).all()
    )


def get_snapshot(
    session: Session, application_id: int, component_id: int, snapshot_id: int
) -> ComponentSnapshot:
    get_component(session, application_id, component_id)
    snapshot = session.get(ComponentSnapshot, snapshot_id)
    if snapshot is None or snapshot.component_id != component_id:
        raise SnapshotNotFound(f"Snapshot id={snapshot_id} does not exist")
    return snapshot


def create_snapshot(
    session: Session,
    application_id: int,
    component_id: int,
    *,
    filename: str,
    stored_path: str,
    size_bytes: int,
    sha256: str,
) -> ComponentSnapshot:
    get_component(session, application_id, component_id)
    snapshot = ComponentSnapshot(
        component_id=component_id,
        filename=filename,
        stored_path=stored_path,
        size_bytes=size_bytes,
        sha256=sha256,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def _remove_snapshot_row(
    session: Session, snapshot: ComponentSnapshot, *, check_referenced: bool = True
) -> None:
    if check_referenced:
        referenced = session.exec(
            select(CampaignSourceMember).where(
                CampaignSourceMember.snapshot_id == snapshot.id
            )
        ).first()
        if referenced is not None:
            raise ReferencedByCampaign("A campaign still references this ZIP snapshot.")
    if snapshot.stored_path:
        try:
            if os.path.isfile(snapshot.stored_path):
                os.remove(snapshot.stored_path)
        except OSError:
            pass
    session.delete(snapshot)


def delete_snapshot(
    session: Session, application_id: int, component_id: int, snapshot_id: int
) -> None:
    snapshot = get_snapshot(session, application_id, component_id, snapshot_id)
    _remove_snapshot_row(session, snapshot)
    session.commit()


# ── Targets (existing Site / ApiCollection) ───────────────────────────────────


def list_targets(session: Session, application_id: int) -> list[ApplicationTarget]:
    get_application(session, application_id)
    return list(
        session.exec(
            select(ApplicationTarget)
            .where(ApplicationTarget.application_id == application_id)
            .order_by(ApplicationTarget.id)
        ).all()
    )


def get_target(
    session: Session, application_id: int, target_id: int
) -> ApplicationTarget:
    target = session.get(ApplicationTarget, target_id)
    if target is None or target.application_id != application_id:
        raise TargetNotFound(f"Target id={target_id} does not exist")
    return target


def attach_target(
    session: Session, application_id: int, payload: ApplicationTargetCreate
) -> ApplicationTarget:
    get_application(session, application_id)
    if payload.target_type == "site":
        if session.get(Site, payload.target_id) is None:
            raise TargetNotFound(f"Site id={payload.target_id} does not exist")
    else:
        if session.get(ApiCollection, payload.target_id) is None:
            raise TargetNotFound(
                f"API collection id={payload.target_id} does not exist"
            )
    existing = session.exec(
        select(ApplicationTarget)
        .where(ApplicationTarget.application_id == application_id)
        .where(ApplicationTarget.target_type == payload.target_type)
        .where(ApplicationTarget.target_id == payload.target_id)
    ).first()
    if existing is not None:
        return existing
    target = ApplicationTarget(
        application_id=application_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
    )
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


def target_display_name(session: Session, target: ApplicationTarget) -> str | None:
    if target.target_type == "site":
        site = session.get(Site, target.target_id)
        return site.name if site else None
    collection = session.get(ApiCollection, target.target_id)
    return collection.name if collection else None


def detach_target(session: Session, application_id: int, target_id: int) -> None:
    target = get_target(session, application_id, target_id)
    referenced = session.exec(
        select(CampaignTargetMember).where(CampaignTargetMember.target_id == target_id)
    ).first()
    if referenced is not None:
        raise ReferencedByCampaign("A campaign still references this target.")
    for hint in session.exec(
        select(ComponentTargetHint).where(ComponentTargetHint.target_id == target_id)
    ).all():
        session.delete(hint)
    session.delete(target)
    session.commit()


# ── Connection hints ───────────────────────────────────────────────────────────


def list_hints(session: Session, application_id: int) -> list[ComponentTargetHint]:
    get_application(session, application_id)
    return list(
        session.exec(
            select(ComponentTargetHint)
            .where(ComponentTargetHint.application_id == application_id)
            .order_by(ComponentTargetHint.id)
        ).all()
    )


def create_hint(
    session: Session, application_id: int, payload: ComponentTargetHintCreate
) -> ComponentTargetHint:
    get_application(session, application_id)
    component = session.get(ApplicationComponent, payload.component_id)
    if component is None or component.application_id != application_id:
        raise CrossApplicationReference("Component does not belong to this application")
    target = session.get(ApplicationTarget, payload.target_id)
    if target is None or target.application_id != application_id:
        raise CrossApplicationReference("Target does not belong to this application")
    existing = session.exec(
        select(ComponentTargetHint)
        .where(ComponentTargetHint.component_id == payload.component_id)
        .where(ComponentTargetHint.target_id == payload.target_id)
    ).first()
    if existing is not None:
        if payload.note is not None:
            existing.note = payload.note
            session.add(existing)
            session.commit()
            session.refresh(existing)
        return existing
    hint = ComponentTargetHint(
        application_id=application_id,
        component_id=payload.component_id,
        target_id=payload.target_id,
        note=payload.note,
    )
    session.add(hint)
    session.commit()
    session.refresh(hint)
    return hint


def delete_hint(session: Session, application_id: int, hint_id: int) -> None:
    hint = session.get(ComponentTargetHint, hint_id)
    if hint is None or hint.application_id != application_id:
        raise HintNotFound(f"Hint id={hint_id} does not exist")
    session.delete(hint)
    session.commit()


# ── ZIP upload helpers (mirrors services/sast_runs upload limits) ───────────

MAX_SNAPSHOT_UPLOAD_BYTES = 25 * 1024 * 1024
SNAPSHOT_UPLOAD_CHUNK_BYTES = 1024 * 1024


def snapshot_storage_dir(data_dir: str) -> Path:
    base = Path(data_dir) / "application_snapshots"
    base.mkdir(parents=True, exist_ok=True)
    return base
