"""Environment and CLI configuration with fail-safe validation."""

from __future__ import annotations

import os
import re
import stat
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import isfinite
from pathlib import Path

from .errors import ConfigurationError

PREFIX = "OCI_A1_HUNTER_"
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$")
LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
OCI_REQUIRED_FIELDS = {"user", "fingerprint", "key_file", "tenancy", "region"}
SSH_PUBLIC_KEY_TYPES = (
    "ssh-ed25519",
    "ssh-rsa",
    "ecdsa-sha2-",
    "sk-ssh-ed25519@",
    "sk-ecdsa-sha2-",
)


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
        if (
            not isfinite(self.ocpus)
            or not isfinite(self.memory_gb)
            or self.ocpus <= 0
            or self.memory_gb <= 0
        ):
            raise ConfigurationError("OCPU and memory values must be finite and positive")
        if self.max_attempts < 1:
            raise ConfigurationError("Maximum attempts must be at least one")
        if (
            not isfinite(self.min_delay)
            or not isfinite(self.max_delay)
            or self.min_delay < 0
            or self.max_delay < self.min_delay
        ):
            raise ConfigurationError("Retry delays must be nonnegative and correctly ordered")
        if not SAFE_NAME.fullmatch(self.display_name):
            raise ConfigurationError("Display name has an unsafe format")
        if not SAFE_NAME.fullmatch(self.project_tag):
            raise ConfigurationError("Project tag has an unsafe format")
        if self.shape != "VM.Standard.A1.Flex":
            raise ConfigurationError("Only the VM.Standard.A1.Flex shape is supported")
        if self.boot_volume_size_gb is not None and self.boot_volume_size_gb <= 0:
            raise ConfigurationError("Boot volume size must be positive")
        if self.log_level not in LOG_LEVELS:
            raise ConfigurationError("Log level is unsupported")
        if require_local_files:
            if not self.oci_config_file.is_file():
                raise ConfigurationError("OCI config file does not exist")
            if not self.ssh_public_key_path.is_file():
                raise ConfigurationError("SSH public-key file does not exist")
            try:
                public_key = self.ssh_public_key_path.read_text(encoding="utf-8").strip()
            except (OSError, UnicodeError) as exc:
                raise ConfigurationError("SSH public-key file cannot be read safely") from exc
            fields = public_key.split()
            if (
                len(fields) < 2
                or not fields[0].startswith(SSH_PUBLIC_KEY_TYPES)
                or not re.fullmatch(r"[A-Za-z0-9+/]+={0,3}", fields[1])
            ):
                raise ConfigurationError("SSH public-key file is not a plausible public key")

    def validate_oci_profile(
        self,
        loader: Callable[[str, str], Mapping[str, object]] | None = None,
    ) -> None:
        """Validate the selected SDK profile and signing key without a network call."""
        if loader is None:
            try:
                import oci

                profile = oci.config.from_file(
                    file_location=str(self.oci_config_file), profile_name=self.oci_profile
                )
            except Exception as exc:
                raise ConfigurationError("Selected OCI profile is missing or invalid") from exc
        else:
            try:
                profile = loader(str(self.oci_config_file), self.oci_profile)
            except Exception as exc:
                raise ConfigurationError("Selected OCI profile is missing or invalid") from exc

        if not isinstance(profile, Mapping):
            raise ConfigurationError("Selected OCI profile is missing or invalid")
        missing = OCI_REQUIRED_FIELDS.difference(profile)
        if missing or any(not str(profile[name]).strip() for name in OCI_REQUIRED_FIELDS):
            raise ConfigurationError("Selected OCI profile lacks required SDK fields")

        signing_key = Path(str(profile["key_file"])).expanduser()
        try:
            key_stat = signing_key.stat()
        except OSError as exc:
            raise ConfigurationError("OCI signing-key file does not exist") from exc
        if not stat.S_ISREG(key_stat.st_mode):
            raise ConfigurationError("OCI signing-key path is not a regular file")
        if stat.S_IMODE(key_stat.st_mode) & 0o077:
            raise ConfigurationError("OCI signing-key permissions allow group or other access")
