#!/usr/bin/env python3
"""iOS 캡처 데이터 → 학습용 데이터 처리 메인 스크립트.

사용법:
    python scripts/01_process_capture.py --scene scene_desk
    python scripts/01_process_capture.py --scene scene_desk --visualize
    python scripts/01_process_capture.py --scene scene_desk --raw_dir data/raw --output_dir data/processed
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from tqdm import tqdm

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lidargs.depth.backproject import depth_to_pointcloud_with_colors
from lidargs.depth.merge_clouds import merge_pointclouds, statistical_outlier_removal
from lidargs.io.export_colmap import export_colmap_text
from lidargs.io.export_nerfstudio import export_transforms_json
from lidargs.io.export_ply import export_ply
from lidargs.io.load_capture import load_capture, load_depth_map, load_image
from lidargs.transform.intrinsics import scale_intrinsics_for_depth


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="iOS 캡처 → 학습 데이터 처리")
    parser.add_argument("--scene", required=True, help="씬 이름 (예: scene_desk)")
    parser.add_argument("--raw_dir", default="data/raw", help="raw 캡처 루트 디렉토리")
    parser.add_argument("--output_dir", default="data/processed", help="출력 루트 디렉토리")
    parser.add_argument("--voxel_size", type=float, default=0.01, help="voxel 다운샘플링 크기 (m)")
    parser.add_argument("--min_depth", type=float, default=0.1, help="최소 유효 깊이 (m)")
    parser.add_argument("--max_depth", type=float, default=5.0, help="최대 유효 깊이 (m)")
    parser.add_argument("--subsample", type=int, default=1, help="깊이 서브샘플링 간격")
    parser.add_argument("--visualize", action="store_true", help="Open3D 시각화 실행")
    parser.add_argument("--run_colmap", action="store_true", help="Method A에 대해 COLMAP SfM 자동 실행")
    parser.add_argument("--matcher_type", default="exhaustive", choices=["exhaustive", "sequential"],
                        help="COLMAP matcher 유형 (기본: exhaustive)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    raw_dir = Path(args.raw_dir)
    output_dir = Path(args.output_dir)
    scene_dir = raw_dir / args.scene

    if not scene_dir.exists():
        print(f"오류: {scene_dir} 경로가 존재하지 않습니다.")
        sys.exit(1)

    # 1. 캡처 데이터 로드
    print(f"[1/6] 캡처 데이터 로드: {scene_dir}")
    capture = load_capture(scene_dir)
    print(f"  씬: {capture.scene_name}, 기기: {capture.device_model}, "
          f"프레임: {len(capture.frames)}개")

    # 2. 깊이 역투영 → 포인트 클라우드
    print(f"[2/6] 깊이 역투영 (voxel={args.voxel_size}m, "
          f"depth={args.min_depth}-{args.max_depth}m)")
    all_points: list[np.ndarray] = []
    all_colors: list[np.ndarray] = []

    for frame in tqdm(capture.frames, desc="  역투영"):
        depth_map = load_depth_map(
            frame.depth_path, frame.depth_width, frame.depth_height,
        )
        K_depth = scale_intrinsics_for_depth(
            frame.intrinsics,
            (frame.image_width, frame.image_height),
            (frame.depth_width, frame.depth_height),
        )

        # 이미지가 있으면 색상도 추출
        if frame.image_path.exists():
            image = load_image(frame.image_path)
            pts, colors = depth_to_pointcloud_with_colors(
                depth_map, K_depth, frame.c2w, image,
                rgb_size=(frame.image_width, frame.image_height),
                min_depth=args.min_depth, max_depth=args.max_depth,
                subsample=args.subsample,
            )
            all_points.append(pts)
            all_colors.append(colors)
        else:
            from lidargs.depth.backproject import depth_to_pointcloud
            pts = depth_to_pointcloud(
                depth_map, K_depth, frame.c2w,
                min_depth=args.min_depth, max_depth=args.max_depth,
                subsample=args.subsample,
            )
            all_points.append(pts)

    # 3. 포인트 클라우드 병합 + 다운샘플링
    print("[3/6] 포인트 클라우드 병합 + voxel 다운샘플링")
    total_raw = sum(p.shape[0] for p in all_points)
    has_colors = len(all_colors) == len(all_points)

    merged_pts, merged_colors = merge_pointclouds(
        all_points,
        colors_list=all_colors if has_colors else None,
        voxel_size=args.voxel_size,
    )
    print(f"  raw: {total_raw:,} → merged: {merged_pts.shape[0]:,} 포인트")

    # Outlier 제거
    print("[4/6] Statistical outlier removal")
    cleaned_pts = statistical_outlier_removal(merged_pts)
    print(f"  {merged_pts.shape[0]:,} → {cleaned_pts.shape[0]:,} 포인트")

    # 4. Method B (LidarGS) COLMAP 포맷 내보내기
    method_b_dir = output_dir / args.scene / "method_b_lidargs"
    print(f"[5/6] Method B 내보내기: {method_b_dir}")

    # 색상이 있으면 PLY용 uint8 색상 추출
    pts_rgb = None
    if merged_colors is not None:
        pts_rgb = (merged_colors * 255).astype(np.uint8) if merged_colors.max() <= 1.0 \
            else merged_colors.astype(np.uint8)

    export_colmap_text(capture.frames, method_b_dir, cleaned_pts, pts_rgb)
    export_transforms_json(capture.frames, method_b_dir)
    export_ply(cleaned_pts, method_b_dir / "points3d_lidar.ply", pts_rgb)

    # Method C (Random init) — 포즈는 동일, 포인트 없음
    method_c_dir = output_dir / args.scene / "method_c_random"
    export_colmap_text(capture.frames, method_c_dir)

    # Method A (COLMAP baseline) — 이미지 복사 + 선택적 COLMAP 실행
    method_a_dir = output_dir / args.scene / "method_a_colmap"
    method_a_images = method_a_dir / "images"
    method_a_images.mkdir(parents=True, exist_ok=True)

    import shutil
    for frame in capture.frames:
        src = frame.image_path
        dst = method_a_images / src.name
        if src.exists() and not dst.exists():
            shutil.copy2(str(src), str(dst))

    num_copied = len(list(method_a_images.glob("*.jpg"))) + len(list(method_a_images.glob("*.png")))
    print(f"  Method A 이미지: {num_copied}장 → {method_a_images}")

    if args.run_colmap:
        from lidargs.io.run_colmap import run_colmap_sfm
        print(f"  COLMAP SfM 실행 중 (matcher: {args.matcher_type})...")
        colmap_result = run_colmap_sfm(
            method_a_dir,
            matcher_type=args.matcher_type,
        )
        if colmap_result["success"]:
            print(f"  COLMAP 완료: {colmap_result['num_registered']}장 등록, "
                  f"{colmap_result['num_points3d']}개 포인트, "
                  f"{colmap_result['total_seconds']}초")
        else:
            print(f"  COLMAP 실패: {colmap_result['error']}")
    else:
        print("  → COLMAP SfM은 별도 실행 필요:")
        print(f"    bash scripts/run_colmap.sh {method_a_dir}")

    print("[6/6] 완료!")
    print(f"  Method B: {method_b_dir}")
    print(f"  Method C: {method_c_dir}")
    print(f"  Method A: {method_a_dir} (COLMAP 실행 필요)")

    # 5. 시각화 (optional)
    if args.visualize:
        print("시각화 실행...")
        from lidargs.viz.visualize_poses import visualize_cameras_and_points
        c2ws = np.stack([f.c2w for f in capture.frames])
        visualize_cameras_and_points(
            c2ws=c2ws,
            intrinsics=capture.frames[0].intrinsics,
            image_width=capture.frames[0].image_width,
            image_height=capture.frames[0].image_height,
            points=cleaned_pts,
            points_colors=pts_rgb,
            title=f"LidarGS - {args.scene}",
        )


if __name__ == "__main__":
    main()
