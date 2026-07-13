# OCI A1 Flex Hunter

[![CI](https://github.com/Sagneo/oci-a1-flex-hunter/actions/workflows/ci.yml/badge.svg)](https://github.com/Sagneo/oci-a1-flex-hunter/actions/workflows/ci.yml)

OCI A1 Flex Hunter is a safe-by-default Python CLI for coordinating bounded attempts to launch one Oracle Cloud Infrastructure Ampere A1 Flex instance when capacity is available.

**OCI capacity is not guaranteed.** Shape eligibility, pricing, quotas, limits, policies, images, and regional capacity are account-specific and can change. Review current Oracle documentation and your tenancy before enabling live mode.

### Current resource-limit note

As reviewed on 2026-07-13, Oracle's specific [Always Free Resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) page publishes 1,500 OCPU-hours and 9,000 GB-hours monthly for A1 Flex, described as 2 OCPUs and 12 GB total for an Always Free tenancy. It describes either one 2-OCPU instance or up to two 1-OCPU instances. A separate Oracle Free Tier page still contains a 4-OCPU/24-GB statement, so this repository deliberately treats 4/24 as a historical or account-specific possibility, not a safe default. Confirm the OCI Console, account type, current pricing, quota, and boot-volume allowance before choosing either one larger instance or several smaller instances.

## Features

- Dry-run is the default; `--live` is required for creation.
- Read-only authentication and duplicate checks.
- Duplicate identity requires both a stable display name and project tag.
- Sequential, bounded retries with configurable jitter.
- Capacity and transient failures are separated from fatal failures.
- Local process lock and atomic, sanitized JSON state.
- Structured console logs with sensitive-value redaction.
- One-shot and bounded continuous operation.
- Official OCI Python SDK adapter with fully offline fake-adapter tests.
- No inbound service, web framework, or database.

## Architecture

The CLI validates configuration and coordinates a controller. The controller owns stop/retry policy and depends on a narrow compute-adapter protocol. Production uses the official OCI SDK; tests use a deterministic fake. Local locking prevents concurrent processes, while an atomic state file records only status, counters, categories, and timestamps.

See [Architecture](docs/ARCHITECTURE.md) for the detailed control flow and trust boundaries.

## Requirements

- Python 3.11 or newer
- An OCI config profile and signing key prepared by the user
- Existing OCI compartment, subnet, compatible image, and SSH public key
- Account-specific confirmation of pricing, quota, policy, and approved shape resources

The project does not create IAM policies, networks, keys, or supporting resources.

## Installation

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
oci-a1-flex-hunter --help
```

For development:

```bash
python -m pip install -e '.[dev]'
```

## Configuration

Set project variables in a protected file outside the repository, using [.env.example](.env.example) only as a name reference. The application reads variables from its process environment; it does not automatically load `.env` files.

OCI authentication is indirect:

- `OCI_A1_HUNTER_OCI_CONFIG` selects the standard OCI config file.
- `OCI_A1_HUNTER_OCI_PROFILE` selects the standard profile.

Required project variables identify the compartment, availability domain, subnet, image, display name, SSH public-key file, and project tag. CLI options can override them. See [Configuration](docs/CONFIGURATION.md).

## Validate configuration

```bash
oci-a1-flex-hunter validate-config
```

This validates local settings and referenced files. It makes no OCI request.

## Read-only check

```bash
oci-a1-flex-hunter check
```

This authenticates to OCI, lists instances in the configured compartment, and reports whether a display-name-and-tag match exists. It makes no create request.

## Dry-run

```bash
oci-a1-flex-hunter run --once
```

Dry-run is the default. It validates the plan, acquires the local lock, writes sanitized state, and does not construct the OCI adapter or contact OCI.

## Explicit live mode

```bash
oci-a1-flex-hunter run --live --once
```

This command can create a cloud resource. Review current pricing, limits, policy, placement, image compatibility, configuration, and the read-only check first.

## Bounded continuous mode

```bash
oci-a1-flex-hunter run --live --continuous \
  --max-attempts 5 --min-delay 30 --max-delay 120
```

Continuous mode is still bounded. It stops on an existing match, accepted launch, fatal error, signal, or attempt exhaustion. It never sends parallel requests.

## Status

```bash
oci-a1-flex-hunter status
```

Status reads only local sanitized state. Add `--refresh` only when an explicit read-only OCI lookup is desired.

## systemd example

The repository includes [an example unit](examples/oci-a1-flex-hunter.service). It is not installed automatically and deliberately uses `/opt/oci-a1-flex-hunter`, a dedicated non-login user, protected external environment configuration, bounded restart controls, and hardening. Review [Deployment](docs/DEPLOYMENT.md) before adapting it.

## Safety model

- Live creation is explicitly gated.
- A matching active or stopped target prevents creation.
- The controller performs one create call per attempt.
- Retryable categories are bounded; fatal categories stop immediately.
- Logs and state exclude request payloads and complete identifiers.
- The application never stops, resizes, terminates, or modifies an existing instance.

Local locking coordinates only one host. Multiple hosts require external coordination and are outside version 0.1.0.

## Tests and quality checks

All automated tests are offline:

```bash
python -m compileall src tests
ruff format --check .
ruff check .
mypy src
python -m pytest
```

CI contains no OCI credentials and performs no live cloud calls.

## Troubleshooting

- Configuration errors stop before OCI access.
- Authentication and authorization errors do not retry.
- Capacity errors retry only in bounded continuous mode.
- Lock contention means another local process owns the workflow.
- `status` shows the last sanitized category without exposing identifiers.

See [Troubleshooting](docs/TROUBLESHOOTING.md) for corrective actions.

## Repository status

Version 0.1.0 is the initial greenfield release. It is suitable for offline evaluation and carefully reviewed manual deployment. Live use remains the operator's responsibility.

## License

MIT. See [LICENSE](LICENSE).
