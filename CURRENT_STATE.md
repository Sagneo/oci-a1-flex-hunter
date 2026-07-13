# OCI A1 Flex Hunter — Current State

## Classification

- Project mode: **Greenfield**
- Product version: **0.1.0**
- Repository target: `Sagneo/oci-a1-flex-hunter`
- Legacy migration: **Not applicable**

The earlier Phase 01 brownfield premise is superseded. This host has no legacy installation, and the current build is intentionally created from scratch. No legacy search or migration is part of the product plan.

## Implementation state

The repository contains a Python 3.11+ CLI with:

- configuration validation;
- default dry-run behavior;
- explicit live-mode gating;
- read-only duplicate detection by display name and project tag;
- bounded capacity retry with jitter;
- local process locking;
- atomic sanitized JSON state;
- structured redacted logging;
- an official OCI SDK adapter boundary;
- deterministic offline tests;
- CI, deployment examples, and operational documentation.

## Safety state

- No OCI mutation is performed by project build, tests, validation, or CI.
- No credentials or real infrastructure identifiers belong in the repository.
- No systemd unit is installed automatically.
- No host path outside this project is modified.
- Dry-run remains the default; live creation requires explicit user action.

## Release state

Local and remote validation results are recorded chronologically in `PROJECT_LOG.md`. The public release target is `v0.1.0`.

## Remaining limitations

- OCI capacity is not guaranteed.
- Pricing, quota, policy, and zero-cost eligibility are account-specific and time-sensitive.
- Multi-host coordination is outside version 0.1.0.
- A user must prepare valid OCI authentication and existing network/image resources before any manual live run.

