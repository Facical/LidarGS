import CoreImage
import CoreVideo
import Foundation

/// ARKit의 capturedImage(CVPixelBuffer, YCbCr)를 JPEG Data로 변환.
///
/// - `CIImage`가 YCbCr → RGB 변환을 자동 처리한다.
/// - `CIContext`는 비용이 크므로 외부에서 공유 인스턴스를 전달받는다.
/// - 기본 품질: 0.9 (90%)
func createJPEGData(
    from pixelBuffer: CVPixelBuffer,
    context: CIContext,
    quality: CGFloat = 0.9
) throws -> Data {
    let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
    let options: [CIImageRepresentationOption: Any] = [
        CIImageRepresentationOption(rawValue: kCGImageDestinationLossyCompressionQuality as String): quality
    ]
    guard let jpegData = context.jpegRepresentation(
        of: ciImage,
        colorSpace: CGColorSpaceCreateDeviceRGB(),
        options: options
    ) else {
        throw CaptureError.imageConversionFailed
    }
    return jpegData
}
