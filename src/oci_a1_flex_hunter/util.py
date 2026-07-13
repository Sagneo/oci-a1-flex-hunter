"""Pure helpers used by retry control."""

from collections.abc import Callable


def jitter_delay(
    minimum: float, maximum: float, random_fn: Callable[[float, float], float]
) -> float:
    if minimum < 0 or maximum < minimum:
        raise ValueError("Invalid jitter bounds")
    return random_fn(minimum, maximum)
