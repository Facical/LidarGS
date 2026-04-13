import ARKit
import Combine
import CoreImage
import Foundation
import UIKit

/// ARKit 세션 관리 및 프레임 캡처 로직.
///
/// - 1~2fps로 RGB, LiDAR 깊이, 6DoF 포즈를 캡처
/// - 정상 트래킹 상태(`.normal`)의 프레임만 저장
/// - metadata.json + images/ + depths/ 구조로 출력
class ARSessionManager: NSObject, ObservableObject {

    // MARK: - Published (UI 바인딩)

    @Published var isCapturing = false
    @Published var frameCount = 0
    @Published var trackingStateText = "준비"
    @Published var isDeviceSupported = true

    // MARK: - ARSession

    let session = ARSession()

    // MARK: - Private

    private var capturedFrames: [CapturedFrame] = []
    private var lastCaptureTime: TimeInterval = 0
    private var captureInterval: TimeInterval = 1.0  // 1fps 기본
    private var outputDirectory: URL?
    private var currentSceneName = ""

    /// 디스크 쓰기 전용 직렬 큐 (프레임 순서 보장)
    private let ioQueue = DispatchQueue(label: "com.lidargs.capture.io", qos: .userInitiated)

    /// JPEG 인코딩용 공유 CIContext (생성 비용이 높아 재사용)
    private let ciContext = CIContext()

    // MARK: - Init

    override init() {
        super.init()
        session.delegate = self
        checkDeviceSupport()
    }

    // MARK: - Public Methods

    /// AR 세션 프리뷰 시작 (카메라 권한 요청 + 프리뷰 표시, 캡처는 하지 않음).
    func startPreview() {
        let config = ARWorldTrackingConfiguration()
        config.frameSemantics = [.sceneDepth]
        config.isAutoFocusEnabled = true
        session.run(config, options: [.removeExistingAnchors, .resetTracking])
    }

    /// 캡처 시작.
    ///
    /// - Parameters:
    ///   - sceneName: 씬 이름 (출력 디렉토리 이름)
    ///   - fps: 초당 캡처 프레임 수 (기본 1.0)
    func startCapture(sceneName: String, fps: Double = 1.0) {
        currentSceneName = sceneName
        captureInterval = 1.0 / fps
        capturedFrames = []
        frameCount = 0
        lastCaptureTime = 0

        // 출력 디렉토리 생성
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let sceneDir = docs.appendingPathComponent(sceneName)
        let imagesDir = sceneDir.appendingPathComponent("images")
        let depthsDir = sceneDir.appendingPathComponent("depths")

        try? FileManager.default.removeItem(at: sceneDir)  // 기존 데이터 덮어쓰기
        try? FileManager.default.createDirectory(at: imagesDir, withIntermediateDirectories: true)
        try? FileManager.default.createDirectory(at: depthsDir, withIntermediateDirectories: true)

        outputDirectory = sceneDir
        isCapturing = true
    }

    /// 캡처 중지 및 metadata.json 저장 (프리뷰는 유지).
    ///
    /// - Returns: 캡처 데이터가 저장된 디렉토리 URL
    @discardableResult
    func stopCapture() -> URL? {
        isCapturing = false

        guard let outputDir = outputDirectory else { return nil }

        let metadata = CaptureMetadata(
            deviceModel: deviceModelIdentifier(),
            iosVersion: UIDevice.current.systemVersion,
            captureDate: ISO8601DateFormatter().string(from: Date()),
            sceneName: currentSceneName,
            frameCount: capturedFrames.count,
            samplingFPS: 1.0 / captureInterval,
            frames: capturedFrames
        )

        // metadata.json 저장
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]

        do {
            let jsonData = try encoder.encode(metadata)
            try jsonData.write(to: outputDir.appendingPathComponent("metadata.json"))
        } catch {
            print("[LidarCapture] metadata.json 저장 실패: \(error)")
        }

        return outputDir
    }

    // MARK: - Private Helpers

    private func checkDeviceSupport() {
        isDeviceSupported = ARWorldTrackingConfiguration.isSupported
            && ARWorldTrackingConfiguration.supportsFrameSemantics(.sceneDepth)
    }

    /// 디바이스 모델 식별자 반환 (예: "iPhone16,1").
    private func deviceModelIdentifier() -> String {
        var systemInfo = utsname()
        uname(&systemInfo)
        return withUnsafePointer(to: &systemInfo.machine) {
            $0.withMemoryRebound(to: CChar.self, capacity: 1) {
                String(validatingUTF8: $0) ?? "Unknown"
            }
        }
    }
}

// MARK: - ARSessionDelegate

extension ARSessionManager: ARSessionDelegate {

    func session(_ session: ARSession, didUpdate frame: ARFrame) {
        // 트래킹 상태 업데이트 (UI)
        let stateText = trackingStateString(frame.camera.trackingState)
        DispatchQueue.main.async { self.trackingStateText = stateText }

        // 캡처 중이 아니면 무시
        guard isCapturing else { return }

        // 정상 트래킹만 처리
        guard case .normal = frame.camera.trackingState else { return }

        // 시간 간격 확인 (fps 제한)
        guard frame.timestamp - lastCaptureTime >= captureInterval else { return }

        // LiDAR 깊이 존재 확인
        guard let sceneDepth = frame.sceneDepth else { return }

        // --- 동기적으로 데이터 추출 (픽셀버퍼 재활용 방지) ---
        let index = frameCount
        let timestamp = frame.timestamp
        let transform = frame.camera.transform.toRowMajorArray()
        let intrinsics = frame.camera.intrinsics.toArray()
        let imageWidth = CVPixelBufferGetWidth(frame.capturedImage)
        let imageHeight = CVPixelBufferGetHeight(frame.capturedImage)

        let jpegData: Data
        let depthData: Data
        do {
            jpegData = try createJPEGData(from: frame.capturedImage, context: ciContext)
            depthData = try extractDepthData(from: sceneDepth.depthMap)
        } catch {
            print("[LidarCapture] 프레임 \(index) 데이터 추출 실패: \(error)")
            return
        }

        lastCaptureTime = frame.timestamp

        // --- 디스크 쓰기는 비동기 (직렬 큐) ---
        guard let outputDir = outputDirectory else { return }
        let imgRelPath = "images/frame_\(String(format: "%06d", index)).jpg"
        let depthRelPath = "depths/frame_\(String(format: "%06d", index)).bin"

        ioQueue.async { [weak self] in
            do {
                try jpegData.write(to: outputDir.appendingPathComponent(imgRelPath))
                try depthData.write(to: outputDir.appendingPathComponent(depthRelPath))
            } catch {
                print("[LidarCapture] 프레임 \(index) 파일 쓰기 실패: \(error)")
                return
            }

            let capturedFrame = CapturedFrame(
                index: index,
                timestamp: timestamp,
                imagePath: imgRelPath,
                depthPath: depthRelPath,
                transform: transform,
                intrinsics: intrinsics,
                imageWidth: imageWidth,
                imageHeight: imageHeight,
                depthWidth: 256,
                depthHeight: 192
            )

            DispatchQueue.main.async {
                self?.capturedFrames.append(capturedFrame)
                self?.frameCount += 1
            }
        }
    }

    func session(_ session: ARSession, cameraDidChangeTrackingState camera: ARCamera) {
        let stateText = trackingStateString(camera.trackingState)
        DispatchQueue.main.async { self.trackingStateText = stateText }
    }

    // MARK: - Tracking State Text

    private func trackingStateString(_ state: ARCamera.TrackingState) -> String {
        switch state {
        case .notAvailable:
            return "사용 불가"
        case .limited(let reason):
            switch reason {
            case .initializing:
                return "초기화 중..."
            case .excessiveMotion:
                return "움직임이 너무 빠름"
            case .insufficientFeatures:
                return "특징점 부족"
            case .relocalizing:
                return "재위치 파악 중"
            @unknown default:
                return "제한됨"
            }
        case .normal:
            return "정상"
        }
    }
}
