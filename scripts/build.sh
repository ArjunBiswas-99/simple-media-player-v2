#!/bin/bash
#
# Quick Build Script for macOS
#

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build"

echo "🔨 Building Simple Media Player V2..."

# Check dependencies
if [ ! -d "$PROJECT_DIR/external/imgui" ]; then
    echo "⚠️  Dear ImGui not found. Downloading..."
    git clone https://github.com/ocornut/imgui.git "$PROJECT_DIR/external/imgui"
fi

# Configure and build
cmake -G Ninja -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE=Release
cmake --build "$BUILD_DIR"

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo ""
    echo "Run with: ./build/MediaPlayer"
else
    echo "❌ Build failed!"
    exit 1
fi
