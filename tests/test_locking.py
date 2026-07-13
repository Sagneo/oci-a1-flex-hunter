from pathlib import Path

import pytest

from oci_a1_flex_hunter.errors import LockUnavailableError
from oci_a1_flex_hunter.locking import ProcessLock


def test_lock_acquire_and_release(tmp_path: Path) -> None:
    lock = ProcessLock(tmp_path / "hunter.lock")
    lock.acquire()
    lock.release()
    with ProcessLock(tmp_path / "hunter.lock"):
        pass


def test_lock_contention(tmp_path: Path) -> None:
    path = tmp_path / "hunter.lock"
    first = ProcessLock(path)
    second = ProcessLock(path)
    first.acquire()
    try:
        with pytest.raises(LockUnavailableError):
            second.acquire()
    finally:
        first.release()
