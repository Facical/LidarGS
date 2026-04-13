import Foundation

/// 단일 캡처 프레임 메타데이터.
/// Python `load_capture.py`가 읽는 JSON 키와 정확히 매칭된다.
struct CapturedFrame: Codable {
    let index: Int
    let timestamp: TimeInterval
    let imagePath: String           // "images/frame_000042.jpg"
    let depthPath: String           // "depths/frame_000042.bin"
    let transform: [[Float]]       // 4x4 camera-to-world, row-major
    let intrinsics: [[Float]]      // 3x3 RGB 카메라 intrinsics
    let imageWidth: Int             // 1920 or 3840
    let imageHeight: Int            // 1080 or 2160
    let depthWidth: Int             // 256 (LiDAR 고정)
    let depthHeight: Int            // 192 (LiDAR 고정)
}
