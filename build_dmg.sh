#!/usr/bin/env bash
# PDF 工具箱 — macOS DMG 构建脚本
# 在 macOS 上运行：bash build_dmg.sh
set -euo pipefail

APP_NAME="PDF工具箱"
BUNDLE_ID="com.pdftoolbox.app"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

# 工作目录（构建中间产物放这里，不污染项目）
BUILD_DIR="$SRC_DIR/build_dmg_work"
DIST_DIR="$SRC_DIR/dist"

# ---------- 预检 ----------
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "❌ 此脚本只能在 macOS 上运行"
    exit 1
fi

echo "===== PDF 工具箱 macOS DMG 构建 ====="

# ---------- 可选：应用图标 ----------
ICON_ARG=""
if [ -f "$SRC_DIR/icon.icns" ]; then
    ICON_ARG="--icon=$SRC_DIR/icon.icns"
    echo "[icon] 检测到 icon.icns，将嵌入应用图标"
else
    echo "[icon] 未找到 icon.icns（可选：将 .icns 文件放到项目根目录即可自动使用）"
fi

# ---------- 清理旧构建 ----------
rm -rf "$BUILD_DIR" "$DIST_DIR/$APP_NAME.app" "$DIST_DIR/$APP_NAME.dmg"

# ---------- 创建干净 venv ----------
echo "[venv] 创建干净 Python 虚拟环境…"
PYTHON_BIN="${PYTHON_BIN:-python3}"
"$PYTHON_BIN" -m venv "$BUILD_DIR/venv"
VENV_PYTHON="$BUILD_DIR/venv/bin/python"

echo "[venv] 安装依赖…"
"$VENV_PYTHON" -m pip install --quiet --upgrade pip
"$VENV_PYTHON" -m pip install --quiet PySide6 pypdf pyinstaller

# ---------- PyInstaller 构建 .app ----------
echo "[pyinstaller] 构建 .app 包…"
"$VENV_PYTHON" -m PyInstaller \
    --onedir \
    --windowed \
    --name "$APP_NAME" \
    --osx-bundle-identifier "$BUNDLE_ID" \
    --add-data "$SRC_DIR/_qt_compat.py:." \
    $ICON_ARG \
    --clean \
    --noconfirm \
    --distpath "$DIST_DIR" \
    --workpath "$BUILD_DIR/pyinstaller_work" \
    --specpath "$BUILD_DIR" \
    "$SRC_DIR/main.py"

echo "[pyinstaller] 完成 → $DIST_DIR/$APP_NAME.app"

# ---------- 验证 .app 结构 ----------
APP_PATH="$DIST_DIR/$APP_NAME.app"
if [ ! -d "$APP_PATH" ]; then
    echo "❌ .app 包未生成"
    exit 1
fi
echo "[verify] .app 大小: $(du -sh "$APP_PATH" | cut -f1)"

# ---------- 创建 DMG ----------
echo "[dmg] 创建 DMG…"
DMG_TMP="$BUILD_DIR/dmg_root"
mkdir -p "$DMG_TMP"

# 拷贝 .app
cp -R "$APP_PATH" "$DMG_TMP/"

# 创建 /Applications 快捷方式（macOS 用户习惯：拖到 Applications 文件夹）
ln -s /Applications "$DMG_TMP/Applications"

# 生成 DMG
DMG_PATH="$DIST_DIR/$APP_NAME.dmg"
hdiutil create \
    -volname "$APP_NAME" \
    -srcfolder "$DMG_TMP" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

echo "[dmg] 完成 → $DMG_PATH"
echo "[dmg] DMG 大小: $(du -sh "$DMG_PATH" | cut -f1)"

# ---------- 清理 ----------
rm -rf "$BUILD_DIR"
echo "===== 构建完成 ====="
echo ""
echo "输出文件:"
echo "  .app : $APP_PATH"
echo "  .dmg : $DMG_PATH"
echo ""
echo "用户双击 DMG 后，将 PDF工具箱 拖入 Applications 文件夹即可使用。"
