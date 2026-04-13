import Foundation

/// 캡처 세션 전체 메타데이터.
/// `metadata.json`으로 저장되어 Python 파이프라인에서 소비된다.
struct CaptureMetadata: Codable {
    let deviceModel: String         // "iPhone16,1"
    let iosVersion: String          // "17.4"
    let captureDate: String         // ISO 8601 (예: "2026-04-15T14:30:00Z")
    let sceneName: String
    let frameCount: Int
    let samplingFPS: Double
    let frames: [CapturedFrame]
}
