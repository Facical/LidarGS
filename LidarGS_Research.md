# LiDAR-GS: iPhone LiDAR 깊이 기반 COLMAP-free 3D Gaussian Splatting 파이프라인

> **프로젝트 코드명**: LidarGS (폴더/코드), LiDAR-GS (논문)  
> **논문 제목(안)**: "LiDAR-GS: iPhone LiDAR 깊이 정보를 활용한 COLMAP-free 3D Gaussian Splatting 초기화 및 학습 파이프라인"  
> **대상 학회**: 한국디지털콘텐츠학회 2026 하계종합학술대회 (세부 분과 3: 디지털 트윈 및 XR 콘텐츠)  
> **개최**: 2026.07.01 ~ 07.03, 오션스위츠제주호텔  
> **논문 마감**: 2026.06.07  
> **형식**: 2단 편집, 1~2 페이지  
> **최종 수정일**: 2026.04.10

---

## 1. 연구 개요 (Research Overview)

### 1.1 문제 정의

3D Gaussian Splatting(3DGS)은 NeRF 대비 실시간 렌더링이 가능한 차세대 3D 장면 표현 기법으로, XR 응용에서 큰 잠재력을 가진다. 그러나 3DGS 학습의 전처리 단계에서 COLMAP 기반 Structure-from-Motion(SfM)이 필수적이며, 이 과정이 전체 파이프라인의 주요 병목으로 작용한다:

- **시간 병목**: 수백 장의 이미지에 대해 COLMAP SfM은 수십 분~수 시간 소요
- **컴퓨팅 자원**: GPU 메모리 및 CPU 연산 부담이 큼
- **실패 가능성**: 텍스처가 적거나 반복 패턴이 많은 환경에서 SfM 실패율 높음
- **XR 워크플로우 단절**: 캡처 → COLMAP → 학습 → 뷰잉의 다단계 파이프라인이 실시간/온디바이스 활용을 제약

### 1.2 핵심 관찰 (Key Observation)

iPhone Pro 시리즈는 ARKit 6DoF 포즈 트래킹과 LiDAR 깊이 센서를 동시에 제공한다:
- **ARKit 포즈**: SLAM 기반 실시간 6DoF 카메라 포즈 (SfM 대체 가능)
- **LiDAR 깊이**: 하드웨어 기반 실측 깊이 맵 (SfM sparse point cloud 대체 가능)
- **카메라 내부 파라미터**: intrinsics 자동 제공 (COLMAP 캘리브레이션 불필요)

즉, COLMAP SfM이 제공하는 두 가지 핵심 출력(카메라 포즈 + sparse point cloud)을 **iPhone 센서 데이터로 완전히 대체**할 수 있다.

### 1.3 연구 목표

1. **iPhone ARKit 포즈 + LiDAR 깊이를 활용하여 COLMAP SfM을 완전히 생략하는 3DGS 학습 파이프라인 제안**
2. **LiDAR 깊이 기반 Gaussian 초기화가 COLMAP SfM sparse point 기반 초기화 대비 품질/속도에서 어떠한지 정량 비교**
3. **전체 end-to-end 파이프라인(캡처→학습→XR 뷰잉) 시간 및 접근성 비교**

### 1.4 신규성 (Novelty)

| 비교 축 | 기존 연구 | 본 연구 (LidarGS) |
|---------|-----------|---------------------|
| **포즈** | COLMAP SfM (수십 분) | ARKit 네이티브 포즈 (실시간) |
| **초기 포인트** | SfM sparse points 또는 **단안 깊이 추정(monocular depth estimation)** | **iPhone LiDAR 실측 깊이(hardware depth)** → 추정이 아닌 측정값 |
| **대상 환경** | LighthouseGS: 실내 파노라마 한정 | 실내 연구실 환경 (다양한 특성의 씬) |
| **뷰잉** | PC/웹 뷰어 | XR 공간 뷰잉 (Vision Pro) |

> **핵심 차별점**: 기존 COLMAP-free 연구(CF-3DGS, LighthouseGS)는 단안 깊이 **추정** 네트워크에 의존하지만, 본 연구는 LiDAR **실측** 깊이를 활용. 추정 깊이는 스케일 모호성과 오차가 있으나, LiDAR 깊이는 미터 스케일의 정확한 기하 정보를 직접 제공.

---

## 2. 관련 연구 (Related Work)

### 2.1 3D Gaussian Splatting 기초

- **3D Gaussian Splatting for Real-Time Radiance Field Rendering** (Kerbl et al., SIGGRAPH 2023)
  - 3D Gaussian primitives를 사용한 명시적 장면 표현
  - 차별화 가능한 타일 기반 래스터라이저로 실시간 렌더링 달성
  - 입력 요구사항: SfM으로부터의 sparse point cloud + 카메라 포즈 (COLMAP 포맷)

### 2.2 COLMAP-free 3DGS 연구

| 논문 | 연도/학회 | 핵심 기법 | 한계 (본 연구와의 차이) |
|------|----------|----------|----------------------|
| **CF-3DGS** (Fu, Liu, Kulkarni, Kautz, Efros, Wang) | CVPR 2024 | 단안 깊이 + 순차적 포즈-장면 동시 최적화. 인접 프레임 쌍에서 시작하여 점진적으로 확장 | 포즈가 이미 있으면 불필요한 재추정, 학습 시간 증가, 루프 클로저 미지원 |
| **InstantSplat** (Fan et al.) | 2024 | DUSt3R(학습 기반 스테레오) → 초기 포인트 클라우드 + 포즈 → 3DGS 학습 | 학습 기반 대안이나 디바이스 네이티브 포즈 미활용 |
| **SplaTAM** (Keetha et al.) | CVPR 2024 | RGBD + 실시간 트래킹 → Dense 3DGS SLAM | 실시간 SLAM 기반, 사전 포즈 활용과는 다른 접근 |
| **MonoGS / Gaussian-SLAM** (Matsuki et al.) | CVPR 2024 | Photometric SLAM + 3D Gaussians | 실시간 SLAM 기반 |
| **LighthouseGS** (Huang et al.) | 2025 | 아이폰 ARKit 포즈 + 단안 깊이 → plane scaffold assembly | 실내 파노라마 한정, HMD 미고려. *주의: 학회 제출 시점에 최신 상태 재확인 필요* |

> **Note**: LighthouseGS, PCR-GS, TrackGS는 2025년 이후 프리프린트로, 정확한 내용은 arxiv.org에서 재확인 필요

### 2.3 디바이스 네이티브 포즈 활용

- **ARKitScenes** (Apple, 2021): iPad에서 ARKit 포즈 + LiDAR 깊이로 캡처한 대규모 데이터셋. 다수의 논문에서 ARKit 포즈를 직접 3DGS/NeRF 입력으로 사용한 선례가 있음. (https://github.com/apple/ARKitScenes)
- **Record3D** (https://record3d.app/): iOS에서 RGBD + ARKit 포즈를 캡처하여 Nerfstudio 호환 포맷으로 내보내는 앱. 커뮤니티에서 ARKit→3DGS 파이프라인의 사실상 표준 도구
- **스마트폰 ARKit/ARCore 기반 3D 재구성**: 다수의 연구에서 스마트폰 SLAM 포즈를 NeRF/3DGS 입력으로 활용
- **HMD 기반 캡처**: Quest 3, Vision Pro, HoloLens 2 등 HMD의 트래킹을 3DGS에 활용한 연구는 극히 제한적
  - HoloLens 2 Research Mode: RGB + depth + 6DoF head tracking 동기 제공 → NeRF 학습 사례 존재 (ISMAR, IEEE VR 워크샵)
  - Quest 3 패스스루 카메라: 실험적 API로 접근 가능, 커뮤니티 프로젝트 존재
- **Vision Pro 특이사항**: visionOS의 ARKit 프레임워크는 iOS ARKit과 유사하나, HMD 폼팩터로 인한 트래킹 특성이 상이 (헤드 마운트 안정성, 스테레오 패스스루 카메라, 더 많은 센서)

### 2.4 Metal 기반 3DGS 렌더링

- **MetalSplatter**: Metal 기반 3DGS 렌더러, macOS/visionOS 대상, .ply/.splat 파일 렌더링
- **GaussianSplatting-Metal** (scimake): Metal Compute Shader 구현, macOS → visionOS 포팅 가능
- 다수의 커뮤니티 프로젝트 존재 (GitHub: `gaussian splatting visionOS metal` 검색)
- Luma AI, Polycam 등 상용 앱이 Vision Pro에서 Gaussian Splat 뷰잉을 시연 → 기술적 실현 가능성 확인됨
- 본 연구에서는 오픈소스를 참고하되 자체 구현 예정

---

## 3. 제안 파이프라인 (Proposed Pipeline)

### 3.1 전체 아키텍처

```
┌──────────────────────────────────────────────────────────────────┐
│                      LidarGS Pipeline                        │
│                                                                  │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌──────────┐│
│  │  Capture  │───▶│ Transform │───▶│   Train   │───▶│   View   ││
│  │ (iPhone   │    │ + Depth   │    │  (gsplat) │    │(Vision   ││
│  │  Pro)     │    │   Init    │    │           │    │ Pro/Mac) ││
│  └───────────┘    └───────────┘    └───────────┘    └──────────┘│
│   ARKit 6DoF      좌표 변환 +       SfM 완전 생략    .ply 공간   │
│   + RGB + LiDAR   LiDAR→PointCloud  포즈+포인트 주입  렌더링     │
└──────────────────────────────────────────────────────────────────┘

기존 파이프라인과의 비교:
[기존] 이미지 → COLMAP(특징추출→매칭→SfM→포즈+sparse) → 3DGS 학습 → PC 뷰잉
[제안] iPhone 캡처(RGB+포즈+깊이) → 좌표변환+깊이초기화 → 3DGS 학습 → XR 뷰잉
```

### 3.2 Stage 1: 캡처 (Capture)

**캡처 디바이스**: iPhone Pro (LiDAR 탑재)

> iPhone을 캡처 디바이스로 채택한 이유: (1) ARKit API로 포즈/RGB/깊이 모두 자유 접근 가능 (2) LiDAR Pro 모델 보급률이 높아 재현성 우수 (3) Vision Pro 카메라 접근은 Enterprise API(Organization 계정 필수)로 제한되어 범용 연구에 부적합

#### iPhone ARKit 캡처 데이터

| 데이터 | 소스 | 포맷 |
|--------|------|------|
| RGB 프레임 | ARFrame.capturedImage | CVPixelBuffer → JPEG/PNG |
| 카메라 포즈 (6DoF) | ARFrame.camera.transform | simd_float4x4 (camera-to-world) |
| 카메라 내부 파라미터 | ARFrame.camera.intrinsics | simd_float3x3 (fx, fy, cx, cy) |
| 타임스탬프 | ARFrame.timestamp | TimeInterval |
| 깊이 맵 | ARFrame.sceneDepth | 32-bit float (LiDAR) |
| 이미지 해상도 | ARFrame.camera.imageResolution | CGSize |

#### 구현 방식 (Swift/ARKit, iPhone)

```swift
// 핵심 데이터 기록 구조
struct CapturedFrame: Codable {
    let timestamp: TimeInterval
    let imagePath: String                   // 저장된 이미지 파일 경로
    let transform: [[Float]]               // 4x4 camera-to-world (row-major로 변환하여 저장)
    let intrinsics: [[Float]]              // 3x3 (fx, fy, cx, cy)
    let imageWidth: Int
    let imageHeight: Int
}

// ARSession delegate에서 프레임 기록
func session(_ session: ARSession, didUpdate frame: ARFrame) {
    let captured = CapturedFrame(
        timestamp: frame.timestamp,
        imagePath: saveImage(frame.capturedImage, index: frameCount),
        transform: frame.camera.transform.toRowMajorArray(),  // column→row major 변환
        intrinsics: frame.camera.intrinsics.toArray(),
        imageWidth: Int(frame.camera.imageResolution.width),
        imageHeight: Int(frame.camera.imageResolution.height)
    )
    frameBuffer.append(captured)
}
```

**캡처 프로토콜**:
- 씬 주위를 천천히 이동하며 캡처 (보행 속도 이하)
- 30fps 중 1~2fps 샘플링 (과도한 중복 방지)
- 씬당 100~300 프레임 목표
- 캡처 시작/종료 시 정적 자세 유지 (트래킹 안정화)

### 3.3 Stage 2: 좌표 변환 (Coordinate Transform)

**문제**: ARKit과 COLMAP/3DGS의 좌표계 불일치

| | ARKit (OpenGL 계열) | COLMAP (OpenCV 계열) | gsplat / Nerfstudio |
|---|-------|---------------------|---------------------|
| 좌표계 | 오른손 | 오른손 | 오른손 |
| 카메라 X | 오른쪽 | 오른쪽 | 오른쪽 |
| 카메라 Y | **위** | **아래** | 위 (OpenGL) |
| 카메라 Z | **뒤쪽** (-Z = forward) | **앞쪽** (+Z = forward) | 뒤쪽 (-Z) |
| 변환 행렬 | camera-to-world | world-to-camera (quat+tvec) | world-to-camera (viewmat 4x4) |
| 행렬 저장 | column-major (simd) | row-major | row-major (PyTorch) |
| 단위 | 미터 | 스케일 무관 | 미터 |

**변환 경로별 코드**:

```python
import numpy as np
from scipy.spatial.transform import Rotation

# ============================================================
# 경로 1: ARKit → COLMAP (images.txt 포맷)
# ============================================================
def arkit_to_colmap(arkit_c2w: np.ndarray) -> tuple:
    """
    ARKit camera-to-world(OpenGL) → COLMAP world-to-camera(OpenCV)
    
    ARKit: camera.transform = camera-to-world, OpenGL 좌표계
    COLMAP: images.txt = world-to-camera, OpenCV 좌표계 (Y-down, Z-forward)
    """
    # Step 1: OpenGL → OpenCV 좌표계 변환 (Y, Z 축 반전)
    flip_yz = np.diag([1, -1, -1, 1]).astype(np.float64)
    c2w_opencv = arkit_c2w @ flip_yz
    
    # Step 2: camera-to-world → world-to-camera (역행렬)
    w2c = np.linalg.inv(c2w_opencv)
    
    R = w2c[:3, :3]
    t = w2c[:3, 3]
    
    # Step 3: Rotation matrix → quaternion (COLMAP: qw, qx, qy, qz)
    r = Rotation.from_matrix(R)
    quat = r.as_quat()  # scipy: [qx, qy, qz, qw]
    quat_colmap = np.array([quat[3], quat[0], quat[1], quat[2]])  # → [qw, qx, qy, qz]
    
    return quat_colmap, t

# ============================================================
# 경로 2: ARKit → gsplat viewmat (직접 주입, COLMAP 파일 불필요)
# ============================================================
def arkit_to_gsplat_viewmat(arkit_c2w: np.ndarray) -> np.ndarray:
    """
    ARKit camera-to-world → gsplat world-to-camera (OpenGL 유지)
    gsplat은 OpenGL 좌표계를 사용하므로 축 변환 불필요, 역행렬만 필요
    """
    w2c = np.linalg.inv(arkit_c2w)
    return w2c  # 4x4 → torch.FloatTensor로 변환하여 gsplat에 전달

# ============================================================
# 경로 3: ARKit → Nerfstudio transforms.json (가장 간단)
# ============================================================
def arkit_to_nerfstudio(arkit_c2w: np.ndarray) -> np.ndarray:
    """
    ARKit과 Nerfstudio 모두 OpenGL 좌표계의 camera-to-world 사용
    → 축 변환 불필요, 행렬 레이아웃(column→row major)만 확인
    
    주의: Swift simd_float4x4는 column-major → numpy row-major로 전치 필요
    (캡처 앱에서 row-major로 변환하여 저장하면 여기서는 그대로 사용)
    """
    return arkit_c2w  # 이미 row-major로 저장된 경우

# ============================================================
# COLMAP 텍스트 파일 생성
# ============================================================
def generate_colmap_files(frames: list, output_dir: str):
    """
    캡처된 프레임 → COLMAP 텍스트 포맷 생성
    """
    import os
    os.makedirs(os.path.join(output_dir, "sparse", "0"), exist_ok=True)
    
    # cameras.txt
    with open(os.path.join(output_dir, "sparse", "0", "cameras.txt"), "w") as f:
        f.write("# Camera list with one line of data per camera:\n")
        f.write("# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
        frame0 = frames[0]
        fx, fy = frame0["intrinsics"][0][0], frame0["intrinsics"][1][1]
        cx, cy = frame0["intrinsics"][0][2], frame0["intrinsics"][1][2]
        w, h = frame0["imageWidth"], frame0["imageHeight"]
        f.write(f"1 PINHOLE {w} {h} {fx} {fy} {cx} {cy}\n")
    
    # images.txt
    with open(os.path.join(output_dir, "sparse", "0", "images.txt"), "w") as f:
        f.write("# Image list with two lines of data per image:\n")
        f.write("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        for i, frame in enumerate(frames):
            c2w = np.array(frame["transform"])
            quat, t = arkit_to_colmap(c2w)
            name = os.path.basename(frame["imagePath"])
            f.write(f"{i+1} {quat[0]} {quat[1]} {quat[2]} {quat[3]} "
                    f"{t[0]} {t[1]} {t[2]} 1 {name}\n")
            f.write("\n")  # 빈 줄 (2D points 없음)
    
    # points3D.txt (빈 파일)
    with open(os.path.join(output_dir, "sparse", "0", "points3D.txt"), "w") as f:
        f.write("# 3D point list (empty — no SfM, using depth-based or random init)\n")
```

**핵심 함정 (Pitfalls)**:

| 함정 | 설명 | 해결 |
|------|------|------|
| Column-major 전치 | Swift `simd_float4x4`는 column-major, numpy는 row-major | 캡처 앱에서 저장 시 row-major로 변환 |
| Y/Z 축 반전 누락 | ARKit(OpenGL) → COLMAP(OpenCV) 변환 시 `diag([1,-1,-1,1])` 필수 | gsplat 직접 주입 시에는 불필요 (둘 다 OpenGL) |
| c2w vs w2c 혼동 | ARKit은 c2w, COLMAP images.txt는 w2c | 역행렬 `np.linalg.inv()` 필수 |
| 이미지 방향 | ARKit이 landscape-left로 반환할 수 있음 | UIInterfaceOrientation 확인, intrinsics 조정 |
| Quaternion 순서 | scipy: [qx,qy,qz,qw], COLMAP: [qw,qx,qy,qz] | 순서 변환 주의 |

**검증 방법**: 좌표 변환이 올바른지 시각적으로 확인하는 것이 필수
```python
# Open3D로 카메라 포즈 + 포인트 클라우드 시각화
import open3d as o3d

def visualize_cameras(frames, point_cloud=None):
    """변환된 카메라 포즈를 3D로 시각화하여 정합성 확인"""
    geometries = []
    for frame in frames:
        # 카메라 frustum을 wireframe으로 표시
        cam = o3d.geometry.LineSet.create_camera_visualization(
            frame["imageWidth"], frame["imageHeight"],
            np.array(frame["intrinsics"]),
            np.linalg.inv(np.array(frame["transform"])),  # w2c
            scale=0.1
        )
        geometries.append(cam)
    if point_cloud is not None:
        geometries.append(point_cloud)
    o3d.visualization.draw_geometries(geometries)
```

### 3.4 Stage 3: 3DGS 학습 (Training)

**프레임워크**: gsplat (https://github.com/nerfstudio-project/gsplat)

**gsplat 선택 이유**:
- 원본 3DGS repo는 COLMAP 포맷에 강하게 결합 → 커스텀 포즈 주입이 번거로움
- gsplat은 래스터라이저 수준에서 COLMAP 의존성 없음 — 카메라 파라미터를 PyTorch 텐서로 직접 전달
- 핵심 함수 시그니처: `rasterize_gaussians(means3d, quats, scales, opacities, colors, viewmats, Ks, width, height, ...)`
- nerfstudio의 `DataParser` 추상화를 통해 커스텀 데이터 로더 작성 가능

**gsplat 포즈 입력 방식** (2가지 경로):

```python
# 경로 A: gsplat 직접 사용 (저수준, 유연)
import torch
from gsplat import rasterization

# ARKit 포즈 → viewmat (world-to-camera) 변환
viewmats = torch.tensor([arkit_to_gsplat_viewmat(f["transform"]) for f in frames])  # [N, 4, 4]
Ks = torch.tensor([f["intrinsics"] for f in frames])  # [N, 3, 3]

# rasterization 호출 — COLMAP 파일 불필요
rendered, alpha, info = rasterization(
    means=gaussians.means,      # [M, 3]
    quats=gaussians.quats,      # [M, 4]
    scales=gaussians.scales,    # [M, 3]
    opacities=gaussians.opacities,
    colors=gaussians.colors,
    viewmats=viewmats,          # ← ARKit 포즈 직접 주입
    Ks=Ks,                      # ← ARKit intrinsics 직접 주입
    width=width, height=height,
)
```

```python
# 경로 B: nerfstudio 프레임워크 사용 (고수준, 편리)
# 커스텀 DataParser를 만들어 ARKit JSON 데이터를 로드
# nerfstudio는 transforms.json (Instant-NGP 포맷)을 기본 지원
# ARKit c2w는 Nerfstudio와 동일 좌표계이므로 거의 직접 사용 가능
```

**학습 설정**:
```
- Gaussian 초기화: Random 또는 Depth-based (LiDAR 깊이맵 활용)
- Iterations: 30,000 (기본값)
- Learning rate: 기본 gsplat 설정 유지
- Densification: 기본 설정
```

**SfM 없는 학습의 초기화 전략**:

| 전략 | 방법 | 장점 | 단점 |
|------|------|------|------|
| **Random Init** | 씬 바운딩 박스 내 랜덤 포인트 | 구현 간단 | 수렴 느림, 품질 하락 |
| **Depth-based Init (권장)** | LiDAR 깊이 맵 → 3D 역투영 → 병합 | 빠른 수렴, 높은 품질 | 깊이 맵 처리 코드 필요 |
| **Uniform Grid Init** | 씬 공간 균등 분할 | 구현 간단 | 빈 공간에도 Gaussian 배치 |

```python
# Depth-based Init 구현 개요
def depth_to_pointcloud(depth_map, intrinsics, c2w, subsample=4):
    """LiDAR 깊이 맵 → 3D 포인트 클라우드"""
    h, w = depth_map.shape
    u, v = np.meshgrid(np.arange(0, w, subsample), np.arange(0, h, subsample))
    z = depth_map[v, u]
    valid = z > 0
    
    fx, fy = intrinsics[0, 0], intrinsics[1, 1]
    cx, cy = intrinsics[0, 2], intrinsics[1, 2]
    
    x = (u[valid] - cx) * z[valid] / fx
    y = (v[valid] - cy) * z[valid] / fy
    points_cam = np.stack([x, y, z[valid]], axis=-1)  # [N, 3]
    
    # Camera → World
    R = c2w[:3, :3]
    t = c2w[:3, 3]
    points_world = (R @ points_cam.T).T + t
    return points_world

# 모든 프레임의 깊이 맵을 병합하여 초기 포인트 클라우드 생성
all_points = np.concatenate([
    depth_to_pointcloud(f["depth"], f["intrinsics"], f["transform"])
    for f in frames
])
# → voxel downsampling으로 중복 제거 후 Gaussian 초기 위치로 사용
```

### 3.5 Stage 4: 뷰잉 (Viewing)

**1차 뷰잉 (평가용)**: macOS/웹 기반 3DGS 뷰어로 렌더링 품질 정량 평가 (PSNR, SSIM, LPIPS)

**2차 뷰잉 (XR 데모, 선택)**: Vision Pro visionOS 앱으로 공간 뷰잉
- 학습된 `.ply` 파일 로드 → Metal 기반 Gaussian 렌더링
- 논문의 핵심 기여는 아니지만, 발표 시 데모로 활용 가능
- 오픈소스 Metal 렌더러(MetalSplatter 등) 참고하여 구현

---

## 4. 실험 설계 (Experiment Design)

### 4.1 실험 환경

| 항목 | 사양 |
|------|------|
| 캡처 디바이스 | iPhone 15/16 Pro (LiDAR) |
| 학습 머신 | Mac Studio (Apple Silicon) 또는 NVIDIA GPU 장착 워크스테이션 |
| 학습 프레임워크 | gsplat (latest) |
| 비교 베이스라인 | COLMAP SfM + 원본 3DGS |
| 뷰잉/평가 | macOS 3DGS 뷰어 (정량 평가) + Vision Pro (데모, 선택) |

### 4.2 실험 씬 (Scenes)

최소 3개 씬으로 다양한 환경 커버:

| 씬 ID | 환경 | 특성 | 난이도 |
|--------|------|------|--------|
| S1 | 연구실 책상 위 오브젝트 | 텍스처 풍부, 소규모, 근거리 | 쉬움 |
| S2 | 연구실 전체 (데스크/장비/선반) | 중간 규모, 다양한 재질 | 중간 |
| S3 | 연구실 복도/공용 공간 | 넓은 공간, 반복 패턴(타일 바닥 등), 균일 조명 | 어려움 |

**각 씬에 대해 동일 경로로 2회 캡처**:
- (A) iPhone ARKit 캡처 → LidarGS 파이프라인
- (B) 동일 이미지 → COLMAP SfM → 원본 3DGS 파이프라인

### 4.3 평가 지표 (Evaluation Metrics)

#### 정량 평가

| 카테고리 | 지표 | 설명 |
|----------|------|------|
| **전처리 시간** | SfM 시간 (초) | COLMAP: SfM 소요 시간 / LidarGS: 좌표 변환 스크립트 소요 시간 |
| **전체 파이프라인 시간** | 캡처~학습완료 (분) | 캡처 시간 + 전처리 + 학습 시간 총합 |
| **렌더링 품질** | PSNR (dB) | Peak Signal-to-Noise Ratio |
| | SSIM | Structural Similarity Index |
| | LPIPS | Learned Perceptual Image Patch Similarity |
| **장면 복원** | Gaussian 개수 | 최종 학습된 Gaussian primitive 수 |
| | 모델 크기 (MB) | .ply 파일 크기 |

#### 정성 평가
- 렌더링 결과 비교 이미지 (동일 시점에서의 렌더링)
- 아티팩트 분석 (floater, 흐릿함, 구조 붕괴 등)

### 4.4 비교 실험 구성

```
Experiment Matrix (3-way 비교):
──────────────────────────────────────────────────────────────────────────
                    방법 A (Baseline)    방법 B (LidarGS)  방법 C (Ablation)
──────────────────────────────────────────────────────────────────────────
포즈 소스            COLMAP SfM          ARKit 네이티브 포즈    ARKit 네이티브 포즈
초기 포인트          COLMAP sparse       LiDAR depth-based     Random init
전처리 시간          수십 분              수 초                  수 초
학습 프레임워크       gsplat              gsplat                gsplat
학습 설정            동일                 동일                   동일
──────────────────────────────────────────────────────────────────────────
```

> **방법 C (Random init)**를 추가하여 "LiDAR 깊이 초기화의 기여"를 분리 측정. B vs C 비교로 Depth-based init의 효과를 ablation.

### 4.5 추가 분석 (선택)

- **포즈 정확도 비교**: ARKit 포즈 vs COLMAP 포즈의 직접 비교 (ATE, RPE)
- **수렴 속도 비교**: 학습 iteration별 PSNR 곡선 (A vs B vs C)
- **LiDAR 깊이 밀도 ablation**: 깊이 맵 서브샘플링 비율에 따른 초기화 품질 변화

---

## 5. 예상 결과 및 가설 (Expected Results)

### 가설

1. **전처리 시간 대폭 단축**: COLMAP SfM(수십 분) → 좌표 변환+깊이 초기화(수 초~수 분) → **10x~100x 속도 향상**
2. **LiDAR 초기화가 COLMAP sparse보다 빠른 수렴**: 더 밀집된 초기 포인트로 학습 초기 단계에서 빠르게 수렴
3. **LiDAR 초기화가 Random init보다 품질 우수**: 정확한 기하 정보로 시작하므로 PSNR/SSIM 최종 품질 개선
4. **텍스처리스 환경에서 우위**: COLMAP SfM이 실패하는 저텍스처 씬에서 ARKit 포즈 + LiDAR 깊이는 안정적으로 동작
5. **LiDAR 실측 깊이 > 단안 깊이 추정**: 기존 연구(CF-3DGS)의 monocular depth 대비 스케일 정확도와 기하 정밀도에서 우위

### 리스크 요인

| 리스크 | 영향도 | 대응 방안 |
|--------|--------|----------|
| ARKit 포즈 드리프트 | 중 | 루프 클로저 포함 캡처 경로 설계 |
| 좌표 변환 오류 | **높음** | 시각적 검증 툴 제작 (포즈를 3D로 시각화) |
| LiDAR 깊이 노이즈/범위 한계 | 중 | 반사면/투명체 제외 필터링, 5m 이내 씬 선택 |
| gsplat이 커스텀 init을 잘 처리 못함 | 중 | nerfstudio DataParser 커스텀 작성 또는 gsplat 저수준 API 사용 |
| 학습 품질이 COLMAP 대비 크게 떨어짐 | 중 | 포즈 refinement 후처리 추가 검토 |

---

## 6. 논문 구성 (Paper Structure)

> 2단 편집, 1~2 페이지 기준

### 페이지 1

| 섹션 | 분량 | 내용 |
|------|------|------|
| **제목 + 저자** | 상단 | "iPhone LiDAR 깊이 정보를 활용한 COLMAP-free 3D Gaussian Splatting 초기화 및 학습 파이프라인" |
| **Abstract** | 5줄 | 문제(COLMAP 병목)-제안(ARKit 포즈 + LiDAR 깊이 초기화)-실험(3-way 비교)-결과 요약 |
| **1. 서론** | ¼p | 3DGS의 XR 응용 가치 → COLMAP 병목(포즈+초기화) → iPhone 센서로 둘 다 대체 가능 → 제안 |
| **2. 관련 연구** | ¼p | CF-3DGS(단안 깊이 추정), LighthouseGS 언급 + "LiDAR 실측 깊이 기반 초기화는 미탐색" 갭 명시 |
| **3. 제안 방법** | ½p + Fig.1 | 파이프라인 다이어그램 + LiDAR depth-based init 핵심 설명 |

### 페이지 2

| 섹션 | 분량 | 내용 |
|------|------|------|
| **4. 실험** | ½p + Table 1 + Fig.2 | 씬 설명, 3-way 비교 결과표 (전처리 시간, PSNR, SSIM, 수렴 속도), 렌더링 비교 이미지 |
| **5. 논의 및 결론** | ¼p | LiDAR 초기화의 효과 분석, 한계(LiDAR 범위, 포즈 드리프트), 향후 과제(HMD 네이티브 캡처, 실외 확장) |
| **참고문헌** | ¼p | 8~12개 |

### 핵심 그림/표

- **Fig. 1**: LidarGS 파이프라인 다이어그램 (iPhone 캡처 → 변환+깊이초기화 → 학습)
- **Fig. 2**: 렌더링 비교 (방법 A: COLMAP vs B: LiDAR init vs C: Random init, 동일 시점 2~3개)
- **Table 1**: 3-way 정량 비교 (전처리 시간, PSNR, SSIM, Gaussian 수, 수렴 iteration)

---

## 7. 개발 일정 (Timeline)

> 2026.04.10 ~ 2026.06.07 (약 8주)

| 주차 | 기간 | 작업 내용 | 마일스톤 |
|------|------|----------|----------|
| **1주차** | 04/10-04/16 | ARKit 캡처 앱 개발 (iPhone) — RGB + 포즈 + intrinsics + **LiDAR 깊이** 동기 기록 | 캡처 앱 v1 완성 |
| **2주차** | 04/17-04/23 | 좌표 변환 스크립트 + gsplat 환경 세팅, 작은 씬 1개로 end-to-end 테스트 | 첫 end-to-end 실행 |
| **3주차** | 04/24-04/30 | **좌표 변환 디버깅** (가장 큰 리스크) + 포즈 시각화 검증 + **Depth-based init 구현** | 좌표 변환 확인 + LiDAR 포인트 클라우드 생성 |
| **4주차** | 05/01-05/07 | 3-way 비교 파이프라인 세팅 (COLMAP baseline + Random init + LiDAR init) | 3가지 방법 모두 실행 가능 |
| **5주차** | 05/08-05/14 | 실험 씬 3개 캡처 + 3-way 비교 실험 수행 | 전체 실험 데이터 확보 |
| **6주차** | 05/15-05/21 | 정량 평가 (PSNR/SSIM/LPIPS) + 수렴 곡선 분석 | 실험 결과 완성 |
| **7주차** | 05/22-05/28 | 논문 초안 작성 + 그림/표 제작 | 초안 완성 |
| **8주차** | 05/29-06/07 | 퇴고 + 제출 | **06/07 제출** |

### 크리티컬 패스
```
캡처 앱+깊이(1주) → 좌표 변환+깊이초기화(2~3주) → 3-way 비교(4~5주) → 평가(6주) → 논문(7~8주)
                          ↑
                    최대 리스크 구간
```

---

## 8. 기술 스택 및 개발 환경

| 항목 | 기술 |
|------|------|
| 캡처 앱 | Swift, ARKit, iOS |
| 좌표 변환 + 깊이 초기화 | Python, NumPy, SciPy, Open3D |
| 3DGS 학습 | gsplat (PyTorch), CUDA |
| 비교 베이스라인 | COLMAP + 원본 3DGS |
| 포즈 시각화 (디버깅) | Open3D 또는 Matplotlib 3D |
| 평가 도구 | torchmetrics (PSNR, SSIM), LPIPS |

---

## 9. 참고 문헌 (References)

1. Kerbl, B. et al. "3D Gaussian Splatting for Real-Time Radiance Field Rendering." *ACM Trans. Graphics (SIGGRAPH)*, 2023.
2. Fu, Y., Liu, S., Kulkarni, A., Kautz, J., Efros, A.A., & Wang, X. "COLMAP-Free 3D Gaussian Splatting." *CVPR*, 2024. (arXiv:2312.07504)
3. Fan, Z. et al. "InstantSplat: Unbounded Sparse-view Pose-free Gaussian Splatting in 40 Seconds." *arXiv*, 2024. (arXiv:2403.20309)
4. Keetha, N. et al. "SplaTAM: Splat, Track & Map 3D Gaussians for Dense RGB-D SLAM." *CVPR*, 2024.
5. Matsuki, H. et al. "Gaussian Splatting SLAM." *CVPR*, 2024.
6. Ye, V. et al. "gsplat: An Open-Source Library for Gaussian Splatting." *arXiv*, 2024.
7. Schönberger, J. L. & Frahm, J.-M. "Structure-from-Motion Revisited." *CVPR*, 2016. (COLMAP)
8. Mildenhall, B. et al. "NeRF: Representing Scenes as Neural Radiance Fields for View Synthesis." *ECCV*, 2020.
9. Baruch, G. et al. "ARKitScenes — A Diverse Real-World Dataset for 3D Indoor Scene Understanding Using Mobile RGB-D Data." *NeurIPS Datasets and Benchmarks*, 2021.
10. Apple Inc. "ARKit Documentation — ARFrame, ARCamera, ARSession." *Apple Developer*, 2024.
11. Apple Inc. "ARKit — SceneDepth, LiDAR Sensor." *Apple Developer*, 2024.

> **Note**: LighthouseGS, PCR-GS, TrackGS 등 2025년 이후 프리프린트는 논문 제출 시점에 arxiv.org에서 최신 상태를 재확인하여 추가할 것

---

## 10. 용어 정리 (Glossary)

| 용어 | 설명 |
|------|------|
| 3DGS | 3D Gaussian Splatting — 3D Gaussian 프리미티브 기반 실시간 장면 표현 |
| SfM | Structure-from-Motion — 다시점 이미지에서 3D 구조와 카메라 포즈를 복원 |
| COLMAP | 대표적인 SfM/MVS 오픈소스 파이프라인 |
| 6DoF | 6 Degrees of Freedom — 3D 위치(x,y,z) + 3D 회전(roll, pitch, yaw) |
| ARKit | Apple의 증강현실 프레임워크 (iOS, visionOS) |
| gsplat | nerfstudio 기반 3DGS 학습 라이브러리 |
| PSNR | Peak Signal-to-Noise Ratio — 렌더링 품질 정량 지표 |
| SSIM | Structural Similarity Index — 구조적 유사도 지표 |
| LPIPS | Learned Perceptual Image Patch Similarity — 지각적 유사도 지표 |
| HMD | Head-Mounted Display — 머리 착용형 디스플레이 |

---

## 부록 A: ARKit 좌표계 상세

```
ARKit World Coordinate System:
       Y (Up)
       |
       |
       +------- X (Right)
      /
     /
    Z (Toward viewer, out of screen)

카메라 기준:
- +X: 오른쪽
- +Y: 위쪽
- -Z: 카메라가 바라보는 방향 (forward)

camera.transform (simd_float4x4):
- camera-to-world 변환 행렬
- column-major 저장 (Swift simd 기본)
- 4열이 카메라의 월드 좌표 위치 (translation)
```

## 부록 B: COLMAP 포맷 상세

```
cameras.txt:
# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
1 PINHOLE 1920 1080 fx fy cx cy

images.txt:
# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
# (world-to-camera 변환)
# 빈 줄 (2D points — 우리는 비워둠)

points3D.txt:
# 비어있음 (SfM 없이 시작)
# 또는 depth-based init 사용 시 LiDAR 포인트 기록
```
