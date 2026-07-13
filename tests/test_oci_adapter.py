from types import SimpleNamespace

from oci_a1_flex_hunter.config import HunterConfig
from oci_a1_flex_hunter.oci_adapter import (
    PROJECT_TAG_KEY,
    OCIComputeAdapter,
)


def test_match_requires_display_name_tag_and_lifecycle(config: HunterConfig) -> None:
    matching = SimpleNamespace(
        display_name=config.display_name,
        freeform_tags={PROJECT_TAG_KEY: config.project_tag},
        lifecycle_state="RUNNING",
    )
    wrong_tag = SimpleNamespace(
        display_name=config.display_name,
        freeform_tags={PROJECT_TAG_KEY: "different"},
        lifecycle_state="RUNNING",
    )
    terminated = SimpleNamespace(
        display_name=config.display_name,
        freeform_tags={PROJECT_TAG_KEY: config.project_tag},
        lifecycle_state="TERMINATED",
    )
    assert OCIComputeAdapter._is_match(matching, config)
    assert not OCIComputeAdapter._is_match(wrong_tag, config)
    assert not OCIComputeAdapter._is_match(terminated, config)
