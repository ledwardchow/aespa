"""Refresh the Retire.js list shipped with AESPA.

Downloads the latest ``jsrepository-v6.json`` from the Retire.js project,
checks it the same way scans check a downloaded copy, and writes it to
``src/aespa/services/data/retire/``. Exits with status 0 whether or not the
file changed; prints ``changed`` or ``unchanged`` on the last line.

    uv run python scripts/update_retire_repository.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys

import httpx

from aespa.services import retire_repository


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=retire_repository.RETIRE_URL)
    args = parser.parse_args()

    response = httpx.get(
        args.url, timeout=retire_repository.TIMEOUT_S, follow_redirects=True
    )
    response.raise_for_status()
    raw = response.content
    retire_repository.validate(raw)

    directory = retire_repository.BUNDLED_DIR
    current = directory / retire_repository.FILE_NAME
    digest = hashlib.sha256(raw).hexdigest()
    if current.is_file() and hashlib.sha256(current.read_bytes()).hexdigest() == digest:
        print("unchanged")
        return 0

    meta = retire_repository.store(
        directory, raw, etag=response.headers.get("etag"), source=args.url
    )
    libraries = len(json.loads(raw))
    print(f"Wrote {meta['size']} bytes ({libraries} entries) to {current}")
    print("changed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
