"""ARKit camera-to-world (OpenGL) → COLMAP world-to-camera (OpenCV) 변환.

변환 단계:
1. Y/Z 축 반전: OpenGL(Y-up, -Z-forward) → OpenCV(Y-down, +Z-forward)
2. c2w → w2c 역행렬
3. 회전 행렬 → 쿼터니언 (COLMAP 순서: qw, qx, qy, qz)
"""

from __future__ import annotations

import numpy as np
from scipy.spatial.transform import Rotation


# OpenGL → OpenCV 축 변환 행렬 (Y, Z 반전)
_FLIP_YZ = np.diag([1.0, -1.0, -1.0, 1.0])


def arkit_c2w_to_colmap(c2w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """ARKit c2w (OpenGL) → COLMAP 쿼터니언 + 이동 벡터 (OpenCV).

    Args:
        c2w: (4, 4) ARKit camera-to-world, row-major, OpenGL

    Returns:
        quat_colmap: (4,) 쿼터니언 [qw, qx, qy, qz]
        t_colmap: (3,) 이동 벡터
    """
    # Step 1: OpenGL → OpenCV (Y, Z 축 반전)
    c2w_opencv = c2w @ _FLIP_YZ

    # Step 2: c2w → w2c
    w2c = np.linalg.inv(c2w_opencv)
    R = w2c[:3, :3]
    t = w2c[:3, 3]

    # Step 3: 회전 행렬 → 쿼터니언
    r = Rotation.from_matrix(R)
    quat_scipy = r.as_quat()  # scipy: [qx, qy, qz, qw]
    quat_colmap = np.array([
        quat_scipy[3],  # qw
        quat_scipy[0],  # qx
        quat_scipy[1],  # qy
        quat_scipy[2],  # qz
    ])

    return quat_colmap, t


def colmap_to_arkit_c2w(quat_colmap: np.ndarray, t_colmap: np.ndarray) -> np.ndarray:
    """COLMAP 쿼터니언 + 이동 벡터 → ARKit c2w (역변환, 테스트용).

    Args:
        quat_colmap: (4,) [qw, qx, qy, qz]
        t_colmap: (3,) 이동 벡터

    Returns:
        c2w: (4, 4) ARKit camera-to-world, OpenGL
    """
    # COLMAP [qw,qx,qy,qz] → scipy [qx,qy,qz,qw]
    quat_scipy = np.array([
        quat_colmap[1],  # qx
        quat_colmap[2],  # qy
        quat_colmap[3],  # qz
        quat_colmap[0],  # qw
    ])

    R = Rotation.from_quat(quat_scipy).as_matrix()
    w2c = np.eye(4, dtype=np.float64)
    w2c[:3, :3] = R
    w2c[:3, 3] = t_colmap

    # w2c → c2w (OpenCV)
    c2w_opencv = np.linalg.inv(w2c)

    # OpenCV → OpenGL (flip 역변환: flip은 자기 자신의 역)
    c2w = c2w_opencv @ _FLIP_YZ

    return c2w
