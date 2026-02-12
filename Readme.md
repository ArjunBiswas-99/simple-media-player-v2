# ArjunBiswasMediaPlayer

ArjunBiswasMediaPlayer is an ambitious, modern media player designed to combine the comprehensive format support and power of players like VLC with the polished, fluid user experience of streaming services like Netflix. It is built from the ground up to be high-performance, cross-platform, and completely free of external dependencies for the end-user.

## Core Features (Functional Requirements)

### 1. Playback & UI
- **Core Controls:** Play, Pause, Stop, and frame-accurate Seek (scrubbing).
- **UI:** A clean, distraction-free video canvas with auto-hiding controls styled after modern streaming platforms.
- **Modes:** Seamless switching between Full-screen and Windowed modes.
- **Interaction:** Drag-and-drop file support, single-click to pause, double-click for fullscreen, and click-and-hold for 2x speed playback.
- **Playlist:** Add, remove, and reorder files with looping (single/all) and shuffle modes.
- **Navigation:** Next/Previous file buttons and frame-by-frame playback.

### 2. Engine & Performance
- **Hardware Acceleration:** GPU-based decoding (DXVA, NVDEC, VideoToolbox, VAAPI) for smooth 4K/8K playback.
- **Zero-Latency Scrubbing:** A high-performance seeking engine for MPEG-TS/TS containers using real-time index generation for instant visual feedback.
- **Low Resource Footprint:** Lightweight and fast to launch.
- **Resume Playback:** Remembers the last playback position for each video.

### 3. Format & Subtitle Support
- **Video Codecs:** MP4, AVI, MKV, MOV, WMV, FLV, TS, and more via `libavcodec`.
- **Audio Codecs:** MP3, WAV, AAC, FLAC, and more.
- **Subtitles:** Internal and external subtitle support (.SRT, .VTT) with on/off toggle.
- **Subtitle Customization:** Ability to change font size, color, position, and timing.

### 4. Advanced Features
- **Audio:** Multi-band equalizer, audio track selection (for multiple languages), and audio delay adjustment.
- **Video:** Real-time post-processing filters (Brightness, Contrast, Saturation), deinterlacing, rotation, and mirroring.
- **360-Degree Video:** Support for spherical video navigation.

### 5. Network & Tools
- **Streaming:** Playback from network URLs (HTTP, RTSP, etc.) and YouTube links.
- **Casting:** Support for Chromecast, AirPlay, or DLNA/UPnP.
- **Utilities:** Snapshot/Screengrab tool and a built-in video transcoder.

## Technical Architecture & Tech Stack

This project prioritizes performance, developer velocity, and a high-quality user experience by leveraging a modern, professional C++ toolchain.

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Language** | **C++17** | For high-performance, low-level control over memory and hardware, which is essential for video processing. |
| **Core Framework** | **Qt 6** | A mature, cross-platform framework for building the application shell, handling events, and rendering. |
| **User Interface** | **QML** | Qt's declarative UI language. Allows for creating fluid, animated, GPU-accelerated interfaces similar to modern web tech, but with native performance. |
| **Media Engine** | **FFmpeg** | The industry-standard open-source media library. Used for all demuxing, decoding, and filtering tasks. We use its core libraries (`libavcodec`, `libavformat`, etc.), not the command-line tool. |
| **Build System** | **CMake** | The modern standard for cross-platform C++ project configuration. It generates native build files (e.g., Visual Studio projects or Makefiles) automatically. |
| **Dependency Mgmt**| **vcpkg** | A C++ package manager from Microsoft. It automates the acquisition and building of third-party libraries like Qt and FFmpeg, eliminating "setup hell". |

## Project Goals

- **Performance:** To deliver a user experience that is always fast and responsive, even when handling high-bitrate 8K video.
- **UX First:** To create an interface that is as intuitive and aesthetically pleasing as the best streaming platforms.
- **Portability:** To maintain a single, clean codebase that compiles and runs natively on Windows, macOS, Linux, Android, and iOS.
- **Self-Contained:** To ship a final application that "just works" for the end-user, with no need to install codecs or runtimes.

## Getting Started (Developer Guide)

### Prerequisites
1.  **Git:** For version control.
2.  **C++ Compiler:** MSVC on Windows (via Visual Studio Build Tools), Clang on macOS (via Xcode), GCC on Linux.
3.  **CMake:** Version 3.21 or higher.
4.  **vcpkg:** For C++ package management.

### Build Steps
1.  Clone the repository:
    ```bash
    git clone <your-repo-url>
    cd ArjunBiswasMediaPlayer
    ```
2.  Configure the project using CMake and the vcpkg toolchain file. This will automatically install dependencies defined in `vcpkg.json`.
    ```bash
    # This command only needs to be run once, or when dependencies change.
    cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=[path-to-vcpkg]/scripts/buildsystems/vcpkg.cmake
    ```
3.  Build the application:
    ```bash
    # This is the command you will run to compile your code.
    cmake --build build
    ```
4.  Run the executable from the build directory:
    ```bash
    ./build/ArjunBiswasMediaPlayer
    ```
