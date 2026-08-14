"""Shared color utilities for map and chart themes."""
from typing import Iterable, List, Sequence, Tuple


# RGB anchors used across views
STATION_RGB: Tuple[int, int, int] = (8, 127, 120)
SELECTED_RGB: Tuple[int, int, int] = (20, 32, 43)
WHITE_RGB: Tuple[int, int, int] = (255, 255, 255)


def with_alpha(rgb: Sequence[int], alpha: int) -> List[int]:
    return [int(rgb[0]), int(rgb[1]), int(rgb[2]), int(alpha)]


MAP_LINE_COLOR: List[int] = with_alpha(WHITE_RGB, 210)


def map_fill_colors(positions: Iterable[float]) -> List[List[int]]:
    """Return RGBA rows for a series of normalized positions in [0,1].

    The palette matches the Fire & Rescue view: light warm -> deep orange/red.
    """
    return [
        [255, int(235 - 185 * float(v)), int(170 - 150 * float(v)), 205]
        for v in positions
    ]


# Heatmap continuous range matching the same warm palette (low -> high)
HEATMAP_RANGE = ["#FFEBAA", "#FF8E5F", "#FF3214"]
