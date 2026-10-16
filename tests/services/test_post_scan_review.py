from __future__ import annotations

import asyncio

import pytest
from sqlmodel import Session

from aespa.models import (
    ApiCollection,
    ApiTestRun,
    ScanFinding,
    ScannerPolicy,
    Site,
    TestRun,
)
from aespa.services import scanner


def _seed(engine, count: int, concurrency: int = 2):
    with Session(engine) as session:
        site = Site(name="Review target", base_url="https://example.test")
        session.add(site)
        session.flush()
        run = TestRun(site_id=site.id, name="Review run")
        session.add(run)
        session.flush()
        policy = session.get(ScannerPolicy, 1)
        if policy is None:
            policy = ScannerPolicy(id=1)
        policy.dast_max_concurrent_llm_requests = concurrency
        session.add(policy)
        findings = []
        for n in range(count):
            finding = ScanFinding(
                test_run_id=run.id,
                public_reference=f"WEB-{n:03d}",
                owasp_category="A01",
                severity="high",
                title=f"Finding {n}",
                description="Evidence from a test",
            )
            session.add(finding)
            findings.append(finding)
        session.commit()
        return run.id, [(f.id, f.public_reference) for f in findings]


def _events(monkeypatch):
    emitted = []
    monkeypatch.setattr(
        scanner.events_svc, "emit", lambda run_id, event: emitted.append(event)
    )
    return emitted


def _rows(engine, ids):
    with Session(engine) as session:
        return {
            fid: (
                session.get(ScanFinding, fid).validation_status,
                session.get(ScanFinding, fid).validation_note,
            )
            for fid in ids
        }


def test_review_runs_up_to_saved_limit_and_reports_completion_order(
    monkeypatch, engine
):
    async def exercise():
        run_id, findings = _seed(engine, 25, concurrency=2)
        events = _events(monkeypatch)
        started = [asyncio.Event() for _ in range(3)]
        release = [asyncio.Event() for _ in range(3)]
        active = 0
        peak = 0

        async def completion(_config, prompt):
            nonlocal active, peak
            turn = next(n for n in range(3) if f"{findings[n * 10][1]} |" in prompt)
            active += 1
            peak = max(peak, active)
            started[turn].set()
            try:
                await release[turn].wait()
                return "\n".join(
                    f"{ref} | ACCEPT"
                    for _, ref in findings[turn * 10 : (turn + 1) * 10]
                )
            finally:
                active -= 1

        monkeypatch.setattr(scanner.llm_svc, "plain_completion", completion)
        task = asyncio.create_task(
            scanner._run_post_scan_llm_review(run_id, object(), 0)
        )
        await asyncio.wait_for(asyncio.gather(started[0].wait(), started[1].wait()), 2)
        assert not started[2].is_set()
        assert peak == 2
        release[1].set()
        await asyncio.wait_for(started[2].wait(), 2)
        release[2].set()
        release[0].set()
        await asyncio.wait_for(task, 2)
        turns = [
            e["data"]["turn"] for e in events if e.get("phase") == "post_review_turn"
        ]
        assert turns[0] == 2
        assert set(turns) == {1, 2, 3}
        assert all(
            status == "unvalidated"
            for status, _ in _rows(engine, [f[0] for f in findings]).values()
        )
        assert "25 accepted" in next(
            e["message"]
            for e in events
            if e.get("phase") == "post_scan_review" and e["status"] == "complete"
        )

    asyncio.run(exercise())


def test_review_limit_one_runs_serially(monkeypatch, engine):
    async def exercise():
        run_id, findings = _seed(engine, 11, concurrency=1)
        _events(monkeypatch)
        first_started = asyncio.Event()
        release_first = asyncio.Event()
        second_started = asyncio.Event()

        async def completion(_config, prompt):
            if f"{findings[0][1]} |" in prompt:
                first_started.set()
                await release_first.wait()
            else:
                second_started.set()
            return ""

        monkeypatch.setattr(scanner.llm_svc, "plain_completion", completion)
        task = asyncio.create_task(
            scanner._run_post_scan_llm_review(run_id, object(), 0)
        )
        await asyncio.wait_for(first_started.wait(), 2)
        assert not second_started.is_set()
        release_first.set()
        await asyncio.wait_for(task, 2)
        assert second_started.is_set()

    asyncio.run(exercise())


def test_review_ignores_foreign_unknown_duplicate_and_missing_verdicts(
    monkeypatch, engine
):
    async def exercise():
        run_id, findings = _seed(engine, 11)
        events = _events(monkeypatch)

        async def completion(_config, prompt):
            if f"{findings[0][1]} |" in prompt:
                return "\n".join(
                    [
                        f"{findings[0][1]} | LOW_CONFIDENCE: weak evidence",
                        f"{findings[0][1]} | LOW_CONFIDENCE: repeated",
                        f"{findings[1][1]} | LOW_CONFIDENCE: vague",
                        f"{findings[10][1]} | LOW_CONFIDENCE: foreign batch",
                        "UNKNOWN | LOW_CONFIDENCE: missing",
                        f"{findings[2][1]} | MAYBE",
                        "malformed line",
                    ]
                )
            return f"{findings[10][1]} | ACCEPT"

        monkeypatch.setattr(scanner.llm_svc, "plain_completion", completion)
        await scanner._run_post_scan_llm_review(run_id, object(), 0)
        rows = _rows(engine, [fid for fid, _ in findings])
        assert rows[findings[0][0]][0] == "unvalidated"
        assert rows[findings[1][0]] == ("low_confidence", "vague")
        assert rows[findings[10][0]][0] == "unvalidated"
        changes = [e for e in events if e["type"] == "finding_validation_update"]
        assert [e["finding_id"] for e in changes] == [findings[1][0]]
        final = next(
            e["message"]
            for e in events
            if e.get("phase") == "post_scan_review" and e["status"] == "complete"
        )
        assert (
            "1 accepted" in final and "1 flagged" in final and "9 unreviewed" in final
        )

    asyncio.run(exercise())


def test_review_failure_is_isolated_and_unreviewed(monkeypatch, engine):
    async def exercise():
        run_id, findings = _seed(engine, 11)
        events = _events(monkeypatch)

        async def completion(_config, prompt):
            if f"{findings[0][1]} |" in prompt:
                raise RuntimeError("provider unavailable")
            return f"{findings[10][1]} | LOW_CONFIDENCE: no evidence"

        monkeypatch.setattr(scanner.llm_svc, "plain_completion", completion)
        await scanner._run_post_scan_llm_review(run_id, object(), 0)
        assert _rows(engine, [findings[0][0], findings[10][0]]) == {
            findings[0][0]: ("unvalidated", None),
            findings[10][0]: ("low_confidence", "no evidence"),
        }
        assert any(
            e.get("data", {}).get("error") == "provider unavailable"
            and e.get("status") == "error"
            for e in events
        )
        assert "10 unreviewed" in next(
            e["message"]
            for e in events
            if e.get("phase") == "post_scan_review" and e["status"] == "complete"
        )

    asyncio.run(exercise())


@pytest.mark.parametrize("verdict", ["LOW_CONFIDENCE", "ACCEPT"])
def test_review_does_not_overwrite_changed_or_deleted_findings(
    monkeypatch, engine, verdict
):
    async def exercise():
        run_id, findings = _seed(engine, 4)
        events = _events(monkeypatch)
        started = asyncio.Event()
        release = asyncio.Event()

        async def completion(_config, _prompt):
            started.set()
            await release.wait()
            response = (
                "LOW_CONFIDENCE: weak" if verdict == "LOW_CONFIDENCE" else "ACCEPT"
            )
            return "\n".join(f"{ref} | {response}" for _, ref in findings)

        monkeypatch.setattr(scanner.llm_svc, "plain_completion", completion)
        task = asyncio.create_task(
            scanner._run_post_scan_llm_review(run_id, object(), 0)
        )
        await asyncio.wait_for(started.wait(), 2)
        with Session(engine) as session:
            changed = session.get(ScanFinding, findings[0][0])
            changed.validation_status = "confirmed"
            session.add(changed)
            session.delete(session.get(ScanFinding, findings[1][0]))
            other_run = TestRun(
                site_id=session.get(TestRun, run_id).site_id, name="Other run"
            )
            session.add(other_run)
            session.flush()
            moved = session.get(ScanFinding, findings[2][0])
            moved.test_run_id = other_run.id
            session.add(moved)
            session.commit()
        release.set()
        await asyncio.wait_for(task, 2)
        assert _rows(engine, [findings[0][0], findings[2][0], findings[3][0]]) == {
            findings[0][0]: ("confirmed", None),
            findings[2][0]: ("unvalidated", None),
            findings[3][0]: ("low_confidence", "weak")
            if verdict == "LOW_CONFIDENCE"
            else ("unvalidated", None),
        }
        assert [
            e["finding_id"] for e in events if e["type"] == "finding_validation_update"
        ] == ([findings[3][0]] if verdict == "LOW_CONFIDENCE" else [])
        final = next(
            e["message"]
            for e in events
            if e.get("phase") == "post_scan_review" and e["status"] == "complete"
        )
        expected = (
            "0 accepted, 1 flagged as low confidence, 3 unreviewed"
            if verdict == "LOW_CONFIDENCE"
            else "1 accepted, 0 flagged as low confidence, 3 unreviewed"
        )
        assert expected in final
        assert "3 finding(s) changed or were removed" in final

    asyncio.run(exercise())


def test_review_scope_excludes_baseline_other_run_and_api_findings(monkeypatch, engine):
    async def exercise():
        run_id, findings = _seed(engine, 2)
        events = _events(monkeypatch)
        with Session(engine) as session:
            site = session.get(TestRun, run_id).site_id
            other = TestRun(site_id=site, name="Other web run")
            session.add(other)
            session.flush()
            collection = ApiCollection(name="API", base_url="https://api.example.test")
            session.add(collection)
            session.flush()
            api_run = ApiTestRun(collection_id=collection.id, name="API run")
            session.add(api_run)
            session.flush()
            session.add(
                ScanFinding(
                    test_run_id=other.id,
                    public_reference="OTHER",
                    owasp_category="A01",
                    severity="high",
                    title="Other",
                    description="other",
                )
            )
            session.add(
                ScanFinding(
                    api_test_run_id=api_run.id,
                    public_reference="API",
                    owasp_category="A01",
                    severity="high",
                    title="API",
                    description="api",
                )
            )
            session.commit()
        prompts = []

        async def completion(_config, prompt):
            prompts.append(prompt)
            return f"{findings[1][1]} | LOW_CONFIDENCE: weak"

        monkeypatch.setattr(scanner.llm_svc, "plain_completion", completion)
        await scanner._run_post_scan_llm_review(run_id, object(), findings[0][0])
        assert len(prompts) == 1
        assert f"{findings[0][1]} |" not in prompts[0]
        assert "OTHER |" not in prompts[0] and "API |" not in prompts[0]
        assert [
            e["finding_id"] for e in events if e["type"] == "finding_validation_update"
        ] == [findings[1][0]]

    asyncio.run(exercise())


def test_review_empty_run_makes_no_provider_call_or_events(monkeypatch, engine):
    async def exercise():
        run_id, _ = _seed(engine, 0)
        events = _events(monkeypatch)

        async def completion(_config, _prompt):
            raise AssertionError("No review should be requested")

        monkeypatch.setattr(scanner.llm_svc, "plain_completion", completion)
        await scanner._run_post_scan_llm_review(run_id, object(), 0)
        assert events == []

    asyncio.run(exercise())


def test_review_cancellation_drains_calls_without_finalizing(monkeypatch, engine):
    async def exercise():
        run_id, findings = _seed(engine, 21, concurrency=2)
        events = _events(monkeypatch)
        started = asyncio.Event()
        cancelled = 0
        active = 0

        async def completion(_config, _prompt):
            nonlocal active, cancelled
            active += 1
            if active == 2:
                started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                cancelled += 1
                raise
            finally:
                active -= 1

        monkeypatch.setattr(scanner.llm_svc, "plain_completion", completion)
        task = asyncio.create_task(
            scanner._run_post_scan_llm_review(run_id, object(), 0)
        )
        await asyncio.wait_for(started.wait(), 2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 2)
        assert active == 0 and cancelled == 2
        assert all(
            status == "unvalidated"
            for status, _ in _rows(engine, [f[0] for f in findings]).values()
        )
        assert not any(
            e.get("phase") == "post_scan_review" and e.get("status") == "complete"
            for e in events
        )
        assert not any(e["type"] == "finding_validation_update" for e in events)

    asyncio.run(exercise())
