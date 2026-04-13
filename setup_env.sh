#!/bin/bash
# =============================================================================
# LidarGS 환경 설정 스크립트
# Linux GPU 서버 (A100/A6000)에서 실행
#
# 사용법:
#   chmod +x setup_env.sh
#   ./setup_env.sh
# =============================================================================
set -euo pipefail

ENV_NAME="lidargs"
PYTHON_VERSION="3.10"
CUDA_VERSION="cu121"

echo "============================================"
echo " LidarGS 환경 설정"
echo " Python ${PYTHON_VERSION}, CUDA ${CUDA_VERSION}"
echo "============================================"

# ---------------------------------------------------------------------------
# 1. Conda 환경 생성
# ---------------------------------------------------------------------------
echo ""
echo "[1/5] Conda 환경 생성: ${ENV_NAME} (Python ${PYTHON_VERSION})"

if conda env list | grep -q "^${ENV_NAME} "; then
    echo "  환경 '${ENV_NAME}'이 이미 존재합니다. 건너뜁니다."
    echo "  (재설치하려면: conda env remove -n ${ENV_NAME})"
else
    conda create -n "${ENV_NAME}" python="${PYTHON_VERSION}" -y
    echo "  환경 생성 완료."
fi

# conda activate는 스크립트 내에서 직접 사용 불가 → conda run 사용
CONDA_RUN="conda run -n ${ENV_NAME} --no-banner"

# ---------------------------------------------------------------------------
# 2. PyTorch + CUDA 설치
# ---------------------------------------------------------------------------
echo ""
echo "[2/5] PyTorch + CUDA ${CUDA_VERSION} 설치"

${CONDA_RUN} pip install torch torchvision torchaudio \
    --index-url "https://download.pytorch.org/whl/${CUDA_VERSION}"

echo "  PyTorch 설치 확인:"
${CONDA_RUN} python -c "
import torch
print(f'  PyTorch: {torch.__version__}')
print(f'  CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'  GPU: {torch.cuda.get_device_name(0)}')
    print(f'  VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB')
"

# ---------------------------------------------------------------------------
# 3. gsplat 설치
# ---------------------------------------------------------------------------
echo ""
echo "[3/5] gsplat 설치"

${CONDA_RUN} pip install gsplat

echo "  gsplat 설치 확인:"
${CONDA_RUN} python -c "import gsplat; print(f'  gsplat: {gsplat.__version__}')"

# ---------------------------------------------------------------------------
# 4. 프로젝트 패키지 설치 (editable 모드)
# ---------------------------------------------------------------------------
echo ""
echo "[4/5] lidargs 패키지 설치 (editable 모드)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
${CONDA_RUN} pip install -e "${SCRIPT_DIR}/python[dev,train]"

echo "  lidargs 설치 확인:"
${CONDA_RUN} python -c "import lidargs; print(f'  lidargs: {lidargs.__version__}')"

# ---------------------------------------------------------------------------
# 5. COLMAP 설치 확인
# ---------------------------------------------------------------------------
echo ""
echo "[5/5] COLMAP 설치 확인"

if command -v colmap &> /dev/null; then
    echo "  COLMAP이 이미 설치되어 있습니다:"
    colmap --version 2>&1 | head -1 || echo "  (버전 확인 불가)"
else
    echo "  COLMAP이 설치되어 있지 않습니다."
    echo "  다음 중 하나로 설치하세요:"
    echo ""
    echo "  방법 1 (conda):"
    echo "    conda install -n ${ENV_NAME} -c conda-forge colmap"
    echo ""
    echo "  방법 2 (apt, Ubuntu):"
    echo "    sudo apt install colmap"
    echo ""
    echo "  방법 3 (소스 빌드):"
    echo "    https://colmap.github.io/install.html"
fi

# ---------------------------------------------------------------------------
# 완료
# ---------------------------------------------------------------------------
echo ""
echo "============================================"
echo " 설정 완료!"
echo ""
echo " 사용법:"
echo "   conda activate ${ENV_NAME}"
echo "   cd ${SCRIPT_DIR}/python"
echo "   pytest tests/                    # 테스트 실행"
echo "   python scripts/01_process_capture.py --help"
echo "============================================"
