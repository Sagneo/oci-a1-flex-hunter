from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from oci_a1_flex_hunter.config import HunterConfig
from oci_a1_flex_hunter.errors import (
    AuthenticationError,
    AuthorizationError,
    CapacityUnavailableError,
    HunterError,
    MalformedRequestError,
    NonRetryableOCIError,
    TransientOCIError,
)
from oci_a1_flex_hunter.hunter import Hunter, launch_request_fingerprint
from oci_a1_flex_hunter.models import ExitCode, HunterState, RunOptions
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
    token_factory: Callable[[], str] | None = None,
    now: datetime | None = None,
) -> Hunter:
    recorded = sleeps if sleeps is not None else []
    counter = iter(range(100))
    return Hunter(
        config,
        StateStore(tmp_path / "runtime"),
        logging.getLogger("test"),
        sleep_fn=lambda delay: recorded.append(delay),
        random_fn=lambda low, high: (low + high) / 2,
        shutdown_event=shutdown,
        token_factory=(
            token_factory if token_factory is not None else lambda: f"test-token-{next(counter)}"
        ),
        now_fn=lambda: now or datetime(2026, 7, 13, tzinfo=UTC),
    )


def test_dry_run_never_calls_adapter(config: HunterConfig, tmp_path: Path) -> None:
    adapter = FakeAdapter()
    result = make_hunter(config, tmp_path).run(options(live=False), adapter)
    assert result.status == "dry-run"
    assert adapter.check_calls == 0
    assert adapter.launch_calls == 0


def test_request_fingerprint_is_deterministic(config: HunterConfig) -> None:
    assert launch_request_fingerprint(config) == launch_request_fingerprint(config)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("compartment_id", "different-compartment"),
        ("availability_domain", "different-domain"),
        ("subnet_id", "different-subnet"),
        ("image_id", "different-image"),
        ("shape", "different-shape"),
        ("ocpus", 2.0),
        ("memory_gb", 12.0),
        ("display_name", "different-name"),
        ("project_tag", "different-tag"),
        ("boot_volume_size_gb", 50),
    ],
)
def test_every_launch_field_changes_fingerprint(
    config: HunterConfig, field: str, value: object
) -> None:
    assert launch_request_fingerprint(
        replace(config, **{field: value})
    ) != launch_request_fingerprint(config)


def test_ssh_public_key_content_changes_fingerprint(config: HunterConfig) -> None:
    original = launch_request_fingerprint(config)
    config.ssh_public_key_path.write_text("ssh-ed25519 AAAB changed-fixture\n", encoding="utf-8")
    assert launch_request_fingerprint(config) != original


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
    assert adapter.retry_tokens == ["test-token-0", "test-token-1"]


def test_ambiguous_retry_reuses_token(config: HunterConfig, tmp_path: Path) -> None:
    adapter = FakeAdapter(launch_results=[TransientOCIError("synthetic"), None])
    result = make_hunter(config, tmp_path).run(options(continuous=True), adapter)
    assert result.status == "success"
    assert adapter.retry_tokens == ["test-token-0", "test-token-0"]


def test_ambiguous_token_survives_bounded_process_restart(
    config: HunterConfig, tmp_path: Path
) -> None:
    first = FakeAdapter(launch_results=[TransientOCIError("synthetic")])
    result = make_hunter(config, tmp_path).run(options(), first)
    assert result.status == "retry-exhausted"

    second = FakeAdapter()
    make_hunter(config, tmp_path).run(options(), second)
    assert second.retry_tokens == ["test-token-0"]


def test_dry_run_preserves_matching_recovered_intent(config: HunterConfig, tmp_path: Path) -> None:
    make_hunter(config, tmp_path).run(
        options(), FakeAdapter(launch_results=[TransientOCIError("synthetic")])
    )
    result = make_hunter(config, tmp_path).run(options(live=False), FakeAdapter())
    assert result.status == "dry-run"
    state = StateStore(tmp_path / "runtime").read()
    assert state is not None
    assert state.retry_token == "test-token-0"
    assert state.retry_request_fingerprint == launch_request_fingerprint(config)


def test_persisted_intent_contains_only_digests_for_request_data(
    config: HunterConfig, tmp_path: Path
) -> None:
    adapter = FakeAdapter(launch_results=[TransientOCIError("synthetic")])
    make_hunter(config, tmp_path).run(options(), adapter)
    raw = (tmp_path / "runtime" / "state.json").read_text(encoding="utf-8")
    ssh_content = config.ssh_public_key_path.read_text(encoding="utf-8").strip()
    for raw_value in (
        config.compartment_id,
        config.availability_domain,
        config.subnet_id,
        config.image_id,
        config.display_name,
        config.project_tag,
        ssh_content,
        str(config.ssh_public_key_path),
    ):
        assert raw_value not in raw
    state = StateStore(tmp_path / "runtime").read()
    assert state is not None
    assert state.retry_request_fingerprint == launch_request_fingerprint(config)


def test_expired_retry_token_is_replaced(config: HunterConfig, tmp_path: Path) -> None:
    start = datetime(2026, 7, 13, tzinfo=UTC)
    first = FakeAdapter(launch_results=[TransientOCIError("synthetic")])
    make_hunter(config, tmp_path, now=start, token_factory=lambda: "old-token").run(
        options(), first
    )

    second = FakeAdapter()
    make_hunter(
        config,
        tmp_path,
        now=start + timedelta(hours=24),
        token_factory=lambda: "new-token",
    ).run(options(), second)
    assert second.retry_tokens == ["new-token"]
    assert second.check_calls == 1


def test_changed_request_rejects_nonexpired_intent(config: HunterConfig, tmp_path: Path) -> None:
    first = FakeAdapter(launch_results=[TransientOCIError("synthetic")])
    make_hunter(config, tmp_path).run(options(), first)
    changed = replace(config, display_name="different-target")
    second = FakeAdapter()
    with pytest.raises(ValueError, match="does not match"):
        make_hunter(changed, tmp_path).run(options(), second)
    assert second.check_calls == 0
    assert second.launch_calls == 0


def test_definitive_launch_error_stops(config: HunterConfig, tmp_path: Path) -> None:
    adapter = FakeAdapter(launch_results=[AuthenticationError("synthetic")])
    result = make_hunter(config, tmp_path).run(options(continuous=True), adapter)
    assert result.status == "fatal"
    assert result.attempts == 1
    assert adapter.launch_calls == 1
    state = StateStore(tmp_path / "runtime").read()
    assert state is not None
    assert state.retry_token is None
    assert state.retry_token_created_at is None
    assert state.retry_request_fingerprint is None


@pytest.mark.parametrize(
    "error",
    [
        AuthenticationError("synthetic"),
        AuthorizationError("synthetic"),
        MalformedRequestError("synthetic"),
    ],
)
def test_definitive_post_submission_rejection_clears_intent(
    config: HunterConfig, tmp_path: Path, error: HunterError
) -> None:
    result = make_hunter(config, tmp_path).run(options(), FakeAdapter(launch_results=[error]))
    assert result.status == "fatal"
    state = StateStore(tmp_path / "runtime").read()
    assert state is not None
    assert (state.retry_token, state.retry_token_created_at, state.retry_request_fingerprint) == (
        None,
        None,
        None,
    )


@pytest.mark.parametrize(
    "error",
    [TransientOCIError("synthetic"), NonRetryableOCIError("synthetic")],
)
def test_ambiguous_post_submission_result_preserves_intent(
    config: HunterConfig, tmp_path: Path, error: HunterError
) -> None:
    make_hunter(config, tmp_path).run(options(), FakeAdapter(launch_results=[error]))
    state = StateStore(tmp_path / "runtime").read()
    assert state is not None
    assert state.retry_token == "test-token-0"
    assert state.retry_request_fingerprint == launch_request_fingerprint(config)


def test_capacity_rejection_clears_complete_intent(config: HunterConfig, tmp_path: Path) -> None:
    make_hunter(config, tmp_path).run(
        options(), FakeAdapter(launch_results=[CapacityUnavailableError("synthetic")])
    )
    state = StateStore(tmp_path / "runtime").read()
    assert state is not None
    assert (state.retry_token, state.retry_token_created_at, state.retry_request_fingerprint) == (
        None,
        None,
        None,
    )


@pytest.mark.parametrize(
    "error",
    [
        AuthenticationError("synthetic"),
        AuthorizationError("synthetic"),
        NonRetryableOCIError("synthetic"),
    ],
)
def test_preflight_fatal_error_preserves_recovered_intent(
    config: HunterConfig, tmp_path: Path, error: HunterError
) -> None:
    first = FakeAdapter(launch_results=[TransientOCIError("synthetic")])
    make_hunter(config, tmp_path).run(options(), first)

    preflight = FakeAdapter(check_results=[error])
    result = make_hunter(config, tmp_path).run(options(), preflight)
    assert result.status == "fatal"
    assert preflight.check_calls == 1
    assert preflight.launch_calls == 0
    state = StateStore(tmp_path / "runtime").read()
    assert state is not None
    assert state.retry_token == "test-token-0"
    assert state.retry_request_fingerprint == launch_request_fingerprint(config)


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


def test_live_mode_requires_adapter(config: HunterConfig, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires an OCI adapter"):
        make_hunter(config, tmp_path).run(options(), None)


def test_shutdown_after_retry_preserves_ambiguous_token(
    config: HunterConfig, tmp_path: Path
) -> None:
    shutdown = threading.Event()

    def stop_after_delay(delay: float) -> None:
        del delay
        shutdown.set()

    hunter = make_hunter(config, tmp_path, shutdown=shutdown)
    hunter.sleep_fn = stop_after_delay
    adapter = FakeAdapter(launch_results=[TransientOCIError("synthetic")])
    result = hunter.run(options(continuous=True), adapter)
    assert result.exit_code == ExitCode.INTERRUPTED
    state = StateStore(tmp_path / "runtime").read()
    assert state is not None
    assert state.retry_token == "test-token-0"


def test_recovery_fails_closed_for_invalid_token_timestamps(
    config: HunterConfig, tmp_path: Path
) -> None:
    store = StateStore(tmp_path / "runtime")
    store.write(
        HunterState.create(
            "waiting",
            1,
            "transient-service-error",
            retry_token="old-token",
            retry_token_created_at="not-a-timestamp",
            retry_request_fingerprint=launch_request_fingerprint(config),
        )
    )
    with pytest.raises(ValueError, match="Retry intent state"):
        make_hunter(config, tmp_path, token_factory=lambda: "new-token").run(
            options(), FakeAdapter()
        )


def test_recovery_fails_closed_for_naive_token_timestamp(
    config: HunterConfig, tmp_path: Path
) -> None:
    store = StateStore(tmp_path / "runtime")
    store.write(
        HunterState.create(
            "waiting",
            1,
            "transient-service-error",
            retry_token="old-token",
            retry_token_created_at="2026-07-13T00:00:00",
            retry_request_fingerprint=launch_request_fingerprint(config),
        )
    )
    with pytest.raises(ValueError, match="Retry intent state"):
        make_hunter(config, tmp_path, token_factory=lambda: "new-token").run(
            options(), FakeAdapter()
        )


def test_recovery_fails_closed_for_incomplete_token_state(
    config: HunterConfig, tmp_path: Path
) -> None:
    store = StateStore(tmp_path / "runtime")
    store.write(
        HunterState.create("waiting", 1, "transient-service-error", retry_token="old-token")
    )
    with pytest.raises(ValueError, match="incomplete"):
        make_hunter(config, tmp_path).run(options(), FakeAdapter())


def test_recovery_fails_closed_when_active_token_has_no_fingerprint(
    config: HunterConfig, tmp_path: Path
) -> None:
    StateStore(tmp_path / "runtime").write(
        HunterState.create(
            "waiting",
            1,
            "transient-service-error",
            retry_token="old-token",
            retry_token_created_at="2026-07-13T00:00:00+00:00",
        )
    )
    with pytest.raises(ValueError, match="incomplete"):
        make_hunter(config, tmp_path).run(options(), FakeAdapter())


def test_recovery_fails_closed_for_malformed_fingerprint(
    config: HunterConfig, tmp_path: Path
) -> None:
    StateStore(tmp_path / "runtime").write(
        HunterState.create(
            "waiting",
            1,
            "transient-service-error",
            retry_token="old-token",
            retry_token_created_at="2026-07-13T00:00:00+00:00",
            retry_request_fingerprint="not-a-sha256-digest",
        )
    )
    with pytest.raises(ValueError, match="fingerprint is invalid"):
        make_hunter(config, tmp_path).run(options(), FakeAdapter())


def test_recovery_fails_closed_for_future_timestamp(config: HunterConfig, tmp_path: Path) -> None:
    now = datetime(2026, 7, 13, tzinfo=UTC)
    store = StateStore(tmp_path / "runtime")
    store.write(
        HunterState.create(
            "waiting",
            1,
            "transient-service-error",
            retry_token="old-token",
            retry_token_created_at=(now + timedelta(minutes=1)).isoformat(),
            retry_request_fingerprint=launch_request_fingerprint(config),
        )
    )
    with pytest.raises(ValueError, match="future"):
        make_hunter(config, tmp_path, now=now).run(options(), FakeAdapter())


def test_invalid_run_mode_bounds(config: HunterConfig, tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        make_hunter(config, tmp_path).run(options(max_attempts=0), FakeAdapter())
    with pytest.raises(ValueError, match="delay"):
        make_hunter(config, tmp_path).run(options(min_delay=4, max_delay=3), FakeAdapter())
