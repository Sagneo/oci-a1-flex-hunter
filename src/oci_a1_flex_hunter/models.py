"""Small data models shared by the controller and adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import IntEnum
from pathlib import Path
from typing import Any, Protocol


class ExitCode(IntEnum):
    SUCCESS = 0
    CONFIGURATION = 2
    LOCKED = 3
    RETRY_EXHAUSTED = 4
    OCI_ERROR = 5
    STATE_ERROR = 6
    INTERRUPTED = 130


@dataclass(frozen=True, slots=True)
class LaunchResult:
    """Sanitized acknowledgement from an accepted launch request."""

    accepted: bool = True


@dataclass(frozen=True, slots=True)
class RunOptions:
    live: bool
    continuous: bool
    max_attempts: int
    min_delay: float
    max_delay: float


@dataclass(frozen=True, slots=True)
class RunOutcome:
    status: str
    attempts: int
    exit_code: ExitCode


@dataclass(frozen=True, slots=True)
class HunterState:
    schema_version: int
    status: str
    attempts: int
    last_result: str
    updated_at: str
    retry_token: str | None = None
    retry_token_created_at: str | None = None
    retry_request_fingerprint: str | None = None

    @classmethod
    def create(
        cls,
        status: str,
        attempts: int,
        last_result: str,
        *,
        retry_token: str | None = None,
        retry_token_created_at: str | None = None,
        retry_request_fingerprint: str | None = None,
        now: datetime | None = None,
    ) -> HunterState:
        return cls(
            schema_version=3,
            status=status,
            attempts=attempts,
            last_result=last_result,
            updated_at=(now or datetime.now(UTC)).isoformat(),
            retry_token=retry_token,
            retry_token_created_at=retry_token_created_at,
            retry_request_fingerprint=retry_request_fingerprint,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HunterConfigProtocol(Protocol):
    @property
    def compartment_id(self) -> str: ...

    @property
    def availability_domain(self) -> str: ...

    @property
    def subnet_id(self) -> str: ...

    @property
    def image_id(self) -> str: ...

    @property
    def shape(self) -> str: ...

    @property
    def ocpus(self) -> float: ...

    @property
    def memory_gb(self) -> float: ...

    @property
    def display_name(self) -> str: ...

    @property
    def ssh_public_key_path(self) -> Path: ...

    @property
    def project_tag(self) -> str: ...

    @property
    def boot_volume_size_gb(self) -> int | None: ...


class ComputeAdapter(Protocol):
    def matching_instance_exists(self, config: HunterConfigProtocol) -> bool: ...

    def launch_instance(self, config: HunterConfigProtocol, retry_token: str) -> LaunchResult: ...
