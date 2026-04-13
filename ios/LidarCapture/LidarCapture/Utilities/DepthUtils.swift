import CoreVideo
import Foundation

/// 캡처 관련 에러.
enum CaptureError: Error, LocalizedError {
    case noDepthData
    case imageConversionFailed
    case fileWriteFailed(String)

    var errorDescription: String? {
        switch self {
        case .noDepthData:
            return "깊이 데이터를 읽을 수 없습니다."
        case .imageConversionFailed:
            return "이미지 변환에 실패했습니다."
        case .fileWriteFailed(let detail):
            return "파일 쓰기 실패: \(detail)"
        }
    }
}

/// LiDAR 깊이맵(CVPixelBuffer, DepthFloat32)을 float32 바이너리 Data로 추출.
///
/// - 포맷: `kCVPixelFormatType_DepthFloat32` (픽셀당 4바이트)
/// - 출력: 256×192×4 = 196,608 bytes, row-major
/// - `bytesPerRow`에 패딩이 있을 수 있으므로 행 단위로 복사한다.
/// - Python 소비: `np.fromfile(dtype=np.float32).reshape(192, 256)`
func extractDepthData(from depthMap: CVPixelBuffer) throws -> Data {
    CVPixelBufferLockBaseAddress(depthMap, .readOnly)
    defer { CVPixelBufferUnlockBaseAddress(depthMap, .readOnly) }

    let width = CVPixelBufferGetWidth(depthMap)     // 256
    let height = CVPixelBufferGetHeight(depthMap)    // 192
    let bytesPerRow = CVPixelBufferGetBytesPerRow(depthMap)

    guard let baseAddress = CVPixelBufferGetBaseAddress(depthMap) else {
        throw CaptureError.noDepthData
    }

    let rowBytes = width * MemoryLayout<Float32>.size
    var data = Data(capacity: rowBytes * height)

    for y in 0..<height {
        let rowPtr = baseAddress.advanced(by: y * bytesPerRow)
        data.append(Data(bytes: rowPtr, count: rowBytes))
    }

    return data
}
