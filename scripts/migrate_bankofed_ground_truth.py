"""Replace the local BankOfEd dataset and its saved result snapshots.

This is a one-time migration for the October 2026 severity revision. It keeps
result identities and finding matches, so the Sites publisher updates existing
graphs under the revised dataset key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DATASET_ID = 3
RETIRED_DATASET_ID = 2
OLD_DIGEST = "sha256:8ecd18567525c4b5cf36e508dec89c59653ae6218d1d734c993d6453086180ee"
NEW_DIGEST = "sha256:4d2f2e2ee132c086715bd8f1629d4a69ed28e84488bea80e5a6ac69959464ab3"


def canonical(value: object) -> str:
    return json.dumps(value, default=str, ensure_ascii=False, sort_keys=True)


def migrate(database: Path, ground_truth_file: Path, backup: Path) -> dict[str, object]:
    revised = json.loads(ground_truth_file.read_text(encoding="utf-8"))
    if len(revised.get("items", [])) != 35:
        raise ValueError("Expected exactly 35 ground-truth findings")
    revised_json = canonical(revised)
    digest = "sha256:" + hashlib.sha256(revised_json.encode()).hexdigest()
    if digest != NEW_DIGEST:
        raise ValueError("The revised ground truth does not match the reviewed file")

    if backup.exists():
        raise FileExistsError(f"Backup already exists: {backup}")
    database = database.resolve(strict=True)
    connection = sqlite3.connect(database, isolation_level=None, timeout=30)
    connection.execute("PRAGMA busy_timeout = 30000")
    try:
        datasets = connection.execute(
            "SELECT id, ground_truth_json, ground_truth_digest FROM benchmarking_dataset"
        ).fetchall()
        if {row[0] for row in datasets} != {DATASET_ID, RETIRED_DATASET_ID}:
            raise ValueError("Dataset list changed; inspect it before migrating")
        original_json, original_digest = next(
            (row[1], row[2]) for row in datasets if row[0] == DATASET_ID
        )
        if original_digest != OLD_DIGEST or (
            "sha256:" + hashlib.sha256(original_json.encode()).hexdigest()
        ) != OLD_DIGEST:
            raise ValueError("The saved BankOfEd ground truth changed")
        original = json.loads(original_json)
        original_items = {item["external_id"]: item for item in original["items"]}
        revised_items = {item["external_id"]: item for item in revised["items"]}
        if set(original_items) != set(revised_items) or len(revised_items) != 35:
            raise ValueError("Finding IDs changed")
        if any(
            {key: value for key, value in old.items() if key != "severity"}
            != {key: value for key, value in revised_items[item_id].items() if key != "severity"}
            for item_id, old in original_items.items()
        ) or {
            key: value for key, value in original.items() if key != "items"
        } != {key: value for key, value in revised.items() if key != "items"}:
            raise ValueError("The revised file changes more than severity")

        results = connection.execute(
            "SELECT id, dataset_id, ground_truth_json, rows_json, updated_at "
            "FROM benchmarking_scan_result ORDER BY id"
        ).fetchall()
        expected_ids = set(original_items)
        for result_id, dataset_id, snapshot, rows_json, _ in results:
            if dataset_id != DATASET_ID or json.loads(snapshot) != original:
                raise ValueError(f"Result {result_id} uses different ground truth")
            saved = json.loads(rows_json)
            rows = saved.get("rows", []) if isinstance(saved, dict) else saved
            if {row["external_id"] for row in rows} != expected_ids or len(rows) != 35:
                raise ValueError(f"Result {result_id} has different finding matches")
        for table in (
            "benchmarking_ground_truth_binding",
            "benchmarking_evaluation",
            "benchmarking_comparison",
        ):
            if connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE dataset_id = ?",
                (RETIRED_DATASET_ID,),
            ).fetchone()[0]:
                raise ValueError(f"The retired dataset is still used by {table}")

        backup.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(backup) as destination:
            connection.backup(destination)

        updated_at = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ")
        connection.execute("BEGIN IMMEDIATE")
        try:
            current = connection.execute(
                "SELECT ground_truth_digest FROM benchmarking_dataset WHERE id = ?",
                (DATASET_ID,),
            ).fetchone()
            if current != (OLD_DIGEST,):
                raise ValueError("The dataset changed during backup")
            if connection.execute(
                "SELECT id, dataset_id, ground_truth_json, rows_json, updated_at "
                "FROM benchmarking_scan_result ORDER BY id"
            ).fetchall() != results:
                raise ValueError("Saved results changed during backup")
            connection.execute(
                "UPDATE benchmarking_dataset SET ground_truth_json = ?, "
                "ground_truth_digest = ?, updated_at = ? WHERE id = ?",
                (revised_json, NEW_DIGEST, updated_at, DATASET_ID),
            )
            connection.execute(
                "UPDATE benchmarking_scan_result SET ground_truth_json = ?, updated_at = ? "
                "WHERE dataset_id = ?",
                (revised_json, updated_at, DATASET_ID),
            )
            connection.execute(
                "DELETE FROM benchmarking_dataset_label WHERE dataset_id = ?",
                (RETIRED_DATASET_ID,),
            )
            connection.execute(
                "DELETE FROM benchmarking_dataset WHERE id = ?",
                (RETIRED_DATASET_ID,),
            )
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
        return {
            "dataset_id": DATASET_ID,
            "results_updated": len(results),
            "ground_truth_digest": NEW_DIGEST,
            "backup": str(backup),
        }
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("ground_truth_file", type=Path)
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    print(json.dumps(migrate(args.database, args.ground_truth_file, args.backup), indent=2))
