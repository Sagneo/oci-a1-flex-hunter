from __future__ import annotations

import logging
import threading
from pathlib import Path

import pytest

from oci_a1_flex_hunter.config import HunterConfig
from oci_a1_flex_hunter.errors import AuthenticationError, CapacityUnavailableError
from oci_a1_flex_hunter.hunter import Hunter
from oci_a1_flex_hunter.models import ExitCode, RunOptions
from oci_a1_flex_hunter.state import StateStore

from .fakes import FakeAdapter, repeated_capacity_failures


def options(**changes: object) -> RunOptions:
    values = {
        "live": True,
        "continuous": False,
        "max_attempts": 3,
        "min_delay": 1.0,
        "max_delay": 3.0,
    }
    values.update(changes)
    return RunOptions(**values)  # type: ignore[arg-type]


def make_hunter(
    config: HunterConfig,
    tmp_path: Path,
    *,
    sleeps: list[float] | None = None,
    shutdown: threading.Event | None = None,
) -> Hunter:
    recorded = sleeps if sleeps is not None else []
    return Hunter(
        config,
        StateStore(tmp_path / "runtime"),
        logging.getLogger("test"),
        sleep_fn=lambda delay: recorded.append(delay),
        random_fn=lambda low, high: (low + high) / 2,
        shutdown_event=shutdown,
    )


def test_dry_run_never_calls_adapter(config: HunterConfig, tmp_path: Path) -> None:
    adapter = FakeAdapter()
    result = make_hunter(config, tmp_path).run(options(live=False), adapter)
    assert result.status == "dry-run"
    assert adapter.check_calls == 0
    assert adapter.launch_calls == 0


def test_existing_instance_prevents_launch(config: HunterConfig, tmp_path: Path) -> None:
    adapter = FakeAdapter(existing=True)
    result = make_hunter(config, tmp_path).run(options(), adapter)
    assert result.status == "existing-instance"
    assert adapter.check_calls == 1
    assert adapter.launch_calls == 0


def test_live_launch_exactly_once(config: HunterConfig, tmp_path: Path) -> None:
    adapter = FakeAdapter()
    result = make_hunter(config, tmp_path).run(options(), adapter)
    assert result.exit_code == ExitCode.SUCCESS
    assert adapter.launch_calls == 1


def test_capacity_retries_then_succeeds(config: HunterConfig, tmp_path: Path) -> None:
    sleeps: list[float] = []
    adapter = FakeAdapter(launch_results=[CapacityUnavailableError("synthetic"), None])
    result = make_hunter(config, tmp_path, sleeps=sleeps).run(options(continuous=True), adapter)
    assert result.status == "success"
    assert result.attempts == 2
    assert sleeps == [2.0]


def test_non_retryable_error_stops(config: HunterConfig, tmp_path: Path) -> None:
    adapter = FakeAdapter(launch_results=[AuthenticationError("synthetic")])
    result = make_hunter(config, tmp_path).run(options(continuous=True), adapter)
    assert result.status == "fatal"
    assert result.attempts == 1
    assert adapter.launch_calls == 1


def test_max_attempts_terminates(config: HunterConfig, tmp_path: Path) -> None:
    adapter = FakeAdapter(launch_results=repeated_capacity_failures(3))
    result = make_hunter(config, tmp_path).run(options(continuous=True), adapter)
    assert result.status == "retry-exhausted"
    assert result.exit_code == ExitCode.RETRY_EXHAUSTED
    assert adapter.launch_calls == 3


def test_once_never_retries(config: HunterConfig, tmp_path: Path) -> None:
    adapter = FakeAdapter(launch_results=repeated_capacity_failures(2))
    result = make_hunter(config, tmp_path).run(options(continuous=False), adapter)
    assert result.attempts == 1
    assert adapter.launch_calls == 1


def test_shutdown_before_request(config: HunterConfig, tmp_path: Path) -> None:
    shutdown = threading.Event()
    shutdown.set()
    adapter = FakeAdapter()
    result = make_hunter(config, tmp_path, shutdown=shutdown).run(options(continuous=True), adapter)
    assert result.exit_code == ExitCode.INTERRUPTED
    assert adapter.launch_calls == 0


def test_invalid_run_mode_bounds(config: HunterConfig, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        make_hunter(config, tmp_path).run(options(max_attempts=0), FakeAdapter())
