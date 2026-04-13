#!/bin/bash
# =============================================================================
# COLMAP SfM 파이프라인 실행 스크립트
#
# iPhone 캡처 이미지에 대해 COLMAP Structure-from-Motion을 실행하여
# Method A (Baseline) 데이터를 생성한다.
#
# 사용법:
#   bash run_colmap.sh <scene_path>
#   bash run_colmap.sh data/processed/scene_desk/method_a_colmap
#   bash run_colmap.sh <scene_path> --no-gpu          # CPU 전용
#   bash run_colmap.sh <scene_path> --sequential      # sequential matcher
#
# 입력 구조:
#   <scene_path>/images/     ← RGB 이미지 (JPEG)
#
# 출력 구조:
#   <scene_path>/database.db
#   <scene_path>/sparse/0/cameras.txt
#   <scene_path>/sparse/0/images.txt
#   <scene_path>/sparse/0/points3D.txt
# =============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# 인자 파싱
# ---------------------------------------------------------------------------
if [ $# -lt 1 ]; then
    echo "사용법: $0 <scene_path> [--no-gpu] [--sequential]"
    exit 1
fi

SCENE_PATH="$1"
shift

USE_GPU=1
MATCHER_TYPE="exhaustive"

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-gpu)
            USE_GPU=0
            shift
            ;;
        --sequential)
            MATCHER_TYPE="sequential"
            shift
            ;;
        *)
            echo "알 수 없는 옵션: $1"
            exit 1
            ;;
    esac
done

IMAGE_PATH="${SCENE_PATH}/images"
DATABASE_PATH="${SCENE_PATH}/database.db"
SPARSE_PATH="${SCENE_PATH}/sparse"

# ---------------------------------------------------------------------------
# 입력 검증
# ---------------------------------------------------------------------------
if [ ! -d "${IMAGE_PATH}" ]; then
    echo "오류: 이미지 디렉토리가 없습니다: ${IMAGE_PATH}"
    exit 1
fi

NUM_IMAGES=$(find "${IMAGE_PATH}" -maxdepth 1 -type f \( -name "*.jpg" -o -name "*.jpeg" -o -name "*.png" \) | wc -l)
if [ "${NUM_IMAGES}" -eq 0 ]; then
    echo "오류: 이미지가 없습니다: ${IMAGE_PATH}"
    exit 1
fi

echo "============================================"
echo " COLMAP SfM 파이프라인"
echo " Scene: ${SCENE_PATH}"
echo " Images: ${NUM_IMAGES}장"
echo " GPU: ${USE_GPU}, Matcher: ${MATCHER_TYPE}"
echo "============================================"

# 기존 database 삭제
if [ -f "${DATABASE_PATH}" ]; then
    echo "기존 database.db 삭제"
    rm "${DATABASE_PATH}"
fi

mkdir -p "${SPARSE_PATH}"

TOTAL_START=$(date +%s)

# ---------------------------------------------------------------------------
# Stage 1: Feature Extraction
# ---------------------------------------------------------------------------
echo ""
echo "[1/4] Feature Extraction (SIFT)"
STAGE_START=$(date +%s)

colmap feature_extractor \
    --database_path "${DATABASE_PATH}" \
    --image_path "${IMAGE_PATH}" \
    --ImageReader.camera_model PINHOLE \
    --ImageReader.single_camera 1 \
    --SiftExtraction.use_gpu "${USE_GPU}"

STAGE_END=$(date +%s)
STAGE1_TIME=$((STAGE_END - STAGE_START))
echo "  완료: ${STAGE1_TIME}초"

# ---------------------------------------------------------------------------
# Stage 2: Feature Matching
# ---------------------------------------------------------------------------
echo ""
echo "[2/4] Feature Matching (${MATCHER_TYPE})"
STAGE_START=$(date +%s)

if [ "${MATCHER_TYPE}" = "exhaustive" ]; then
    colmap exhaustive_matcher \
        --database_path "${DATABASE_PATH}" \
        --SiftMatching.use_gpu "${USE_GPU}"
elif [ "${MATCHER_TYPE}" = "sequential" ]; then
    colmap sequential_matcher \
        --database_path "${DATABASE_PATH}" \
        --SiftMatching.use_gpu "${USE_GPU}"
fi

STAGE_END=$(date +%s)
STAGE2_TIME=$((STAGE_END - STAGE_START))
echo "  완료: ${STAGE2_TIME}초"

# ---------------------------------------------------------------------------
# Stage 3: Sparse Reconstruction (Mapper)
# ---------------------------------------------------------------------------
echo ""
echo "[3/4] Sparse Reconstruction (Mapper)"
STAGE_START=$(date +%s)

colmap mapper \
    --database_path "${DATABASE_PATH}" \
    --image_path "${IMAGE_PATH}" \
    --output_path "${SPARSE_PATH}"

STAGE_END=$(date +%s)
STAGE3_TIME=$((STAGE_END - STAGE_START))
echo "  완료: ${STAGE3_TIME}초"

# ---------------------------------------------------------------------------
# Stage 4: Model Converter (Binary → Text)
# ---------------------------------------------------------------------------
echo ""
echo "[4/4] Model Converter (bin → txt)"
STAGE_START=$(date +%s)

# sparse/0이 생성되었는지 확인
if [ ! -d "${SPARSE_PATH}/0" ]; then
    echo "오류: COLMAP mapper가 모델을 생성하지 못했습니다."
    echo "씬의 텍스처가 충분한지 확인하세요."
    exit 1
fi

colmap model_converter \
    --input_path "${SPARSE_PATH}/0" \
    --output_path "${SPARSE_PATH}/0" \
    --output_type TXT

STAGE_END=$(date +%s)
STAGE4_TIME=$((STAGE_END - STAGE_START))
echo "  완료: ${STAGE4_TIME}초"

# ---------------------------------------------------------------------------
# 결과 요약
# ---------------------------------------------------------------------------
TOTAL_END=$(date +%s)
TOTAL_TIME=$((TOTAL_END - TOTAL_START))

# 등록된 이미지 수 파싱
REGISTERED=0
if [ -f "${SPARSE_PATH}/0/images.txt" ]; then
    REGISTERED=$(grep -c "^[0-9]" "${SPARSE_PATH}/0/images.txt" || true)
fi

# 3D 포인트 수 파싱
NUM_POINTS=0
if [ -f "${SPARSE_PATH}/0/points3D.txt" ]; then
    NUM_POINTS=$(grep -c "^[0-9]" "${SPARSE_PATH}/0/points3D.txt" || true)
fi

echo ""
echo "============================================"
echo " COLMAP SfM 완료"
echo "============================================"
echo " 총 소요 시간: ${TOTAL_TIME}초"
echo "   Feature Extraction: ${STAGE1_TIME}초"
echo "   Feature Matching:   ${STAGE2_TIME}초"
echo "   Mapper:             ${STAGE3_TIME}초"
echo "   Model Converter:    ${STAGE4_TIME}초"
echo ""
echo " 등록 이미지: ${REGISTERED} / ${NUM_IMAGES}"
echo " 3D 포인트:   ${NUM_POINTS}"
echo ""
echo " 출력:"
echo "   ${SPARSE_PATH}/0/cameras.txt"
echo "   ${SPARSE_PATH}/0/images.txt"
echo "   ${SPARSE_PATH}/0/points3D.txt"
echo "============================================"

# 타이밍 결과를 JSON으로 저장 (논문용)
cat > "${SCENE_PATH}/colmap_timing.json" << EOF
{
    "total_seconds": ${TOTAL_TIME},
    "feature_extraction_seconds": ${STAGE1_TIME},
    "feature_matching_seconds": ${STAGE2_TIME},
    "mapper_seconds": ${STAGE3_TIME},
    "model_converter_seconds": ${STAGE4_TIME},
    "num_images": ${NUM_IMAGES},
    "num_registered": ${REGISTERED},
    "num_points3d": ${NUM_POINTS},
    "matcher_type": "${MATCHER_TYPE}",
    "use_gpu": ${USE_GPU}
}
EOF
echo " 타이밍 저장: ${SCENE_PATH}/colmap_timing.json"
