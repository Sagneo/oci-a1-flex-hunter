# Troubleshooting

## Configuration error

Run `validate-config`. Confirm every required variable is present, numeric ranges are positive, delay ordering is valid, names use the safe format, and referenced local files exist. Error output intentionally omits sensitive values.

## Authentication failure

Confirm the selected standard OCI config path and profile, clock synchronization, signing-key permissions, and key registration through approved OCI administration. Do not paste the config or key into an issue.

## Authorization failure

The process stops rather than retrying. Review the exact read or launch operation and the principal's policy through your normal OCI administration workflow. The application does not modify IAM.

## No matching instance

`check` requires both display name and the `sagneo-project` tag value to match an eligible lifecycle state. Verify the configuration through a protected local review without publishing identifiers.

## Capacity unavailable

One-shot mode exits after one failure. Bounded continuous mode waits with jitter while attempts remain. Capacity may never become available; the tool does not guarantee success or automatically change region, shape, or placement.

## Lock contention

Another local process owns the state-directory lock. Inspect local process supervision. Do not delete the lock while a process is active; the advisory lock is released automatically when its process exits.

## State error

Check state-directory ownership, permissions, free space, and JSON integrity. The application fails instead of continuing without reliable local state.

## Unexpected restart

Review the unit's restart policy and exit status. The sample unit prevents restart for all expected application outcomes and restarts only unexpected failures within systemd start limits.

