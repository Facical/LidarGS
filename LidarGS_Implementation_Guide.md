# LidarGS 상세 구현 가이드

> 이 문서는 LidarGS 프로젝트의 파일별 구현 설계, API 시그니처, 데이터 흐름, 디버깅 전략을 담고 있다.
> `CLAUDE.md`와 `LidarGS_Research.md`를 보완하며, 향후 Claude Code 세션에서 이 가이드를 참조하여 일관성 있게 구현을 진행한다.

---

## 1. 프로젝트 디렉토리 구조

```
LidarGS/
├── CLAUDE.md
├── LidarGS_Research.md
├── LidarGS_Implementation_Guide.md      # 이 문서
├── .gitignore
│
├── ios/                                  # Stage 1: iPhone 캡처 앱
│   └── LidarCapture/
│       ├── LidarCapture.xcodeproj/
│       └── LidarCapture/
│           ├── LidarCaptureApp.swift
│           ├── ContentView.swift
│           ├── ARSessionManager.swift           # 핵심: ARSession + 프레임 캡처
│           ├── CaptureState.swift               # ObservableObject 상태 관리
│           ├── Models/
│           │   ├── CapturedFrame.swift          # Codable 프레임 데이터
│           │   └── CaptureMetadata.swift        # 세션 메타데이터
│           ├── Utilities/
│           │   ├── MatrixExtensions.swift        # simd → row-major 변환
│           │   ├── DepthUtils.swift              # CVPixelBuffer → float32 바이너리
│           │   └── ImageUtils.swift              # CVPixelBuffer → JPEG
│           └── Views/
│               ├── CaptureView.swift             # AR 카메라 프리뷰 + 컨트롤
│               ├── ReviewView.swift              # 캡처 후 프레임 브라우저
│               └── ExportView.swift              # 데이터 내보내기
│
├── python/                               # Stages 2-4: Python 파이프라인
│   ├── environment.yml
│   ├── requirements.txt
│   │
│   ├── lidargs/                          # 메인 Python 패키지
│   │   ├── __init__.py
│   │   ├── io/                           # 데이터 I/O
│   │   │   ├── __init__.py
│   │   │   ├── load_capture.py           # iOS 캡처 데이터 로드
│   │   │   ├── export_colmap.py          # COLMAP 텍스트 파일 생성
│   │   │   ├── export_nerfstudio.py      # transforms.json 생성
│   │   │   └── export_ply.py             # 포인트 클라우드 .ply 내보내기
│   │   │
│   │   ├── transform/                    # 좌표 변환
│   │   │   ├── __init__.py
│   │   │   ├── arkit_to_colmap.py
│   │   │   ├── arkit_to_gsplat.py
│   │   │   ├── arkit_to_nerfstudio.py
│   │   │   └── intrinsics.py             # 해상도별 intrinsics 스케일링
│   │   │
│   │   ├── depth/                        # 깊이 처리
│   │   │   ├── __init__.py
│   │   │   ├── backproject.py            # 깊이맵 → 3D 포인트 클라우드
│   │   │   ├── merge_clouds.py           # 멀티프레임 병합 + 복셀 다운샘플
│   │   │   └── filter.py                 # 깊이 필터링 (범위, 이상치)
│   │   │
│   │   ├── train/                        # gsplat 학습
│   │   │   ├── __init__.py
│   │   │   ├── dataset.py                # Custom Dataset (COLMAP Parser 대체)
│   │   │   ├── trainer.py                # 메인 학습 루프
│   │   │   ├── config.py                 # 학습 설정 dataclass
│   │   │   ├── init_gaussians.py         # Gaussian 초기화 (LiDAR/random/SfM)
│   │   │   └── utils.py                  # knn, rgb_to_sh 등 헬퍼
│   │   │
│   │   ├── eval/                         # 평가
│   │   │   ├── __init__.py
│   │   │   ├── metrics.py                # PSNR, SSIM, LPIPS
│   │   │   ├── compare.py                # 3-way 비교 자동화
│   │   │   ├── convergence.py            # 수렴 곡선 추출 + 플롯
│   │   │   └── render.py                 # 평가용 렌더링
│   │   │
│   │   └── viz/                          # 시각화 / 디버그
│   │       ├── __init__.py
│   │       ├── visualize_poses.py        # Open3D 카메라 frustum + 포인트 클라우드
│   │       ├── visualize_depth.py        # 깊이맵 컬러화 + 오버레이
│   │       └── plot_results.py           # 논문 그래프
│   │
│   ├── scripts/                          # 실행 스크립트
│   │   ├── 01_process_capture.py         # iOS 캡처 → 처리된 데이터 + 포인트 클라우드
│   │   ├── 02_train_lidargs.py           # Method B 학습
│   │   ├── 03_train_colmap.py            # Method A 학습
│   │   ├── 04_train_random.py            # Method C 학습
│   │   ├── 05_evaluate.py               # 전체 메트릭 실행
│   │   ├── 06_generate_tables.py         # LaTeX 표 + 그래프 생성
│   │   ├── run_colmap.sh                 # COLMAP SfM 실행
│   │   └── run_all_experiments.sh        # 마스터 실험 스크립트
│   │
│   └── tests/                            # 단위 테스트
│       ├── test_transforms.py            # 좌표 변환 검증
│       ├── test_backproject.py           # 깊이 역투영 검증
│       └── test_dataset.py              # Dataset/Parser 검증
│
├── data/                                 # 데이터 (gitignore)
│   ├── raw/                              # iOS 원시 캡처
│   │   └── scene_desk/
│   │       ├── images/                   # frame_000000.jpg, ...
│   │       ├── depths/                   # frame_000000.bin, ...
│   │       └── metadata.json
│   ├── processed/                        # 학습용 처리 데이터
│   │   └── scene_desk/
│   │       ├── method_a_colmap/
│   │       │   ├── images/
│   │       │   └── sparse/0/            # cameras.txt, images.txt, points3D.txt
│   │       ├── method_b_lidargs/
│   │       │   ├── images/
│   │       │   ├── sparse/0/
│   │       │   └── points3d_lidar.ply   # LiDAR 포인트 클라우드
│   │       └── method_c_random/
│   │           ├── images/
│   │           └── sparse/0/
│   └── results/                          # 학습 결과
│       └── scene_desk/
│           └── method_b_lidargs/
│               ├── ckpts/
│               ├── stats/
│               ├── renders/
│               └── ply/
│
└── paper/                                # 논문 소스 (선택)
    ├── main.tex
    └── references.bib
```

---

## 2. Stage 1: iOS 캡처 앱 (Swift)

### 2.1 Xcode 프로젝트 설정

- **템플릿**: App (SwiftUI lifecycle)
- **Deployment Target**: iOS 17+
- **필수 프레임워크**: ARKit (자동 링크)
- **Info.plist**: `NSCameraUsageDescription` 추가
- **테스트 디바이스**: iPhone 15 Pro / 16 Pro (LiDAR 필수)
- **외부 의존성**: 없음 (순수 Apple 프레임워크)

### 2.2 데이터 모델

#### CapturedFrame.swift

```swift
struct CapturedFrame: Codable {
    let index: Int
    let timestamp: TimeInterval
    let imagePath: String           // "images/frame_000042.jpg"
    let depthPath: String           // "depths/frame_000042.bin"
    let transform: [[Float]]        // 4x4 camera-to-world, row-major
    let intrinsics: [[Float]]       // 3x3 카메라 intrinsics
    let imageWidth: Int             // 1920
    let imageHeight: Int            // 1080
    let depthWidth: Int             // 256 (LiDAR 고정)
    let depthHeight: Int            // 192 (LiDAR 고정)
}
```

#### CaptureMetadata.swift

```swift
struct CaptureMetadata: Codable {
    let deviceModel: String         // "iPhone16,1"
    let iosVersion: String
    let captureDate: String         // ISO 8601
    let sceneName: String
    let frameCount: Int
    let samplingFPS: Double
    let frames: [CapturedFrame]
}
```

### 2.3 행렬 변환 (MatrixExtensions.swift)

**핵심**: `simd_float4x4`는 column-major로 저장된다. JSON에 row-major로 내보내야 한다.

```swift
extension simd_float4x4 {
    /// column-major simd → row-major 2D 배열
    /// self.columns.0 = 첫 번째 열, self.columns.0.x = (row=0, col=0)
    /// row[r][c] = columns[c][r]
    func toRowMajorArray() -> [[Float]] {
        return (0..<4).map { r in
            (0..<4).map { c in self.columns[c][r] }
        }
    }
}

extension simd_float3x3 {
    func toArray() -> [[Float]] {
        return (0..<3).map { r in
            (0..<3).map { c in self.columns[c][r] }
        }
    }
}
```

**검증 방법**: 단위 행렬(identity)에 대해 `toRowMajorArray()`가 `[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]`을 반환하는지 확인.

### 2.4 깊이 유틸리티 (DepthUtils.swift)

```swift
func saveDepthMap(_ depthMap: CVPixelBuffer, to url: URL) throws {
    CVPixelBufferLockBaseAddress(depthMap, .readOnly)
    defer { CVPixelBufferUnlockBaseAddress(depthMap, .readOnly) }
    
    let width = CVPixelBufferGetWidth(depthMap)    // 256
    let height = CVPixelBufferGetHeight(depthMap)   // 192
    let bytesPerRow = CVPixelBufferGetBytesPerRow(depthMap)
    
    guard let baseAddress = CVPixelBufferGetBaseAddress(depthMap) else {
        throw CaptureError.noDepthData
    }
    
    // 포맷: kCVPixelFormatType_DepthFloat32
    // 각 픽셀 = Float32 (4 bytes), 단위: 미터, 0.0 = 무효
    var data = Data()
    for y in 0..<height {
        let rowPtr = baseAddress.advanced(by: y * bytesPerRow)
        data.append(Data(bytes: rowPtr, count: width * MemoryLayout<Float32>.size))
    }
    try data.write(to: url)
}
```

**주의**: `bytesPerRow`가 `width * 4`와 다를 수 있다 (패딩). 행 단위로 복사해야 한다.

### 2.5 이미지 유틸리티 (ImageUtils.swift)

```swift
func saveImage(_ pixelBuffer: CVPixelBuffer, to url: URL, quality: CGFloat = 0.9) throws {
    let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
    let context = CIContext()
    // capturedImage는 YCbCr(420f/420v) 포맷; CIImage가 자동 변환
    guard let jpegData = context.jpegRepresentation(
        of: ciImage, colorSpace: CGColorSpaceCreateDeviceRGB(),
        options: [kCGImageDestinationLossyCompressionQuality: quality]
    ) else {
        throw CaptureError.imageConversionFailed
    }
    try jpegData.write(to: url)
}
```

### 2.6 ARSession 매니저 (ARSessionManager.swift)

```swift
class ARSessionManager: NSObject, ObservableObject, ARSessionDelegate {
    @Published var isCapturing = false
    @Published var frameCount = 0
    @Published var trackingState = "Not Available"
    
    let session = ARSession()
    private var capturedFrames: [CapturedFrame] = []
    private var lastCaptureTime: TimeInterval = 0
    private var captureInterval: TimeInterval = 1.0  // 1fps 기본
    private var outputDirectory: URL!
    
    func startCapture(sceneName: String, fps: Double) {
        captureInterval = 1.0 / fps
        // outputDirectory 설정 (Documents/{sceneName}/)
        // images/, depths/ 하위 디렉토리 생성
        
        let config = ARWorldTrackingConfiguration()
        config.frameSemantics = [.sceneDepth]     // LiDAR 깊이 활성화
        config.isAutoFocusEnabled = true
        // sceneReconstruction 설정 안 함 (메시 불필요, 깊이맵만 필요)
        
        session.delegate = self
        session.run(config, options: [.removeExistingAnchors, .resetTracking])
        isCapturing = true
    }
    
    func stopCapture() -> CaptureMetadata {
        session.pause()
        isCapturing = false
        // CaptureMetadata 생성 및 metadata.json 저장
        return metadata
    }
    
    // MARK: - ARSessionDelegate
    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        // 1. 트래킹 상태 확인
        guard case .normal = frame.camera.trackingState else { return }
        
        // 2. 시간 간격 확인
        guard frame.timestamp - lastCaptureTime >= captureInterval else { return }
        
        // 3. LiDAR 깊이 존재 확인
        guard let sceneDepth = frame.sceneDepth else { return }
        
        // 4. 프레임 저장 (백그라운드 큐에서)
        let index = frameCount
        let transform = frame.camera.transform.toRowMajorArray()
        let intrinsics = frame.camera.intrinsics.toArray()
        let imageWidth = CVPixelBufferGetWidth(frame.capturedImage)
        let imageHeight = CVPixelBufferGetHeight(frame.capturedImage)
        
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            let imgPath = "images/frame_\(String(format: "%06d", index)).jpg"
            let depthPath = "depths/frame_\(String(format: "%06d", index)).bin"
            
            try? saveImage(frame.capturedImage,
                          to: self!.outputDirectory.appendingPathComponent(imgPath))
            try? saveDepthMap(sceneDepth.depthMap,
                            to: self!.outputDirectory.appendingPathComponent(depthPath))
            
            let capturedFrame = CapturedFrame(
                index: index, timestamp: frame.timestamp,
                imagePath: imgPath, depthPath: depthPath,
                transform: transform, intrinsics: intrinsics,
                imageWidth: imageWidth, imageHeight: imageHeight,
                depthWidth: 256, depthHeight: 192
            )
            
            DispatchQueue.main.async {
                self?.capturedFrames.append(capturedFrame)
                self?.frameCount += 1
            }
        }
        
        lastCaptureTime = frame.timestamp
    }
}
```

**중요 사항**:
- `ARFrame.capturedImage`와 `sceneDepth.depthMap`은 delegate 콜백 중에만 유효하다. 즉시 복사하거나 백그라운드 큐로 dispatch해야 한다.
- 깊이맵 해상도(256x192)는 디바이스와 무관하게 고정이다.
- `frame.camera.intrinsics`는 RGB 카메라의 네이티브 해상도(1920x1080 또는 1920x1440)에 대한 intrinsics를 반환한다.

### 2.7 데이터 전송

Mac으로 전송하는 3가지 방법:
1. **AirDrop**: 캡처 폴더를 공유하여 AirDrop으로 Mac Studio에 전송
2. **Files 앱 + iCloud**: iCloud Drive에 저장하면 Mac에 자동 동기화
3. **USB + Finder**: iPhone 연결 후 Finder 사이드바에서 앱 Documents 폴더 접근

전송 후 `data/raw/{scene_name}/` 아래에 배치한다.

### 2.8 iOS 캡처 데이터 출력 형식

```
data/raw/scene_desk/
├── images/
│   ├── frame_000000.jpg          # 1920x1080 JPEG
│   ├── frame_000001.jpg
│   └── ... (100-300 파일)
├── depths/
│   ├── frame_000000.bin          # 256*192*4 = 196,608 bytes (float32)
│   ├── frame_000001.bin
│   └── ...
└── metadata.json                 # CaptureMetadata JSON
```

#### metadata.json 예시

```json
{
    "deviceModel": "iPhone16,1",
    "iosVersion": "17.4",
    "captureDate": "2026-04-15T14:30:00Z",
    "sceneName": "scene_desk",
    "frameCount": 150,
    "samplingFPS": 1.0,
    "frames": [
        {
            "index": 0,
            "timestamp": 12345.678,
            "imagePath": "images/frame_000000.jpg",
            "depthPath": "depths/frame_000000.bin",
            "transform": [
                [0.998, 0.012, -0.058, 0.150],
                [-0.010, 0.999, 0.031, 1.420],
                [0.059, -0.030, 0.998, -0.320],
                [0.0, 0.0, 0.0, 1.0]
            ],
            "intrinsics": [
                [1598.0, 0.0, 960.0],
                [0.0, 1598.0, 540.0],
                [0.0, 0.0, 1.0]
            ],
            "imageWidth": 1920,
            "imageHeight": 1080,
            "depthWidth": 256,
            "depthHeight": 192
        }
    ]
}
```

---

## 3. Stage 2: Python 변환 파이프라인

### 3.1 환경 설정

#### environment.yml

```yaml
name: lidargs
channels:
  - pytorch
  - nvidia
  - conda-forge
dependencies:
  - python=3.10
  - pytorch>=2.1
  - torchvision
  - numpy
  - scipy
  - pillow
  - imageio
  - tqdm
  - matplotlib
  - pip:
    - gsplat>=1.0.0
    - open3d>=0.18
    - lpips
    - torchmetrics
    - fused-ssim
    - tyro
    - tensorboard
```

**하드웨어 참고**:
- gsplat은 CUDA를 필요로 한다. Apple Silicon(MPS)은 gsplat의 CUDA 커널을 지원하지 않는다.
- Mac Studio만 사용 가능한 경우: nerfstudio의 splatfacto(MPS 지원) 사용 또는 클라우드 GPU(Colab, Lambda 등) 활용
- NVIDIA GPU 워크스테이션이 있다면 그것으로 학습
- 학습 외 모든 스크립트(변환, 깊이, 시각화)는 CPU/Apple Silicon에서 동작

### 3.2 데이터 로딩 (load_capture.py)

```python
from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path
import numpy as np
import json

@dataclass
class FrameData:
    """iOS 캡처에서 로드된 단일 프레임."""
    index: int
    timestamp: float
    image_path: Path                    # JPEG 절대 경로
    depth_path: Path                    # .bin 절대 경로
    c2w: np.ndarray                     # (4, 4) float64, camera-to-world, row-major
    intrinsics: np.ndarray              # (3, 3) float64, RGB 카메라 intrinsics
    image_width: int                    # 1920
    image_height: int                   # 1080
    depth_width: int                    # 256
    depth_height: int                   # 192

@dataclass
class CaptureData:
    """전체 캡처 세션."""
    scene_name: str
    device_model: str
    frames: List[FrameData]

def load_capture(capture_dir: str | Path) -> CaptureData:
    """
    iOS 캡처 디렉토리에서 데이터 로드.

    Args:
        capture_dir: 원시 캡처 경로 (예: data/raw/scene_desk/)

    Returns:
        CaptureData: 모든 프레임이 로드된 캡처 데이터
    """
    capture_dir = Path(capture_dir)
    with open(capture_dir / "metadata.json") as f:
        meta = json.load(f)

    frames = []
    for frame_dict in meta["frames"]:
        frames.append(FrameData(
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
        ))

    return CaptureData(
        scene_name=meta["sceneName"],
        device_model=meta["deviceModel"],
        frames=frames,
    )

def load_depth_map(depth_path: str | Path, width: int = 256, height: int = 192) -> np.ndarray:
    """
    바이너리 float32 깊이맵 로드.

    Returns:
        np.ndarray: shape (height, width) dtype float32, 단위: 미터
    """
    data = np.fromfile(str(depth_path), dtype=np.float32)
    return data.reshape(height, width)

def load_image(image_path: str | Path) -> np.ndarray:
    """
    JPEG 이미지 로드.

    Returns:
        np.ndarray: shape (H, W, 3) dtype uint8
    """
    import imageio
    return imageio.imread(str(image_path))
```

### 3.3 좌표 변환

#### arkit_to_colmap.py

```python
import numpy as np
from scipy.spatial.transform import Rotation

def arkit_c2w_to_colmap(c2w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    ARKit camera-to-world (OpenGL) → COLMAP world-to-camera (OpenCV).

    변환 단계:
    1. Y/Z축 뒤집기: OpenGL(Y-up, -Z-forward) → OpenCV(Y-down, +Z-forward)
    2. c2w → w2c 역행렬
    3. 회전 행렬 → 쿼터니언 (COLMAP 순서로)

    Args:
        c2w: (4,4) ARKit camera-to-world 행렬, row-major, OpenGL 컨벤션

    Returns:
        quat_colmap: (4,) 쿼터니언 [qw, qx, qy, qz]
        t_colmap: (3,) 변환 벡터
    """
    # Step 1: OpenGL → OpenCV (Y, Z축 반전)
    flip_yz = np.diag([1.0, -1.0, -1.0, 1.0])
    c2w_opencv = c2w @ flip_yz

    # Step 2: c2w → w2c
    w2c = np.linalg.inv(c2w_opencv)
    R = w2c[:3, :3]
    t = w2c[:3, 3]

    # Step 3: 회전 행렬 → 쿼터니언
    r = Rotation.from_matrix(R)
    quat_scipy = r.as_quat()  # scipy: [qx, qy, qz, qw]
    quat_colmap = np.array([quat_scipy[3], quat_scipy[0],
                            quat_scipy[1], quat_scipy[2]])  # COLMAP: [qw, qx, qy, qz]

    return quat_colmap, t
```

#### arkit_to_gsplat.py

```python
import numpy as np
import torch

def arkit_c2w_to_viewmat(c2w: np.ndarray) -> np.ndarray:
    """
    ARKit camera-to-world → gsplat viewmat (world-to-camera).

    ARKit과 gsplat 모두 OpenGL 컨벤션을 사용하므로 축 뒤집기가 불필요하다.
    단순히 역행렬만 계산하면 된다.

    Args:
        c2w: (4,4) ARKit c2w, row-major

    Returns:
        w2c: (4,4) world-to-camera 행렬, float32
    """
    return np.linalg.inv(c2w).astype(np.float32)

def batch_c2w_to_viewmats(c2ws: np.ndarray) -> torch.Tensor:
    """
    배치 ARKit c2w → gsplat viewmats 텐서.

    Args:
        c2ws: (N, 4, 4) camera-to-world 행렬 배열

    Returns:
        viewmats: torch.Tensor (N, 4, 4) float32
    """
    w2cs = np.linalg.inv(c2ws).astype(np.float32)
    return torch.from_numpy(w2cs)
```

#### arkit_to_nerfstudio.py

```python
import numpy as np

def arkit_c2w_to_nerfstudio(c2w: np.ndarray) -> np.ndarray:
    """
    ARKit → Nerfstudio (Identity 변환).

    ARKit과 Nerfstudio 모두 OpenGL camera-to-world를 사용한다.
    iOS 앱에서 row-major로 저장했다면 변환이 필요 없다.

    Args:
        c2w: (4,4) ARKit c2w, row-major

    Returns:
        c2w: (4,4) 동일한 행렬
    """
    return c2w.astype(np.float64)
```

#### intrinsics.py

```python
import numpy as np

def scale_intrinsics(
    K: np.ndarray,
    from_size: tuple[int, int],
    to_size: tuple[int, int],
) -> np.ndarray:
    """
    Intrinsics를 한 해상도에서 다른 해상도로 스케일링.

    Args:
        K: (3,3) from_size 해상도의 intrinsic 행렬
        from_size: (width, height) 원본 해상도
        to_size: (width, height) 대상 해상도

    Returns:
        K_scaled: (3,3) to_size 해상도의 intrinsic 행렬
    """
    sx = to_size[0] / from_size[0]
    sy = to_size[1] / from_size[1]
    K_scaled = K.copy()
    K_scaled[0, 0] *= sx  # fx
    K_scaled[1, 1] *= sy  # fy
    K_scaled[0, 2] *= sx  # cx
    K_scaled[1, 2] *= sy  # cy
    return K_scaled

def scale_intrinsics_for_depth(
    K_rgb: np.ndarray,
    rgb_size: tuple[int, int],
    depth_size: tuple[int, int] = (256, 192),
) -> np.ndarray:
    """
    RGB 카메라 intrinsics를 LiDAR 깊이맵 해상도로 스케일링.
    깊이 역투영 시 사용.

    예시: RGB 1920x1080 → Depth 256x192
    sx = 256/1920 = 0.1333, sy = 192/1080 = 0.1778
    """
    return scale_intrinsics(K_rgb, rgb_size, depth_size)
```

### 3.4 깊이 역투영 (backproject.py)

```python
import numpy as np

def depth_to_pointcloud(
    depth_map: np.ndarray,        # (H, W) float32, 미터
    intrinsics: np.ndarray,       # (3, 3) 깊이맵 해상도에 맞는 intrinsics
    c2w: np.ndarray,              # (4, 4) camera-to-world (OpenGL/ARKit)
    min_depth: float = 0.1,
    max_depth: float = 5.0,
    subsample: int = 1,
) -> np.ndarray:
    """
    깊이맵을 월드 공간 3D 포인트 클라우드로 역투영.

    수학:
        x_cam = (u - cx) * d / fx
        y_cam = (v - cy) * d / fy
        z_cam = d
        P_world = R @ P_cam + t  (여기서 R, t는 c2w의 회전/변환)

    ARKit sceneDepth는 카메라 -Z축 방향의 거리를 양수 float으로 제공한다.
    ARKit 카메라 intrinsics는 Z > 0인 표준 핀홀 모델을 따른다.
    따라서 양수 Z = depth로 표준 핀홀 역투영이 그대로 동작한다.
    OpenGL 부호 컨벤션은 c2w 행렬 자체에 내장되어 있다.

    Args:
        depth_map: 깊이 값 (미터)
        intrinsics: 깊이맵 해상도의 카메라 intrinsics
        c2w: Camera-to-world 변환 행렬
        min_depth / max_depth: 유효 깊이 범위 필터
        subsample: N번째 픽셀마다 샘플링

    Returns:
        points_world: (M, 3) 월드 공간 포인트
    """
    h, w = depth_map.shape

    # 픽셀 좌표 그리드 생성
    v_coords, u_coords = np.mgrid[0:h:subsample, 0:w:subsample]
    depths = depth_map[v_coords, u_coords]

    # 유효 깊이 필터링
    valid = (depths > min_depth) & (depths < max_depth)
    u = u_coords[valid].astype(np.float64)
    v = v_coords[valid].astype(np.float64)
    z = depths[valid].astype(np.float64)

    # Intrinsics 추출
    fx, fy = intrinsics[0, 0], intrinsics[1, 1]
    cx, cy = intrinsics[0, 2], intrinsics[1, 2]

    # 카메라 공간으로 역투영
    x = (u - cx) * z / fx
    y = (v - cy) * z / fy
    points_cam = np.stack([x, y, z], axis=-1)  # (M, 3)

    # 월드 공간으로 변환
    R = c2w[:3, :3]
    t = c2w[:3, 3]
    points_world = (R @ points_cam.T).T + t  # (M, 3)

    return points_world
```

### 3.5 포인트 클라우드 병합 (merge_clouds.py)

```python
import numpy as np
import open3d as o3d
from typing import Optional

def merge_pointclouds(
    points_list: list[np.ndarray],
    colors_list: Optional[list[np.ndarray]] = None,
    voxel_size: float = 0.01,
) -> tuple[np.ndarray, Optional[np.ndarray]]:
    """
    여러 포인트 클라우드를 병합하고 복셀 다운샘플링.

    Args:
        points_list: [(M_i, 3)] 포인트 배열 리스트
        colors_list: [(M_i, 3)] 색상 배열 리스트 (0-1 float), 선택
        voxel_size: 다운샘플링 복셀 크기 (미터). 0.01 = 1cm

    Returns:
        points: (N, 3) 병합 + 다운샘플된 포인트
        colors: (N, 3) 또는 None
    """
    all_points = np.concatenate(points_list, axis=0)

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_points)

    if colors_list is not None:
        all_colors = np.concatenate(colors_list, axis=0)
        pcd.colors = o3d.utility.Vector3dVector(all_colors)

    pcd_down = pcd.voxel_down_sample(voxel_size=voxel_size)

    points_out = np.asarray(pcd_down.points)
    colors_out = np.asarray(pcd_down.colors) if pcd_down.has_colors() else None

    return points_out, colors_out

def statistical_outlier_removal(
    points: np.ndarray,
    nb_neighbors: int = 20,
    std_ratio: float = 2.0,
) -> np.ndarray:
    """Open3D를 사용한 통계적 이상치 제거."""
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    pcd_clean, _ = pcd.remove_statistical_outlier(
        nb_neighbors=nb_neighbors, std_ratio=std_ratio
    )
    return np.asarray(pcd_clean.points)
```

### 3.6 COLMAP 포맷 내보내기 (export_colmap.py)

```python
import numpy as np
from pathlib import Path
from typing import Optional, List
import shutil

def export_colmap_text(
    frames: list,                           # List[FrameData]
    output_dir: str | Path,
    points: Optional[np.ndarray] = None,    # (N, 3) 포인트 클라우드
    points_rgb: Optional[np.ndarray] = None,# (N, 3) uint8
) -> None:
    """
    ARKit 캡처 데이터에서 COLMAP 텍스트 포맷 파일 생성.

    생성 파일:
        output_dir/sparse/0/cameras.txt   — 카메라 모델 + intrinsics
        output_dir/sparse/0/images.txt    — 프레임별 쿼터니언 포즈
        output_dir/sparse/0/points3D.txt  — 3D 포인트 (또는 빈 파일)
    또한 이미지를 output_dir/images/에 복사/심볼릭 링크.

    cameras.txt 포맷:
        # Camera list with one line of data per camera:
        # CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]
        1 PINHOLE {width} {height} {fx} {fy} {cx} {cy}

    images.txt 포맷:
        # Image list with two lines of data per image:
        # IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME
        # POINTS2D[] as (X, Y, POINT3D_ID)  ← 빈 줄
        1 {qw} {qx} {qy} {qz} {tx} {ty} {tz} 1 frame_000000.jpg
        (빈 줄)

    points3D.txt 포맷:
        # Point3D list with one line of data per point:
        # POINT3D_ID X Y Z R G B ERROR TRACK[]
    """
    output_dir = Path(output_dir)
    sparse_dir = output_dir / "sparse" / "0"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    # cameras.txt (단일 카메라 모델)
    frame0 = frames[0]
    K = frame0.intrinsics
    fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
    with open(sparse_dir / "cameras.txt", "w") as f:
        f.write("# Camera list with one line of data per camera:\n")
        f.write("# CAMERA_ID, MODEL, WIDTH, HEIGHT, PARAMS[]\n")
        f.write(f"1 PINHOLE {frame0.image_width} {frame0.image_height} "
                f"{fx} {fy} {cx} {cy}\n")

    # images.txt
    from .transform.arkit_to_colmap import arkit_c2w_to_colmap
    with open(sparse_dir / "images.txt", "w") as f:
        f.write("# Image list with two lines of data per image:\n")
        f.write("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        for i, frame in enumerate(frames):
            quat, t = arkit_c2w_to_colmap(frame.c2w)
            name = frame.image_path.name
            f.write(f"{i+1} {quat[0]} {quat[1]} {quat[2]} {quat[3]} "
                    f"{t[0]} {t[1]} {t[2]} 1 {name}\n")
            f.write("\n")  # POINTS2D 빈 줄

    # points3D.txt
    with open(sparse_dir / "points3D.txt", "w") as f:
        f.write("# Point3D list with one line of data per point:\n")
        if points is not None:
            for i in range(len(points)):
                x, y, z = points[i]
                if points_rgb is not None:
                    r, g, b = points_rgb[i].astype(int)
                else:
                    r, g, b = 128, 128, 128
                f.write(f"{i+1} {x} {y} {z} {r} {g} {b} 0.0\n")

    # 이미지 복사
    for frame in frames:
        src = frame.image_path
        dst = images_dir / src.name
        if not dst.exists():
            shutil.copy2(str(src), str(dst))
```

### 3.7 Nerfstudio 포맷 내보내기 (export_nerfstudio.py)

```python
import json
import numpy as np
from pathlib import Path

def export_transforms_json(
    frames: list,                   # List[FrameData]
    output_dir: str | Path,
    include_depth: bool = True,
) -> None:
    """
    Nerfstudio 호환 transforms.json 생성.

    ARKit과 Nerfstudio 모두 OpenGL camera-to-world를 사용하므로
    transform_matrix를 그대로 사용한다.

    출력 JSON:
    {
        "camera_model": "OPENCV",
        "fl_x": fx, "fl_y": fy,
        "cx": cx, "cy": cy,
        "w": 1920, "h": 1080,
        "k1": 0, "k2": 0, "p1": 0, "p2": 0,
        "frames": [
            {
                "file_path": "images/frame_000000.jpg",
                "transform_matrix": [[...], [...], [...], [...]],
                "depth_file_path": "depths/frame_000000.png"
            }
        ]
    }
    """
    output_dir = Path(output_dir)
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
        "k1": 0.0, "k2": 0.0, "p1": 0.0, "p2": 0.0,
        "frames": [],
    }

    for frame in frames:
        frame_entry = {
            "file_path": f"images/{frame.image_path.name}",
            "transform_matrix": frame.c2w.tolist(),
        }
        if include_depth:
            frame_entry["depth_file_path"] = f"depths/{frame.depth_path.stem}.png"
        data["frames"].append(frame_entry)

    with open(output_dir / "transforms.json", "w") as f:
        json.dump(data, f, indent=2)
```

### 3.8 시각화 도구 (visualize_poses.py)

```python
import numpy as np
import open3d as o3d
from typing import Optional

def visualize_cameras_and_points(
    c2ws: np.ndarray,                       # (N, 4, 4) camera-to-world
    intrinsics: np.ndarray,                 # (3, 3)
    image_width: int,
    image_height: int,
    points: Optional[np.ndarray] = None,    # (M, 3)
    points_colors: Optional[np.ndarray] = None,
    camera_scale: float = 0.1,
    title: str = "Pose Visualization",
) -> None:
    """
    카메라 포즈를 frustum으로, 포인트 클라우드와 함께 시각화.

    검증 체크리스트:
    - 카메라 frustum이 일관된 궤적을 형성해야 한다
    - 모든 frustum이 대체로 안쪽(캡처된 장면 방향)을 가리켜야 한다
    - 포인트 클라우드가 카메라 궤적 "안쪽"에 있어야 한다
    - 월드 축이 합리적이어야 한다 (Y-up 등)
    """
    geometries = []

    for i in range(len(c2ws)):
        w2c = np.linalg.inv(c2ws[i])
        cam = o3d.geometry.LineSet.create_camera_visualization(
            image_width, image_height, intrinsics, w2c, scale=camera_scale
        )
        geometries.append(cam)

    if points is not None:
        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(points)
        if points_colors is not None:
            pcd.colors = o3d.utility.Vector3dVector(points_colors / 255.0)
        geometries.append(pcd)

    axes = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.5)
    geometries.append(axes)

    o3d.visualization.draw_geometries(geometries, window_name=title)
```

---

## 4. Stage 3: gsplat 학습 파이프라인

### 4.1 gsplat rasterization() API 레퍼런스

```python
from gsplat import rasterization

rendered, alpha, info = rasterization(
    means=gaussians.means,           # [N, 3] Gaussian 중심 좌표
    quats=gaussians.quats,           # [N, 4] 쿼터니언 (wxyz 순서)
    scales=gaussians.scales,         # [N, 3] 스케일 벡터
    opacities=gaussians.opacities,   # [N] 불투명도 (0-1)
    colors=gaussians.colors,         # [(C,) N, D] 또는 [(C,) N, K, 3] (SH)
    viewmats=viewmats,               # [C, 4, 4] world-to-camera 행렬
    Ks=Ks,                           # [C, 3, 3] 카메라 intrinsics
    width=image_width,               # 이미지 너비 (픽셀)
    height=image_height,             # 이미지 높이 (픽셀)
    sh_degree=3,                     # SH degree (선택)
    near_plane=0.01,
    far_plane=1e10,
    eps2d=0.3,                       # 투영된 공분산 엡실론
    packed=False,
    rasterize_mode="classic",        # "classic" 또는 "antialiased"
)
```

**반환값**:
- `rendered`: [C, height, width, X] 렌더링된 색상
- `alpha`: [C, height, width, 1] 알파/투명도
- `info`: 중간 결과 딕셔너리 (densification에 사용)

**핵심 파라미터**:
- `viewmats`: **world-to-camera** (camera-to-world의 역행렬)
- `Ks`: 픽셀 단위 (정규화된 값이 아님)
- `quats`: **wxyz** 순서 (w=스칼라, xyz=벡터)
- `scales`: **log-space**로 저장, `torch.exp(scales)`로 전달
- `opacities`: **logit-space**로 저장, `torch.sigmoid(opacities)`로 전달

### 4.2 viewmat/Ks 데이터 흐름

전체 파이프라인에서 카메라 데이터가 흐르는 경로:

```
iOS ARKit
  ARFrame.camera.transform (simd_float4x4, column-major, c2w, OpenGL)
    ↓ MatrixExtensions.swift: toRowMajorArray()
metadata.json "transform" (row-major, c2w, OpenGL)
    ↓ load_capture.py: np.array(frame_dict["transform"])
FrameData.c2w (np.ndarray (4,4), row-major, c2w, OpenGL)
    ↓ LidarGSParser: self.camtoworlds[i]
LidarGSDataset.__getitem__: "camtoworld" (torch.Tensor (4,4))
    ↓ trainer.py: viewmats = torch.linalg.inv(camtoworlds)
rasterization() viewmats (torch.Tensor (C,4,4), w2c, OpenGL)
```

**핵심**: gsplat의 원래 COLMAP 로더도 camtoworlds를 저장(COLMAP w2c를 역행렬로 변환)한 후, 렌더링 시 다시 역행렬을 계산한다. 우리 파이프라인은 ARKit의 네이티브 c2w를 저장하고 한 번만 역행렬을 계산한다. 두 경로 모두 동일한 w2c viewmats를 gsplat에 전달한다.

### 4.3 Custom Dataset (dataset.py)

```python
import torch
from torch.utils.data import Dataset as TorchDataset
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict
import imageio

@dataclass
class LidarGSParser:
    """
    LidarGS 데이터 파서. gsplat의 Parser 인터페이스를 모방.

    gsplat simple_trainer.py가 기대하는 속성:
    - image_names: List[str]
    - image_paths: List[str]
    - camtoworlds: np.ndarray (N, 4, 4)
    - Ks_dict: Dict[int, np.ndarray]     # camera_id → (3,3) intrinsics
    - imsize_dict: Dict[int, tuple]       # camera_id → (width, height)
    - points: np.ndarray (M, 3)           # 초기화용 3D 포인트
    - points_rgb: np.ndarray (M, 3)       # 포인트 색상 (uint8)
    - scene_scale: float                  # 정규화용
    """
    data_dir: Path
    init_type: str = "lidar"    # "lidar", "random", "sfm"
    test_every: int = 8
    normalize: bool = True

    def __post_init__(self):
        self.data_dir = Path(self.data_dir)

        # metadata.json 또는 COLMAP 포맷에서 로드
        # init_type에 따라 포인트 소스 결정:
        #   "lidar": points3d_lidar.ply 로드
        #   "sfm": sparse/0/points3D.txt 로드
        #   "random": points = None (init_gaussians에서 처리)

        # scene_scale: 카메라 위치의 표준편차로 계산
        # normalize가 True이면 camtoworlds를 scene_scale로 나누어 정규화

class LidarGSDataset(TorchDataset):
    """
    gsplat simple_trainer와 호환되는 PyTorch Dataset.

    __getitem__이 반환하는 dict:
    {
        "K": torch.Tensor (3, 3),           # 카메라 intrinsics
        "camtoworld": torch.Tensor (4, 4),  # camera-to-world
        "image": torch.Tensor (H, W, 3),    # float32 [0, 1]
        "image_id": int,
    }
    """
    def __init__(self, parser: LidarGSParser, split: str = "train"):
        indices = list(range(len(parser.image_names)))
        if split == "train":
            self.indices = [i for i in indices if i % parser.test_every != 0]
        else:
            self.indices = [i for i in indices if i % parser.test_every == 0]
        self.parser = parser

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        real_idx = self.indices[idx]
        image = imageio.imread(self.parser.image_paths[real_idx])[..., :3]
        image = torch.from_numpy(image).float() / 255.0

        camera_id = 1  # 단일 iPhone 카메라
        K = torch.from_numpy(self.parser.Ks_dict[camera_id]).float()
        c2w = torch.from_numpy(self.parser.camtoworlds[real_idx]).float()

        return {"K": K, "camtoworld": c2w, "image": image, "image_id": real_idx}

    def __len__(self):
        return len(self.indices)
```

### 4.4 Gaussian 초기화 (init_gaussians.py)

```python
import torch
import numpy as np
from typing import Optional, Tuple, Dict

def init_from_lidar_pointcloud(
    points: np.ndarray,               # (N, 3) LiDAR 역투영 포인트
    colors: Optional[np.ndarray],     # (N, 3) uint8 또는 None
    sh_degree: int = 3,
    init_opacity: float = 0.1,
    init_scale: float = 1.0,
    device: str = "cuda",
) -> Tuple[Dict[str, torch.nn.Parameter], Dict[str, torch.optim.Optimizer]]:
    """
    LiDAR 포인트 클라우드에서 3D Gaussians 초기화.

    생성되는 파라미터:
    - means: (N, 3) 포인트 위치
    - scales: (N, 3) log-space, k-NN 거리로 계산
    - quats: (N, 4) 항등 쿼터니언 [1, 0, 0, 0] (wxyz 순서)
    - opacities: (N,) logit-space, logit(init_opacity)
    - sh0: (N, 1, 3) DC spherical harmonic (포인트 색상 또는 회색)
    - shN: (N, (sh_degree+1)^2-1, 3) 고차 SH (0)

    스케일 계산:
    k-NN (k=4)으로 로컬 밀도를 찾아
    scale = log(mean_distance_to_3_nearest_neighbors * init_scale)
    """
    N = len(points)
    means = torch.from_numpy(points).float().to(device)

    # k-NN으로 초기 스케일 계산
    from .utils import knn
    distances = knn(means, k=4)  # (N, 4) 거리
    avg_dist = distances[:, 1:].mean(dim=1)  # 자기 자신 제외
    scales = torch.log(avg_dist * init_scale).unsqueeze(-1).repeat(1, 3)  # (N, 3)

    # 항등 쿼터니언
    quats = torch.zeros((N, 4), device=device)
    quats[:, 0] = 1.0  # w=1 (wxyz 순서)

    # logit-space 불투명도
    opacities = torch.logit(torch.full((N,), init_opacity, device=device))

    # SH 계수
    if colors is not None:
        from .utils import rgb_to_sh
        sh0 = rgb_to_sh(torch.from_numpy(colors).float().to(device) / 255.0)
        sh0 = sh0.unsqueeze(1)  # (N, 1, 3)
    else:
        sh0 = torch.zeros((N, 1, 3), device=device)

    num_sh_higher = (sh_degree + 1) ** 2 - 1
    shN = torch.zeros((N, num_sh_higher, 3), device=device)

    # nn.Parameter로 래핑
    splats = torch.nn.ParameterDict({
        "means": torch.nn.Parameter(means),
        "scales": torch.nn.Parameter(scales),
        "quats": torch.nn.Parameter(quats),
        "opacities": torch.nn.Parameter(opacities),
        "sh0": torch.nn.Parameter(sh0),
        "shN": torch.nn.Parameter(shN),
    })

    return splats

def init_random(
    num_points: int = 100_000,
    extent: float = 3.0,
    scene_scale: float = 1.0,
    sh_degree: int = 3,
    init_opacity: float = 0.1,
    device: str = "cuda",
) -> Dict[str, torch.nn.Parameter]:
    """
    Method C (ablation)용 랜덤 초기화.

    [-extent * scene_scale, extent * scene_scale]^3 범위에
    균일 분포로 포인트 생성.
    """
    means = (torch.rand((num_points, 3), device=device) - 0.5) * 2 * extent * scene_scale
    # 나머지는 init_from_lidar_pointcloud와 동일한 초기화 로직
    ...
```

### 4.5 학습 설정 (config.py)

```python
from dataclasses import dataclass, field
from typing import List

@dataclass
class LidarGSConfig:
    """학습 설정. gsplat Config 기반 + LidarGS 확장."""

    # 데이터
    data_dir: str = ""
    result_dir: str = ""
    data_factor: int = 1               # 이미지 다운스케일 팩터
    test_every: int = 8

    # 초기화
    init_type: str = "lidar"           # "lidar", "random", "sfm"
    init_num_pts: int = 100_000        # random init용
    init_extent: float = 3.0
    init_opa: float = 0.1
    init_scale: float = 1.0

    # 학습
    max_steps: int = 30_000
    batch_size: int = 1
    eval_steps: List[int] = field(default_factory=lambda: [7_000, 15_000, 30_000])
    save_steps: List[int] = field(default_factory=lambda: [7_000, 30_000])

    # 학습률 (gsplat 기본값)
    means_lr: float = 1.6e-4
    scales_lr: float = 5e-3
    quats_lr: float = 1e-3
    opacities_lr: float = 5e-2
    sh0_lr: float = 2.5e-3
    shN_lr: float = 1.25e-4            # sh0_lr / 20

    # 손실 함수
    ssim_lambda: float = 0.2           # L1과 SSIM의 보간 비율

    # Densification
    refine_start_iter: int = 500
    refine_stop_iter: int = 15_000
    refine_every: int = 100

    # SH
    sh_degree: int = 3
    sh_degree_interval: int = 1000

    # 렌더링
    near_plane: float = 0.01
    far_plane: float = 1e10

    # 수렴 로깅
    log_psnr_every: int = 500
```

### 4.6 메인 트레이너 (trainer.py)

```python
import torch
import torch.nn.functional as F
from gsplat.rendering import rasterization
from gsplat.strategy import DefaultStrategy
from fused_ssim import fused_ssim
from pathlib import Path
import json
import time

from .config import LidarGSConfig
from .dataset import LidarGSParser, LidarGSDataset
from .init_gaussians import init_from_lidar_pointcloud, init_random

class LidarGSTrainer:
    """
    LidarGS 3DGS 트레이너.

    gsplat/examples/simple_trainer.py Runner를 기반으로 적응.
    주요 차이점:
    1. LidarGSParser/Dataset 사용 (COLMAP Parser/Dataset 대신)
    2. "lidar" init_type 지원
    3. 수렴 곡선 분석을 위한 정기적 PSNR 로깅
    """

    def __init__(self, cfg: LidarGSConfig):
        self.cfg = cfg
        self.device = "cuda"

        # 출력 디렉토리
        self.result_dir = Path(cfg.result_dir)
        for subdir in ["ckpts", "stats", "renders", "ply"]:
            (self.result_dir / subdir).mkdir(parents=True, exist_ok=True)

        # 데이터 로드
        self.parser = LidarGSParser(
            data_dir=Path(cfg.data_dir),
            init_type=cfg.init_type,
            test_every=cfg.test_every,
        )
        self.trainset = LidarGSDataset(self.parser, split="train")
        self.valset = LidarGSDataset(self.parser, split="test")

        # Gaussian 초기화
        if cfg.init_type == "lidar":
            self.splats = init_from_lidar_pointcloud(
                points=self.parser.points,
                colors=self.parser.points_rgb,
                sh_degree=cfg.sh_degree,
                init_opacity=cfg.init_opa,
                init_scale=cfg.init_scale,
                device=self.device,
            )
        elif cfg.init_type == "random":
            self.splats = init_random(
                num_points=cfg.init_num_pts,
                extent=cfg.init_extent,
                scene_scale=self.parser.scene_scale,
                sh_degree=cfg.sh_degree,
                device=self.device,
            )

        # Optimizer 설정
        self.optimizers = {
            "means": torch.optim.Adam([self.splats["means"]], lr=cfg.means_lr),
            "scales": torch.optim.Adam([self.splats["scales"]], lr=cfg.scales_lr),
            "quats": torch.optim.Adam([self.splats["quats"]], lr=cfg.quats_lr),
            "opacities": torch.optim.Adam([self.splats["opacities"]], lr=cfg.opacities_lr),
            "sh0": torch.optim.Adam([self.splats["sh0"]], lr=cfg.sh0_lr),
            "shN": torch.optim.Adam([self.splats["shN"]], lr=cfg.shN_lr),
        }

        # Densification 전략
        self.strategy = DefaultStrategy(
            refine_start_iter=cfg.refine_start_iter,
            refine_stop_iter=cfg.refine_stop_iter,
            refine_every=cfg.refine_every,
        )
        self.strategy_state = self.strategy.initialize_state()

        # 수렴 추적
        self.train_psnr_log = []
        self.start_time = None

    def train(self):
        """메인 학습 루프."""
        cfg = self.cfg
        trainloader = torch.utils.data.DataLoader(
            self.trainset, batch_size=cfg.batch_size, shuffle=True,
            num_workers=4, pin_memory=True,
        )
        trainloader_iter = iter(trainloader)
        self.start_time = time.time()

        for step in range(cfg.max_steps):
            try:
                data = next(trainloader_iter)
            except StopIteration:
                trainloader_iter = iter(trainloader)
                data = next(trainloader_iter)

            camtoworlds = data["camtoworld"].to(self.device)  # (B, 4, 4)
            Ks = data["K"].to(self.device)                     # (B, 3, 3)
            pixels = data["image"].to(self.device)             # (B, H, W, 3)

            height, width = pixels.shape[1], pixels.shape[2]
            viewmats = torch.linalg.inv(camtoworlds)           # (B, 4, 4) w2c

            sh_degree_to_use = min(cfg.sh_degree, step // cfg.sh_degree_interval)

            # 래스터화
            renders, alphas, info = rasterization(
                means=self.splats["means"],
                quats=self.splats["quats"],
                scales=torch.exp(self.splats["scales"]),
                opacities=torch.sigmoid(self.splats["opacities"]),
                colors=torch.cat([self.splats["sh0"], self.splats["shN"]], dim=1),
                viewmats=viewmats, Ks=Ks,
                width=width, height=height,
                sh_degree=sh_degree_to_use,
                near_plane=cfg.near_plane, far_plane=cfg.far_plane,
            )

            colors = renders[..., :3]  # (B, H, W, 3)

            # 손실 계산
            l1loss = F.l1_loss(colors, pixels)
            ssimloss = 1.0 - fused_ssim(
                colors.permute(0, 3, 1, 2),
                pixels.permute(0, 3, 1, 2),
                padding="valid",
            )
            loss = torch.lerp(l1loss, ssimloss, cfg.ssim_lambda)

            # Densification pre-backward
            self.strategy.step_pre_backward(
                params=self.splats, optimizers=self.optimizers,
                state=self.strategy_state, step=step, info=info,
            )

            # Backward + Optimizer step
            loss.backward()
            for opt in self.optimizers.values():
                opt.step()
                opt.zero_grad(set_to_none=True)

            # Densification post-backward
            self.strategy.step_post_backward(
                params=self.splats, optimizers=self.optimizers,
                state=self.strategy_state, step=step, info=info,
            )

            # 수렴 PSNR 로깅
            if step % cfg.log_psnr_every == 0:
                with torch.no_grad():
                    psnr = -10 * torch.log10(F.mse_loss(colors, pixels))
                    self.train_psnr_log.append((step, psnr.item()))

            # 평가 + 체크포인트
            if step in cfg.eval_steps:
                self.eval(step)
                self.save_checkpoint(step)

        # 학습 완료 후 통계 저장
        elapsed = time.time() - self.start_time
        stats = {
            "train_time_sec": elapsed,
            "num_gaussians": len(self.splats["means"]),
            "psnr_log": self.train_psnr_log,
        }
        with open(self.result_dir / "stats" / "train_stats.json", "w") as f:
            json.dump(stats, f, indent=2)

    @torch.no_grad()
    def eval(self, step: int):
        """검증 세트에서 평가."""
        from torchmetrics.image import PeakSignalNoiseRatio
        from torchmetrics.image import StructuralSimilarityIndexMeasure
        from torchmetrics.image.lpip import LearnedPerceptualImagePatchSimilarity

        psnr_fn = PeakSignalNoiseRatio(data_range=1.0).to(self.device)
        ssim_fn = StructuralSimilarityIndexMeasure(data_range=1.0).to(self.device)
        lpips_fn = LearnedPerceptualImagePatchSimilarity(net_type="alex").to(self.device)

        metrics = {"psnr": [], "ssim": [], "lpips": []}
        valloader = torch.utils.data.DataLoader(self.valset, batch_size=1)

        for data in valloader:
            camtoworlds = data["camtoworld"].to(self.device)
            Ks = data["K"].to(self.device)
            pixels = data["image"].to(self.device)
            h, w = pixels.shape[1], pixels.shape[2]
            viewmats = torch.linalg.inv(camtoworlds)

            renders, _, _ = rasterization(
                means=self.splats["means"],
                quats=self.splats["quats"],
                scales=torch.exp(self.splats["scales"]),
                opacities=torch.sigmoid(self.splats["opacities"]),
                colors=torch.cat([self.splats["sh0"], self.splats["shN"]], dim=1),
                viewmats=viewmats, Ks=Ks,
                width=w, height=h,
                sh_degree=self.cfg.sh_degree,
            )
            colors_p = renders[..., :3].clamp(0, 1).permute(0, 3, 1, 2)
            pixels_p = pixels.permute(0, 3, 1, 2)

            metrics["psnr"].append(psnr_fn(colors_p, pixels_p))
            metrics["ssim"].append(ssim_fn(colors_p, pixels_p))
            metrics["lpips"].append(lpips_fn(colors_p, pixels_p))

        avg = {k: torch.stack(v).mean().item() for k, v in metrics.items()}

        # 결과 저장
        with open(self.result_dir / "stats" / f"eval_step{step}.json", "w") as f:
            json.dump(avg, f, indent=2)

        # 렌더링 이미지 저장 (첫 번째 검증 이미지)
        import imageio
        rendered_img = (renders[0, ..., :3].clamp(0, 1).cpu().numpy() * 255).astype(np.uint8)
        imageio.imwrite(str(self.result_dir / "renders" / f"step{step}.png"), rendered_img)

    def save_checkpoint(self, step: int):
        """모델 체크포인트 저장."""
        ckpt = {k: v.data.cpu() for k, v in self.splats.items()}
        torch.save(ckpt, self.result_dir / "ckpts" / f"step{step}.pt")
```

---

## 5. Stage 4: 평가 파이프라인

### 5.1 메트릭 계산 (metrics.py)

```python
from dataclasses import dataclass

@dataclass
class EvalResult:
    """단일 Method/Scene 조합의 평가 결과."""
    scene: str
    method: str          # "method_a_colmap", "method_b_lidargs", "method_c_random"
    psnr: float
    ssim: float
    lpips: float
    num_gaussians: int
    model_size_mb: float
    preprocess_time_sec: float
    train_time_sec: float
    total_time_sec: float
```

### 5.2 3-Way 비교 자동화 (compare.py)

```python
from typing import List
import json

def run_three_way_comparison(
    scene_name: str,
    results_base_dir: str,
) -> dict:
    """
    하나의 장면에 대해 3가지 방법 전체 평가 실행.

    로드 경로:
    - results/{scene}/method_a_colmap/stats/eval_step30000.json
    - results/{scene}/method_b_lidargs/stats/eval_step30000.json
    - results/{scene}/method_c_random/stats/eval_step30000.json

    Returns:
        비교 딕셔너리 (모든 메트릭 포함)
    """

def generate_latex_table(
    all_results: List[dict],
    output_path: str,
) -> str:
    """
    논문용 LaTeX 표 생성 (Table 1).

    포맷:
    Scene | Method | Preprocess (s) | PSNR↑ | SSIM↑ | LPIPS↓ | #Gaussians
    """
```

### 5.3 수렴 곡선 (convergence.py)

```python
import matplotlib.pyplot as plt

def plot_convergence_curves(
    scene_name: str,
    results_base_dir: str,
    output_path: str,
) -> None:
    """
    하나의 장면에 대해 3가지 방법의 PSNR vs 학습 반복 곡선 플롯.

    데이터 소스:
    - results/{scene}/method_*/stats/train_stats.json의 "psnr_log"

    출력: PNG/PDF (A=파란색, B=빨간색, C=초록색)
    """
    fig, ax = plt.subplots(figsize=(8, 5))

    methods = [
        ("method_a_colmap", "COLMAP (A)", "blue"),
        ("method_b_lidargs", "LidarGS (B)", "red"),
        ("method_c_random", "Random (C)", "green"),
    ]

    for method_dir, label, color in methods:
        stats_path = f"{results_base_dir}/{scene_name}/{method_dir}/stats/train_stats.json"
        with open(stats_path) as f:
            stats = json.load(f)
        steps, psnrs = zip(*stats["psnr_log"])
        ax.plot(steps, psnrs, label=label, color=color, linewidth=2)

    ax.set_xlabel("Training Iteration")
    ax.set_ylabel("PSNR (dB)")
    ax.set_title(f"Convergence: {scene_name}")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
```

---

## 6. COLMAP 베이스라인 (Method A)

### 6.1 COLMAP 실행 스크립트 (run_colmap.sh)

```bash
#!/bin/bash
# Usage: ./run_colmap.sh <scene_path>
# scene_path는 images/ 폴더를 포함해야 함

SCENE_PATH=$1
DATABASE_PATH="${SCENE_PATH}/database.db"
IMAGE_PATH="${SCENE_PATH}/images"
SPARSE_PATH="${SCENE_PATH}/sparse"

mkdir -p "${SPARSE_PATH}"

echo "=== Feature Extraction ==="
colmap feature_extractor \
    --database_path "${DATABASE_PATH}" \
    --image_path "${IMAGE_PATH}" \
    --ImageReader.camera_model PINHOLE \
    --ImageReader.single_camera 1

echo "=== Feature Matching (Exhaustive) ==="
colmap exhaustive_matcher \
    --database_path "${DATABASE_PATH}"

echo "=== Mapping (SfM) ==="
colmap mapper \
    --database_path "${DATABASE_PATH}" \
    --image_path "${IMAGE_PATH}" \
    --output_path "${SPARSE_PATH}"

echo "=== Model Conversion to TXT ==="
colmap model_converter \
    --input_path "${SPARSE_PATH}/0" \
    --output_path "${SPARSE_PATH}/0" \
    --output_type TXT

echo "Done. Output in ${SPARSE_PATH}/0/"
```

### 6.2 Method A 학습

Method A는 gsplat의 원래 Parser/Dataset 클래스를 직접 사용한다 (수정 불필요).
COLMAP의 `sparse/0/` 디렉토리에서 cameras.txt, images.txt, points3D.txt를 로드.
학습 루프는 gsplat의 `simple_trainer.py`와 동일.

**핵심**: Method A, B, C 모두 **동일한 RGB 이미지**를 사용한다.
차이점은 포즈 소스와 초기 포인트뿐:
- Method A: COLMAP이 포즈 + sparse 포인트 제공
- Method B: ARKit이 포즈 제공 + LiDAR가 dense 포인트 제공
- Method C: ARKit이 포즈 제공 + 랜덤 포인트

---

## 7. 실행 스크립트

### 7.1 데이터 처리 (01_process_capture.py)

```python
"""
iOS 캡처 데이터를 3가지 방법에 맞게 처리.

Usage:
    python scripts/01_process_capture.py --scene scene_desk

단계:
1. data/raw/{scene}/에서 원시 캡처 로드
2. Method B (LidarGS):
   a. 모든 깊이맵을 월드 공간 포인트 클라우드로 역투영
   b. 병합 + 복셀 다운샘플로 초기 포인트 클라우드 생성
   c. ARKit 포즈로 COLMAP 포맷 파일 생성
   d. 포인트 클라우드를 .ply로 저장
   e. data/processed/{scene}/method_b_lidargs/에 출력
3. Method C (Random):
   a. ARKit 포즈로 COLMAP 포맷 파일 생성 (B와 동일)
   b. 빈 points3D.txt
   c. data/processed/{scene}/method_c_random/에 출력
4. Method A (COLMAP):
   a. data/processed/{scene}/method_a_colmap/images/에 이미지 복사
   b. run_colmap.sh 실행 안내 출력
5. 검증을 위한 포즈 + 포인트 클라우드 시각화
"""
```

### 7.2 마스터 실험 스크립트 (run_all_experiments.sh)

```bash
#!/bin/bash
SCENES=("scene_desk" "scene_lab" "scene_hallway")

for SCENE in "${SCENES[@]}"; do
    echo "=== Processing ${SCENE} ==="
    python scripts/01_process_capture.py --scene "${SCENE}"

    echo "=== Running COLMAP for ${SCENE} ==="
    bash scripts/run_colmap.sh "data/processed/${SCENE}/method_a_colmap"

    echo "=== Training Method A (COLMAP) ==="
    python scripts/03_train_colmap.py \
        --data_dir "data/processed/${SCENE}/method_a_colmap" \
        --result_dir "data/results/${SCENE}/method_a_colmap" \
        --max_steps 30000

    echo "=== Training Method B (LidarGS) ==="
    python scripts/02_train_lidargs.py \
        --data_dir "data/processed/${SCENE}/method_b_lidargs" \
        --result_dir "data/results/${SCENE}/method_b_lidargs" \
        --init_type lidar --max_steps 30000

    echo "=== Training Method C (Random) ==="
    python scripts/04_train_random.py \
        --data_dir "data/processed/${SCENE}/method_c_random" \
        --result_dir "data/results/${SCENE}/method_c_random" \
        --init_type random --max_steps 30000
done

echo "=== Evaluation ==="
python scripts/05_evaluate.py
python scripts/06_generate_tables.py
```

---

## 8. 환경 설정 상세

### 8.1 Python 의존성

| 패키지 | 버전 | 용도 |
|--------|------|------|
| Python | 3.10 | 런타임 |
| PyTorch | >=2.1 | 딥러닝 프레임워크 |
| gsplat | >=1.0.0 | 3DGS 래스터화 |
| numpy | >=1.24 | 수치 계산 |
| scipy | >=1.11 | Rotation 변환 |
| open3d | >=0.18 | 포인트 클라우드 + 시각화 |
| torchmetrics | >=1.0 | PSNR, SSIM |
| lpips | >=0.1.4 | LPIPS |
| fused-ssim | >=0.1 | 학습용 빠른 SSIM |
| imageio | >=2.31 | 이미지 I/O |
| matplotlib | >=3.7 | 플롯 |
| tyro | >=0.7 | CLI 인자 파싱 |
| tensorboard | >=2.14 | 학습 로깅 |

### 8.2 iOS 개발 환경

| 도구 | 버전 | 용도 |
|------|------|------|
| Xcode | 16+ | iOS 앱 개발 |
| iOS SDK | 17+ | Deployment target |
| Swift | 5.9+ | 프로그래밍 언어 |
| ARKit | 6.0 | 포즈 + 깊이 캡처 |

### 8.3 하드웨어 요구사항

| 컴포넌트 | 최소 사양 | 권장 사양 |
|----------|----------|----------|
| 캡처 디바이스 | iPhone 15 Pro (LiDAR) | iPhone 16 Pro |
| 학습 GPU | NVIDIA RTX 3060 (8GB) | RTX 4090 (24GB) |
| 학습 대안 | Google Colab T4/A100 | Lambda Cloud |
| 전처리/시각화 | Mac Studio M2 | Mac Studio M2 Ultra |

---

## 9. 위험 관리

### 9.1 좌표 변환 검증 전략 (가장 높은 위험 영역)

#### Layer 1: 단위 테스트 (test_transforms.py)

```python
def test_identity_camera():
    """단위 행렬 c2w에 대해 모든 변환 경로 검증."""
    c2w = np.eye(4)
    # gsplat: viewmat도 identity여야 함
    assert np.allclose(arkit_c2w_to_viewmat(c2w), np.eye(4))
    # COLMAP: quat=[1,0,0,0], t=[0,0,0]
    quat, t = arkit_c2w_to_colmap(c2w)
    assert np.allclose(quat, [1, 0, 0, 0])
    assert np.allclose(t, [0, 0, 0])

def test_translated_camera():
    """(1, 0, 0)으로 이동된 카메라."""
    c2w = np.eye(4)
    c2w[:3, 3] = [1, 0, 0]
    viewmat = arkit_c2w_to_viewmat(c2w)
    assert np.allclose(viewmat[:3, 3], [-1, 0, 0])  # w2c 변환

def test_rotated_camera():
    """Y축 90도 회전 카메라."""
    from scipy.spatial.transform import Rotation
    R = Rotation.from_euler('y', 90, degrees=True).as_matrix()
    c2w = np.eye(4)
    c2w[:3, :3] = R
    quat, t = arkit_c2w_to_colmap(c2w)
    # 쿼터니언 검증
    ...

def test_roundtrip():
    """ARKit → COLMAP → c2w 왕복 검증."""
    c2w_original = random_c2w()
    quat, t = arkit_c2w_to_colmap(c2w_original)
    # COLMAP quat+t → w2c → inv → c2w
    R = Rotation.from_quat([quat[1], quat[2], quat[3], quat[0]]).as_matrix()
    w2c = np.eye(4)
    w2c[:3, :3] = R
    w2c[:3, 3] = t
    c2w_recovered = np.linalg.inv(w2c)
    # OpenCV→OpenGL 역변환
    flip = np.diag([1, -1, -1, 1])
    c2w_recovered = c2w_recovered @ flip
    assert np.allclose(c2w_original, c2w_recovered, atol=1e-6)
```

#### Layer 2: Open3D 시각 검증

데이터 처리 후 `visualize_poses.py` 실행:
- 카메라 frustum이 일관된 궤적을 형성하는지 확인
- 모든 frustum이 장면 방향을 가리키는지 확인
- 포인트 클라우드가 궤적 "안쪽"에 위치하는지 확인

#### Layer 3: 단일 프레임 렌더링 테스트

전체 학습 전에, 계산된 viewmat과 K로 단일 프레임 래스터화:
- 학습되지 않은 Gaussians(포인트 위치에 색상 구)라도 실루엣이 캡처 이미지와 대략 일치해야 함

#### Layer 4: Record3D 교차 검증

같은 장면을 커스텀 앱과 Record3D로 캡처하여 포즈를 비교.

### 9.2 폴백 계획

| 실패 모드 | 감지 방법 | 폴백 |
|----------|---------|------|
| 좌표 변환으로 뒤집힌/반전된 렌더링 | 첫 렌더링에서 시각 확인 | 특정 축 부호 변경; Record3D 출력과 비교 |
| LiDAR 깊이가 너무 sparse/noisy | 포인트 클라우드 <10K 또는 산재 분포 | subsample=1로 2배 오버샘플링, 복셀 크기 0.005m로 축소 |
| gsplat이 Apple Silicon에서 실패 (CUDA 없음) | gsplat CUDA 모듈 ImportError | Google Colab T4/A100 GPU 사용; Google Drive로 데이터 전송 |
| COLMAP SfM 실패 | 빈/매우 sparse 재구성 | sequential_matcher 시도; 이미지 수 줄이기; 다른 장면 선택 |
| ARKit 포즈 drift로 정렬 불일치 | 다른 프레임의 포인트 클라우드 불일치 | 캡처 경로에 loop closure 포함; nerfstudio 포즈 refinement |
| 학습 발산/아티팩트 | PSNR <15 dB 또는 NaN loss | 학습률 감소; init_opa 증가; intrinsics 스케일링 확인 |

### 9.3 각 단계별 디버그 시각화

1. **iOS 캡처 후**: metadata.json 확인, transform 값이 미터 단위로 합리적인지, 깊이맵 컬러맵 시각화
2. **좌표 변환 후**: `visualize_poses.py`로 카메라 궤적 + LiDAR 포인트 클라우드 3D 확인
3. **깊이 역투영 후**: 병합된 포인트 클라우드를 .ply로 내보내, Open3D/MeshLab에서 장면 기하 확인
4. **학습 중**: TensorBoard로 loss 곡선, eval 단계에서 렌더링 이미지 모니터링
5. **학습 후**: novel view 렌더링으로 아티팩트(floater, 뒤집힌 기하, 정렬 불량) 시각 검사

---

## 10. 주차별 구현 순서

### Week 1 (4/10-4/16): 캡처 + 기본 변환

**우선 구현 파일:**
1. `ios/LidarCapture/` — iOS 캡처 앱 전체
2. `python/lidargs/io/load_capture.py` — 데이터 로드 검증
3. `python/lidargs/transform/` — 3가지 변환 경로 전부
4. `python/lidargs/viz/visualize_poses.py` — 즉시 변환 검증

### Week 2 (4/17-4/23): 깊이 처리 + 학습 준비

1. `python/lidargs/depth/backproject.py` + `merge_clouds.py`
2. `python/lidargs/io/export_colmap.py`
3. `python/lidargs/train/dataset.py` — Custom Dataset
4. `python/lidargs/train/trainer.py` — simple_trainer.py 적응
5. `python/scripts/01_process_capture.py`
6. 1개 소규모 장면으로 첫 end-to-end 테스트

### Week 3 (4/24-4/30): 디버깅 + 초기화 (최고 위험 주차)

1. 좌표 변환 디버깅 (최고 위험)
2. `python/lidargs/train/init_gaussians.py` — LiDAR 초기화
3. `python/lidargs/depth/filter.py` — 깊이 필터링
4. 학습이 합리적인 렌더링을 생성하는지 검증

### Week 4 (5/1-5/7): 3-Way 파이프라인 완성

1. `python/scripts/run_colmap.sh` — COLMAP 베이스라인
2. `python/scripts/03_train_colmap.py` — Method A
3. `python/scripts/04_train_random.py` — Method C
4. 3가지 방법 모두 결과 생성 확인

### Week 5-6 (5/8-5/21): 실험 실행

1. 3개 장면 모두 캡처
2. `python/scripts/run_all_experiments.sh`
3. `python/lidargs/eval/` — 전체 평가 코드
4. `python/scripts/05_evaluate.py` + `06_generate_tables.py`

### Week 7-8 (5/22-6/7): 논문 작성

1. `python/lidargs/viz/plot_results.py` — 논문 그래프
2. 논문 작성
3. 최종 수정 + 제출 (6/7)

---

## 부록 A: gsplat 주요 참고 자료

- [gsplat Rasterization API](https://docs.gsplat.studio/main/apis/rasterization.html)
- [gsplat Data Conventions](https://docs.gsplat.studio/main/conventions/data_conventions.html)
- [gsplat simple_trainer.py](https://github.com/nerfstudio-project/gsplat/blob/main/examples/simple_trainer.py) — 우리 trainer.py의 기반
- [nerfstudio DataParsers](https://docs.nerf.studio/developer_guides/pipelines/dataparsers.html) — 대안 경로
- [nerfstudio ARKitScenes DataParser](https://docs.nerf.studio/_modules/nerfstudio/data/dataparsers/arkitscenes_dataparser.html) — ARKit 데이터 로딩 참고

## 부록 B: 관련 구현 참고

- **LiDAR-GSplat**: iPhone LiDAR 깊이 감독, 신뢰도 가중 깊이 초기화
- **CF-3DGS**: COLMAP-free, 단안 깊이 추정 + 조인트 포즈-장면 최적화
- **LighthouseGS**: ARKit 네이티브 포즈 + 단안 깊이, 실내 평면 스캐폴드
- **nerfstudio ARKitScenes DataParser**: ARKit 데이터 로딩 레퍼런스 구현
