"""Find running scans that use plan-based providers.

Readings around a scan show how much of the plan that scan used. AESPA does
not tell extensions when scans start or stop, so this reads the Active Jobs
list and each run's LLM profile from the main database without changing it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlmodel import Session

from aespa.db import get_engine

from . import usage

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Scan:
    key: tuple[str, int, str]
    label: str


def _run(session: Session, run_type: str, run_id: int):
    from aespa import models

    model = {
        "web": models.TestRun,
        "api": models.ApiTestRun,
        "sast": models.SastRun,
        "campaign": models.AssessmentCampaign,
    }.get(run_type)
    return session.get(model, run_id) if model else None


def run_providers(session: Session, run) -> set[str]:
    """Providers any agent role of this run would use."""
    from aespa.services.settings import get_llm_config_for_role
    from aespa.services.settings_values import AGENT_ROLES

    providers = set()
    for role in (None, *AGENT_ROLES):
        try:
            config = get_llm_config_for_role(session, run, role)
        except Exception:
            continue
        provider = getattr(config, "provider", None)
        if provider:
            providers.add(str(getattr(provider, "value", provider)))
    return providers


def active_plan_scans() -> dict[tuple[str, int, str], Scan]:
    """Running jobs whose profile uses the ChatGPT plan or Codex CLI provider."""
    from aespa.services.active_jobs import list_active_jobs

    result = {}
    with Session(get_engine()) as session:
        for job in list_active_jobs(session):
            run = _run(session, job.run_type, job.run_id)
            if run is None or not run_providers(session, run) & set(usage.PROVIDERS):
                continue
            key = (job.run_type, job.run_id, job.job_type)
            result[key] = Scan(key, f"{job.job_type} '{job.run_name}'")
    return result


class ScanWatcher:
    """Report scans that started or stopped since the previous check."""

    def __init__(self) -> None:
        self.active: dict[tuple[str, int, str], Scan] = {}

    def check(
        self, current: dict[tuple[str, int, str], Scan]
    ) -> tuple[list[Scan], list[Scan]]:
        started = [scan for key, scan in current.items() if key not in self.active]
        stopped = [scan for key, scan in self.active.items() if key not in current]
        self.active = dict(current)
        return started, stopped
