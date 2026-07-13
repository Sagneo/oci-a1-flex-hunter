# Contributing

Use Python 3.11 or newer and keep every test offline. Install development dependencies with:

```bash
python -m pip install -e '.[dev]'
```

Before submitting a change, run:

```bash
ruff format --check .
ruff check .
mypy src
python -m pytest
```

Never include OCI credentials, complete cloud identifiers, addresses, fingerprints, key material, production logs, or user-specific configuration. Features that create parallel requests, modify existing resources, or weaken explicit live-mode gating are out of scope.

