"""Atomic, sanitized local state storage."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from .models import HunterState


class StateStore:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.path = state_dir / "state.json"

    def write(self, state: HunterState) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary = tempfile.mkstemp(prefix=".state-", dir=self.state_dir)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(state.to_dict(), handle, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except BaseException:
            with suppress(FileNotFoundError):
                os.unlink(temporary)
            raise

    def read(self) -> HunterState | None:
        try:
            raw: dict[str, Any] = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        return HunterState(
            schema_version=int(raw["schema_version"]),
            status=str(raw["status"]),
            attempts=int(raw["attempts"]),
            last_result=str(raw["last_result"]),
            updated_at=str(raw["updated_at"]),
            retry_token=(str(raw["retry_token"]) if raw.get("retry_token") else None),
            retry_token_created_at=(
                str(raw["retry_token_created_at"]) if raw.get("retry_token_created_at") else None
            ),
            retry_request_fingerprint=(
                str(raw["retry_request_fingerprint"])
                if raw.get("retry_request_fingerprint")
                else None
            ),
        )
