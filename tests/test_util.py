import pytest

from oci_a1_flex_hunter.util import jitter_delay


def test_jitter_boundaries() -> None:
    assert jitter_delay(2, 8, lambda low, high: low) == 2
    assert jitter_delay(2, 8, lambda low, high: high) == 8


def test_invalid_jitter_boundaries() -> None:
    with pytest.raises(ValueError):
        jitter_delay(8, 2, lambda low, high: low)
