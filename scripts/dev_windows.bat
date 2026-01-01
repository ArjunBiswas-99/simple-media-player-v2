@echo off
REM Windows Development Script - Hot Reload Workflow
REM Builds the project and watches for changes

setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0.."
set "BUILD_DIR=%PROJECT_DIR%\build"

echo ========================================
echo Simple Media Player V2 - Development Mode
echo ========================================
echo.

REM Check if Dear ImGui exists
if not exist "%PROJECT_DIR%\external\imgui" (
    echo [WARNING] Dear ImGui not found. Downloading...
    git clone https://github.com/ocornut/imgui.git "%PROJECT_DIR%\external\imgui"
    echo [OK] Dear ImGui downloaded
)

REM Initial build
if not exist "%BUILD_DIR%" (
    echo Creating build directory...
    mkdir "%BUILD_DIR%"
)

echo Configuring CMake...
cmake -G "Visual Studio 17 2022" -A x64 -B "%BUILD_DIR%"

if errorlevel 1 (
    echo [ERROR] CMake configuration failed!
    pause
    exit /b 1
)

echo Building project...
cmake --build "%BUILD_DIR%" --config Debug

if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo [OK] Build successful!
echo.
echo Starting Media Player...
echo (Edit files and rebuild manually with: cmake --build build --config Debug)
echo.

start "" "%BUILD_DIR%\Debug\MediaPlayer.exe"

echo.
echo Media Player is running.
echo To rebuild after changes, press any key...
echo (Or press Ctrl+C to exit)
pause >nul

:watch_loop
echo.
echo Rebuilding...
cmake --build "%BUILD_DIR%" --config Debug

if errorlevel 1 (
    echo [ERROR] Build failed! Fix errors and try again.
) else (
    echo [OK] Rebuilt successfully!
    echo Restart the app to see changes (hot reload coming in Phase 5)
)

echo.
echo Press any key to rebuild again (or Ctrl+C to exit)...
pause >nul
goto watch_loop
