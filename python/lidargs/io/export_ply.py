"""포인트 클라우드 PLY 내보내기."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import open3d as o3d


def export_ply(
    points: np.ndarray,
    output_path: str | Path,
    colors: np.ndarray | None = None,
) -> None:
    """포인트 클라우드를 PLY 파일로 저장.

    Args:
        points: (N, 3) 포인트 좌표
        output_path: 출력 PLY 파일 경로
        colors: (N, 3) uint8 또는 float [0,1] 색상 (optional)
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points.astype(np.float64))

    if colors is not None:
        colors_f = colors.astype(np.float64)
        if colors_f.max() > 1.0:
            colors_f = colors_f / 255.0
        pcd.colors = o3d.utility.Vector3dVector(colors_f)

    o3d.io.write_point_cloud(str(output_path), pcd)
