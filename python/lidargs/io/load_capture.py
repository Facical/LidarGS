"""iOS 캡처 데이터 로딩 모듈.

metadata.json + images/ + depths/ 로부터 FrameData/CaptureData를 구성한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import imageio
import numpy as np


@dataclass
class FrameData:
    """단일 프레임 데이터."""

    index: int
    timestamp: float
    image_path: Path
    depth_path: Path
    c2w: np.ndarray  # (4, 4) float64, camera-to-world, row-major, OpenGL
    intrinsics: np.ndarray  # (3, 3) float64, RGB 카메라 intrinsics
    image_width: int  # 1920
    image_height: int  # 1080
    depth_width: int  # 256
    depth_height: int  # 192


@dataclass
class CaptureData:
    """캡처 세션 전체 데이터."""

    scene_name: str
    device_model: str
    frames: list[FrameData]


def load_capture(capture_dir: str | Path) -> CaptureData:
    """iOS 캡처 디렉토리에서 데이터를 로드한다.

    Args:
        capture_dir: raw 캡처 경로 (예: data/raw/scene_desk/)

    Returns:
        CaptureData: 로드된 전체 프레임
    """
    capture_dir = Path(capture_dir)
    with open(capture_dir / "metadata.json") as f:
        meta = json.load(f)

    frames: list[FrameData] = []
    for frame_dict in meta["frames"]:
        frames.append(
            FrameData(
                index=frame_dict["index"],
                timestamp=frame_dict["timestamp"],
                image_path=capture_dir / frame_dict["imagePath"],
                depth_path=capture_dir / frame_dict["depthPath"],
                c2w=np.array(frame_dict["transform"], dtype=np.float64),
                intrinsics=np.array(frame_dict["intrinsics"], dtype=np.float64),
                image_width=frame_dict["imageWidth"],
                image_height=frame_dict["imageHeight"],
                depth_width=frame_dict["depthWidth"],
                depth_height=frame_dict["depthHeight"],
            )
        )

    return CaptureData(
        scene_name=meta["sceneName"],
        device_model=meta["deviceModel"],
        frames=frames,
    )


def load_depth_map(
    depth_path: str | Path,
    width: int = 256,
    height: int = 192,
) -> np.ndarray:
    """바이너리 float32 깊이 맵을 로드한다.

    Returns:
        np.ndarray: shape (height, width), dtype float32, 단위: 미터
    """
    data = np.fromfile(str(depth_path), dtype=np.float32)
    return data.reshape(height, width)


def load_image(image_path: str | Path) -> np.ndarray:
    """JPEG 이미지를 로드한다.

    Returns:
        np.ndarray: shape (H, W, 3), dtype uint8
    """
    return imageio.imread(str(image_path))
