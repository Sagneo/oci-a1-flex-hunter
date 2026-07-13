# Security Policy

## Supported version

Version 0.1.x receives security fixes while it is the current release line.

## Reporting a vulnerability

Report vulnerabilities privately through GitHub's security-advisory interface for this repository. Do not open a public issue containing credentials, cloud identifiers, configuration files, logs, or key material.

## Secret handling

- Keep OCI configuration and signing keys outside the repository.
- Use owner-restricted permissions for configuration, keys, environment files, and local state.
- Never paste credentials or complete infrastructure identifiers into issues or discussions.
- Treat logs as sensitive until their redaction has been reviewed.
- Rotate a credential through OCI if exposure is suspected; this project does not generate or rotate credentials.

## Scope limitations

This software cannot guarantee cloud capacity, pricing, quota, policy correctness, or zero-cost eligibility. It does not secure the surrounding host, OCI tenancy, IAM policy, network, or supply chain. Review all configuration and deployment examples before live use.

