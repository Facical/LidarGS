"""깊이 맵 필터링."""

from __future__ import annotations

import numpy as np


def filter_depth_range(
    depth_map: np.ndarray,
    min_depth: float = 0.1,
    max_depth: float = 5.0,
) -> np.ndarray:
    """유효 범위 밖의 깊이 값을 0으로 설정.

    Args:
        depth_map: (H, W) float32, 단위: 미터
        min_depth: 최소 유효 깊이
        max_depth: 최대 유효 깊이

    Returns:
        필터링된 깊이 맵 (범위 밖 = 0)
    """
    filtered = depth_map.copy()
    invalid = (filtered <= min_depth) | (filtered >= max_depth)
    filtered[invalid] = 0.0
    return filtered
