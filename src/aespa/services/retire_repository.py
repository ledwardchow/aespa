"""Where AESPA gets its Retire.js vulnerable-library list.

AESPA ships a copy of the Retire.js repository (``jsrepository-v6.json``) in
``services/data/retire/``. When automatic updates are on, scans also download
the latest list into the data folder at most once a day. A downloaded copy is
used only after it passes the same checks as the shipped copy, and any
download failure leaves the current copy in place.

``scripts/update_retire_repository.py`` uses the same download and checks to
refresh the shipped copy.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import logging
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlmodel import Session

from aespa.db import get_engine
from aespa.services.settings_integrations import get_upstream_proxy_config

log = logging.getLogger(__name__)

RETIRE_URL = (
    "https://raw.githubusercontent.com/RetireJS/retire.js/master/"
    "repository/jsrepository-v6.json"
)
FILE_NAME = "jsrepository-v6.json"
META_NAME = "metadata.json"
BUNDLED_DIR = Path(__file__).with_name("data") / "retire"

MAX_AGE = timedelta(hours=24)
MAX_BYTES = 10 * 1024 * 1024
TIMEOUT_S = 15.0
MIN_LIBRARIES = 50
MIN_COMPILE_RATIO = 0.95

_VERSION_TOKEN = "§§version§§"
_refresh_lock = asyncio.Lock()


class RepositoryError(ValueError):
    """The downloaded data is not a usable Retire.js repository."""


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def cache_dir() -> Path:
    from aespa.config import get_settings

    return Path(get_settings().data_dir) / "retire"


def _read_meta(directory: Path) -> dict[str, Any]:
    try:
        meta = json.loads((directory / META_NAME).read_text("utf-8"))
        return meta if isinstance(meta, dict) else {}
    except (OSError, ValueError):
        return {}


def validate(raw: bytes) -> dict[str, Any]:
    """Parse and check a Retire.js repository, raising ``RepositoryError``."""
    if len(raw) > MAX_BYTES:
        raise RepositoryError(f"file is larger than {MAX_BYTES} bytes")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise RepositoryError(f"not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise RepositoryError("top level is not an object")
    libraries = {
        name: entry
        for name, entry in data.items()
        if isinstance(entry, dict) and name not in {"retire-example", "dont check"}
    }
    if len(libraries) < MIN_LIBRARIES:
        raise RepositoryError(f"only {len(libraries)} libraries listed")
    if "jquery" not in libraries:
        raise RepositoryError("jquery entry is missing")
    total = compiled = 0
    for name, entry in libraries.items():
        vulns = entry.get("vulnerabilities")
        if not isinstance(vulns, list):
            raise RepositoryError(f"{name}: vulnerabilities is not a list")
        for vuln in vulns:
            if not isinstance(vuln, dict) or not vuln.get("below"):
                raise RepositoryError(f"{name}: vulnerability without 'below'")
        extractors = entry.get("extractors") or {}
        for kind in ("uri", "filename", "filecontent"):
            for pattern in extractors.get(kind) or []:
                total += 1
                try:
                    re.compile(str(pattern).replace(_VERSION_TOKEN, "(x)"))
                    compiled += 1
                except re.error:
                    pass
    if total and compiled / total < MIN_COMPILE_RATIO:
        raise RepositoryError(
            f"only {compiled} of {total} patterns are usable in Python"
        )
    return data


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def store(directory: Path, raw: bytes, *, etag: str | None, source: str) -> dict:
    """Write a validated repository and its metadata into ``directory``."""
    validate(raw)
    meta = {
        "source": source,
        "fetched_at": _utcnow().isoformat(),
        "etag": etag,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size": len(raw),
    }
    _write_atomic(directory / FILE_NAME, raw)
    _write_atomic(directory / META_NAME, json.dumps(meta, indent=2).encode())
    return meta


def active_path() -> Path:
    """The repository file scans should use: the download, else the shipped copy."""
    downloaded = cache_dir() / FILE_NAME
    if downloaded.is_file() and _read_meta(cache_dir()).get("sha256"):
        return downloaded
    return BUNDLED_DIR / FILE_NAME


def info() -> dict[str, Any]:
    """Describe the copy in use, for scan messages and findings."""
    path = active_path()
    downloaded = path.parent == cache_dir()
    meta = _read_meta(path.parent)
    return {
        "copy": "downloaded" if downloaded else "shipped",
        "path": str(path),
        "fetched_at": meta.get("fetched_at"),
    }


def describe() -> str:
    details = info()
    stamp = str(details.get("fetched_at") or "")[:10]
    label = "downloaded" if details["copy"] == "downloaded" else "shipped with AESPA"
    return f"Retire.js list {label}" + (f", {stamp}" if stamp else "")


def _is_fresh(meta: dict[str, Any], max_age: timedelta) -> bool:
    try:
        fetched = datetime.fromisoformat(str(meta.get("fetched_at")))
    except ValueError:
        return False
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    return _utcnow() - fetched < max_age


async def _download(
    url: str, etag: str | None, client: httpx.AsyncClient
) -> tuple[int, bytes, str | None]:
    headers = {"If-None-Match": etag} if etag else {}
    async with client.stream("GET", url, headers=headers) as response:
        if response.status_code == 304:
            return 304, b"", etag
        response.raise_for_status()
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > MAX_BYTES:
                raise RepositoryError(f"file is larger than {MAX_BYTES} bytes")
            chunks.append(chunk)
        return response.status_code, b"".join(chunks), response.headers.get("etag")


async def ensure_fresh(
    *,
    enabled: bool = True,
    max_age: timedelta = MAX_AGE,
    url: str = RETIRE_URL,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Download the latest list when the cached copy is stale.

    Never raises: scans continue with the copy they already have.
    """
    if not enabled:
        return {**info(), "status": "disabled"}
    async with _refresh_lock:
        directory = cache_dir()
        meta = _read_meta(directory)
        if (directory / FILE_NAME).is_file() and _is_fresh(meta, max_age):
            return {**info(), "status": "fresh"}
        owns_client = client is None
        if client is None:
            with Session(get_engine()) as session:
                ca_bundle = get_upstream_proxy_config(session).scanner_ca_bundle_path
            http = httpx.AsyncClient(
                timeout=TIMEOUT_S,
                follow_redirects=True,
                verify=ca_bundle or True,
            )
        else:
            http = client
        try:
            etag = meta.get("etag") if (directory / FILE_NAME).is_file() else None
            status, raw, new_etag = await _download(url, etag, http)
            if status == 304:
                meta["fetched_at"] = _utcnow().isoformat()
                _write_atomic(
                    directory / META_NAME, json.dumps(meta, indent=2).encode()
                )
                return {**info(), "status": "unchanged"}
            store(directory, raw, etag=new_etag, source=url)
            return {**info(), "status": "updated"}
        except Exception as exc:  # noqa: BLE001 - keep scanning on any failure
            log.warning("Could not update the Retire.js list: %s", exc)
            return {**info(), "status": "failed", "error": str(exc)[:300]}
        finally:
            if owns_client:
                await http.aclose()
