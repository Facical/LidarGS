"""Nerfstudio transforms.json 생성.

ARKit과 Nerfstudio 모두 OpenGL camera-to-world를 사용하므로
transform_matrix를 직접 저장한다.
"""

from __future__ import annotations

import json
from pathlib import Path

from lidargs.io.load_capture import FrameData


def export_transforms_json(
    frames: list[FrameData],
    output_dir: str | Path,
    include_depth: bool = True,
) -> None:
    """Nerfstudio transforms.json을 생성.

    Args:
        frames: FrameData 리스트
        output_dir: 출력 디렉토리
        include_depth: depth_file_path 포함 여부
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame0 = frames[0]
    K = frame0.intrinsics

    data = {
        "camera_model": "OPENCV",
        "fl_x": float(K[0, 0]),
        "fl_y": float(K[1, 1]),
        "cx": float(K[0, 2]),
        "cy": float(K[1, 2]),
        "w": frame0.image_width,
        "h": frame0.image_height,
        "k1": 0.0,
        "k2": 0.0,
        "p1": 0.0,
        "p2": 0.0,
        "frames": [],
    }

    for frame in frames:
        frame_entry: dict = {
            "file_path": f"images/{frame.image_path.name}",
            "transform_matrix": frame.c2w.tolist(),
        }
        if include_depth:
            frame_entry["depth_file_path"] = (
                f"depths/{frame.depth_path.stem}.png"
            )
        data["frames"].append(frame_entry)

    with open(output_dir / "transforms.json", "w") as f:
        json.dump(data, f, indent=2)
