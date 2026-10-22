"""Reject rewritten migrations and new SAST parent-table rebuilds."""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
from pathlib import Path


def _git_lines(*args: str) -> set[str]:
    result = subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    return set(result.stdout.splitlines())


def _sast_parent_rebuilds(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(), filename=str(path))
    unsafe = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        argument = node.args[0] if node.args else None
        if node.func.attr in {"batch_alter_table", "drop_table"}:
            argument = next(
                (
                    keyword.value
                    for keyword in node.keywords
                    if keyword.arg == "table_name"
                ),
                argument,
            )
            if isinstance(argument, ast.Constant) and argument.value == "sast_run":
                unsafe.append(node.lineno)
        elif node.func.attr == "execute":
            if isinstance(argument, ast.Call) and isinstance(
                argument.func, ast.Attribute
            ):
                if argument.func.attr == "text" and argument.args:
                    argument = argument.args[0]
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                sql = argument.value
                if re.match(
                    r"^\s*DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?"
                    r'(?:(?:main|"main"|`main`|\[main\])\.)?'
                    r'(?:sast_run|"sast_run"|`sast_run`|\[sast_run\])\s*(?:;|$)',
                    sql,
                    re.IGNORECASE,
                ):
                    unsafe.append(node.lineno)
    return unsafe


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
    new_revisions = sorted(changed - existing)
    unsafe = [
        (path, line)
        for name in new_revisions
        if (path := Path(name)).is_file()
        for line in _sast_parent_rebuilds(path)
    ]
    if unsafe:
        print("New migrations must not rebuild or drop sast_run with child rows:")
        for path, line in unsafe:
            print(f"  {path}:{line}: add or drop columns in place instead")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
