import SwiftUI

/// 캡처 완료 후 결과 리뷰 화면.
struct ReviewView: View {
    let sceneURL: URL
    let frameCount: Int
    let onExport: () -> Void
    let onRecapture: () -> Void

    @State private var thumbnails: [UIImage] = []

    var body: some View {
        VStack(spacing: 16) {
            // 헤더
            VStack(spacing: 4) {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 48))
                    .foregroundColor(.green)
                Text("캡처 완료")
                    .font(.title2.bold())
                Text("\(frameCount)개 프레임 저장됨")
                    .foregroundColor(.secondary)
                Text(sceneURL.lastPathComponent)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.top, 24)

            // 썸네일 그리드
            if !thumbnails.isEmpty {
                ScrollView {
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 80))], spacing: 4) {
                        ForEach(0..<thumbnails.count, id: \.self) { i in
                            Image(uiImage: thumbnails[i])
                                .resizable()
                                .aspectRatio(contentMode: .fill)
                                .frame(width: 80, height: 60)
                                .clipped()
                                .cornerRadius(4)
                        }
                    }
                    .padding(.horizontal)
                }
            } else {
                Spacer()
            }

            // 버튼
            VStack(spacing: 12) {
                Button(action: onExport) {
                    Label("내보내기", systemImage: "square.and.arrow.up")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)

                Button(action: onRecapture) {
                    Label("다시 촬영", systemImage: "arrow.counterclockwise")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
            }
            .padding(.horizontal, 32)
            .padding(.bottom, 24)
        }
        .onAppear(perform: loadThumbnails)
    }

    private func loadThumbnails() {
        let imagesDir = sceneURL.appendingPathComponent("images")
        guard let files = try? FileManager.default.contentsOfDirectory(
            at: imagesDir,
            includingPropertiesForKeys: nil
        ) else { return }

        let sorted = files
            .filter { $0.pathExtension == "jpg" }
            .sorted { $0.lastPathComponent < $1.lastPathComponent }

        // 최대 50개까지만 로드
        let limited = Array(sorted.prefix(50))

        DispatchQueue.global(qos: .userInitiated).async {
            let images = limited.compactMap { url -> UIImage? in
                guard let data = try? Data(contentsOf: url) else { return nil }
                return UIImage(data: data)?.preparingThumbnail(of: CGSize(width: 160, height: 120))
            }
            DispatchQueue.main.async {
                thumbnails = images
            }
        }
    }
}
