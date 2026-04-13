"""합성 테스트 데이터 생성 fixture.

iOS 앱이 아직 없으므로 모든 테스트는 합성 데이터로 수행한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from lidargs.io.load_capture import CaptureData, FrameData


# ---------------------------------------------------------------------------
# 기본 상수
# ---------------------------------------------------------------------------
# 테스트용 대표값. 프로덕션 코드는 metadata.json에서 동적으로 읽으므로
# 실제 캡처 해상도와 무관하게 동작한다.
# ARKit 비디오: 1080p(1920×1080) 또는 4K(3840×2160) 모두 지원.
RGB_WIDTH, RGB_HEIGHT = 1920, 1080
# LiDAR 깊이 해상도는 iPhone 기종·영상 해상도에 관계없이 ARKit에서 항상 256×192.
DEPTH_WIDTH, DEPTH_HEIGHT = 256, 192
FOCAL_LENGTH = 1598.0  # iPhone 15 Pro 1080p 대표값
CX, CY = RGB_WIDTH / 2.0, RGB_HEIGHT / 2.0


def make_intrinsics(fx: float = FOCAL_LENGTH, fy: float = FOCAL_LENGTH,
                    cx: float = CX, cy: float = CY) -> np.ndarray:
    """3x3 intrinsics 행렬 생성."""
    return np.array([
        [fx, 0.0, cx],
        [0.0, fy, cy],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)


def make_c2w(R: np.ndarray | None = None, t: np.ndarray | None = None) -> np.ndarray:
    """camera-to-world 4x4 행렬 생성."""
    c2w = np.eye(4, dtype=np.float64)
    if R is not None:
        c2w[:3, :3] = R
    if t is not None:
        c2w[:3, 3] = t
    return c2w


def random_c2w(rng: np.random.Generator | None = None) -> np.ndarray:
    """랜덤 유효 camera-to-world SE(3) 행렬 생성."""
    if rng is None:
        rng = np.random.default_rng()
    R = Rotation.random(random_state=rng).as_matrix()
    t = rng.uniform(-5.0, 5.0, size=3)
    return make_c2w(R, t)


def make_lookat_c2w(eye: np.ndarray, target: np.ndarray,
                    up: np.ndarray = np.array([0.0, 1.0, 0.0])) -> np.ndarray:
    """eye에서 target을 바라보는 camera-to-world 행렬 생성 (OpenGL 좌표계).

    OpenGL: -Z가 forward, Y가 up.
    """
    forward = target - eye
    forward = forward / np.linalg.norm(forward)
    # OpenGL에서 카메라 -Z가 forward이므로 z축은 -forward
    z = -forward
    right = np.cross(up, z)
    right = right / np.linalg.norm(right)
    y = np.cross(z, right)
    R = np.column_stack([right, y, z])  # (3, 3)
    return make_c2w(R, eye)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def identity_c2w() -> np.ndarray:
    """단위 행렬 c2w."""
    return np.eye(4, dtype=np.float64)


@pytest.fixture
def standard_intrinsics() -> np.ndarray:
    """표준 RGB intrinsics (1920x1080)."""
    return make_intrinsics()


@pytest.fixture
def depth_intrinsics() -> np.ndarray:
    """depth 해상도(256x192)에 맞춘 intrinsics."""
    sx = DEPTH_WIDTH / RGB_WIDTH
    sy = DEPTH_HEIGHT / RGB_HEIGHT
    return make_intrinsics(
        fx=FOCAL_LENGTH * sx, fy=FOCAL_LENGTH * sy,
        cx=CX * sx, cy=CY * sy,
    )


@pytest.fixture
def flat_depth_map() -> np.ndarray:
    """2m 거리의 평면 벽 깊이 맵."""
    return np.full((DEPTH_HEIGHT, DEPTH_WIDTH), 2.0, dtype=np.float32)


@pytest.fixture
def circular_capture() -> CaptureData:
    """원형 궤적 카메라 10프레임 합성 캡처 데이터.

    카메라가 원점 주위 반경 2m 원형 궤적 위에서 원점을 바라본다.
    """
    num_frames = 10
    radius = 2.0
    height = 1.5
    frames: list[FrameData] = []

    for i in range(num_frames):
        angle = 2.0 * np.pi * i / num_frames
        eye = np.array([
            radius * np.cos(angle),
            height,
            radius * np.sin(angle),
        ])
        target = np.array([0.0, 0.0, 0.0])
        c2w = make_lookat_c2w(eye, target)

        frames.append(FrameData(
            index=i,
            timestamp=float(i),
            image_path=Path(f"images/frame_{i:06d}.jpg"),
            depth_path=Path(f"depths/frame_{i:06d}.bin"),
            c2w=c2w,
            intrinsics=make_intrinsics(),
            image_width=RGB_WIDTH,
            image_height=RGB_HEIGHT,
            depth_width=DEPTH_WIDTH,
            depth_height=DEPTH_HEIGHT,
        ))

    return CaptureData(
        scene_name="synthetic_circle",
        device_model="Synthetic",
        frames=frames,
    )


@pytest.fixture
def synthetic_capture_on_disk(tmp_path: Path) -> Path:
    """디스크에 기록된 합성 캡처 데이터.

    metadata.json + images/ + depths/ 전체를 tmp_path에 생성.
    load_capture() 테스트에 사용.
    """
    scene_dir = tmp_path / "scene_test"
    images_dir = scene_dir / "images"
    depths_dir = scene_dir / "depths"
    images_dir.mkdir(parents=True)
    depths_dir.mkdir(parents=True)

    num_frames = 5
    frames_meta: list[dict] = []
    K = make_intrinsics()

    for i in range(num_frames):
        # 합성 이미지 (단색 JPEG)
        img = np.full((RGB_HEIGHT, RGB_WIDTH, 3), fill_value=(i * 50) % 256, dtype=np.uint8)
        img_name = f"frame_{i:06d}.jpg"
        import imageio
        imageio.imwrite(str(images_dir / img_name), img)

        # 합성 깊이 (float32 binary)
        depth = np.full((DEPTH_HEIGHT, DEPTH_WIDTH), 1.5 + i * 0.2, dtype=np.float32)
        depth_name = f"frame_{i:06d}.bin"
        depth.tofile(str(depths_dir / depth_name))

        # 포즈: 단순 이동
        c2w = make_c2w(t=np.array([float(i) * 0.1, 0.0, 0.0]))

        frames_meta.append({
            "index": i,
            "timestamp": float(i) * 0.5,
            "imagePath": f"images/{img_name}",
            "depthPath": f"depths/{depth_name}",
            "transform": c2w.tolist(),
            "intrinsics": K.tolist(),
            "imageWidth": RGB_WIDTH,
            "imageHeight": RGB_HEIGHT,
            "depthWidth": DEPTH_WIDTH,
            "depthHeight": DEPTH_HEIGHT,
        })

    metadata = {
        "deviceModel": "Synthetic",
        "iosVersion": "17.4",
        "captureDate": "2026-04-10T12:00:00Z",
        "sceneName": "scene_test",
        "frameCount": num_frames,
        "samplingFPS": 1.0,
        "frames": frames_meta,
    }

    with open(scene_dir / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    return scene_dir
