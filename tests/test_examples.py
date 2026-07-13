from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def test_ci_contains_no_live_oci_invocation() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "--live" not in workflow
    assert "OCI_A1_HUNTER_" not in workflow


def test_systemd_examples_have_valid_syntax(tmp_path: Path) -> None:
    executable = shutil.which("systemd-analyze")
    if executable is None:
        pytest.skip("systemd-analyze is unavailable")

    names = (
        "oci-a1-flex-hunter.service",
        "oci-a1-flex-hunter@.service",
        "oci-a1-flex-hunter@.timer",
    )
    candidates: list[str] = []
    for name in names:
        content = (ROOT / "examples" / name).read_text(encoding="utf-8")
        content = content.replace(
            "/opt/oci-a1-flex-hunter/.venv/bin/oci-a1-flex-hunter", "/bin/true"
        )
        candidate = tmp_path / name
        candidate.write_text(content, encoding="utf-8")
        candidates.append(str(candidate))

    result = subprocess.run(
        [executable, "verify", *candidates],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
