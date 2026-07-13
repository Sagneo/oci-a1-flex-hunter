# Testing

All automated tests are offline and use deterministic fakes. They do not require OCI credentials and never create cloud resources.

```bash
python -m pip install -e '.[dev]'
python -m compileall src tests
ruff format --check .
ruff check .
mypy src
python -m pytest
```

Coverage includes configuration success/failure, dry-run gating, live single-call behavior through a fake, display-name/tag matching, retryable capacity behavior, fatal errors, attempt exhaustion, jitter boundaries, lock contention, atomic state, state readback, log redaction, CLI exit codes, and shutdown behavior.

GitHub Actions runs the same offline checks on supported Python versions. Do not add credentials, live SDK calls, or cloud mutation tests to CI.

