"""Environment and CLI configuration with fail-safe validation."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigurationError

PREFIX = "OCI_A1_HUNTER_"
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$")
LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _required(values: Mapping[str, str], name: str) -> str:
    value = values.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"Required setting {name} is missing")
    return value


def _float(values: Mapping[str, str], name: str, default: str) -> float:
    try:
        return float(values.get(name, default))
    except ValueError as exc:
        raise ConfigurationError(f"Setting {name} must be numeric") from exc


def _int(values: Mapping[str, str], name: str, default: str) -> int:
    try:
        return int(values.get(name, default))
    except ValueError as exc:
        raise ConfigurationError(f"Setting {name} must be an integer") from exc


@dataclass(frozen=True, slots=True)
class HunterConfig:
    oci_config_file: Path
    oci_profile: str
    compartment_id: str
    availability_domain: str
    subnet_id: str
    image_id: str
    shape: str
    ocpus: float
    memory_gb: float
    display_name: str
    ssh_public_key_path: Path
    project_tag: str
    boot_volume_size_gb: int | None
    max_attempts: int
    min_delay: float
    max_delay: float
    state_dir: Path
    log_level: str

    @classmethod
    def from_environment(cls, overrides: Mapping[str, str | None] | None = None) -> HunterConfig:
        values = {
            key.removeprefix(PREFIX): value
            for key, value in os.environ.items()
            if key.startswith(PREFIX)
        }
        for key, value in (overrides or {}).items():
            if value is not None:
                values[key] = value

        boot_raw = values.get("BOOT_VOLUME_SIZE_GB", "").strip()
        boot_size = _int(values, "BOOT_VOLUME_SIZE_GB", boot_raw) if boot_raw else None
        config = cls(
            oci_config_file=Path(
                values.get("OCI_CONFIG", str(Path.home() / ".oci" / "config"))
            ).expanduser(),
            oci_profile=values.get("OCI_PROFILE", "DEFAULT").strip() or "DEFAULT",
            compartment_id=_required(values, "COMPARTMENT_ID"),
            availability_domain=_required(values, "AVAILABILITY_DOMAIN"),
            subnet_id=_required(values, "SUBNET_ID"),
            image_id=_required(values, "IMAGE_ID"),
            shape=values.get("SHAPE", "VM.Standard.A1.Flex").strip() or "VM.Standard.A1.Flex",
            ocpus=_float(values, "OCPUS", "1"),
            memory_gb=_float(values, "MEMORY_GB", "6"),
            display_name=_required(values, "DISPLAY_NAME"),
            ssh_public_key_path=Path(_required(values, "SSH_PUBLIC_KEY")).expanduser(),
            project_tag=_required(values, "PROJECT_TAG"),
            boot_volume_size_gb=boot_size,
            max_attempts=_int(values, "MAX_ATTEMPTS", "5"),
            min_delay=_float(values, "MIN_DELAY", "30"),
            max_delay=_float(values, "MAX_DELAY", "120"),
            state_dir=Path(
                values.get(
                    "STATE_DIR", str(Path.home() / ".local" / "state" / "oci-a1-flex-hunter")
                )
            ).expanduser(),
            log_level=values.get("LOG_LEVEL", "INFO").upper(),
        )
        config.validate()
        return config

    def validate(self, *, require_local_files: bool = True) -> None:
        required_text = (
            self.compartment_id,
            self.availability_domain,
            self.subnet_id,
            self.image_id,
            self.oci_profile,
        )
        if any(not value.strip() for value in required_text):
            raise ConfigurationError("A required identifier or profile is empty")
        if self.ocpus <= 0 or self.memory_gb <= 0:
            raise ConfigurationError("OCPU and memory values must be positive")
        if self.max_attempts < 1:
            raise ConfigurationError("Maximum attempts must be at least one")
        if self.min_delay < 0 or self.max_delay < self.min_delay:
            raise ConfigurationError("Retry delays must be nonnegative and correctly ordered")
        if not SAFE_NAME.fullmatch(self.display_name):
            raise ConfigurationError("Display name has an unsafe format")
        if not SAFE_NAME.fullmatch(self.project_tag):
            raise ConfigurationError("Project tag has an unsafe format")
        if not self.shape:
            raise ConfigurationError("Shape is required")
        if self.boot_volume_size_gb is not None and self.boot_volume_size_gb <= 0:
            raise ConfigurationError("Boot volume size must be positive")
        if self.log_level not in LOG_LEVELS:
            raise ConfigurationError("Log level is unsupported")
        if require_local_files:
            if not self.oci_config_file.is_file():
                raise ConfigurationError("OCI config file does not exist")
            if not self.ssh_public_key_path.is_file():
                raise ConfigurationError("SSH public-key file does not exist")
