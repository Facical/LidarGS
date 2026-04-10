"""COLMAP 텍스트 포맷 생성.

cameras.txt, images.txt, points3D.txt를 생성한다.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

from lidargs.io.load_capture import FrameData
from lidargs.transform.arkit_to_colmap import arkit_c2w_to_colmap


def export_colmap_text(
    frames: list[FrameData],
    output_dir: str | Path,
    points: np.ndarray | None = None,
    points_rgb: np.ndarray | None = None,
) -> None:
    """ARKit 캡처 데이터로부터 COLMAP 텍스트 포맷 파일을 생성.

    생성 파일:
        output_dir/sparse/0/cameras.txt
        output_dir/sparse/0/images.txt
        output_dir/sparse/0/points3D.txt
        output_dir/images/ (이미지 복사)

    Args:
        frames: FrameData 리스트
        output_dir: 출력 디렉토리
        points: (N, 3) 3D 포인트 (optional)
        points_rgb: (N, 3) uint8 색상 (optional)
    """
    output_dir = Path(output_dir)
    sparse_dir = output_dir / "sparse" / "0"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # cameras.txt — 단일 PINHOLE 카메라 모델
    frame0 = frames[0]
    K = frame0.intrinsics
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]

    with open(sparse_dir / "cameras.txt", "w") as f:
        f.write("# Camera list with one line of data per camera:\n")
        f.write("# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
        f.write(
            f"1 PINHOLE {frame0.image_width} {frame0.image_height} "
            f"{fx} {fy} {cx} {cy}\n"
        )

    # images.txt — 프레임별 포즈 (쿼터니언 + 이동 벡터)
    with open(sparse_dir / "images.txt", "w") as f:
        f.write("# Image list with two lines of data per image:\n")
        f.write("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        for i, frame in enumerate(frames):
            quat, t = arkit_c2w_to_colmap(frame.c2w)
            name = frame.image_path.name
            f.write(
                f"{i + 1} {quat[0]} {quat[1]} {quat[2]} {quat[3]} "
                f"{t[0]} {t[1]} {t[2]} 1 {name}\n"
            )
            f.write("\n")  # POINTS2D 빈 줄

    # points3D.txt
    with open(sparse_dir / "points3D.txt", "w") as f:
        f.write("# 3D point list with one line of data per point:\n")
        f.write("# POINT3D_ID X Y Z R G B ERROR TRACK[]\n")
        if points is not None:
            for i in range(len(points)):
                x, y, z = points[i]
                if points_rgb is not None:
                    r, g, b = points_rgb[i].astype(int)
                else:
                    r, g, b = 128, 128, 128
                f.write(f"{i + 1} {x} {y} {z} {r} {g} {b} 0.0\n")

    # 이미지 복사
    for frame in frames:
        src = frame.image_path
        dst = images_dir / src.name
        if src.exists() and not dst.exists():
            shutil.copy2(str(src), str(dst))
