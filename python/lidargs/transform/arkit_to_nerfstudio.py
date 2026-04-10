"""ARKit → Nerfstudio 변환 (identity).

ARKit과 Nerfstudio 모두 OpenGL camera-to-world 컨벤션을 사용하므로
변환이 필요 없다. API 일관성을 위해 함수를 제공한다.
"""

from __future__ import annotations

import numpy as np


def arkit_c2w_to_nerfstudio(c2w: np.ndarray) -> np.ndarray:
    """ARKit c2w → Nerfstudio c2w (identity 변환).

    Args:
        c2w: (4, 4) ARKit camera-to-world, row-major

    Returns:
        c2w: (4, 4) 동일 행렬
    """
    return c2w.astype(np.float64)
