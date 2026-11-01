#!/usr/bin/env bash
# macOS 一鍵打包：產生 dist/EdgeRunners.app
#
# 用法：  chmod +x build_mac.sh && ./build_mac.sh

set -e
cd "$(dirname "$0")"

echo "============================================================"
echo "  EdgeRunners — macOS build"
echo "============================================================"
echo

# 1) Python
if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] 找不到 python3，請先安裝：brew install python@3.12"
  exit 1
fi
echo "[1/4] Python: $(python3 --version)"

# 2) 虛擬環境
if [ ! -d .venv ]; then
  echo "[2/4] 建立虛擬環境 .venv ..."
  python3 -m venv .venv
else
  echo "[2/4] 使用既有虛擬環境 .venv"
fi
source .venv/bin/activate

# 3) 依賴
echo "[3/4] 安裝依賴（第一次會比較久）..."
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
python -m pip install pyinstaller -q

# 4) 打包
echo "[4/4] 開始打包 ..."
python -m PyInstaller build_mac.spec --noconfirm --clean

echo
echo "============================================================"
echo "  完成！產出： dist/EdgeRunners.app"
echo "============================================================"
echo
echo "  測試：open dist/EdgeRunners.app"
echo "  首次開啟若被 Gatekeeper 攔下：右鍵 → 打開 → 仍要打開"
echo
