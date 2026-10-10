from __future__ import annotations

SEVERITY_POINTS = {
    "informational": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}
DOUBLED_CATEGORIES = {"A01", "A03", "A04", "A07"}


def matched_score(ground_truth: dict, rows: list) -> int | None:
    items = ground_truth.get("items") if isinstance(ground_truth, dict) else None
    if not isinstance(items, list) or not isinstance(rows, list):
        return None
    items_by_id = {
        item.get("external_id"): item
        for item in items
        if isinstance(item, dict)
    }
    score = 0
    for row in rows:
        if not isinstance(row, dict):
            return None
        if row.get("disposition") not in {"full", "partial"}:
            continue
        item = items_by_id.get(row.get("external_id"), {})
        severity = str(item.get("severity", "")).strip().lower()
        points = SEVERITY_POINTS.get(severity)
        if points is None:
            return None
        category = str(item.get("category") or "").split(":", 1)[0].strip().upper()
        if severity in {"high", "critical"} and category in DOUBLED_CATEGORIES:
            points *= 2
        score += points
    return score


def matched_categories(ground_truth: dict, rows: list) -> dict[str, int] | None:
    items = ground_truth.get("items") if isinstance(ground_truth, dict) else None
    if not isinstance(items, list) or not isinstance(rows, list):
        return None
    categories_by_id = {
        item.get("external_id"): item.get("category")
        for item in items
        if isinstance(item, dict)
    }
    categories = {
        category: 0
        for category in categories_by_id.values()
        if isinstance(category, str) and category.strip()
    }
    if not categories:
        return None
    for row in rows:
        if not isinstance(row, dict):
            return None
        if row.get("disposition") not in {"full", "partial"}:
            continue
        category = categories_by_id.get(row.get("external_id"))
        if category not in categories:
            return None
        categories[category] += 1
    return dict(sorted(categories.items()))


def ground_truth_category_totals(ground_truth: dict) -> dict[str, int] | None:
    items = ground_truth.get("items") if isinstance(ground_truth, dict) else None
    if not isinstance(items, list) or not items:
        return None
    totals: dict[str, int] = {}
    for item in items:
        category = item.get("category") if isinstance(item, dict) else None
        if not isinstance(category, str) or not category.strip():
            return None
        totals[category] = totals.get(category, 0) + 1
    return dict(sorted(totals.items()))
