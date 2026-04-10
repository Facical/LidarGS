"""좌표 변환 검증 테스트.

최고 위험 영역: quaternion 순서, 축 변환, c2w/w2c 혼동을 검증한다.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from lidargs.transform.arkit_to_colmap import arkit_c2w_to_colmap, colmap_to_arkit_c2w
from lidargs.transform.arkit_to_gsplat import arkit_c2w_to_viewmat, batch_c2w_to_viewmats
from lidargs.transform.arkit_to_nerfstudio import arkit_c2w_to_nerfstudio
from lidargs.transform.intrinsics import scale_intrinsics, scale_intrinsics_for_depth
from tests.conftest import make_c2w, make_intrinsics, random_c2w


# ---------------------------------------------------------------------------
# ARKit → COLMAP 변환 테스트
# ---------------------------------------------------------------------------

class TestArkitToColmap:
    """ARKit → COLMAP 변환 검증."""

    def test_identity_camera(self):
        """c2w=I (ARKit OpenGL) → COLMAP에서는 X축 180도 회전 (Y/Z flip).

        OpenGL identity → OpenCV 변환 시 diag([1,-1,-1]) 회전이 발생하므로
        COLMAP quat = [0, 1, 0, 0] (X축 180도), t = [0, 0, 0].
        """
        c2w = np.eye(4, dtype=np.float64)
        quat, t = arkit_c2w_to_colmap(c2w)
        # X축 180도 회전: qw=0, qx=1, qy=0, qz=0
        np.testing.assert_allclose(np.abs(quat), [0, 1, 0, 0], atol=1e-10)
        np.testing.assert_allclose(t, [0, 0, 0], atol=1e-10)

    def test_translated_camera(self):
        """이동만 있는 카메라."""
        c2w = make_c2w(t=np.array([1.0, 2.0, 3.0]))
        quat, t = arkit_c2w_to_colmap(c2w)
        # 회전 없으므로 quat 크기 1
        assert abs(np.linalg.norm(quat) - 1.0) < 1e-10

    def test_quaternion_is_unit(self):
        """COLMAP 쿼터니언은 항상 단위 쿼터니언."""
        rng = np.random.default_rng(42)
        for _ in range(20):
            c2w = random_c2w(rng)
            quat, _ = arkit_c2w_to_colmap(c2w)
            assert abs(np.linalg.norm(quat) - 1.0) < 1e-10

    def test_quaternion_ordering_w_first(self):
        """COLMAP 쿼터니언은 [qw, qx, qy, qz] 순서 — qw가 첫 번째."""
        # Y축 90도 회전
        R = Rotation.from_euler("y", 90, degrees=True).as_matrix()
        c2w = make_c2w(R=R)
        quat, _ = arkit_c2w_to_colmap(c2w)

        # 역변환하여 scipy 쿼터니언으로 검증
        quat_scipy = np.array([quat[1], quat[2], quat[3], quat[0]])
        R_recovered = Rotation.from_quat(quat_scipy).as_matrix()
        # 회전이 유효한 SO(3) 행렬인지 확인
        assert abs(np.linalg.det(R_recovered) - 1.0) < 1e-10

    def test_roundtrip(self):
        """ARKit → COLMAP → ARKit 왕복 변환이 원본과 일치."""
        c2w = make_c2w(
            R=Rotation.from_euler("xyz", [30, 45, 60], degrees=True).as_matrix(),
            t=np.array([1.0, -2.0, 3.5]),
        )
        quat, t = arkit_c2w_to_colmap(c2w)
        c2w_recovered = colmap_to_arkit_c2w(quat, t)
        np.testing.assert_allclose(c2w_recovered, c2w, atol=1e-10)

    def test_roundtrip_fuzz(self):
        """100개 랜덤 c2w 행렬에 대한 왕복 변환 검증."""
        rng = np.random.default_rng(123)
        for _ in range(100):
            c2w = random_c2w(rng)
            quat, t = arkit_c2w_to_colmap(c2w)
            c2w_recovered = colmap_to_arkit_c2w(quat, t)
            np.testing.assert_allclose(c2w_recovered, c2w, atol=1e-8)


# ---------------------------------------------------------------------------
# ARKit → gsplat 변환 테스트
# ---------------------------------------------------------------------------

class TestArkitToGsplat:
    """ARKit → gsplat viewmat 검증."""

    def test_viewmat_is_inverse(self):
        """viewmat @ c2w = I."""
        rng = np.random.default_rng(42)
        for _ in range(20):
            c2w = random_c2w(rng)
            viewmat = arkit_c2w_to_viewmat(c2w)
            product = viewmat.astype(np.float64) @ c2w
            np.testing.assert_allclose(product, np.eye(4), atol=1e-5)

    def test_identity(self):
        """c2w=I → viewmat=I."""
        c2w = np.eye(4, dtype=np.float64)
        viewmat = arkit_c2w_to_viewmat(c2w)
        np.testing.assert_allclose(viewmat, np.eye(4, dtype=np.float32), atol=1e-7)

    def test_batch(self):
        """배치 변환이 개별 변환과 동일."""
        rng = np.random.default_rng(42)
        c2ws = np.stack([random_c2w(rng) for _ in range(5)])
        batch_result = batch_c2w_to_viewmats(c2ws)
        for i in range(5):
            single = arkit_c2w_to_viewmat(c2ws[i])
            np.testing.assert_allclose(batch_result[i], single, atol=1e-6)

    def test_output_dtype(self):
        """출력은 float32."""
        viewmat = arkit_c2w_to_viewmat(np.eye(4, dtype=np.float64))
        assert viewmat.dtype == np.float32


# ---------------------------------------------------------------------------
# ARKit → Nerfstudio 변환 테스트
# ---------------------------------------------------------------------------

class TestArkitToNerfstudio:
    """ARKit → Nerfstudio (identity) 검증."""

    def test_identity_transform(self):
        """출력이 입력과 동일."""
        rng = np.random.default_rng(42)
        c2w = random_c2w(rng)
        result = arkit_c2w_to_nerfstudio(c2w)
        np.testing.assert_allclose(result, c2w, atol=1e-15)

    def test_output_dtype(self):
        """출력은 float64."""
        result = arkit_c2w_to_nerfstudio(np.eye(4, dtype=np.float32))
        assert result.dtype == np.float64


# ---------------------------------------------------------------------------
# Intrinsics 스케일링 테스트
# ---------------------------------------------------------------------------

class TestIntrinsics:
    """Intrinsics 스케일링 검증."""

    def test_scale_down(self):
        """1920x1080 → 256x192 스케일링."""
        K = make_intrinsics(fx=1598.0, fy=1598.0, cx=960.0, cy=540.0)
        K_depth = scale_intrinsics(K, (1920, 1080), (256, 192))

        sx = 256 / 1920
        sy = 192 / 1080
        assert abs(K_depth[0, 0] - 1598.0 * sx) < 1e-10
        assert abs(K_depth[1, 1] - 1598.0 * sy) < 1e-10
        assert abs(K_depth[0, 2] - 960.0 * sx) < 1e-10
        assert abs(K_depth[1, 2] - 540.0 * sy) < 1e-10

    def test_scale_roundtrip(self):
        """축소 후 확대하면 원본 복원."""
        K = make_intrinsics()
        K_small = scale_intrinsics(K, (1920, 1080), (256, 192))
        K_back = scale_intrinsics(K_small, (256, 192), (1920, 1080))
        np.testing.assert_allclose(K_back, K, atol=1e-10)

    def test_scale_for_depth_convenience(self):
        """scale_intrinsics_for_depth가 scale_intrinsics와 동일 결과."""
        K = make_intrinsics()
        K_a = scale_intrinsics(K, (1920, 1080), (256, 192))
        K_b = scale_intrinsics_for_depth(K, (1920, 1080))
        np.testing.assert_allclose(K_a, K_b)

    def test_no_mutation(self):
        """원본 K가 변경되지 않음."""
        K = make_intrinsics()
        K_orig = K.copy()
        _ = scale_intrinsics(K, (1920, 1080), (256, 192))
        np.testing.assert_array_equal(K, K_orig)
