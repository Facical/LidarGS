"""깊이 맵 → 3D 포인트 클라우드 역투영.

수학:
    x_cam = (u - cx) * z / fx
    y_cam = (v - cy) * z / fy
    z_cam = z
    P_world = R @ P_cam + t  (R, t from c2w)
"""

from __future__ import annotations

import numpy as np


def depth_to_pointcloud(
    depth_map: np.ndarray,
    intrinsics: np.ndarray,
    c2w: np.ndarray,
    min_depth: float = 0.1,
    max_depth: float = 5.0,
    subsample: int = 1,
) -> np.ndarray:
    """깊이 맵을 월드 좌표계 3D 포인트 클라우드로 역투영.

    ARKit sceneDepth는 카메라 시선 방향의 거리를 양수 float로 제공한다.
    표준 pinhole 역투영 공식이 직접 적용된다.

    Args:
        depth_map: (H, W) float32, 단위: 미터
        intrinsics: (3, 3) depth 해상도에 맞춘 intrinsics
        c2w: (4, 4) camera-to-world (OpenGL/ARKit)
        min_depth: 최소 유효 깊이
        max_depth: 최대 유효 깊이
        subsample: N번째 픽셀마다 샘플링

    Returns:
        points_world: (M, 3) 월드 좌표 포인트
    """
    h, w = depth_map.shape

    # 픽셀 좌표 그리드 생성
    v_coords, u_coords = np.mgrid[0:h:subsample, 0:w:subsample]
    depths = depth_map[v_coords, u_coords]

    # 유효 깊이 필터링
    valid = (depths > min_depth) & (depths < max_depth)
    u = u_coords[valid].astype(np.float64)
    v = v_coords[valid].astype(np.float64)
    z = depths[valid].astype(np.float64)

    if len(z) == 0:
        return np.empty((0, 3), dtype=np.float64)

    # Intrinsics 추출
    fx, fy = intrinsics[0, 0], intrinsics[1, 1]
    cx, cy = intrinsics[0, 2], intrinsics[1, 2]

    # 카메라 좌표로 역투영
    x = (u - cx) * z / fx
    y = (v - cy) * z / fy
    points_cam = np.stack([x, y, z], axis=-1)  # (M, 3)

    # 월드 좌표로 변환
    R = c2w[:3, :3]
    t = c2w[:3, 3]
    points_world = (R @ points_cam.T).T + t  # (M, 3)

    return points_world


def depth_to_pointcloud_with_colors(
    depth_map: np.ndarray,
    intrinsics: np.ndarray,
    c2w: np.ndarray,
    image: np.ndarray,
    rgb_size: tuple[int, int],
    min_depth: float = 0.1,
    max_depth: float = 5.0,
    subsample: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    """깊이 맵을 포인트 클라우드로 역투영하면서 RGB 색상도 샘플링.

    Args:
        depth_map: (H, W) float32
        intrinsics: (3, 3) depth 해상도 intrinsics
        c2w: (4, 4) camera-to-world
        image: (H_rgb, W_rgb, 3) uint8 RGB 이미지
        rgb_size: (width, height) RGB 해상도
        min_depth / max_depth: 유효 깊이 범위
        subsample: 서브샘플링 간격

    Returns:
        points_world: (M, 3)
        colors: (M, 3) uint8
    """
    h, w = depth_map.shape
    v_coords, u_coords = np.mgrid[0:h:subsample, 0:w:subsample]
    depths = depth_map[v_coords, u_coords]

    valid = (depths > min_depth) & (depths < max_depth)
    u = u_coords[valid].astype(np.float64)
    v = v_coords[valid].astype(np.float64)
    z = depths[valid].astype(np.float64)

    if len(z) == 0:
        return np.empty((0, 3), dtype=np.float64), np.empty((0, 3), dtype=np.uint8)

    fx, fy = intrinsics[0, 0], intrinsics[1, 1]
    cx, cy = intrinsics[0, 2], intrinsics[1, 2]

    x = (u - cx) * z / fx
    y = (v - cy) * z / fy
    points_cam = np.stack([x, y, z], axis=-1)

    R = c2w[:3, :3]
    t = c2w[:3, 3]
    points_world = (R @ points_cam.T).T + t

    # depth 좌표 → RGB 좌표 매핑
    img_h, img_w = image.shape[:2]
    u_rgb = (u * rgb_size[0] / w).astype(int).clip(0, img_w - 1)
    v_rgb = (v * rgb_size[1] / h).astype(int).clip(0, img_h - 1)
    colors = image[v_rgb, u_rgb]

    return points_world, colors
