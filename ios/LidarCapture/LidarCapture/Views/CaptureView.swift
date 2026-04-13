import ARKit
import RealityKit
import SwiftUI

/// AR 카메라 프리뷰를 UIViewRepresentable로 래핑.
struct ARViewContainer: UIViewRepresentable {
    let session: ARSession

    func makeUIView(context: Context) -> ARView {
        let arView = ARView(frame: .zero)
        arView.session = session
        arView.renderOptions = [
            .disableMotionBlur,
            .disableDepthOfField,
            .disableFaceMesh,
            .disablePersonOcclusion,
        ]
        return arView
    }

    func updateUIView(_ uiView: ARView, context: Context) {}
}

/// 캡처 화면: AR 카메라 프리뷰 + 녹화 컨트롤 오버레이.
struct CaptureView: View {
    @ObservedObject var sessionManager: ARSessionManager
    let onCaptureComplete: (URL) -> Void

    @State private var sceneName = "scene_lab"
    @State private var selectedFPS: Double = 1.0
    @State private var previewStarted = false

    private let fpsOptions: [Double] = [0.5, 1.0, 2.0]

    var body: some View {
        ZStack {
            // AR 카메라 프리뷰
            ARViewContainer(session: sessionManager.session)
                .ignoresSafeArea()

            // 오버레이
            VStack {
                // 상단: 씬 이름 + 트래킹 상태
                topBar
                Spacer()
                // 하단: 프레임 카운터 + 컨트롤
                bottomControls
            }
            .padding()

            // 디바이스 미지원 안내
            if !sessionManager.isDeviceSupported {
                unsupportedOverlay
            }
        }
        .navigationBarHidden(true)
        .onAppear {
            if !previewStarted {
                sessionManager.startPreview()
                previewStarted = true
            }
        }
    }

    // MARK: - Top Bar

    private var topBar: some View {
        VStack(spacing: 8) {
            // 트래킹 상태
            HStack {
                Circle()
                    .fill(trackingColor)
                    .frame(width: 10, height: 10)
                Text(sessionManager.trackingStateText)
                    .font(.caption)
                    .foregroundColor(.white)
                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 8))

            // 씬 이름 입력
            if !sessionManager.isCapturing {
                TextField("씬 이름 (예: scene_desk)", text: $sceneName)
                    .textFieldStyle(.roundedBorder)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
            }
        }
    }

    // MARK: - Bottom Controls

    private var bottomControls: some View {
        VStack(spacing: 16) {
            // 프레임 카운터
            if sessionManager.isCapturing {
                Text("\(sessionManager.frameCount) frames")
                    .font(.title2.monospacedDigit())
                    .foregroundColor(.white)
                    .padding(.horizontal, 20)
                    .padding(.vertical, 8)
                    .background(.ultraThinMaterial, in: Capsule())
            }

            // FPS 선택 (캡처 전만)
            if !sessionManager.isCapturing {
                HStack(spacing: 12) {
                    Text("FPS")
                        .foregroundColor(.white)
                        .font(.caption)
                    Picker("FPS", selection: $selectedFPS) {
                        ForEach(fpsOptions, id: \.self) { fps in
                            Text(String(format: "%.1f", fps)).tag(fps)
                        }
                    }
                    .pickerStyle(.segmented)
                    .frame(width: 180)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 8)
                .background(.ultraThinMaterial, in: Capsule())
            }

            // Start / Stop 버튼
            Button(action: toggleCapture) {
                Image(systemName: sessionManager.isCapturing ? "stop.circle.fill" : "record.circle")
                    .font(.system(size: 72))
                    .foregroundColor(sessionManager.isCapturing ? .white : .red)
            }
            .disabled(!sessionManager.isDeviceSupported || (!sessionManager.isCapturing && sceneName.isEmpty))
        }
    }

    // MARK: - Unsupported Overlay

    private var unsupportedOverlay: some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 48))
                .foregroundColor(.yellow)
            Text("이 기기는 LiDAR를 지원하지 않습니다.")
                .font(.headline)
            Text("iPhone 15 Pro / 16 Pro 이상이 필요합니다.")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .padding(32)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 16))
    }

    // MARK: - Actions

    private func toggleCapture() {
        if sessionManager.isCapturing {
            if let url = sessionManager.stopCapture() {
                onCaptureComplete(url)
            }
        } else {
            sessionManager.startCapture(sceneName: sceneName, fps: selectedFPS)
        }
    }

    // MARK: - Helpers

    private var trackingColor: Color {
        switch sessionManager.trackingStateText {
        case "정상": return .green
        case "사용 불가": return .red
        default: return .yellow
        }
    }
}
