"""Bounded, sequential launch controller."""

from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Callable

from .config import HunterConfig
from .errors import (
    AuthenticationError,
    AuthorizationError,
    CapacityUnavailableError,
    MalformedRequestError,
    NonRetryableOCIError,
    TransientOCIError,
)
from .models import ComputeAdapter, ExitCode, HunterState, RunOptions, RunOutcome
from .state import StateStore
from .util import jitter_delay

RetryableError = CapacityUnavailableError | TransientOCIError
FatalError = AuthenticationError | AuthorizationError | MalformedRequestError | NonRetryableOCIError


class Hunter:
    def __init__(
        self,
        config: HunterConfig,
        state_store: StateStore,
        logger: logging.Logger,
        *,
        sleep_fn: Callable[[float], object] = time.sleep,
        random_fn: Callable[[float, float], float] = random.uniform,
        shutdown_event: threading.Event | None = None,
    ) -> None:
        self.config = config
        self.state_store = state_store
        self.logger = logger
        self.sleep_fn = sleep_fn
        self.random_fn = random_fn
        self.shutdown_event = shutdown_event or threading.Event()

    def run(self, options: RunOptions, adapter: ComputeAdapter | None = None) -> RunOutcome:
        self._validate_options(options)
        if not options.live:
            self.logger.info("dry_run_validated mode=dry-run")
            return self._finish("dry-run", 0, "launch-not-requested", ExitCode.SUCCESS)
        if adapter is None:
            raise ValueError("Live mode requires an OCI adapter")

        attempt_limit = options.max_attempts if options.continuous else 1
        attempts = 0
        while attempts < attempt_limit:
            if self.shutdown_event.is_set():
                return self._finish("interrupted", attempts, "signal", ExitCode.INTERRUPTED)
            attempts += 1
            self.state_store.write(HunterState.create("checking", attempts, "read-only-check"))
            try:
                if adapter.matching_instance_exists(self.config):
                    self.logger.info("matching_instance_exists action=stop")
                    return self._finish(
                        "existing-instance", attempts, "duplicate-prevented", ExitCode.SUCCESS
                    )
                adapter.launch_instance(self.config)
                self.logger.info("launch_accepted action=stop")
                return self._finish("success", attempts, "launch-accepted", ExitCode.SUCCESS)
            except (CapacityUnavailableError, TransientOCIError) as exc:
                category = (
                    "capacity-unavailable"
                    if isinstance(exc, CapacityUnavailableError)
                    else "transient-service-error"
                )
                self.logger.warning("retryable_failure category=%s attempt=%d", category, attempts)
                self.state_store.write(HunterState.create("waiting", attempts, category))
                if attempts >= attempt_limit:
                    return self._finish(
                        "retry-exhausted", attempts, category, ExitCode.RETRY_EXHAUSTED
                    )
                delay = jitter_delay(options.min_delay, options.max_delay, self.random_fn)
                self.logger.info("retry_wait seconds=%.3f", delay)
                self.sleep_fn(delay)
                if self.shutdown_event.is_set():
                    return self._finish("interrupted", attempts, "signal", ExitCode.INTERRUPTED)
            except (
                AuthenticationError,
                AuthorizationError,
                MalformedRequestError,
                NonRetryableOCIError,
            ) as exc:
                category = type(exc).__name__
                self.logger.error("fatal_failure category=%s action=stop", category)
                return self._finish("fatal", attempts, category, ExitCode.OCI_ERROR)

        return self._finish("retry-exhausted", attempts, "attempt-limit", ExitCode.RETRY_EXHAUSTED)

    def _finish(
        self, status: str, attempts: int, last_result: str, exit_code: ExitCode
    ) -> RunOutcome:
        self.state_store.write(HunterState.create(status, attempts, last_result))
        return RunOutcome(status=status, attempts=attempts, exit_code=exit_code)

    @staticmethod
    def _validate_options(options: RunOptions) -> None:
        if options.max_attempts < 1:
            raise ValueError("Maximum attempts must be at least one")
        if options.min_delay < 0 or options.max_delay < options.min_delay:
            raise ValueError("Invalid retry delay bounds")
