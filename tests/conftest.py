from __future__ import annotations

from pathlib import Path

import pytest

from oci_a1_flex_hunter.config import HunterConfig


@pytest.fixture
def config(tmp_path: Path) -> HunterConfig:
    oci_config = tmp_path / "oci-config"
    ssh_key = tmp_path / "id_test.pub"
    oci_config.write_text("[DEFAULT]\n", encoding="utf-8")
    ssh_key.write_text("ssh-ed25519 AAAA synthetic-test\n", encoding="utf-8")
    return HunterConfig.from_environment(
        {
            "OCI_CONFIG": str(oci_config),
            "OCI_PROFILE": "DEFAULT",
            "COMPARTMENT_ID": "compartment-test-value",
            "AVAILABILITY_DOMAIN": "availability-domain-test",
            "SUBNET_ID": "subnet-test-value",
            "IMAGE_ID": "image-test-value",
            "SHAPE": "VM.Standard.A1.Flex",
            "OCPUS": "1",
            "MEMORY_GB": "6",
            "DISPLAY_NAME": "sagneo-a1-test",
            "SSH_PUBLIC_KEY": str(ssh_key),
            "PROJECT_TAG": "sagneo-a1-test",
            "MAX_ATTEMPTS": "3",
            "MIN_DELAY": "1",
            "MAX_DELAY": "3",
            "STATE_DIR": str(tmp_path / "state"),
            "LOG_LEVEL": "INFO",
        }
    )
