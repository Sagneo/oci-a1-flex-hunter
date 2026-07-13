"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .config import HunterConfig
from .errors import ConfigurationError, HunterError, LockUnavailableError
from .hunter import Hunter
from .locking import ProcessLock
from .logging_utils import configure_logging
from .models import ComputeAdapter, ExitCode, RunOptions
from .oci_adapter import OCIComputeAdapter
from .state import StateStore

AdapterFactory = Callable[[HunterConfig], ComputeAdapter]
ProfileLoader = Callable[[str, str], Mapping[str, object]]


def _add_config_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--oci-config", help="OCI SDK config-file path")
    parser.add_argument("--oci-profile", help="OCI SDK profile name")
    parser.add_argument("--compartment-id", help="Target compartment identifier")
    parser.add_argument("--availability-domain", help="Target availability domain")
    parser.add_argument("--subnet-id", help="Target subnet identifier")
    parser.add_argument("--image-id", help="Target image identifier")
    parser.add_argument("--shape", help="Compute shape")
    parser.add_argument("--ocpus", type=float, help="Shape OCPU count")
    parser.add_argument("--memory-gb", type=float, help="Shape memory in GB")
    parser.add_argument("--display-name", help="Stable target display name")
    parser.add_argument("--ssh-public-key", help="SSH public-key file path")
    parser.add_argument("--project-tag", help="Stable Sagneo project tag")
    parser.add_argument("--boot-volume-size-gb", type=int, help="Optional boot volume size")
    parser.add_argument("--state-dir", help="Local state directory")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oci-a1-flex-hunter",
        description="Safely coordinate bounded OCI A1 Flex launch attempts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-config", help="Validate local configuration")
    _add_config_arguments(validate)

    check = subparsers.add_parser("check", help="Perform a read-only OCI readiness check")
    _add_config_arguments(check)

    run = subparsers.add_parser("run", help="Run a dry-run or explicitly live workflow")
    _add_config_arguments(run)
    run.add_argument("--live", action="store_true", help="Allow one OCI create call per attempt")
    mode = run.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="Run one cycle (default)")
    mode.add_argument("--continuous", action="store_true", help="Run bounded repeated cycles")
    run.add_argument("--max-attempts", type=int, help="Maximum process attempts")
    run.add_argument("--min-delay", type=float, help="Minimum retry delay in seconds")
    run.add_argument("--max-delay", type=float, help="Maximum retry delay in seconds")

    status = subparsers.add_parser("status", help="Read sanitized local state")
    _add_config_arguments(status)
    status.add_argument(
        "--refresh", action="store_true", help="Also perform an explicit read-only OCI check"
    )
    return parser


def _string(value: object) -> str | None:
    return None if value is None else str(value)


def _config_overrides(args: argparse.Namespace) -> dict[str, str | None]:
    return {
        "OCI_CONFIG": _string(args.oci_config),
        "OCI_PROFILE": _string(args.oci_profile),
        "COMPARTMENT_ID": _string(args.compartment_id),
        "AVAILABILITY_DOMAIN": _string(args.availability_domain),
        "SUBNET_ID": _string(args.subnet_id),
        "IMAGE_ID": _string(args.image_id),
        "SHAPE": _string(args.shape),
        "OCPUS": _string(args.ocpus),
        "MEMORY_GB": _string(args.memory_gb),
        "DISPLAY_NAME": _string(args.display_name),
        "SSH_PUBLIC_KEY": _string(args.ssh_public_key),
        "PROJECT_TAG": _string(args.project_tag),
        "BOOT_VOLUME_SIZE_GB": _string(args.boot_volume_size_gb),
        "STATE_DIR": _string(args.state_dir),
        "LOG_LEVEL": _string(args.log_level),
    }


def _load_config(args: argparse.Namespace) -> HunterConfig:
    return HunterConfig.from_environment(_config_overrides(args))


def _state_dir_from_args(args: argparse.Namespace) -> Path:
    raw = args.state_dir or os.environ.get("OCI_A1_HUNTER_STATE_DIR")
    return Path(raw).expanduser() if raw else Path.home() / ".local/state/oci-a1-flex-hunter"


def _print_state(store: StateStore) -> None:
    state = store.read()
    if state is None:
        print(json.dumps({"status": "no-state"}, sort_keys=True))
    else:
        payload = state.to_dict()
        payload["retry_token_active"] = bool(payload.pop("retry_token"))
        print(json.dumps(payload, sort_keys=True))


def main(
    argv: Sequence[str] | None = None,
    *,
    adapter_factory: AdapterFactory = OCIComputeAdapter,
    profile_loader: ProfileLoader | None = None,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "status" and not args.refresh:
            _print_state(StateStore(_state_dir_from_args(args)))
            return int(ExitCode.SUCCESS)

        config = _load_config(args)
        logger = configure_logging(config.log_level)

        if args.command == "validate-config":
            config.validate_oci_profile(profile_loader)
            print("Configuration is valid; no OCI request was made.")
            return int(ExitCode.SUCCESS)

        if args.command == "check" or (args.command == "status" and args.refresh):
            adapter = adapter_factory(config)
            exists = adapter.matching_instance_exists(config)
            print(
                "Read-only check complete: "
                + ("matching instance exists." if exists else "no matching instance found.")
            )
            if args.command == "status":
                _print_state(StateStore(config.state_dir))
            return int(ExitCode.SUCCESS)

        if args.command == "run":
            shutdown = threading.Event()

            def request_shutdown(signum: int, frame: Any) -> None:
                del signum, frame
                shutdown.set()

            signal.signal(signal.SIGINT, request_shutdown)
            signal.signal(signal.SIGTERM, request_shutdown)

            max_attempts = args.max_attempts or config.max_attempts
            min_delay = config.min_delay if args.min_delay is None else args.min_delay
            max_delay = config.max_delay if args.max_delay is None else args.max_delay
            options = RunOptions(
                live=args.live,
                continuous=args.continuous,
                max_attempts=max_attempts,
                min_delay=min_delay,
                max_delay=max_delay,
            )
            store = StateStore(config.state_dir)
            lock = ProcessLock(config.state_dir / "hunter.lock")
            with lock:
                run_adapter = adapter_factory(config) if args.live else None
                hunter = Hunter(
                    config,
                    store,
                    logger,
                    sleep_fn=shutdown.wait,
                    shutdown_event=shutdown,
                )
                outcome = hunter.run(options, run_adapter)
            print(f"Run completed: status={outcome.status} attempts={outcome.attempts}")
            return int(outcome.exit_code)
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return int(ExitCode.CONFIGURATION)
    except LockUnavailableError as exc:
        print(str(exc), file=sys.stderr)
        return int(ExitCode.LOCKED)
    except HunterError as exc:
        print(f"OCI workflow error: {type(exc).__name__}", file=sys.stderr)
        return int(ExitCode.OCI_ERROR)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Local state error: {type(exc).__name__}", file=sys.stderr)
        return int(ExitCode.STATE_ERROR)
    return int(ExitCode.STATE_ERROR)


def entrypoint() -> None:
    raise SystemExit(main())
