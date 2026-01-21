#!/bin/bash

# Ensure we are in the right directory
cd "$(dirname "$0")"

echo "================================================"
echo "  EPUB Generator 빌드 시작 (PyQt 버전)"
echo "================================================"

# Activate virtual environment
source ./venv/bin/activate

# Clean previous builds
rm -rf build dist

# Build using PyInstaller
pyinstaller --noconsole --windowed --clean \
    --name "EPUB-Generator" \
    --add-data "epub_gen.py:." \
    --add-data "text_extractor.py:." \
    --hidden-import "text_extractor" \
    --hidden-import "pypdf" \
    --hidden-import "docx" \
    --hidden-import "hwp5" \
    --hidden-import "hwp5.xmlmodel" \
    --hidden-import "hwp5.hwp5txt" \
    epub_gui_qt.py

# Move to /Applications folder
APP_NAME="EPUB-Generator.app"
DEST="/Applications/$APP_NAME"

if [ -d "dist/$APP_NAME" ]; then
    echo ""
    echo "앱을 /Applications 폴더로 이동합니다..."

    # Remove old version if exists
    if [ -d "$DEST" ]; then
        echo "기존 버전을 삭제합니다..."
        rm -rf "$DEST"
    fi

    # Move new version
    mv "dist/$APP_NAME" "$DEST"

    # Remove quarantine attribute
    xattr -rd com.apple.quarantine "$DEST" 2>/dev/null

    echo ""
    echo "================================================"
    echo "  빌드 완료!"
    echo "  위치: /Applications/EPUB-Generator.app"
    echo "================================================"
else
    echo ""
    echo "❌ 빌드 실패: dist/$APP_NAME 을 찾을 수 없습니다."
    exit 1
fi
