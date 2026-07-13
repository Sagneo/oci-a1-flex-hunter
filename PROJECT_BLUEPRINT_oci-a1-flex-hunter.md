# OCI A1 Flex Hunter — Greenfield Project Blueprint

## Document control

- Project: OCI A1 Flex Hunter
- Slug: `oci-a1-flex-hunter`
- Version: 0.1.0
- Date: 2026-07-13
- Mode: Greenfield
- Owner: Sagneo
- Repository: `Sagneo/oci-a1-flex-hunter`

This blueprint supersedes the earlier brownfield inventory premise. There is no legacy installation to preserve or migrate. Development begins in this independent repository and must not modify OCI resources during build or test work.

## Purpose

OCI A1 Flex Hunter is a Python CLI that safely coordinates bounded attempts to create one OCI Ampere A1 Flex instance when capacity is available. Capacity, pricing, quotas, and eligibility are controlled by Oracle and the user's account; this project offers no guarantee of capacity or free usage.

## Safety invariants

1. Dry-run is the default and never submits a create request.
2. Cloud creation requires the explicit `run --live` option.
3. Build, CI, and automated tests perform no OCI mutation.
4. A read-only lookup checks display name and project tag before every live attempt.
5. A local process lock prevents concurrent runs on one host.
6. Attempts and delays are bounded, including continuous mode.
7. Capacity failures may retry; configuration, authentication, authorization, and malformed-request failures stop.
8. State is minimal, sanitized, local, and atomically written.
9. Logs redact cloud identifiers, addresses, fingerprints, and authorization material.
10. The application never modifies or terminates existing resources.

## Product surface

- `validate-config`: validate configuration and referenced local files without contacting OCI.
- `check`: authenticate read-only and check for a matching instance.
- `run`: dry-run by default; optionally make bounded live attempts.
- `status`: read sanitized local state, with an explicit optional read-only refresh.

## Architecture

```text
CLI -> configuration validation -> process lock -> hunter controller
                                                |-> state store
                                                |-> structured logging
                                                `-> OCI adapter -> OCI Compute API
```

The controller depends on a narrow adapter protocol. Production uses the official OCI SDK; tests use a deterministic fake. No inbound listener or database is present.

## Configuration

Configuration is supplied with documented environment variables and CLI overrides. OCI authentication uses an OCI config-file path and profile name. Project settings cover placement, network and image references, shape configuration, display name, SSH public-key path, project tag, optional boot-volume size, retry policy, state directory, and log level.

Examples contain placeholders only. The repository must never contain credentials, complete cloud identifiers, user-specific configuration, public addresses, fingerprints, or key bodies.

## Control flow

1. Load and validate configuration.
2. Acquire the local lock.
3. For dry-run, record a sanitized plan and exit without creating an OCI client.
4. For live mode, check for an active or provisioning match by display name and project tag.
5. Stop successfully if a match already exists.
6. Submit at most one launch request for the current attempt.
7. Stop after acceptance, or retry only a classified retryable failure within configured bounds.
8. Record the final sanitized state and release the lock.

## Error model and exit behavior

- Configuration failure: nonzero, no OCI mutation.
- Lock contention: nonzero, no OCI call.
- Existing instance: successful safe stop.
- Launch accepted: successful stop.
- Capacity unavailable: retry only when continuous mode and attempts remain.
- Authentication, authorization, or malformed request: immediate nonzero stop.
- Signal: interrupt waits promptly and stop without another request.

## Quality requirements

- Python 3.11 or newer with a `src/` layout and type hints.
- Offline unit and workflow tests using a fake adapter.
- Ruff formatting/linting and mypy type checking.
- Editable installation and CLI smoke tests.
- GitHub Actions without credentials or live cloud access.
- Pre-publication secret, identifier, artifact, and filename audit.

## Deployment boundary

The repository includes a reviewed systemd example for a future `/opt/oci-a1-flex-hunter` installation under a dedicated non-login user. It does not install the unit, create the user, or write outside the repository.

## Release plan

Release 0.1.0 is complete when local validation passes, a public repository exists only at `Sagneo/oci-a1-flex-hunter`, `main` passes GitHub Actions, and annotated tag and release `v0.1.0` are remotely verified.

## Known limitations

- Capacity and zero-cost eligibility are not guaranteed.
- Users must independently review current Oracle pricing, quotas, limits, policies, images, and regional capacity.
- The CLI creates only an instance launch request; it does not provision IAM or networking.
- Local locking coordinates one host, not multiple hosts sharing the same target configuration.

