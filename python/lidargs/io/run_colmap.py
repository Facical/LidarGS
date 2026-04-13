"""COLMAP SfM 파이프라인 Python 래퍼.

subprocess로 COLMAP CLI를 호출하고 결과를 파싱한다.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path


def run_colmap_sfm(
    scene_dir: str | Path,
    matcher_type: str = "exhaustive",
    use_gpu: bool = True,
) -> dict:
    """COLMAP SfM 파이프라인을 실행.

    Args:
        scene_dir: Method A 씬 디렉토리 (images/ 포함)
        matcher_type: "exhaustive" 또는 "sequential"
        use_gpu: GPU 가속 사용 여부

    Returns:
        dict: {
            "success": bool,
            "total_seconds": float,
            "stages": {stage_name: seconds},
            "num_images": int,
            "num_registered": int,
            "num_points3d": int,
            "error": str | None,
        }
    """
    scene_dir = Path(scene_dir)
    image_dir = scene_dir / "images"
    database_path = scene_dir / "database.db"
    sparse_dir = scene_dir / "sparse"

    # 입력 검증
    if not image_dir.is_dir():
        return _error_result(f"이미지 디렉토리가 없습니다: {image_dir}")

    image_files = list(image_dir.glob("*.jpg")) + list(image_dir.glob("*.jpeg")) + list(image_dir.glob("*.png"))
    if not image_files:
        return _error_result(f"이미지가 없습니다: {image_dir}")

    num_images = len(image_files)
    gpu_flag = "1" if use_gpu else "0"

    # 기존 database 삭제
    if database_path.exists():
        database_path.unlink()
    sparse_dir.mkdir(parents=True, exist_ok=True)

    stages: dict[str, float] = {}
    total_start = time.time()

    # Stage 1: Feature Extraction
    print(f"[COLMAP 1/4] Feature Extraction ({num_images}장)")
    ok, elapsed = _run_stage("feature_extractor", [
        "colmap", "feature_extractor",
        "--database_path", str(database_path),
        "--image_path", str(image_dir),
        "--ImageReader.camera_model", "PINHOLE",
        "--ImageReader.single_camera", "1",
        "--SiftExtraction.use_gpu", gpu_flag,
    ])
    stages["feature_extraction"] = elapsed
    if not ok:
        return _error_result("Feature extraction 실패", stages=stages)

    # Stage 2: Feature Matching
    print(f"[COLMAP 2/4] Feature Matching ({matcher_type})")
    matcher_cmd = "exhaustive_matcher" if matcher_type == "exhaustive" else "sequential_matcher"
    ok, elapsed = _run_stage("matching", [
        "colmap", matcher_cmd,
        "--database_path", str(database_path),
        "--SiftMatching.use_gpu", gpu_flag,
    ])
    stages["feature_matching"] = elapsed
    if not ok:
        return _error_result("Feature matching 실패", stages=stages)

    # Stage 3: Mapper
    print("[COLMAP 3/4] Sparse Reconstruction (Mapper)")
    ok, elapsed = _run_stage("mapper", [
        "colmap", "mapper",
        "--database_path", str(database_path),
        "--image_path", str(image_dir),
        "--output_path", str(sparse_dir),
    ])
    stages["mapper"] = elapsed
    if not ok:
        return _error_result("Mapper 실패", stages=stages)

    # sparse/0 존재 확인
    if not (sparse_dir / "0").is_dir():
        return _error_result("Mapper가 모델을 생성하지 못했습니다", stages=stages)

    # Stage 4: Model Converter (bin → txt)
    print("[COLMAP 4/4] Model Converter (bin → txt)")
    ok, elapsed = _run_stage("converter", [
        "colmap", "model_converter",
        "--input_path", str(sparse_dir / "0"),
        "--output_path", str(sparse_dir / "0"),
        "--output_type", "TXT",
    ])
    stages["model_converter"] = elapsed
    if not ok:
        return _error_result("Model converter 실패", stages=stages)

    total_seconds = time.time() - total_start

    # 결과 파싱
    num_registered = _count_registered_images(sparse_dir / "0" / "images.txt")
    num_points3d = _count_points3d(sparse_dir / "0" / "points3D.txt")

    result = {
        "success": True,
        "total_seconds": round(total_seconds, 1),
        "stages": {k: round(v, 1) for k, v in stages.items()},
        "num_images": num_images,
        "num_registered": num_registered,
        "num_points3d": num_points3d,
        "error": None,
    }

    # 타이밍 JSON 저장
    timing_path = scene_dir / "colmap_timing.json"
    with open(timing_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"타이밍 저장: {timing_path}")

    return result


def _run_stage(name: str, cmd: list[str]) -> tuple[bool, float]:
    """COLMAP 단계를 실행하고 (성공여부, 소요시간)을 반환."""
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        elapsed = time.time() - start
        print(f"  완료: {elapsed:.1f}초")
        return True, elapsed
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start
        print(f"  실패: {name}")
        print(f"  stderr: {e.stderr[:500]}")
        return False, elapsed
    except FileNotFoundError:
        elapsed = time.time() - start
        print("  오류: colmap 명령어를 찾을 수 없습니다. COLMAP이 설치되어 있는지 확인하세요.")
        return False, elapsed


def _count_registered_images(images_txt: Path) -> int:
    """images.txt에서 등록된 이미지 수를 파싱."""
    if not images_txt.exists():
        return 0
    count = 0
    with open(images_txt) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                # images.txt는 2줄씩 한 쌍 (포즈 줄 + POINTS2D 줄)
                # 포즈 줄은 숫자로 시작
                if line[0].isdigit():
                    count += 1
    return count


def _count_points3d(points_txt: Path) -> int:
    """points3D.txt에서 3D 포인트 수를 파싱."""
    if not points_txt.exists():
        return 0
    count = 0
    with open(points_txt) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                count += 1
    return count


def _error_result(msg: str, stages: dict | None = None) -> dict:
    """에러 결과 dict 생성."""
    return {
        "success": False,
        "total_seconds": 0,
        "stages": stages or {},
        "num_images": 0,
        "num_registered": 0,
        "num_points3d": 0,
        "error": msg,
    }
