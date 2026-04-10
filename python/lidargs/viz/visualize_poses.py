"""카메라 포즈 및 포인트 클라우드 3D 시각화.

Open3D를 사용하여 카메라 frustum과 포인트 클라우드를 오버레이한다.
"""

from __future__ import annotations

import numpy as np
import open3d as o3d


def visualize_cameras_and_points(
    c2ws: np.ndarray,
    intrinsics: np.ndarray,
    image_width: int,
    image_height: int,
    points: np.ndarray | None = None,
    points_colors: np.ndarray | None = None,
    camera_scale: float = 0.1,
    title: str = "Pose Visualization",
) -> None:
    """카메라 포즈를 frustum으로, 포인트 클라우드를 오버레이하여 시각화.

    검증 체크리스트:
    - 카메라 frustum이 일관된 궤적을 형성하는가
    - 모든 frustum이 씬 안쪽을 향하는가
    - 포인트 클라우드가 카메라 궤적 "안쪽"에 있는가
    - 월드 좌표축이 합리적인가 (Y-up)

    Args:
        c2ws: (N, 4, 4) camera-to-world 행렬
        intrinsics: (3, 3) intrinsics
        image_width: 이미지 너비
        image_height: 이미지 높이
        points: (M, 3) 포인트 클라우드 (optional)
        points_colors: (M, 3) 색상 uint8 또는 float (optional)
        camera_scale: frustum 표시 크기
        title: 창 제목
    """
    geometries: list = []

    for i in range(len(c2ws)):
        w2c = np.linalg.inv(c2ws[i])
        cam = o3d.geometry.LineSet.create_camera_visualization(
            image_width, image_height, intrinsics, w2c, scale=camera_scale,
        )
        geometries.append(cam)

    if points is not None:
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        if points_colors is not None:
            colors_f = points_colors.astype(np.float64)
            if colors_f.max() > 1.0:
                colors_f = colors_f / 255.0
            pcd.colors = o3d.utility.Vector3dVector(colors_f)
        geometries.append(pcd)

    axes = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.5)
    geometries.append(axes)

    o3d.visualization.draw_geometries(geometries, window_name=title)
