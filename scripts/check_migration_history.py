"""Reject changes to migrations that exist on the base branch."""

from __future__ import annotations

import argparse
import subprocess


def _git_lines(*args: str) -> set[str]:
    result = subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    return set(result.stdout.splitlines())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Base commit to compare with")
    args = parser.parse_args()

    existing = _git_lines(
        "ls-tree", "-r", "--name-only", args.base, "--", "alembic/versions"
    )
    changed = _git_lines("diff", "--name-only", args.base, "--", "alembic/versions")
    rewritten = sorted(existing & changed)
    if rewritten:
        print("Existing Alembic revisions changed:")
        for path in rewritten:
            print(f"  {path}")
        print(
            "Add a new revision instead. Existing databases will not replay these files."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
