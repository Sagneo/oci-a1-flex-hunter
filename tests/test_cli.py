from __future__ import annotations

from pathlib import Path

import pytest

from oci_a1_flex_hunter.cli import main
from oci_a1_flex_hunter.models import ExitCode, HunterState
from oci_a1_flex_hunter.state import StateStore

from .fakes import FakeAdapter


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
    signing_key = tmp_path / "signing.pem"

    def loader(path: str, profile: str) -> dict[str, object]:
        del path, profile
        return {
            "user": "user-test",
            "fingerprint": "fingerprint-test",
            "key_file": str(signing_key),
            "tenancy": "tenancy-test",
            "region": "region-test-1",
        }

    assert main(["validate-config", *args], profile_loader=loader) == ExitCode.SUCCESS
    assert "no OCI request" in capsys.readouterr().out


def test_validate_config_failure_is_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["validate-config"]) == ExitCode.CONFIGURATION
    assert "Configuration error" in capsys.readouterr().err


def test_check_uses_read_only_adapter(tmp_path: Path) -> None:
    fake = FakeAdapter(existing=True)
    result = main(["check", *config_args(tmp_path)], adapter_factory=lambda config: fake)
    assert result == ExitCode.SUCCESS
    assert fake.check_calls == 1
    assert fake.launch_calls == 0


def test_cli_dry_run_does_not_build_adapter(tmp_path: Path) -> None:
    def forbidden_factory(config: object) -> FakeAdapter:
        del config
        raise AssertionError("adapter must not be created for dry-run")

    result = main(["run", *config_args(tmp_path), "--once"], adapter_factory=forbidden_factory)
    assert result == ExitCode.SUCCESS


def test_cli_live_launches_once(tmp_path: Path) -> None:
    fake = FakeAdapter()
    result = main(
        ["run", *config_args(tmp_path), "--live", "--once"],
        adapter_factory=lambda config: fake,
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
    StateStore(state_dir).write(
        HunterState.create(
            "waiting",
            1,
            "transient-service-error",
            retry_token="sensitive-test-token",
            retry_token_created_at="2026-07-13T00:00:00+00:00",
        )
    )
    assert main(["status", "--state-dir", str(state_dir)]) == ExitCode.SUCCESS
    output = capsys.readouterr().out
    assert "sensitive-test-token" not in output
    assert '"retry_token_active": true' in output
