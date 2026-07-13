from __future__ import annotations

import json
import stat
from pathlib import Path

from oci_a1_flex_hunter.models import HunterState
from oci_a1_flex_hunter.state import StateStore


def test_state_round_trip_and_permissions(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state")
    expected = HunterState.create("waiting", 2, "capacity-unavailable")
    store.write(expected)
    actual = store.read()
    assert actual == expected
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600


def test_state_write_replaces_atomically(tmp_path: Path) -> None:
    store = StateStore(tmp_path / "state")
    store.write(HunterState.create("checking", 1, "first"))
    store.write(HunterState.create("success", 2, "second"))
    raw = json.loads(store.path.read_text(encoding="utf-8"))
    assert raw["status"] == "success"
    assert not list(store.state_dir.glob(".state-*"))


def test_missing_state_returns_none(tmp_path: Path) -> None:
    assert StateStore(tmp_path).read() is None
