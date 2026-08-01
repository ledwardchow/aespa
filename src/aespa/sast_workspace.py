"""Cross-process ownership for temporary SAST extraction workspaces."""

from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO


class SastWorkspaceLease:
    """An advisory lock held for the lifetime of one SAST scan workspace."""

    def __init__(self, handle: BinaryIO, path: Path) -> None:
        self._handle = handle
        self.path = path
        self._released = False

    def release(self) -> None:
        if self._released:
            return
        try:
            _unlock(self._handle)
        finally:
            self._handle.close()
            self._released = True


def try_acquire_sast_workspace_lease(
    data_dir: Path, run_id: int
) -> SastWorkspaceLease | None:
    """Try to claim a run workspace without blocking another AESPA process."""
    lock_dir = Path(data_dir) / "sast_extract_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{run_id}.lock"
    handle = lock_path.open("a+b")
    try:
        # Windows byte-range locking needs the byte to exist.
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        if not _try_lock(handle):
            handle.close()
            return None
        return SastWorkspaceLease(handle, lock_path)
    except Exception:
        handle.close()
        raise


def _try_lock(handle: BinaryIO) -> bool:
    if os.name == "nt":
        import msvcrt

        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    import fcntl

    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        return False
    return True


def _unlock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return

    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
