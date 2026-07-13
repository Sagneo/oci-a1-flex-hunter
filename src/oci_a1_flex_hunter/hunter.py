"""Bounded, sequential launch controller."""

from __future__ import annotations

import hashlib
import json
import logging
import random
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

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
RETRY_TOKEN_LIFETIME = timedelta(hours=24)


def launch_request_fingerprint(config: HunterConfig) -> str:
    """Return a stable non-secret digest of every material launch field."""
    ssh_public_key = config.ssh_public_key_path.read_text(encoding="utf-8").strip()
    canonical_request = {
        "availability_domain": config.availability_domain,
        "boot_volume_size_gb": config.boot_volume_size_gb,
        "compartment_id": config.compartment_id,
        "display_name": config.display_name,
        "image_id": config.image_id,
        "memory_gb": float(config.memory_gb).hex(),
        "ocpus": float(config.ocpus).hex(),
        "project_tag": config.project_tag,
        "schema": 1,
        "shape": config.shape,
        "ssh_public_key_sha256": hashlib.sha256(ssh_public_key.encode()).hexdigest(),
        "subnet_id": config.subnet_id,
    }
    canonical = json.dumps(canonical_request, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


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
        token_factory: Callable[[], str] = lambda: str(uuid4()),
        now_fn: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.config = config
        self.state_store = state_store
        self.logger = logger
        self.sleep_fn = sleep_fn
        self.random_fn = random_fn
        self.shutdown_event = shutdown_event or threading.Event()
        self.token_factory = token_factory
        self.now_fn = now_fn

    def run(self, options: RunOptions, adapter: ComputeAdapter | None = None) -> RunOutcome:
        self.validate_options(options)
        request_fingerprint = launch_request_fingerprint(self.config)
        retry_token, token_created_at, intent_fingerprint = self._recover_retry_intent(
            request_fingerprint
        )
        if not options.live:
            self.logger.info("dry_run_validated mode=dry-run")
            return self._finish(
                "dry-run",
                0,
                "launch-not-requested",
                ExitCode.SUCCESS,
                retry_token=retry_token,
                retry_token_created_at=token_created_at,
                retry_request_fingerprint=intent_fingerprint,
            )
        if adapter is None:
            raise ValueError("Live mode requires an OCI adapter")

        attempt_limit = options.max_attempts if options.continuous else 1
        attempts = 0
        while attempts < attempt_limit:
            if self.shutdown_event.is_set():
                return self._finish(
                    "interrupted",
                    attempts,
                    "signal",
                    ExitCode.INTERRUPTED,
                    retry_token=retry_token,
                    retry_token_created_at=token_created_at,
                    retry_request_fingerprint=intent_fingerprint,
                )
            attempts += 1
            self.state_store.write(
                HunterState.create(
                    "checking",
                    attempts,
                    "read-only-check",
                    retry_token=retry_token,
                    retry_token_created_at=token_created_at,
                    retry_request_fingerprint=intent_fingerprint,
                    now=self.now_fn(),
                )
            )
            submission_attempted = False
            try:
                if adapter.matching_instance_exists(self.config):
                    self.logger.info("matching_instance_exists action=stop")
                    return self._finish(
                        "existing-instance", attempts, "duplicate-prevented", ExitCode.SUCCESS
                    )
                if retry_token is None:
                    retry_token = self.token_factory()
                    token_created_at = self.now_fn().isoformat()
                    intent_fingerprint = request_fingerprint
                self.state_store.write(
                    HunterState.create(
                        "launching",
                        attempts,
                        "submission-pending",
                        retry_token=retry_token,
                        retry_token_created_at=token_created_at,
                        retry_request_fingerprint=intent_fingerprint,
                        now=self.now_fn(),
                    )
                )
                submission_attempted = True
                adapter.launch_instance(self.config, retry_token)
                self.logger.info("launch_accepted action=stop")
                return self._finish("success", attempts, "launch-accepted", ExitCode.SUCCESS)
            except (CapacityUnavailableError, TransientOCIError) as exc:
                category = (
                    "capacity-unavailable"
                    if isinstance(exc, CapacityUnavailableError)
                    else "transient-service-error"
                )
                if isinstance(exc, CapacityUnavailableError) and submission_attempted:
                    retry_token = None
                    token_created_at = None
                    intent_fingerprint = None
                self.logger.warning("retryable_failure category=%s attempt=%d", category, attempts)
                self.state_store.write(
                    HunterState.create(
                        "waiting",
                        attempts,
                        category,
                        retry_token=retry_token,
                        retry_token_created_at=token_created_at,
                        retry_request_fingerprint=intent_fingerprint,
                        now=self.now_fn(),
                    )
                )
                if attempts >= attempt_limit:
                    return self._finish(
                        "retry-exhausted",
                        attempts,
                        category,
                        ExitCode.RETRY_EXHAUSTED,
                        retry_token=retry_token,
                        retry_token_created_at=token_created_at,
                        retry_request_fingerprint=intent_fingerprint,
                    )
                delay = jitter_delay(options.min_delay, options.max_delay, self.random_fn)
                self.logger.info("retry_wait seconds=%.3f", delay)
                self.sleep_fn(delay)
                if self.shutdown_event.is_set():
                    return self._finish(
                        "interrupted",
                        attempts,
                        "signal",
                        ExitCode.INTERRUPTED,
                        retry_token=retry_token,
                        retry_token_created_at=token_created_at,
                        retry_request_fingerprint=intent_fingerprint,
                    )
            except (
                AuthenticationError,
                AuthorizationError,
                MalformedRequestError,
                NonRetryableOCIError,
            ) as exc:
                category = type(exc).__name__
                self.logger.error("fatal_failure category=%s action=stop", category)
                preserve = not submission_attempted or isinstance(exc, NonRetryableOCIError)
                return self._finish(
                    "fatal",
                    attempts,
                    category,
                    ExitCode.OCI_ERROR,
                    retry_token=retry_token if preserve else None,
                    retry_token_created_at=token_created_at if preserve else None,
                    retry_request_fingerprint=intent_fingerprint if preserve else None,
                )

        raise AssertionError("bounded retry loop exited unexpectedly")  # pragma: no cover

    def _finish(
        self,
        status: str,
        attempts: int,
        last_result: str,
        exit_code: ExitCode,
        *,
        retry_token: str | None = None,
        retry_token_created_at: str | None = None,
        retry_request_fingerprint: str | None = None,
    ) -> RunOutcome:
        self.state_store.write(
            HunterState.create(
                status,
                attempts,
                last_result,
                retry_token=retry_token,
                retry_token_created_at=retry_token_created_at,
                retry_request_fingerprint=retry_request_fingerprint,
                now=self.now_fn(),
            )
        )
        return RunOutcome(status=status, attempts=attempts, exit_code=exit_code)

    def _recover_retry_intent(
        self, request_fingerprint: str
    ) -> tuple[str | None, str | None, str | None]:
        state = self.state_store.read()
        if state is None or not any(
            (
                state.retry_token,
                state.retry_token_created_at,
                state.retry_request_fingerprint,
            )
        ):
            return None, None, None
        retry_token = state.retry_token
        token_created_at = state.retry_token_created_at
        intent_fingerprint = state.retry_request_fingerprint
        if not retry_token or not token_created_at or not intent_fingerprint:
            raise ValueError("Retry intent state is incomplete")
        if len(intent_fingerprint) != 64 or any(
            char not in "0123456789abcdef" for char in intent_fingerprint
        ):
            raise ValueError("Retry intent fingerprint is invalid")
        try:
            created_at = datetime.fromisoformat(token_created_at)
            if created_at.tzinfo is None:
                raise ValueError("Retry-token timestamp lacks a timezone")
            age = self.now_fn() - created_at.astimezone(UTC)
        except (ValueError, OverflowError) as exc:
            raise ValueError("Retry intent state is invalid") from exc
        if age < timedelta(0):
            raise ValueError("Retry intent timestamp is in the future")
        if age < RETRY_TOKEN_LIFETIME:
            if intent_fingerprint != request_fingerprint:
                raise ValueError("Retry intent does not match the configured launch request")
            return retry_token, token_created_at, intent_fingerprint
        return None, None, None

    @staticmethod
    def validate_options(options: RunOptions) -> None:
        if options.max_attempts < 1:
            raise ValueError("Maximum attempts must be at least one")
        if options.min_delay < 0 or options.max_delay < options.min_delay:
            raise ValueError("Invalid retry delay bounds")
