from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from oci_a1_flex_hunter.config import HunterConfig
from oci_a1_flex_hunter.errors import ConfigurationError


def test_valid_configuration(config: HunterConfig) -> None:
    config.validate()


@pytest.mark.parametrize("field", ["compartment_id", "subnet_id", "image_id"])
def test_required_identifiers_must_be_nonempty(config: HunterConfig, field: str) -> None:
    with pytest.raises(ConfigurationError):
        replace(config, **{field: ""}).validate()


@pytest.mark.parametrize(("ocpus", "memory"), [(0, 1), (1, 0), (-1, 2)])
def test_resources_must_be_positive(config: HunterConfig, ocpus: float, memory: float) -> None:
    with pytest.raises(ConfigurationError):
        replace(config, ocpus=ocpus, memory_gb=memory).validate()


@pytest.mark.parametrize(("ocpus", "memory"), [(float("nan"), 1), (1, float("inf"))])
def test_resources_must_be_finite(config: HunterConfig, ocpus: float, memory: float) -> None:
    with pytest.raises(ConfigurationError, match="finite"):
        replace(config, ocpus=ocpus, memory_gb=memory).validate()


def test_delay_order_is_validated(config: HunterConfig) -> None:
    with pytest.raises(ConfigurationError, match="Retry delays"):
        replace(config, min_delay=5, max_delay=1).validate()
    with pytest.raises(ConfigurationError, match="Retry delays"):
        replace(config, min_delay=float("nan")).validate()


def test_shape_is_restricted_to_a1_flex(config: HunterConfig) -> None:
    with pytest.raises(ConfigurationError, match=r"A1\.Flex"):
        replace(config, shape="VM.Standard.E4.Flex").validate()


@pytest.mark.parametrize("value", ["bad name", "bad/tag", "", "x" * 64])
def test_safe_display_name(config: HunterConfig, value: str) -> None:
    with pytest.raises(ConfigurationError):
        replace(config, display_name=value).validate()


def test_missing_local_file_is_sanitized(config: HunterConfig, tmp_path: Path) -> None:
    missing = tmp_path / "private-location" / "config"
    with pytest.raises(ConfigurationError) as raised:
        replace(config, oci_config_file=missing).validate()
    assert str(missing) not in str(raised.value)


def test_boot_volume_must_be_positive(config: HunterConfig) -> None:
    with pytest.raises(ConfigurationError):
        replace(config, boot_volume_size_gb=0).validate()


@pytest.mark.parametrize(("ocpus", "memory"), [(2, 12), (4, 24)])
def test_resource_profile_is_configurable(
    config: HunterConfig, ocpus: float, memory: float
) -> None:
    replace(config, ocpus=ocpus, memory_gb=memory).validate()


def test_offline_profile_validation(config: HunterConfig, tmp_path: Path) -> None:
    signing_key = tmp_path / "signing-key.pem"
    signing_key.write_text("synthetic fixture\n", encoding="utf-8")
    signing_key.chmod(0o600)
    calls: list[tuple[str, str]] = []

    def loader(path: str, profile: str) -> dict[str, object]:
        calls.append((path, profile))
        return {
            "user": "synthetic-user",
            "fingerprint": "synthetic-fingerprint",
            "key_file": str(signing_key),
            "tenancy": "synthetic-tenancy",
            "region": "synthetic-region-1",
        }

    config.validate_oci_profile(loader)
    assert calls == [(str(config.oci_config_file), config.oci_profile)]


@pytest.mark.parametrize("missing", ["user", "fingerprint", "key_file", "tenancy", "region"])
def test_profile_requires_every_sdk_field(
    config: HunterConfig, tmp_path: Path, missing: str
) -> None:
    signing_key = tmp_path / "key.pem"
    signing_key.write_text("fixture\n", encoding="utf-8")
    signing_key.chmod(0o600)
    profile = {
        "user": "synthetic-user",
        "fingerprint": "synthetic-fingerprint",
        "key_file": str(signing_key),
        "tenancy": "synthetic-tenancy",
        "region": "synthetic-region-1",
    }
    profile.pop(missing)
    with pytest.raises(ConfigurationError, match="required SDK fields"):
        config.validate_oci_profile(lambda path, name: profile)


def test_profile_loader_error_is_sanitized(config: HunterConfig) -> None:
    def rejected(path: str, name: str) -> dict[str, object]:
        raise ValueError(f"sensitive {path} {name}")

    with pytest.raises(ConfigurationError) as raised:
        config.validate_oci_profile(rejected)
    assert str(config.oci_config_file) not in str(raised.value)


def test_signing_key_must_be_private(config: HunterConfig, tmp_path: Path) -> None:
    signing_key = tmp_path / "key.pem"
    signing_key.write_text("fixture\n", encoding="utf-8")
    signing_key.chmod(0o644)
    profile = {
        "user": "u",
        "fingerprint": "f",
        "key_file": str(signing_key),
        "tenancy": "t",
        "region": "r",
    }
    with pytest.raises(ConfigurationError, match="permissions"):
        config.validate_oci_profile(lambda path, name: profile)


def test_signing_key_must_be_regular_file(config: HunterConfig, tmp_path: Path) -> None:
    profile = {
        "user": "u",
        "fingerprint": "f",
        "key_file": str(tmp_path),
        "tenancy": "t",
        "region": "r",
    }
    with pytest.raises(ConfigurationError, match="regular file"):
        config.validate_oci_profile(lambda path, name: profile)


def test_ssh_file_must_look_like_public_key(config: HunterConfig) -> None:
    config.ssh_public_key_path.write_text("not-a-public-key\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="plausible public key"):
        config.validate()
