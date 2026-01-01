#!/bin/bash
#
# Mac Development Script - Hot Reload Workflow
# Builds the project and watches for changes
#

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build"

echo "🚀 Simple Media Player V2 - Development Mode"
echo "================================================"

# Check if Dear ImGui exists
if [ ! -d "$PROJECT_DIR/external/imgui" ]; then
    echo "⚠️  Dear ImGui not found. Downloading..."
    git clone https://github.com/ocornut/imgui.git "$PROJECT_DIR/external/imgui"
    echo "✅ Dear ImGui downloaded"
fi

# Initial build
if [ ! -d "$BUILD_DIR" ]; then
    echo "🔨 Creating build directory..."
    mkdir -p "$BUILD_DIR"
fi

echo "🔧 Configuring CMake..."
cmake -G Ninja -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE=Debug

echo "🔨 Building project..."
cmake --build "$BUILD_DIR"

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Build successful!"
echo ""
echo "📺 Starting Media Player..."
echo "   (Edit files and save - they will auto-rebuild)"
echo ""

# Start the app in background
"$BUILD_DIR/MediaPlayer" &
APP_PID=$!

# Trap to kill app on script exit
trap "echo '🛑 Stopping Media Player...'; kill $APP_PID 2>/dev/null; exit 0" EXIT INT TERM

# Check if fswatch is installed
if ! command -v fswatch &> /dev/null; then
    echo "⚠️  fswatch not found. Install it for auto-rebuild:"
    echo "   brew install fswatch"
    echo ""
    echo "📺 Media Player is running (PID: $APP_PID)"
    echo "   Press Ctrl+C to stop"
    wait $APP_PID
    exit 0
fi

echo "👀 Watching for file changes..."
echo "   (Press Ctrl+C to stop)"
echo ""

# Watch for changes and rebuild
fswatch -o "$PROJECT_DIR/src" | while read num; do
    echo "🔄 File changed, rebuilding..."
    
    START_TIME=$(date +%s.%N)
    ninja -C "$BUILD_DIR" 2>&1 | head -20
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        END_TIME=$(date +%s.%N)
        DURATION=$(echo "$END_TIME - $START_TIME" | bc)
        echo "✅ Rebuilt in ${DURATION}s"
        echo "   (Restart app to see changes - hot reload coming in Phase 5)"
    else
        echo "❌ Build failed! Fix errors and save again."
    fi
    echo ""
done
