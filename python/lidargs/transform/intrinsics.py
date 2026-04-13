"""해상도 간 intrinsics 스케일링."""

from __future__ import annotations

import numpy as np


def scale_intrinsics(
    K: np.ndarray,
    from_size: tuple[int, int],
    to_size: tuple[int, int],
) -> np.ndarray:
    """해상도 변경에 따른 intrinsics 스케일링.

    Args:
        K: (3, 3) intrinsic 행렬
        from_size: (width, height) 원본 해상도
        to_size: (width, height) 대상 해상도

    Returns:
        스케일링된 (3, 3) intrinsic 행렬
    """
    sx = to_size[0] / from_size[0]
    sy = to_size[1] / from_size[1]
    K_scaled = K.copy()
    K_scaled[0, 0] *= sx  # fx
    K_scaled[1, 1] *= sy  # fy
    K_scaled[0, 2] *= sx  # cx
    K_scaled[1, 2] *= sy  # cy
    return K_scaled


def scale_intrinsics_for_depth(
    K_rgb: np.ndarray,
    rgb_size: tuple[int, int],
    depth_size: tuple[int, int] = (256, 192),
) -> np.ndarray:
    """RGB intrinsics를 LiDAR depth 해상도로 스케일링.

    LiDAR 깊이 해상도는 iPhone 기종·영상 해상도에 관계없이 ARKit에서 항상 256×192.
    rgb_size는 ARKit 영상 해상도에 따라 달라진다 (1080p: 1920×1080, 4K: 3840×2160).
    """
    return scale_intrinsics(K_rgb, rgb_size, depth_size)
