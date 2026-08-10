"""Classify video dimensions into canonical aspect ratio buckets."""

import math

CANONICAL_RATIOS = {
    "9:16": 9 / 16,
    "1:1": 1 / 1,
    "4:5": 4 / 5,
    "16:9": 16 / 9,
}

TOLERANCE = 0.01  # ±1%


def classify_aspect_ratio(width: int, height: int) -> str:
    """Return the canonical bucket name for a width/height pair.

    One of "9:16", "1:1", "4:5", "16:9", or "other" if no canonical
    ratio is within ±1% (relative) of the actual ratio.
    """
    if width <= 0 or height <= 0:
        raise ValueError(
            f"width and height must be positive, got width={width}, height={height}"
        )

    actual_ratio = width / height

    for label, canonical_ratio in CANONICAL_RATIOS.items():
        relative_diff = abs(actual_ratio - canonical_ratio) / canonical_ratio
        if relative_diff <= TOLERANCE:
            return label

    return "other"


def simplify_ratio(width: int, height: int) -> str:
    """Return the exact reduced width:height fraction, e.g. 1470x630 -> "7:3".

    Unlike classify_aspect_ratio, this doesn't snap to a canonical bucket --
    it's the literal simplified ratio of the given dimensions.
    """
    if width <= 0 or height <= 0:
        raise ValueError(
            f"width and height must be positive, got width={width}, height={height}"
        )

    divisor = math.gcd(width, height)
    return f"{width // divisor}:{height // divisor}"
