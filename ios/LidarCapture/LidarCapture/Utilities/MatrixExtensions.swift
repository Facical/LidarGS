import simd

// MARK: - simd_float4x4 (column-major → row-major)

extension simd_float4x4 {
    /// ARKit의 column-major simd_float4x4를 row-major 2D 배열로 변환.
    ///
    /// `cols[c][r]` → `result[r][c]`
    /// JSON에 row-major로 저장하여 Python `np.array()`가 바로 (4,4)로 읽을 수 있게 한다.
    func toRowMajorArray() -> [[Float]] {
        let cols = [columns.0, columns.1, columns.2, columns.3]
        return (0..<4).map { r in
            (0..<4).map { c in cols[c][r] }
        }
    }
}

// MARK: - simd_float3x3 (column-major → row-major)

extension simd_float3x3 {
    /// ARKit의 column-major simd_float3x3를 row-major 2D 배열로 변환.
    ///
    /// 카메라 intrinsics `[fx, 0, cx; 0, fy, cy; 0, 0, 1]` 형태로 저장.
    func toArray() -> [[Float]] {
        let cols = [columns.0, columns.1, columns.2]
        return (0..<3).map { r in
            (0..<3).map { c in cols[c][r] }
        }
    }
}
