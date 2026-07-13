# Testing

All automated tests are offline and use deterministic fakes. They do not require OCI credentials and never create cloud resources.

```bash
python -m pip install -e '.[dev]'
python -m compileall src tests
ruff format --check .
ruff check .
mypy src
python -m pytest --cov=oci_a1_flex_hunter --cov-fail-under=90
```

Coverage includes offline OCI-profile validation, production launch-payload propagation, every translated SDK error category, dry-run gating, 100% of controller live safety decisions, stable ambiguous retry tokens, bounded token recovery/expiry, duplicate matching, lock/state behavior, redaction, exit codes, and deterministic shutdown.

GitHub Actions runs the same offline checks on supported Python versions. Do not add credentials, live SDK calls, or cloud mutation tests to CI.
