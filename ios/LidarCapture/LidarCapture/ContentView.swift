import SwiftUI

/// 루트 뷰: 캡처 → 리뷰 → 내보내기 흐름 관리.
struct ContentView: View {
    @StateObject private var sessionManager = ARSessionManager()

    enum AppState {
        case capture
        case review(URL)
        case export(URL)
    }

    @State private var appState: AppState = .capture

    var body: some View {
        switch appState {
        case .capture:
            CaptureView(sessionManager: sessionManager) { url in
                appState = .review(url)
            }

        case .review(let url):
            ReviewView(
                sceneURL: url,
                frameCount: sessionManager.frameCount,
                onExport: { appState = .export(url) },
                onRecapture: { appState = .capture }
            )

        case .export(let url):
            ExportView(sceneURL: url) {
                appState = .capture
            }
        }
    }
}
