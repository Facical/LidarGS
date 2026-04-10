"""다중 프레임 포인트 클라우드 병합 및 다운샘플링."""

from __future__ import annotations

import numpy as np
import open3d as o3d


def merge_pointclouds(
    points_list: list[np.ndarray],
    colors_list: list[np.ndarray] | None = None,
    voxel_size: float = 0.01,
) -> tuple[np.ndarray, np.ndarray | None]:
    """다중 포인트 클라우드를 병합하고 voxel 다운샘플링.

    Args:
        points_list: [(M_i, 3)] 포인트 배열 리스트
        colors_list: [(M_i, 3)] 색상 배열 리스트 (0-1 float 또는 0-255 uint8), optional
        voxel_size: 다운샘플링 voxel 크기 (미터). 0.01 = 1cm

    Returns:
        points: (N, 3) 병합 + 다운샘플링된 포인트
        colors: (N, 3) float [0,1] 또는 None
    """
    all_points = np.concatenate(points_list, axis=0)

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)

    if colors_list is not None:
        all_colors = np.concatenate(colors_list, axis=0).astype(np.float64)
        if all_colors.max() > 1.0:
            all_colors = all_colors / 255.0
        pcd.colors = o3d.utility.Vector3dVector(all_colors)

    pcd_down = pcd.voxel_down_sample(voxel_size=voxel_size)

    points_out = np.asarray(pcd_down.points)
    colors_out = np.asarray(pcd_down.colors) if pcd_down.has_colors() else None

    return points_out, colors_out


def statistical_outlier_removal(
    points: np.ndarray,
    nb_neighbors: int = 20,
    std_ratio: float = 2.0,
) -> np.ndarray:
    """Open3D statistical outlier removal.

    Args:
        points: (N, 3) 포인트 클라우드
        nb_neighbors: 이웃 포인트 수
        std_ratio: 표준편차 배수 임계값

    Returns:
        정리된 포인트 클라우드
    """
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    pcd_clean, _ = pcd.remove_statistical_outlier(
        nb_neighbors=nb_neighbors, std_ratio=std_ratio,
    )
    return np.asarray(pcd_clean.points)
