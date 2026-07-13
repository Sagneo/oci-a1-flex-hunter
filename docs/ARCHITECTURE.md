# Architecture

## Components

1. `cli.py` parses commands, installs signal handlers, enforces explicit live mode, and maps exit codes.
2. `config.py` loads environment/CLI settings and validates values and local files.
3. `hunter.py` owns duplicate checks, bounded attempts, retry classification, delays, and stop behavior.
4. `oci_adapter.py` is the only production OCI SDK boundary.
5. `locking.py` serializes local workflows with an advisory file lock.
6. `state.py` atomically stores sanitized lifecycle state.
7. `logging_utils.py` redacts sensitive patterns from rendered console logs.

## Control flow

```text
validate-config -> local validation -> exit
check           -> local validation -> OCI adapter -> list instances -> exit
run (dry)       -> local validation -> lock -> sanitized state -> exit
run --live      -> local validation -> lock -> list matching instances
                                      |-> match: safe stop
                                      `-> no match: one launch request
                                          |-> accepted: stop
                                          |-> retryable + budget: jittered wait
                                          `-> fatal/exhausted/signal: stop
status          -> local state -> exit
status --refresh-> local state + explicit read-only lookup -> exit
```

## Duplicate identity

A duplicate match requires the configured display name and the free-form tag key `sagneo-project` with the configured project-tag value. Provisioning, starting, running, stopping, and stopped matches block another launch. Terminated historical instances do not.

## Trust boundaries

- The repository contains code and synthetic examples only.
- OCI config, signing keys, SSH public keys, and live environment values stay outside the repository.
- The process reads credentials through the official SDK and never writes them to state.
- OCI API access is outbound HTTPS only; there is no inbound listener.
- Journald or console capture remains operator-controlled and must be protected.

## Failure model

- Invalid local configuration: stop before adapter construction.
- Authentication, authorization, or malformed request: fatal stop.
- Capacity, throttling, or selected service errors: bounded retry in continuous mode.
- Existing match: successful safe stop.
- Lock contention: stop before OCI access.
- Signal: set a shutdown event, interrupt the current wait, and do not start another request.
- State write failure: fail the command instead of continuing without local evidence.

## Idempotency and concurrency

Oracle documents `opc_retry_token` as the identity of one request retry, with a 24-hour lifetime, so a timeout or server error can be retried without executing the action twice. The controller creates one token for a logical launch, writes it before submission, and reuses it after ambiguous transient failures and bounded process restarts. A definitive `OutOfHostCapacity` response clears the intent; an unknown failure retains it. A valid expired token is discarded only after the next preflight duplicate lookup; malformed, incomplete, or future-dated intent state fails closed. Successful, duplicate, and definitive fatal outcomes clean up the token.

The token is a random non-secret request identifier, stored in the mode-`0600` state file but redacted from `status` output. The local lock prevents concurrent processes on one host, and the cloud-side display-name/tag lookup runs before every attempt. Multi-host coordination is not provided.
