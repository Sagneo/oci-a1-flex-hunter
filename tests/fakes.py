from __future__ import annotations

from collections.abc import Sequence

from oci_a1_flex_hunter.errors import CapacityUnavailableError, HunterError
from oci_a1_flex_hunter.models import HunterConfigProtocol, LaunchResult


class FakeAdapter:
    def __init__(
        self,
        *,
        existing: bool = False,
        check_results: Sequence[HunterError | bool] = (),
        launch_results: Sequence[HunterError | None] = (),
    ) -> None:
        self.existing = existing
        self.check_results = list(check_results)
        self.launch_results = list(launch_results)
        self.check_calls = 0
        self.launch_calls = 0
        self.retry_tokens: list[str] = []

    def matching_instance_exists(self, config: HunterConfigProtocol) -> bool:
        del config
        self.check_calls += 1
        result = self.check_results.pop(0) if self.check_results else self.existing
        if isinstance(result, HunterError):
            raise result
        return result

    def launch_instance(self, config: HunterConfigProtocol, retry_token: str) -> LaunchResult:
        del config
        self.launch_calls += 1
        self.retry_tokens.append(retry_token)
        result = self.launch_results.pop(0) if self.launch_results else None
        if result is not None:
            raise result
        return LaunchResult()


def repeated_capacity_failures(count: int) -> list[HunterError]:
    return [CapacityUnavailableError("synthetic capacity failure") for _ in range(count)]
