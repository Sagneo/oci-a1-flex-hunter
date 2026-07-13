# Changelog

All notable changes are documented here.

## 0.1.1 — Unreleased

- Reuse and persist a bounded OCI retry token across ambiguous launch failures and process restarts.
- Add offline SDK-profile, signing-key-permission, and SSH public-key validation.
- Add direct production-adapter payload and error-translation tests; raise coverage above 90% with 100% controller safety-path coverage.
- Add complete OCI Console onboarding, conservative current 2-OCPU/12-GB guidance, and historical/account-specific 4-OCPU/24-GB context.
- Replace restart-driven hunting guidance with reviewed bounded one-shot and per-target systemd timer examples.
- Add wheel builds and clean wheel smoke installation to CI.

## 0.1.0 — 2026-07-13

- Add a safe-by-default OCI A1 Flex hunter CLI.
- Add bounded retry, duplicate detection, locking, state, and log redaction.
- Add offline tests, CI, and deployment/security documentation.
