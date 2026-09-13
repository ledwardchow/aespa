"""Service-layer CRUD for Systems: components, ZIP snapshots, targets,
and code-to-target routing associations.

Pure functions taking a SQLModel ``Session``, mirroring ``services.sites`` /
``services.api_collections``. Campaign orchestration lives in
``services.campaigns``; this module only manages the system's static
setup (the "System setup" screens in the plan).
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session, select

from aespa.models import (
    ApiCollection,
    CampaignSourceMember,
    CampaignTargetMember,
    ComponentSnapshot,
    ComponentTargetHint,
    Site,
    System,
    SystemComponent,
    SystemTarget,
)
from aespa.schemas import (
    ComponentTargetHintCreate,
    SystemComponentCreate,
    SystemComponentUpdate,
    SystemCreate,
    SystemTargetCreate,
    SystemTargetUpdate,
    SystemUpdate,
)


class SystemServiceError(Exception):
    """Base class for service-layer errors."""


class SystemNotFound(SystemServiceError):
    pass


class ComponentNotFound(SystemServiceError):
    pass


class SnapshotNotFound(SystemServiceError):
    pass


class TargetNotFound(SystemServiceError):
    pass


class HintNotFound(SystemServiceError):
    pass


class DuplicateSystemName(SystemServiceError):
    pass


class DuplicateComponentName(SystemServiceError):
    pass


class ReferencedByCampaign(SystemServiceError):
    """Raised when deleting/detaching something a campaign still refers to."""


class CrossSystemReference(SystemServiceError):
    """Raised when a referenced id belongs to a different System."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── System ───────────────────────────────────────────────────────────────


def list_systems(session: Session) -> list[System]:
    return list(session.exec(select(System).order_by(System.name)).all())


def get_system(session: Session, system_id: int) -> System:
    app = session.get(System, system_id)
    if app is None:
        raise SystemNotFound(f"System id={system_id} does not exist")
    return app


def create_system(session: Session, payload: SystemCreate) -> System:
    existing = session.exec(
        select(System).where(System.name == payload.name)
    ).first()
    if existing is not None:
        raise DuplicateSystemName(f"An system named {payload.name!r} exists")
    app = System(name=payload.name, description=payload.description)
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


def update_system(
    session: Session, system_id: int, payload: SystemUpdate
) -> System:
    app = get_system(session, system_id)
    if payload.name is not None and payload.name != app.name:
        existing = session.exec(
            select(System).where(System.name == payload.name)
        ).first()
        if existing is not None and existing.id != app.id:
            raise DuplicateSystemName(
                f"An system named {payload.name!r} exists"
            )
        app.name = payload.name
    if payload.description is not None:
        app.description = payload.description
    app.updated_at = _utcnow()
    session.add(app)
    session.commit()
    session.refresh(app)
    return app


def delete_system(session: Session, system_id: int) -> None:
    from aespa.models import AssessmentCampaign

    app = get_system(session, system_id)
    has_campaign = session.exec(
        select(AssessmentCampaign.id).where(
            AssessmentCampaign.system_id == system_id
        )
    ).first()
    if has_campaign is not None:
        raise ReferencedByCampaign(
            "Delete this system's campaigns first — an system "
            "cannot be deleted while it still owns campaign history."
        )
    for hint in session.exec(
        select(ComponentTargetHint).where(
            ComponentTargetHint.system_id == system_id
        )
    ).all():
        session.delete(hint)
    for target in session.exec(
        select(SystemTarget).where(
            SystemTarget.system_id == system_id
        )
    ).all():
        session.delete(target)
    for component in session.exec(
        select(SystemComponent).where(
            SystemComponent.system_id == system_id
        )
    ).all():
        _delete_component_snapshots(session, component.id)
        session.delete(component)
    session.delete(app)
    session.commit()


# ── Components ────────────────────────────────────────────────────────────────


def list_components(
    session: Session, system_id: int
) -> list[SystemComponent]:
    get_system(session, system_id)  # 404 if missing
    return list(
        session.exec(
            select(SystemComponent)
            .where(SystemComponent.system_id == system_id)
            .order_by(SystemComponent.name)
        ).all()
    )


def get_component(
    session: Session, system_id: int, component_id: int
) -> SystemComponent:
    component = session.get(SystemComponent, component_id)
    if component is None or component.system_id != system_id:
        raise ComponentNotFound(
            f"Component id={component_id} does not exist for this system"
        )
    return component


def create_component(
    session: Session, system_id: int, payload: SystemComponentCreate
) -> SystemComponent:
    get_system(session, system_id)
    existing = session.exec(
        select(SystemComponent)
        .where(SystemComponent.system_id == system_id)
        .where(SystemComponent.name == payload.name)
    ).first()
    if existing is not None:
        raise DuplicateComponentName(
            f"A component named {payload.name!r} already exists in this system"
        )
    component = SystemComponent(
        system_id=system_id,
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
    system_id: int,
    component_id: int,
    payload: SystemComponentUpdate,
) -> SystemComponent:
    component = get_component(session, system_id, component_id)
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


def delete_component(session: Session, system_id: int, component_id: int) -> None:
    component = get_component(session, system_id, component_id)
    target_reference = session.exec(
        select(SystemTarget).where(SystemTarget.component_id == component_id)
    ).first()
    if target_reference is not None:
        raise ReferencedByCampaign(
            "A live target still uses this code component. Clear the target's "
            "component assignment first."
        )
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
    session: Session, system_id: int, component_id: int
) -> list[ComponentSnapshot]:
    get_component(session, system_id, component_id)
    return list(
        session.exec(
            select(ComponentSnapshot)
            .where(ComponentSnapshot.component_id == component_id)
            .order_by(ComponentSnapshot.id.desc())  # type: ignore[attr-defined]
        ).all()
    )


def get_snapshot(
    session: Session, system_id: int, component_id: int, snapshot_id: int
) -> ComponentSnapshot:
    get_component(session, system_id, component_id)
    snapshot = session.get(ComponentSnapshot, snapshot_id)
    if snapshot is None or snapshot.component_id != component_id:
        raise SnapshotNotFound(f"Snapshot id={snapshot_id} does not exist")
    return snapshot


def create_snapshot(
    session: Session,
    system_id: int,
    component_id: int,
    *,
    filename: str,
    stored_path: str,
    size_bytes: int,
    sha256: str,
) -> ComponentSnapshot:
    get_component(session, system_id, component_id)
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
    session: Session, system_id: int, component_id: int, snapshot_id: int
) -> None:
    snapshot = get_snapshot(session, system_id, component_id, snapshot_id)
    _remove_snapshot_row(session, snapshot)
    session.commit()


# ── Targets (existing Site / ApiCollection) ───────────────────────────────────


def list_targets(session: Session, system_id: int) -> list[SystemTarget]:
    get_system(session, system_id)
    return list(
        session.exec(
            select(SystemTarget)
            .where(SystemTarget.system_id == system_id)
            .order_by(SystemTarget.id)
        ).all()
    )


def get_target(
    session: Session, system_id: int, target_id: int
) -> SystemTarget:
    target = session.get(SystemTarget, target_id)
    if target is None or target.system_id != system_id:
        raise TargetNotFound(f"Target id={target_id} does not exist")
    return target


def attach_target(
    session: Session, system_id: int, payload: SystemTargetCreate
) -> SystemTarget:
    get_system(session, system_id)
    if payload.target_type == "site":
        if session.get(Site, payload.target_id) is None:
            raise TargetNotFound(f"Site id={payload.target_id} does not exist")
    else:
        if session.get(ApiCollection, payload.target_id) is None:
            raise TargetNotFound(
                f"API collection id={payload.target_id} does not exist"
            )
    existing = session.exec(
        select(SystemTarget)
        .where(SystemTarget.system_id == system_id)
        .where(SystemTarget.target_type == payload.target_type)
        .where(SystemTarget.target_id == payload.target_id)
    ).first()
    if existing is not None:
        return existing
    target = SystemTarget(
        system_id=system_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
    )
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


def update_target(
    session: Session,
    system_id: int,
    target_id: int,
    payload: SystemTargetUpdate,
) -> SystemTarget:
    target = get_target(session, system_id, target_id)
    if payload.component_id is not None:
        component = session.get(SystemComponent, payload.component_id)
        if component is None or component.system_id != system_id:
            raise CrossSystemReference(
                "Code component does not belong to this system"
            )
    target.component_id = payload.component_id
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


def target_display_name(session: Session, target: SystemTarget) -> str | None:
    if target.target_type == "site":
        site = session.get(Site, target.target_id)
        return site.name if site else None
    collection = session.get(ApiCollection, target.target_id)
    return collection.name if collection else None


def detach_target(session: Session, system_id: int, target_id: int) -> None:
    target = get_target(session, system_id, target_id)
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


# ── Code-to-target routing associations ────────────────────────────────────────


def list_hints(session: Session, system_id: int) -> list[ComponentTargetHint]:
    get_system(session, system_id)
    return list(
        session.exec(
            select(ComponentTargetHint)
            .where(ComponentTargetHint.system_id == system_id)
            .order_by(ComponentTargetHint.id)
        ).all()
    )


def create_hint(
    session: Session, system_id: int, payload: ComponentTargetHintCreate
) -> ComponentTargetHint:
    get_system(session, system_id)
    component = session.get(SystemComponent, payload.component_id)
    if component is None or component.system_id != system_id:
        raise CrossSystemReference("Component does not belong to this system")
    target = session.get(SystemTarget, payload.target_id)
    if target is None or target.system_id != system_id:
        raise CrossSystemReference("Target does not belong to this system")
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
        system_id=system_id,
        component_id=payload.component_id,
        target_id=payload.target_id,
        note=payload.note,
    )
    session.add(hint)
    session.commit()
    session.refresh(hint)
    return hint


def delete_hint(session: Session, system_id: int, hint_id: int) -> None:
    hint = session.get(ComponentTargetHint, hint_id)
    if hint is None or hint.system_id != system_id:
        raise HintNotFound(f"Hint id={hint_id} does not exist")
    session.delete(hint)
    session.commit()


# ── ZIP upload helpers (mirrors services/sast_runs upload limits) ───────────

MAX_SNAPSHOT_UPLOAD_BYTES = 250 * 1024 * 1024
SNAPSHOT_UPLOAD_CHUNK_BYTES = 1024 * 1024


def snapshot_storage_dir(data_dir: str) -> Path:
    base = Path(data_dir) / "system_snapshots"
    base.mkdir(parents=True, exist_ok=True)
    return base
