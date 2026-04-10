# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**LidarGS** (paper name: LiDAR-GS) is a research project building a COLMAP-free 3D Gaussian Splatting pipeline using iPhone LiDAR depth and ARKit 6DoF poses. The core idea: replace COLMAP SfM (which takes minutes-to-hours) with iPhone sensor data (real-time poses + measured depth), achieving 10-100x speedup in the preprocessing stage.

- **Target**: 한국디지털콘텐츠학회 2026 하계종합학술대회 (July 1-3, 2026)
- **Paper deadline**: June 7, 2026
- **Format**: 1-2 page, 2-column
- **Primary documentation**: `LidarGS_Research.md` — the comprehensive research plan with code snippets, coordinate math, experiment design, and timeline
- **Implementation Guide**: `LidarGS_Implementation_Guide.md` — 파일별 상세 구현 설계, API 시그니처, 데이터 흐름, 디버깅 전략

## Pipeline Architecture (4 stages)

1. **Capture (iPhone ARKit/Swift)**: Record RGB frames, 6DoF camera poses (`simd_float4x4` camera-to-world), intrinsics (`simd_float3x3`), and LiDAR depth maps (32-bit float). Sample at 1-2fps from 30fps source, target 100-300 frames per scene.

2. **Transform + Depth Init (Python)**: Convert ARKit coordinate system to target framework format, generate initial point cloud from LiDAR depth maps via back-projection.

3. **Train (gsplat/PyTorch)**: 3DGS training with depth-initialized Gaussians. Two integration paths: gsplat low-level API (direct viewmat injection) or nerfstudio DataParser.

4. **View**: macOS/web viewer for quantitative evaluation (PSNR, SSIM, LPIPS). Optional Vision Pro XR viewer using Metal-based Gaussian rendering.

## Critical: Coordinate System Transformations

This is the highest-risk area of the project. Key differences:

| | ARKit (OpenGL) | COLMAP (OpenCV) | gsplat |
|---|---|---|---|
| Camera Y | Up | **Down** | Up (OpenGL) |
| Camera Z | Back (-Z forward) | **Front** (+Z forward) | Back (-Z forward) |
| Matrix type | camera-to-world | world-to-camera (quat+t) | world-to-camera (4x4) |
| Storage | column-major (simd) | row-major | row-major (PyTorch) |

Three conversion paths exist (see `LidarGS_Research.md` Section 3.3 for code):
- **ARKit -> COLMAP**: Flip Y/Z via `diag([1,-1,-1,1])`, invert to w2c, convert to quaternion `[qw,qx,qy,qz]`
- **ARKit -> gsplat**: Just invert (`np.linalg.inv`) — both use OpenGL, no axis flip needed
- **ARKit -> Nerfstudio**: Identity — both use OpenGL camera-to-world

Common pitfalls: column-major/row-major confusion, Y/Z flip omission, c2w/w2c mixup, quaternion ordering (scipy `[qx,qy,qz,qw]` vs COLMAP `[qw,qx,qy,qz]`).

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
- **Method A (Baseline)**: COLMAP SfM poses + sparse points -> gsplat
- **Method B (LidarGS)**: ARKit poses + LiDAR depth-based init -> gsplat
- **Method C (Ablation)**: ARKit poses + random init -> gsplat

B vs A tests the full pipeline replacement. B vs C isolates the LiDAR depth initialization contribution.

## 언어

사용자는 한국어를 선호합니다. 모든 대화, 설명, 코멘트를 한국어로 작성해주세요. 코드 내 변수명과 함수명은 영어를 사용합니다. 연구 문서와 논문도 한국어로 작성되어 있습니다.
