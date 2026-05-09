"""Finding management helpers."""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from urllib.parse import parse_qsl, urlparse

from sqlmodel import Session, select

from aespa.models import LLMConfig, ScanFinding
from aespa.services import llm as llm_svc


@dataclass(frozen=True)
class DeduplicationGroup:
    kept_id: int
    removed_ids: list[int]
    target: str
    title: str


@dataclass(frozen=True)
class DeduplicationResult:
    total_before: int
    total_after: int
    removed: int
    groups: list[DeduplicationGroup]
    llm_used: bool = False


_DYNAMIC_PARAM_NAMES = {
    "account",
    "account_id",
    "acct",
    "booking",
    "booking_id",
    "id",
    "item",
    "item_id",
    "object",
    "object_id",
    "order",
    "order_id",
    "record",
    "record_id",
    "resource",
    "resource_id",
    "uid",
    "user",
    "user_id",
    "uuid",
}
_STOP_WORDS = {
    "able",
    "about",
    "access",
    "affected",
    "allows",
    "also",
    "application",
    "attacker",
    "because",
    "could",
    "data",
    "does",
    "endpoint",
    "issue",
    "page",
    "parameter",
    "request",
    "response",
    "same",
    "security",
    "should",
    "target",
    "that",
    "their",
    "this",
    "through",
    "user",
    "users",
    "using",
    "vulnerability",
    "when",
    "where",
    "with",
}


async def deduplicate_findings(
    session: Session,
    run_id: int,
    llm_cfg: LLMConfig | None = None,
) -> DeduplicationResult:
    findings = list(
        session.exec(
            select(ScanFinding)
            .where(ScanFinding.test_run_id == run_id)
            .order_by(ScanFinding.id)
        ).all()
    )
    duplicate_id_groups = _heuristic_duplicate_groups(findings)
    llm_used = False
    groups: list[list[ScanFinding]] = []
    if llm_cfg is not None:
        for target, bucket in _llm_candidate_buckets(findings):
            llm_used = True
            duplicate_id_groups.extend(
                await llm_svc.deduplicate_finding_groups(
                    llm_cfg,
                    target=target,
                    findings=[_finding_summary(finding) for finding in bucket],
                )
            )

    groups = _merge_duplicate_id_groups(findings, duplicate_id_groups)
    deduped_groups: list[DeduplicationGroup] = []
    for group in groups:
        kept = min(group, key=_retention_rank)
        removed = [f for f in group if f.id != kept.id]
        removed_ids = [f.id for f in removed if f.id is not None]
        for finding in removed:
            session.delete(finding)
        deduped_groups.append(
            DeduplicationGroup(
                kept_id=kept.id or 0,
                removed_ids=removed_ids,
                target=_canonical_target(kept.affected_url),
                title=kept.title,
            )
        )

    if deduped_groups:
        session.commit()

    removed_count = sum(len(group.removed_ids) for group in deduped_groups)
    return DeduplicationResult(
        total_before=len(findings),
        total_after=len(findings) - removed_count,
        removed=removed_count,
        groups=deduped_groups,
        llm_used=llm_used,
    )


def _heuristic_duplicate_groups(findings: list[ScanFinding]) -> list[list[int]]:
    groups: list[list[ScanFinding]] = []

    for finding in findings:
        for group in groups:
            if any(_is_substantially_same(existing, finding) for existing in group):
                group.append(finding)
                break
        else:
            groups.append([finding])

    return [
        [finding.id for finding in group if finding.id is not None]
        for group in groups
        if len(group) >= 2
    ]


def _llm_candidate_buckets(
    findings: list[ScanFinding],
) -> list[tuple[str, list[ScanFinding]]]:
    by_target: dict[str, list[ScanFinding]] = {}
    for finding in findings:
        target = _canonical_target(finding.affected_url)
        by_target.setdefault(target, []).append(finding)

    buckets: list[tuple[str, list[ScanFinding]]] = []
    for target, items in by_target.items():
        if len(items) < 2:
            continue
        sorted_items = sorted(
            items,
            key=lambda f: (
                (f.owasp_category or "").lower(),
                _normalise_text(f.title or ""),
                f.id or 0,
            ),
        )
        for start in range(0, len(sorted_items), 40):
            chunk = sorted_items[start : start + 40]
            if len(chunk) >= 2:
                buckets.append((target, chunk))
    return buckets


def _merge_duplicate_id_groups(
    findings: list[ScanFinding],
    duplicate_id_groups: list[list[int]],
) -> list[list[ScanFinding]]:
    by_id = {finding.id: finding for finding in findings if finding.id is not None}
    parent = {finding_id: finding_id for finding_id in by_id}

    def find(finding_id: int) -> int:
        while parent[finding_id] != finding_id:
            parent[finding_id] = parent[parent[finding_id]]
            finding_id = parent[finding_id]
        return finding_id

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for raw_group in duplicate_id_groups:
        ids = [finding_id for finding_id in raw_group if finding_id in by_id]
        if len(ids) < 2:
            continue
        first = ids[0]
        for finding_id in ids[1:]:
            union(first, finding_id)

    grouped: dict[int, list[ScanFinding]] = {}
    for finding_id, finding in by_id.items():
        grouped.setdefault(find(finding_id), []).append(finding)
    return [group for group in grouped.values() if len(group) >= 2]


def _finding_summary(finding: ScanFinding) -> dict:
    return {
        "id": finding.id,
        "owasp_category": finding.owasp_category,
        "severity": finding.severity,
        "affected_url": finding.affected_url,
        "title": finding.title,
        "description": finding.description,
        "impact": finding.impact,
        "likelihood": finding.likelihood,
        "recommendation": finding.recommendation,
        "evidence": finding.evidence,
    }


def _is_substantially_same(a: ScanFinding, b: ScanFinding) -> bool:
    if not _category_compatible(a.owasp_category, b.owasp_category):
        return False
    if _canonical_target(a.affected_url) != _canonical_target(b.affected_url):
        return False

    title_similarity = _text_similarity(a.title, b.title)
    substance_similarity = _token_similarity(_substance_text(a), _substance_text(b))
    if title_similarity >= 0.82 and substance_similarity >= 0.42:
        return True
    return substance_similarity >= 0.68


def _category_compatible(left: str, right: str) -> bool:
    left_norm = (left or "").strip().lower()
    right_norm = (right or "").strip().lower()
    return (
        left_norm == right_norm
        or left_norm in {"", "a00"}
        or right_norm in {"", "a00"}
    )


def _canonical_target(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        host = parsed.netloc.lower()
        path = _canonical_path(parsed.path)
        query = _canonical_query(parsed.query)
        return f"{host}{path}?{query}" if query else f"{host}{path}"

    return _normalise_dynamic_tokens(raw.lower())


def _canonical_path(path: str) -> str:
    parts = [
        "{id}" if _looks_dynamic_token(part) else part.lower()
        for part in (path or "/").split("/")
        if part
    ]
    return "/" + "/".join(parts)


def _canonical_query(query: str) -> str:
    pairs = parse_qsl(query, keep_blank_values=True)
    if not pairs:
        return ""
    canonical = []
    for key, value in pairs:
        key_norm = key.lower()
        if key_norm in _DYNAMIC_PARAM_NAMES or _looks_dynamic_token(value):
            canonical.append((key_norm, "{id}"))
        else:
            canonical.append((key_norm, "*"))
    return "&".join(f"{key}={value}" for key, value in sorted(set(canonical)))


def _substance_text(finding: ScanFinding) -> str:
    return " ".join(
        [
            finding.title or "",
            finding.description or "",
            finding.impact or "",
            finding.likelihood or "",
            finding.recommendation or "",
        ]
    )


def _text_similarity(left: str, right: str) -> float:
    left_norm = _normalise_text(left)
    right_norm = _normalise_text(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def _token_similarity(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return overlap / union if union else 0.0


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_]{3,}", _normalise_text(text))
        if token not in _STOP_WORDS and not _looks_dynamic_token(token)
    }


def _normalise_text(text: str) -> str:
    text = _normalise_dynamic_tokens((text or "").lower())
    text = re.sub(r"https?://\S+", " url ", text)
    text = re.sub(r"\b(?:get|post|put|patch|delete|head|options)\b", " method ", text)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9_]+", " ", text)).strip()


def _normalise_dynamic_tokens(text: str) -> str:
    text = re.sub(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
        " {id} ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b\d+\b", " {id} ", text)
    text = re.sub(r"\b[0-9a-f]{12,}\b", " {id} ", text, flags=re.IGNORECASE)
    return text


def _looks_dynamic_token(value: str) -> bool:
    value = (value or "").strip()
    if not value:
        return False
    return bool(
        re.fullmatch(r"\d+", value)
        or re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            value,
            flags=re.IGNORECASE,
        )
        or re.fullmatch(r"[0-9a-f]{12,}", value, flags=re.IGNORECASE)
    )


def _retention_rank(finding: ScanFinding) -> tuple[int, int, int]:
    validation_rank = {
        "confirmed": 0,
        "unvalidated": 1,
        "validating": 2,
        "unconfirmed": 3,
        "false_positive": 4,
    }
    severity_rank = {
        "critical": 0,
        "high": 1,
        "medium": 2,
        "low": 3,
        "info": 4,
    }
    return (
        validation_rank.get((finding.validation_status or "").lower(), 5),
        severity_rank.get((finding.severity or "").lower(), 5),
        finding.id or 0,
    )
