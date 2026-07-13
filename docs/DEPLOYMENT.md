# Deployment

This is a manual example for an installation rooted at `/opt/oci-a1-flex-hunter`. The project does not create users, install units, or write outside its checkout.

## Layout

- Application: `/opt/oci-a1-flex-hunter`
- Virtual environment: `/opt/oci-a1-flex-hunter/.venv`
- Protected environment file: `/etc/oci-a1-flex-hunter/hunter.env`
- State: `/var/lib/oci-a1-flex-hunter`
- Runtime identity: dedicated non-login `oci-a1-hunter` user and group

An administrator should create these paths deliberately, make application code non-writable to the runtime identity, protect configuration and signing keys, and give the runtime identity write access only to its state directory.

## Install candidate

From a reviewed release checkout under the application directory:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install .
.venv/bin/oci-a1-flex-hunter --help
```

Create the protected environment file from documented variable names, never by copying repository examples with live values back into Git. Complete [OCI onboarding](OCI_SETUP.md) first.

## Validate before service use

Run as the dedicated identity:

```bash
.venv/bin/oci-a1-flex-hunter validate-config
.venv/bin/oci-a1-flex-hunter check
.venv/bin/oci-a1-flex-hunter run --once
```

The final command is a dry-run. Review the sample unit before adding `--live`; live mode can create a chargeable resource.

## systemd examples

The files under `examples/` require administrator review. The service is `Type=oneshot`; every process has five bounded internal attempts. The timer, not an infinite process or `Restart=`, schedules a later run. Examples default to dry-run. Inspect paths, permissions, resource profile, state isolation, and all three validation commands before deliberately adding `--live`.

For multiple targets, use `oci-a1-flex-hunter@target-a.timer` and `@target-b.timer`. The `%i` service name selects `/etc/oci-a1-flex-hunter/%i.env`, and each environment must set a matching unique `/var/lib/oci-a1-flex-hunter/%i` state directory. The project neither installs nor enables these units.

## Operations

Use the CLI `status` command, `systemctl list-timers`, and bounded journald queries. A successful launch exits normally. Retry exhaustion is an expected end of one bounded process; the reviewed timer controls the next opportunity.

## Update and rollback

Install and validate a new version separately before replacing the active application directory. Preserve the prior release and protected configuration until the new version passes dry-run and read-only checks. Rollback changes only the installed application version; never rotate credentials or modify OCI resources as part of an application rollback.
