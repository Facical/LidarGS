import SwiftUI

/// 캡처 데이터 내보내기 (AirDrop / Files 앱).
///
/// `UIFileSharingEnabled`와 `LSSupportsOpeningDocumentsInPlace`가 Info.plist에
/// 설정되어 있으므로 USB + Finder에서도 Documents 폴더 접근이 가능하다.
struct ExportView: View {
    let sceneURL: URL
    let onDone: () -> Void

    @State private var isSharePresented = false

    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "square.and.arrow.up")
                .font(.system(size: 48))
                .foregroundColor(.accentColor)

            Text("데이터 내보내기")
                .font(.title2.bold())

            VStack(alignment: .leading, spacing: 8) {
                Label("AirDrop으로 Mac에 전송", systemImage: "airplayaudio")
                Label("Files 앱에서 직접 접근", systemImage: "folder")
                Label("USB + Finder로 복사", systemImage: "cable.connector")
            }
            .font(.subheadline)
            .foregroundColor(.secondary)

            Spacer()

            VStack(spacing: 12) {
                // 공유 시트
                Button(action: { isSharePresented = true }) {
                    Label("공유", systemImage: "square.and.arrow.up")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .sheet(isPresented: $isSharePresented) {
                    ActivityViewController(activityItems: [sceneURL])
                }

                Button("완료", action: onDone)
                    .buttonStyle(.bordered)
                    .frame(maxWidth: .infinity)
            }
            .padding(.horizontal, 32)
            .padding(.bottom, 24)

            Text("Mac에서: data/raw/\(sceneURL.lastPathComponent)/ 에 배치")
                .font(.caption2)
                .foregroundColor(.secondary)
        }
        .padding(.top, 32)
    }
}

// MARK: - UIActivityViewController Wrapper

struct ActivityViewController: UIViewControllerRepresentable {
    let activityItems: [Any]

    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: activityItems, applicationActivities: nil)
    }

    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
