#!/bin/bash

# Ensure we are in the right directory
cd "$(dirname "$0")"

echo "Building EPUB Generator app..."

# Activate virtual environment
source ./venv/bin/activate

# Build using PyInstaller
# --noconsole: Don't show terminal window
# --onefile: Bundle everything into one file (optional, .app bundle is usually better for Mac)
# --name: Name of the application
pyinstaller --noconsole --clean \
    --name "EPUB-Generator" \
    --add-data "epub_gen.py:." \
    epub_gui.py

echo "------------------------------------------------"
echo "Build complete! Check the 'dist' folder."
echo "You can move 'dist/EPUB-Generator.app' to your Applications folder."
echo "------------------------------------------------"
