#!/bin/bash
# Build script for ArjunBiswasMediaPlayer

set -e

PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BUILD_DIR="$PROJECT_DIR/build"
VCPKG_PATH="${VCPKG_PATH:-$HOME/vcpkg}"

echo "======================================"
echo "ArjunBiswasMediaPlayer Build Script"
echo "======================================"
echo "Project: $PROJECT_DIR"
echo "Build Dir: $BUILD_DIR"
echo "vcpkg Path: $VCPKG_PATH"
echo ""

# Create build directory if needed
if [ ! -d "$BUILD_DIR" ]; then
    echo "Creating build directory..."
    mkdir -p "$BUILD_DIR"
fi

# Configure with CMake
echo "Configuring project with CMake..."
cd "$BUILD_DIR"
cmake "$PROJECT_DIR" -DCMAKE_TOOLCHAIN_FILE="$VCPKG_PATH/scripts/buildsystems/vcpkg.cmake"

# Build
echo ""
echo "Building project..."
cmake --build . --parallel

# Output result
echo ""
echo "======================================"
echo "Build Complete!"
echo "======================================"
echo "Executable: $BUILD_DIR/ArjunBiswasMediaPlayer"
echo ""
echo "To run:"
echo "  $BUILD_DIR/ArjunBiswasMediaPlayer"
echo ""
