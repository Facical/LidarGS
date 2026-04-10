"""ARKit camera-to-world → gsplat world-to-camera (viewmat) 변환.

ARKit과 gsplat 모두 OpenGL 좌표계를 사용하므로 축 변환이 불필요하다.
단순히 역행렬만 계산하면 된다.
"""

from __future__ import annotations

import numpy as np


def arkit_c2w_to_viewmat(c2w: np.ndarray) -> np.ndarray:
    """ARKit c2w → gsplat viewmat (w2c).

    Args:
        c2w: (4, 4) ARKit camera-to-world, row-major

    Returns:
        w2c: (4, 4) world-to-camera, float32
    """
    return np.linalg.inv(c2w).astype(np.float32)


def batch_c2w_to_viewmats(c2ws: np.ndarray) -> np.ndarray:
    """배치 ARKit c2w → gsplat viewmats.

    Args:
        c2ws: (N, 4, 4) camera-to-world 배열

    Returns:
        viewmats: (N, 4, 4) world-to-camera, float32
    """
    return np.linalg.inv(c2ws).astype(np.float32)
