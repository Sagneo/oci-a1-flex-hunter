from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from oci_a1_flex_hunter.cli import main
from oci_a1_flex_hunter.errors import CapacityUnavailableError
from oci_a1_flex_hunter.models import ExitCode, HunterState
from oci_a1_flex_hunter.state import StateStore

from .fakes import FakeAdapter


def valid_profile_loader(tmp_path: Path) -> Any:
    def loader(path: str, profile: str) -> dict[str, object]:
        del path, profile
        return {
            "user": "user-test",
            "fingerprint": "fingerprint-test",
            "key_file": str(tmp_path / "signing.pem"),
            "tenancy": "tenancy-test",
            "region": "region-test-1",
        }

    return loader


def config_args(tmp_path: Path) -> list[str]:
    oci_config = tmp_path / "oci-config"
    signing_key = tmp_path / "signing.pem"
    ssh_key = tmp_path / "test.pub"
    signing_key.write_text("synthetic signing fixture\n", encoding="utf-8")
    signing_key.chmod(0o600)
    oci_config.write_text(
        "[DEFAULT]\n"
        "user=user-test\n"
        "fingerprint=fingerprint-test\n"
        f"key_file={signing_key}\n"
        "tenancy=tenancy-test\n"
        "region=region-test-1\n",
        encoding="utf-8",
    )
    ssh_key.write_text("ssh-ed25519 AAAA synthetic-test\n", encoding="utf-8")
    return [
        "--oci-config",
        str(oci_config),
        "--compartment-id",
        "compartment-test",
        "--availability-domain",
        "domain-test",
        "--subnet-id",
        "subnet-test",
        "--image-id",
        "image-test",
        "--display-name",
        "sagneo-a1-test",
        "--ssh-public-key",
        str(ssh_key),
        "--project-tag",
        "sagneo-a1-test",
        "--state-dir",
        str(tmp_path / "state"),
    ]


@pytest.mark.parametrize("command", [None, "validate-config", "check", "run", "status"])
def test_help(command: str | None) -> None:
    args = ["--help"] if command is None else [command, "--help"]
    with pytest.raises(SystemExit) as raised:
        main(args)
    assert raised.value.code == 0


def test_validate_config_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = config_args(tmp_path)
    assert (
        main(["validate-config", *args], profile_loader=valid_profile_loader(tmp_path))
        == ExitCode.SUCCESS
    )
    assert "no OCI request" in capsys.readouterr().out


def test_validate_config_failure_is_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate-config"]) == ExitCode.CONFIGURATION
    assert "Configuration error" in capsys.readouterr().err


def test_check_uses_read_only_adapter(tmp_path: Path) -> None:
    fake = FakeAdapter(existing=True)
    result = main(
        ["check", *config_args(tmp_path)],
        adapter_factory=lambda config: fake,
        profile_loader=valid_profile_loader(tmp_path),
    )
    assert result == ExitCode.SUCCESS
    assert fake.check_calls == 1
    assert fake.launch_calls == 0


def test_cli_dry_run_does_not_build_adapter(tmp_path: Path) -> None:
    def forbidden_factory(config: object) -> FakeAdapter:
        del config
        raise AssertionError("adapter must not be created for dry-run")

    def forbidden_loader(path: str, profile: str) -> dict[str, object]:
        del path, profile
        raise AssertionError("profile must not be loaded for dry-run")

    result = main(
        ["run", *config_args(tmp_path), "--once"],
        adapter_factory=forbidden_factory,
        profile_loader=forbidden_loader,
    )
    assert result == ExitCode.SUCCESS


def test_cli_live_launches_once(tmp_path: Path) -> None:
    fake = FakeAdapter()
    result = main(
        ["run", *config_args(tmp_path), "--live", "--once"],
        adapter_factory=lambda config: fake,
        profile_loader=valid_profile_loader(tmp_path),
    )
    assert result == ExitCode.SUCCESS
    assert fake.launch_calls == 1


def test_status_does_not_contact_adapter(tmp_path: Path) -> None:
    def forbidden_factory(config: object) -> FakeAdapter:
        del config
        raise AssertionError("status must be local by default")

    result = main(
        ["status", "--state-dir", str(tmp_path / "state")],
        adapter_factory=forbidden_factory,
    )
    assert result == ExitCode.SUCCESS


def test_status_redacts_retry_token(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state_dir = tmp_path / "state"
    fingerprint = "a" * 64
    StateStore(state_dir).write(
        HunterState.create(
            "waiting",
            1,
            "transient-service-error",
            retry_token="sensitive-test-token",
            retry_token_created_at="2026-07-13T00:00:00+00:00",
            retry_request_fingerprint=fingerprint,
        )
    )
    assert main(["status", "--state-dir", str(state_dir)]) == ExitCode.SUCCESS
    output = capsys.readouterr().out
    assert "sensitive-test-token" not in output
    assert fingerprint not in output
    assert '"retry_token_active": true' in output
    assert '"retry_intent_bound": true' in output


@pytest.mark.parametrize("command", ["check", "status-refresh", "run-live"])
def test_profile_validation_blocks_adapter_construction(tmp_path: Path, command: str) -> None:
    config = config_args(tmp_path)
    adapter_calls = 0

    def forbidden_factory(loaded: object) -> FakeAdapter:
        nonlocal adapter_calls
        del loaded
        adapter_calls += 1
        raise AssertionError("adapter must not be created")

    def rejected_loader(path: str, profile: str) -> dict[str, object]:
        del path, profile
        raise ValueError("synthetic invalid profile")

    argv = {
        "check": ["check", *config],
        "status-refresh": ["status", *config, "--refresh"],
        "run-live": ["run", *config, "--live", "--once"],
    }[command]
    assert (
        main(argv, adapter_factory=forbidden_factory, profile_loader=rejected_loader)
        == ExitCode.CONFIGURATION
    )
    assert adapter_calls == 0


def test_omitted_max_attempts_uses_config_default(tmp_path: Path) -> None:
    fake = FakeAdapter(launch_results=[CapacityUnavailableError("synthetic")] * 5)
    result = main(
        [
            "run",
            *config_args(tmp_path),
            "--live",
            "--continuous",
            "--min-delay",
            "0",
            "--max-delay",
            "0",
        ],
        adapter_factory=lambda config: fake,
        profile_loader=valid_profile_loader(tmp_path),
    )
    assert result == ExitCode.RETRY_EXHAUSTED
    assert fake.launch_calls == 5


def test_positive_max_attempts_override_is_honored(tmp_path: Path) -> None:
    fake = FakeAdapter(launch_results=[CapacityUnavailableError("synthetic")] * 2)
    result = main(
        [
            "run",
            *config_args(tmp_path),
            "--live",
            "--continuous",
            "--max-attempts",
            "2",
            "--min-delay",
            "0",
            "--max-delay",
            "0",
        ],
        adapter_factory=lambda config: fake,
        profile_loader=valid_profile_loader(tmp_path),
    )
    assert result == ExitCode.RETRY_EXHAUSTED
    assert fake.launch_calls == 2


@pytest.mark.parametrize("invalid", ["0", "-1"])
def test_invalid_max_attempts_never_constructs_adapter(tmp_path: Path, invalid: str) -> None:
    adapter_calls = 0

    def forbidden_factory(config: object) -> FakeAdapter:
        nonlocal adapter_calls
        del config
        adapter_calls += 1
        raise AssertionError("adapter must not be created")

    result = main(
        [
            "run",
            *config_args(tmp_path),
            "--live",
            "--continuous",
            "--max-attempts",
            invalid,
        ],
        adapter_factory=forbidden_factory,
        profile_loader=valid_profile_loader(tmp_path),
    )
    assert result != ExitCode.SUCCESS
    assert adapter_calls == 0
