# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**LidarGS** (paper name: LiDAR-GS) is a research project building a COLMAP-free 3D Gaussian Splatting pipeline using iPhone LiDAR depth and ARKit 6DoF poses. The core idea: replace COLMAP SfM (which takes minutes-to-hours) with iPhone sensor data (real-time poses + measured depth), achieving 10-100x speedup in the preprocessing stage.

- **Target**: 한국디지털콘텐츠학회 2026 하계종합학술대회 (July 1-3, 2026)
- **Paper deadline**: June 7, 2026
- **Format**: 1-2 page, 2-column
- **Primary documentation**: `LidarGS_Research.md` — the comprehensive research plan with code snippets, coordinate math, experiment design, and timeline
- **Implementation Guide**: `LidarGS_Implementation_Guide.md` — 파일별 상세 구현 설계, API 시그니처, 데이터 흐름, 디버깅 전략

## Commands

### Environment Setup
```bash
chmod +x setup_env.sh
./setup_env.sh          # conda env 'lidargs' 생성, PyTorch+CUDA 12.1, gsplat 설치
conda activate lidargs
```

### Tests
```bash
cd python
pytest tests/                        # 전체 테스트
pytest tests/test_transforms.py      # 좌표 변환 테스트
pytest tests/test_backproject.py     # 깊이 역투영 테스트
pytest tests/ -v                     # verbose 출력
```

### Pipeline Execution
```bash
cd python
# Stage 2: iOS 캡처 데이터 처리 (주요 스크립트)
python scripts/01_process_capture.py --scene scene_desk
python scripts/01_process_capture.py --scene scene_desk --visualize
python scripts/01_process_capture.py --scene scene_desk --run_colmap

# 전체 옵션
python scripts/01_process_capture.py \
  --scene scene_desk \
  --raw_dir data/raw \
  --output_dir data/processed \
  --voxel_size 0.01 \
  --min_depth 0.1 \
  --max_depth 5.0 \
  --subsample 1 \
  --visualize \
  --run_colmap \
  --matcher_type exhaustive   # or sequential
```

### COLMAP (Method A Baseline)
```bash
bash python/scripts/run_colmap.sh data/processed/scene_desk/method_a_colmap
bash python/scripts/run_colmap.sh <scene_path> --no-gpu       # CPU 전용
bash python/scripts/run_colmap.sh <scene_path> --sequential   # Sequential matcher
```

## Pipeline Architecture (4 stages)

1. **Capture (iPhone ARKit/Swift)**: RGB 프레임, 6DoF 카메라 포즈(`simd_float4x4` c2w), intrinsics(`simd_float3x3`), LiDAR 깊이맵(32-bit float) 기록. 30fps에서 1-2fps 샘플링, 씬당 100-300 프레임 목표. **미구현 — iOS Swift 앱 제작 필요.**
   - ARKit 비디오 해상도: **1080p(1920×1080)** 또는 **4K(3840×2160)** 선택 가능. 4K는 렌더링 품질↑, 학습 속도↓. LiDAR 깊이는 영상 해상도와 무관하게 항상 **256×192**.
   - Python 파이프라인은 해상도를 metadata.json에서 동적으로 읽으므로 어느 쪽이든 코드 변경 불필요.

2. **Transform + Depth Init (Python)**: ARKit 좌표계를 타깃 프레임워크 포맷으로 변환, LiDAR 깊이맵에서 초기 포인트 클라우드 생성. `01_process_capture.py`가 진입점.

3. **Train (gsplat/PyTorch)**: 깊이 초기화된 Gaussian으로 3DGS 학습. 두 가지 통합 경로: gsplat 저수준 API (직접 viewmat 주입) 또는 nerfstudio DataParser.

4. **View**: 정량 평가(PSNR, SSIM, LPIPS)용 macOS/웹 뷰어. Vision Pro XR 뷰어(Metal 기반 Gaussian 렌더링) 선택사항.

## Python Package Structure (`python/lidargs/`)

| 모듈 | 역할 |
|------|------|
| `io/load_capture.py` | iOS 캡처 데이터 로드 (`FrameData`, `CaptureData` 데이터클래스) |
| `io/export_colmap.py` | COLMAP text 포맷 (cameras.txt, images.txt, points3D.txt) 내보내기 |
| `io/export_nerfstudio.py` | transforms.json 내보내기 |
| `io/export_ply.py` | 포인트 클라우드 PLY 내보내기 |
| `io/run_colmap.py` | COLMAP CLI subprocess 래퍼, 타이밍 반환 |
| `transform/arkit_to_colmap.py` | ARKit c2w → COLMAP w2c + quaternion |
| `transform/arkit_to_gsplat.py` | ARKit c2w → gsplat viewmat (단순 역행렬) |
| `transform/arkit_to_nerfstudio.py` | ARKit c2w → Nerfstudio (identity 변환) |
| `transform/intrinsics.py` | 해상도별 intrinsics 스케일링 (1920×1080 ↔ 256×192) |
| `depth/backproject.py` | 깊이맵 → 월드 좌표 포인트 클라우드 |
| `depth/merge_clouds.py` | 멀티프레임 병합 + voxel 다운샘플 + 통계적 이상치 제거 |
| `depth/filter.py` | 깊이 범위 필터링 |
| `viz/visualize_poses.py` | Open3D 카메라 프러스텀 + 포인트 클라우드 시각화 |

### iOS 캡처 데이터 포맷

```
data/raw/scene_desk/
├── metadata.json          # 씬 이름, 기기 모델, 프레임 목록
├── images/frame_NNNNNN.jpg  # RGB 1920×1080
└── depths/frame_NNNNNN.bin  # float32 binary 256×192
```

metadata.json의 `transform` 필드: row-major 4×4 c2w 행렬 (OpenGL 좌표계).

### 처리 결과 출력 구조

```
data/processed/scene_desk/
├── method_a_colmap/        # Baseline: COLMAP SfM 포즈
├── method_b_lidargs/       # LidarGS: ARKit 포즈 + LiDAR 포인트 클라우드
└── method_c_random/        # Ablation: ARKit 포즈 + 랜덤 초기화
```

## Critical: Coordinate System Transformations

이 프로젝트의 가장 높은 리스크 영역. 주요 차이점:

| | ARKit (OpenGL) | COLMAP (OpenCV) | gsplat |
|---|---|---|---|
| Camera Y | Up | **Down** | Up (OpenGL) |
| Camera Z | Back (-Z forward) | **Front** (+Z forward) | Back (-Z forward) |
| Matrix type | camera-to-world | world-to-camera (quat+t) | world-to-camera (4x4) |
| Storage | column-major (simd) | row-major | row-major (PyTorch) |

세 가지 변환 경로 (구현: `lidargs/transform/`):
- **ARKit → COLMAP**: Y/Z 플립 `diag([1,-1,-1,1])`, c2w 역행렬로 w2c, quaternion 변환 `[qw,qx,qy,qz]`
- **ARKit → gsplat**: 단순 역행렬(`np.linalg.inv`) — 둘 다 OpenGL 좌표계
- **ARKit → Nerfstudio**: Identity — 둘 다 OpenGL c2w

흔한 실수: column-major/row-major 혼동, Y/Z 플립 누락, c2w/w2c 혼동, quaternion 순서(scipy `[qx,qy,qz,qw]` vs COLMAP `[qw,qx,qy,qz]`).

## Technology Stack

| Component | Tech |
|---|---|
| Capture app | Swift, ARKit, iOS (iPhone 15/16 Pro with LiDAR) |
| Coordinate transform + depth init | Python, NumPy, SciPy (`Rotation`), Open3D |
| 3DGS training | gsplat (PyTorch), CUDA |
| Baseline comparison | COLMAP + original 3DGS |
| Pose visualization/debugging | Open3D or Matplotlib 3D |
| Evaluation | torchmetrics (PSNR, SSIM), LPIPS |
| Hardware | Mac Studio (Apple Silicon) or NVIDIA GPU workstation |

## Experiment Design

3-way comparison across 3+ indoor scenes (easy/medium/hard):
- **Method A (Baseline)**: COLMAP SfM poses + sparse points → gsplat
- **Method B (LidarGS)**: ARKit poses + LiDAR depth-based init → gsplat
- **Method C (Ablation)**: ARKit poses + random init → gsplat

B vs A: 전체 파이프라인 대체 검증. B vs C: LiDAR 깊이 초기화의 기여도 분리.

## 언어

사용자는 한국어를 선호합니다. 모든 대화, 설명, 코멘트를 한국어로 작성해주세요. 코드 내 변수명과 함수명은 영어를 사용합니다. 연구 문서와 논문도 한국어로 작성되어 있습니다.
