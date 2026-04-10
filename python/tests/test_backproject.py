"""깊이 역투영 및 포인트 클라우드 처리 검증 테스트."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from lidargs.depth.backproject import depth_to_pointcloud
from lidargs.depth.filter import filter_depth_range
from lidargs.depth.merge_clouds import merge_pointclouds, statistical_outlier_removal
from lidargs.transform.intrinsics import scale_intrinsics_for_depth
from tests.conftest import (
    DEPTH_HEIGHT,
    DEPTH_WIDTH,
    RGB_HEIGHT,
    RGB_WIDTH,
    make_c2w,
    make_intrinsics,
)


def _make_depth_intrinsics() -> np.ndarray:
    """depth 해상도(256x192)에 맞춘 테스트용 intrinsics."""
    K_rgb = make_intrinsics()
    return scale_intrinsics_for_depth(K_rgb, (RGB_WIDTH, RGB_HEIGHT))


class TestBackproject:
    """깊이 역투영 검증."""

    def test_identity_camera_flat_wall(self):
        """c2w=I, 모든 depth=2.0 → 모든 포인트의 z=2.0."""
        depth = np.full((DEPTH_HEIGHT, DEPTH_WIDTH), 2.0, dtype=np.float32)
        K = _make_depth_intrinsics()
        c2w = np.eye(4, dtype=np.float64)

        points = depth_to_pointcloud(depth, K, c2w, min_depth=0.1, max_depth=5.0)

        assert points.shape[0] == DEPTH_HEIGHT * DEPTH_WIDTH
        assert points.shape[1] == 3
        # 모든 z 좌표가 2.0
        np.testing.assert_allclose(points[:, 2], 2.0, atol=1e-10)

    def test_known_single_pixel_center(self):
        """principal point 픽셀, depth=1.0 → 카메라 좌표 (0, 0, 1)."""
        K = _make_depth_intrinsics()
        cx = K[0, 2]
        cy = K[1, 2]

        # 중앙 픽셀 하나만 유효한 depth map
        depth = np.zeros((DEPTH_HEIGHT, DEPTH_WIDTH), dtype=np.float32)
        u_center = int(round(cx))
        v_center = int(round(cy))
        depth[v_center, u_center] = 1.0

        c2w = np.eye(4, dtype=np.float64)
        points = depth_to_pointcloud(depth, K, c2w, min_depth=0.01, max_depth=5.0)

        assert points.shape[0] == 1
        # principal point에서 depth=1 → 카메라 좌표 (0, 0, 1) ≈ 월드 좌표 (0, 0, 1)
        np.testing.assert_allclose(points[0], [0.0, 0.0, 1.0], atol=0.1)

    def test_translated_camera(self):
        """c2w에 이동 t=[1,0,0] → 포인트가 x 방향으로 1 이동."""
        K = _make_depth_intrinsics()
        cx, cy = K[0, 2], K[1, 2]

        depth = np.zeros((DEPTH_HEIGHT, DEPTH_WIDTH), dtype=np.float32)
        u_center = int(round(cx))
        v_center = int(round(cy))
        depth[v_center, u_center] = 1.0

        c2w = make_c2w(t=np.array([1.0, 0.0, 0.0]))
        points = depth_to_pointcloud(depth, K, c2w, min_depth=0.01, max_depth=5.0)

        assert points.shape[0] == 1
        np.testing.assert_allclose(points[0], [1.0, 0.0, 1.0], atol=0.1)

    def test_depth_filtering(self):
        """유효 범위 밖 depth는 제외."""
        depth = np.full((DEPTH_HEIGHT, DEPTH_WIDTH), 2.0, dtype=np.float32)
        # 일부를 범위 밖으로 설정
        depth[0, 0] = 0.0     # 무효
        depth[0, 1] = 0.05    # min_depth 이하
        depth[0, 2] = 6.0     # max_depth 이상

        K = _make_depth_intrinsics()
        c2w = np.eye(4, dtype=np.float64)

        points = depth_to_pointcloud(depth, K, c2w, min_depth=0.1, max_depth=5.0)
        expected_count = DEPTH_HEIGHT * DEPTH_WIDTH - 3
        assert points.shape[0] == expected_count

    def test_subsample_reduces_points(self):
        """subsample=2 → 약 1/4 포인트."""
        depth = np.full((DEPTH_HEIGHT, DEPTH_WIDTH), 2.0, dtype=np.float32)
        K = _make_depth_intrinsics()
        c2w = np.eye(4, dtype=np.float64)

        points_full = depth_to_pointcloud(depth, K, c2w, subsample=1)
        points_sub = depth_to_pointcloud(depth, K, c2w, subsample=2)

        # subsample=2이면 각 축에서 절반 → 총 ~1/4
        ratio = points_sub.shape[0] / points_full.shape[0]
        assert 0.2 < ratio < 0.3

    def test_empty_depth(self):
        """모든 depth가 0이면 빈 결과."""
        depth = np.zeros((DEPTH_HEIGHT, DEPTH_WIDTH), dtype=np.float32)
        K = _make_depth_intrinsics()
        c2w = np.eye(4, dtype=np.float64)

        points = depth_to_pointcloud(depth, K, c2w)
        assert points.shape == (0, 3)


class TestFilter:
    """깊이 필터링 검증."""

    def test_range_filter(self):
        """범위 밖 값이 0으로 설정됨."""
        depth = np.array([[0.05, 1.0, 3.0, 6.0]], dtype=np.float32)
        filtered = filter_depth_range(depth, min_depth=0.1, max_depth=5.0)
        np.testing.assert_array_equal(filtered, [[0.0, 1.0, 3.0, 0.0]])

    def test_no_mutation(self):
        """원본이 변경되지 않음."""
        depth = np.array([[0.05, 1.0]], dtype=np.float32)
        original = depth.copy()
        _ = filter_depth_range(depth)
        np.testing.assert_array_equal(depth, original)


class TestMergeAndOutlier:
    """포인트 클라우드 병합 및 outlier 제거 검증."""

    def test_merge_two_clouds(self):
        """두 포인트 클라우드 병합 → 전체 포인트 수 이하 결과."""
        pts1 = np.random.rand(1000, 3).astype(np.float64)
        pts2 = np.random.rand(1000, 3).astype(np.float64)

        merged, _ = merge_pointclouds([pts1, pts2], voxel_size=0.05)
        # voxel 다운샘플링으로 원본보다 적어야 함
        assert merged.shape[0] < 2000
        assert merged.shape[0] > 0

    def test_merge_identical_clouds(self):
        """동일 포인트 클라우드 2개 병합 → 약 1개분량 결과."""
        pts = np.random.rand(500, 3).astype(np.float64)
        merged_one, _ = merge_pointclouds([pts], voxel_size=0.05)
        merged_two, _ = merge_pointclouds([pts, pts], voxel_size=0.05)

        # 동일 데이터이므로 결과 포인트 수가 비슷해야 함
        ratio = merged_two.shape[0] / merged_one.shape[0]
        assert 0.8 < ratio < 1.3

    def test_outlier_removal(self):
        """극단적 outlier가 제거됨."""
        # 원점 근처 클러스터 + 먼 outlier
        pts_cluster = np.random.randn(200, 3).astype(np.float64) * 0.1
        pts_outlier = np.array([[100.0, 100.0, 100.0], [-50.0, -50.0, -50.0]])
        pts = np.vstack([pts_cluster, pts_outlier])

        cleaned = statistical_outlier_removal(pts, nb_neighbors=20, std_ratio=2.0)
        assert cleaned.shape[0] <= pts.shape[0]
        # outlier가 제거되었으므로 max 값이 줄어들어야 함
        assert np.max(np.abs(cleaned)) < 50.0
