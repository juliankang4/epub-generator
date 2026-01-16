#!/bin/bash

# Ensure we are in the right directory
cd "$(dirname "$0")"

echo "Building EPUB Generator app (PyQt Version)..."

# Activate virtual environment
source ./venv/bin/activate

# Clean previous builds
rm -rf build dist

# Build using PyInstaller
# --noconsole: Don't show terminal window
# --windowed: Mac app bundle
# --name: Name of the application
# --hidden-import: Explicitly include dependencies that might be missed (especially hwp5 plugins)

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

echo "------------------------------------------------"
echo "Build complete! Check the 'dist' folder."
echo "You can move 'dist/EPUB-Generator.app' to your Applications folder."
echo "------------------------------------------------"
