from __future__ import annotations

import asyncio
import json

from aespa.services.sast_semantic import (
    group_candidates_by_fix,
    lead_anchor_error,
    merge_candidate_by_worker,
    parse_fix_anchor,
    reconcile_validated_candidates,
    related_candidate_summary,
    same_fix_anchor,
)


class _FakeLLM:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.prompts: list[str] = []

    async def plain_completion(self, _config, prompt, *, system_prompt=""):
        self.prompts.append(prompt)
        return json.dumps(self.response)


def _lead(candidate_id: int, **overrides) -> dict:
    lead = {
        "candidate_id": candidate_id,
        "reference": f"#{candidate_id}",
        "category": "A02",
        "title": f"Lead {candidate_id}",
        "location": "src/Auth.php:50",
        "source_trace": {"file": "src/routes.php", "line": 10},
        "sink_trace": {"file": "src/Auth.php", "line": 50},
        "discovery_fix_location": "src/Auth.php:50 (Auth::decode)",
        "discovery_root_cause": "JWT signature is never verified.",
        "validation_status": "pending",
        "confidence": 0.8,
    }
    lead.update(overrides)
    return lead


def test_parse_and_compare_fix_anchors():
    assert parse_fix_anchor("src/Auth.php:50 (Auth::decode)") == (
        "src/auth.php",
        50,
        "decode",
    )
    assert parse_fix_anchor("./app.py:3") == ("app.py", 3, "")
    assert same_fix_anchor("src/Auth.php:50 (decode)", "src/Auth.php:90 (decode)")
    assert not same_fix_anchor("src/Auth.php:50 (decode)", "src/Auth.php:52 (encode)")
    assert same_fix_anchor("app.py:10", "app.py:14")
    assert not same_fix_anchor("app.py:10", "app.py:30")
    assert not same_fix_anchor("app.py:10", "other.py:10")


def test_lead_anchor_error_requires_traces_fix_and_root_cause(tmp_path):
    (tmp_path / "app.py").write_text("a\nb\nc\n")
    valid = {
        "source_trace": {"file": "app.py", "line": 1},
        "sink_trace": {"file": "app.py", "line": 3},
        "fix_location": "app.py:3 (handler)",
        "root_cause": "Request input is concatenated into SQL.",
    }
    assert lead_anchor_error(valid, root=tmp_path) is None
    assert "sink_trace" in lead_anchor_error(
        {**valid, "sink_trace": {"file": "app.py"}}, root=tmp_path
    )
    assert "source_trace" in lead_anchor_error(
        {**valid, "source_trace": {}}, root=tmp_path
    )
    assert "fix_location requires" not in (
        lead_anchor_error({**valid, "fix_location": "app.py"}, root=tmp_path) or ""
    )
    assert "does not exist" in lead_anchor_error(
        {**valid, "fix_location": "app.py:99"}, root=tmp_path
    )
    assert "does not exist" in lead_anchor_error(
        {**valid, "fix_location": "missing.py:1"}, root=tmp_path
    )
    assert "root_cause" in lead_anchor_error(
        {**valid, "root_cause": "bad"}, root=tmp_path
    )


def test_worker_merge_requires_shared_file_and_reason():
    candidates = [
        _lead(1),
        _lead(2, title="Forged token grants admin access"),
        _lead(
            3,
            location="src/Other.php:4",
            sink_trace={"file": "src/Other.php", "line": 4},
            source_trace={"file": "src/Other.php", "line": 1},
            discovery_fix_location="src/Other.php:4",
        ),
    ]
    summary = related_candidate_summary(candidates, candidates[0])
    assert "#2" in summary
    assert "#3" not in summary

    ok, message, _, _ = merge_candidate_by_worker(
        candidates, lead_reference="#3", into_reference="#1", reason="x" * 30
    )
    assert not ok and "no common file" in message
    ok, message, _, _ = merge_candidate_by_worker(
        candidates, lead_reference="#2", into_reference="#1", reason="same"
    )
    assert not ok
    ok, _, canonical, duplicate = merge_candidate_by_worker(
        candidates,
        lead_reference="#2",
        into_reference="#1",
        reason="Verifying the signature in Auth::decode closes both leads.",
    )
    assert ok and canonical is candidates[0] and duplicate is candidates[1]
    assert candidates[1]["reconciled_duplicate"]
    assert candidates[1]["reportable"] is False
    ok, message, _, _ = merge_candidate_by_worker(
        candidates, lead_reference="#2", into_reference="#1", reason="x" * 30
    )
    assert not ok and "already been merged" in message


def test_fix_grouping_merges_before_validation(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Auth.php").write_text("line\n" * 60)
    candidates = [
        _lead(1, category="A02", confidence=0.7),
        _lead(
            2, category="A07", title="Admin access with forged token", confidence=0.9
        ),
        _lead(3, category="A01", title="Unrelated lead"),
    ]
    llm = _FakeLLM(
        {
            "groups": [
                {
                    "ids": [1, 2],
                    "fix_location": "src/Auth.php:50",
                    "reason": "Verifying the JWT signature in decode closes both.",
                }
            ]
        }
    )
    result = asyncio.run(group_candidates_by_fix(candidates, llm, None, root=tmp_path))
    assert result["merged"] == 1
    assert result["groups_accepted"] == 1
    assert candidates[0]["reconciled_duplicate"]
    assert candidates[0]["reconciled_into_candidate_id"] == 2
    assert not candidates[1].get("reconciled_duplicate")
    assert not candidates[2].get("reconciled_duplicate")


def test_fix_grouping_rejects_unsupported_fix_file(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Auth.php").write_text("line\n" * 60)
    (tmp_path / "src" / "Other.php").write_text("line\n" * 60)
    candidates = [_lead(1), _lead(2)]
    for fix in ("src/Other.php:5", "src/Auth.php:500", "src/Missing.php:1"):
        llm = _FakeLLM(
            {
                "groups": [
                    {
                        "ids": [1, 2],
                        "fix_location": fix,
                        "reason": "One change fixes both of these leads.",
                    }
                ]
            }
        )
        result = asyncio.run(
            group_candidates_by_fix(candidates, llm, None, root=tmp_path)
        )
        assert result["merged"] == 0
        assert result["groups_rejected"] == 1
    assert not any(item.get("reconciled_duplicate") for item in candidates)


def test_fix_grouping_after_validation_keeps_both_verdicts(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Auth.php").write_text("line\n" * 60)
    candidates = [
        _lead(
            1,
            validation_status="confirmed",
            reportable=True,
            validation_reasoning="First validator confirmed.",
        ),
        _lead(
            2,
            category="A07",
            validation_status="confirmed",
            reportable=True,
            validation_reasoning="Second validator confirmed.",
            confidence=0.5,
        ),
    ]
    llm = _FakeLLM(
        {
            "groups": [
                {
                    "ids": [1, 2],
                    "fix_location": "src/Auth.php:50",
                    "reason": "Verifying the JWT signature closes both.",
                }
            ]
        }
    )
    result = asyncio.run(
        group_candidates_by_fix(
            candidates, llm, None, root=tmp_path, after_validation=True
        )
    )
    assert result["merged"] == 1
    assert candidates[0]["reportable"] is True
    assert candidates[1]["reportable"] is False
    assert "Second validator" in candidates[0]["validation_reasoning"]


def test_fix_grouping_skips_leads_without_shared_files():
    candidates = [
        _lead(1),
        _lead(
            2,
            location="b.py:1",
            source_trace={"file": "b.py", "line": 1},
            sink_trace={"file": "b.py", "line": 1},
            discovery_fix_location="b.py:1",
        ),
    ]
    llm = _FakeLLM({"groups": []})
    result = asyncio.run(group_candidates_by_fix(candidates, llm, None))
    assert result["status"] == "no_groups"
    assert llm.prompts == []


def test_validated_match_uses_shared_fix_across_categories():
    candidates = [
        _lead(
            1,
            category="A02",
            title="JWT signature not verified",
            validation_status="confirmed",
            reportable=True,
            fix_location="src/Auth.php:50 (Auth::decode)",
            validated_root_cause="JWT signature is never verified in decode.",
        ),
        _lead(
            2,
            category="A07",
            title="Forged token grants admin panel access",
            validation_status="confirmed",
            reportable=True,
            fix_location="src/Auth.php:55 (decode)",
            validated_root_cause="decode never verifies the JWT signature.",
        ),
    ]
    unrelated = [dict(item) for item in candidates]
    unrelated[1]["validated_root_cause"] = "Admin role check is missing on routes."
    unrelated[1]["fix_location"] = "src/Auth.php:50 (decode)"
    assert reconcile_validated_candidates(unrelated) == 0

    assert reconcile_validated_candidates(candidates) == 1
    assert candidates[1]["reportable"] is False
