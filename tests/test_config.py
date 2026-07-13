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


def test_delay_order_is_validated(config: HunterConfig) -> None:
    with pytest.raises(ConfigurationError, match="Retry delays"):
        replace(config, min_delay=5, max_delay=1).validate()


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
