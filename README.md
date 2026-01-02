# Simple Media Player V2

A high-performance, Netflix-inspired media player for Windows and macOS with GPU-accelerated playback and modern UI/UX.

# Clone the repo
git clone https://github.com/ArjunBiswas-99/simple-media-player-v2.git
cd simple-media-player-v2

# Clone Dear ImGui into external folder
git clone https://github.com/ocornut/imgui.git external/imgui

# Launch Visual Studio Developer Command Prompt (for MSVC compiler)
& "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\Common7\Tools\LaunchDevCmd.bat"

# Configure with Ninja
cmake -G Ninja -B build -DCMAKE_BUILD_TYPE=Debug

# Build
ninja

# Run the executable
.\build\MediaPlayer.exe


---

## 📋 Functional Specification

### Core Playback Features
- **Playback Controls**: Play, pause, and seek through media files with frame-accurate precision
- **Volume Control**: Adjust volume levels and mute/unmute audio
- **Video Controls**: Change aspect ratio (16:9, 4:3, custom) and crop video
- **Full-Screen Mode**: Seamless full-screen playback experience

### Supported Formats
**Video Formats:**
- `.mp4` - MPEG-4 Video
- `.mov` - QuickTime Movie
- `.wmv` - Windows Media Video
- `.ts` - MPEG Transport Stream (optimized for fast seeking)
- `.mpeg` - MPEG Video

**Audio Formats:**
- `.mp3` - MPEG Audio Layer 3
- `.wav` - Waveform Audio File

### User Interface & Behavior

#### Netflix-Inspired UI
- **Pixel-Perfect Controls**: Play/pause, seek bar, volume slider, and progress bar designed to match Netflix's aesthetic
- **Auto-Hide Controls**: Controls fade out during playback and reappear on mouse movement
- **Smooth Animations**: Fade-in/fade-out transitions matching Netflix's timing (3-second delay)
- **Dark Theme**: Netflix's signature dark background with red accent colors (#E50914)
- **Typography**: SF Pro Display font on macOS (Netflix Sans alternative)

#### YouTube-Inspired Interactions
- **Click-to-Play**: Clicking anywhere on the video surface toggles play/pause
- **Keyboard Shortcuts**: 
  - `Left Arrow` - Seek backward 10 seconds
  - `Right Arrow` - Seek forward 10 seconds
  - `Space` - Toggle play/pause
  - `F` - Toggle full-screen
  - `M` - Mute/unmute
- **Click-and-Hold Scrubbing**: Hold mouse button on video to rapidly skim through content

#### Directory Playlist
- **Episodes Panel**: Netflix-style button near audio controls that opens a right sidebar panel
- **Playlist View**: Shows all playable media files from the current file's directory with "Episode N" style numbering
- **Now Playing Indicator**: Highlights currently playing file with Netflix red accent
- **Quick Navigation**: Click any file in the panel to switch playback instantly

### Menu Bar (VLC-Style)
Comprehensive native menu bar for advanced features:

**Media Menu:**
- Open File (Ctrl/Cmd+O)
- Open Folder (Ctrl/Cmd+Shift+O)
- Quit (Ctrl/Cmd+Q)

**Playback Menu:**
- Control playback speed (0.25x - 2x)
- Jump forward/backward
- Stop playback

**Audio Menu:**
- Select audio tracks (for multi-track files)
- Audio delay adjustment

**Video Menu:**
- Select video tracks
- Change aspect ratio (16:9, 4:3, 1:1, Original)
- Crop video (Top/Bottom/Left/Right)
- Zoom controls

**Tools Menu:**
- Codec Information
- Media Information
- Preferences (placeholder for future features)

### Performance Requirements
- **GPU-Accelerated Decoding**: Hardware-accelerated H.264/H.265 decoding using:
  - Windows: Direct3D 11 with DXVA2
  - macOS: Metal with VideoToolbox
- **Fast Seeking**: Extremely responsive seeking, especially in `.ts` (Transport Stream) files
- **Low Memory**: Target < 200MB RAM usage during playback
- **Smooth Playback**: Locked 60fps UI with zero dropped frames

---

## 🔧 Technical Specification

### Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Language** | C++20 | Native performance, direct hardware access, mature ecosystem |
| **UI Framework** | Dear ImGui | Immediate-mode GUI for pixel-perfect custom controls, GPU-accelerated rendering |
| **Media Decoder** | FFmpeg (libavcodec, libavformat, libavutil) | Industry-standard codec support, optimized TS demuxer, 20+ years of development |
| **Video Rendering** | Direct3D 11 (Windows), Metal (macOS) | Zero-copy GPU rendering, hardware decode acceleration |
| **Audio Output** | WASAPI (Windows), CoreAudio (macOS) | Low-latency audio, native OS integration |
| **Build System** | CMake + Ninja | Fast incremental builds (2-3 seconds), cross-platform |
| **CI/CD** | GitHub Actions | Automated multi-platform builds |

### Why This Stack?

#### ❌ Rejected Technologies
- **Qt**: Requires login/licensing, bloated, difficult setup
- **Electron/Web Tech**: High memory usage (300MB+), poor TS support, startup lag
- **.NET/WPF**: Windows-only, not preferred by developer
- **Python/PyQt**: Not native performance, dependency hell
- **Java/JavaFX**: Not native performance, large runtime
- **VLC Libraries Direct**: Avoided to build custom solution

#### ✅ Why C++ + ImGui + FFmpeg?
1. **Native Performance**: Direct GPU access, no abstraction layers
2. **Cross-Platform**: Single codebase for Windows + macOS (85% shared code)
3. **Fast Iteration**: Hot-reload architecture enables 1-2 second UI updates
4. **Full Control**: Pixel-perfect Netflix UI without framework limitations
5. **Small Binary**: ~50MB app size (vs 200MB+ for Electron)
6. **No Setup Hell**: Pre-built FFmpeg binaries, header-only ImGui

### Architecture

```
┌─────────────────────────────────────────┐
│   Dear ImGui UI Layer                   │
│   - Netflix-style controls              │
│   - Auto-hide animations                │
│   - Hot-reloadable (.dll/.dylib)        │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│   Application Core (C++)                │
│   - Event handling                      │
│   - State management                    │
│   - File system operations              │
└──────────────┬──────────────────────────┘
               │
     ┌─────────┴─────────┐
     ▼                   ▼
┌──────────┐      ┌──────────────┐
│ FFmpeg   │      │ GPU Renderer │
│ Decoder  │─────▶│ D3D11/Metal  │
└──────────┘      └──────────────┘
     │                   │
     └─────────┬─────────┘
               ▼
     ┌──────────────────┐
     │ OS Audio/Video   │
     │ WASAPI/CoreAudio │
     └──────────────────┘
```

### Performance Optimizations

**Compilation Speed:**
- Precompiled headers (PCH) - compile once
- Unity builds - batch compile files
- Incremental linking - link only changed files
- Hot reload DLL - update UI without restart

**Runtime Performance:**
- Zero-copy video rendering (GPU memory → Screen)
- Multi-threaded decode pipeline
- Hardware decode acceleration (DXVA2/VideoToolbox)
- Custom TS demuxer with keyframe indexing

### Platform-Specific Code

| Feature | Windows | macOS | Shared |
|---------|---------|-------|--------|
| UI (ImGui) | ✅ | ✅ | 100% |
| FFmpeg | ✅ | ✅ | 100% |
| Video Output | D3D11 (~200 lines) | Metal (~200 lines) | Interface |
| Audio Output | WASAPI (~150 lines) | CoreAudio (~150 lines) | Interface |
| File Dialogs | Win32 (~50 lines) | Cocoa (~50 lines) | Interface |

**Total platform-specific code: ~15% of codebase**

---

## 🛠️ Development Steps

### Phase 1: GUI Foundation (Week 1)

**Goal**: Build Netflix-style UI with mock data (no video playback yet)

#### Step 1.1: Project Setup
- [ ] Create directory structure (`src/`, `external/`, `scripts/`)
- [ ] Download and integrate Dear ImGui (header-only)
- [ ] Create basic CMake configuration
- [ ] Setup GitHub repository and `.gitignore`

#### Step 1.2: Window and Rendering Context
- [ ] Create main window (Win32/Cocoa)
- [ ] Initialize Direct3D 11 (Windows) or Metal (macOS)
- [ ] Setup ImGui rendering backend
- [ ] Implement main render loop (60fps)

#### Step 1.3: Netflix UI Components
- [ ] **Video Surface**: Fullscreen black rectangle (mock video)
- [ ] **Control Overlay**: Bottom gradient with controls container
- [ ] **Play/Pause Button**: Custom icon rendering (triangle/bars)
- [ ] **Progress Bar**: Netflix-style thin red line with scrubber
- [ ] **Time Display**: Current time / Duration format
- [ ] **Volume Control**: Icon + hover slider
- [ ] **Full-Screen Button**: Icon + click handler

#### Step 1.4: UI Interactions
- [ ] Auto-hide controls (3-second timer on mouse move)
- [ ] Fade in/out animations
- [ ] Click anywhere to toggle play/pause
- [ ] Progress bar hover effects
- [ ] "Next in Folder" button (bottom-right)

#### Step 1.5: Netflix Styling
- [ ] Load custom fonts (Netflix Sans equivalent)
- [ ] Apply Netflix color scheme (#E50914 red, dark grays)
- [ ] Implement smooth transitions
- [ ] Add hover states for all interactive elements

**Deliverable**: Fully functional Netflix-style UI with mock video playback (static image or gradient)

---

### Phase 2: FFmpeg Integration (Week 2)

**Goal**: Replace mock video with actual media playback

#### Step 2.1: FFmpeg Setup
- [ ] Download pre-built FFmpeg binaries
- [ ] Link FFmpeg libraries (libavcodec, libavformat, libavutil)
- [ ] Test basic video decode (file → frames)

#### Step 2.2: Video Decoder
- [ ] Implement `VideoDecoder` class
- [ ] Open media file and read streams
- [ ] Decode video frames to RGB/YUV
- [ ] Upload frames to GPU texture (D3D11/Metal)

#### Step 2.3: Audio Playback
- [ ] Implement `AudioOutput` class (WASAPI/CoreAudio)
- [ ] Decode audio frames
- [ ] Sync audio with video (A/V sync)
- [ ] Implement volume control

#### Step 2.4: Playback Controls
- [ ] Wire play/pause to decoder state
- [ ] Implement seeking (frame-accurate)
- [ ] Handle end-of-file (loop or stop)
- [ ] Display actual video duration

**Deliverable**: Media player that can play MP4 files with audio/video sync

---

### Phase 3: Advanced Features (Week 3)

#### Step 3.1: Format Support
- [ ] Add support for `.ts` files (MPEG-TS demuxer)
- [ ] Add support for `.mov`, `.wmv`, `.mpeg`
- [ ] Add support for `.mp3`, `.wav` audio
- [ ] Optimize TS seeking performance

#### Step 3.2: Directory Playlist
- [ ] Scan current file's directory for media files
- [ ] Build playlist UI panel (side drawer)
- [ ] Implement "Next in Folder" button
- [ ] Auto-play next file on completion

#### Step 3.3: Keyboard Shortcuts
- [ ] Left/Right arrow keys (seek ±10 seconds)
- [ ] Space bar (play/pause)
- [ ] F key (full-screen toggle)
- [ ] M key (mute toggle)

#### Step 3.4: Click-and-Hold Scrubbing
- [ ] Detect mouse hold on video surface
- [ ] Implement rapid seek while held
- [ ] Show timestamp preview

**Deliverable**: Fully functional player with all formats and interactions

---

### Phase 4: Menu Bar & Polish (Week 4)

#### Step 4.1: Native Menu Bar
- [ ] Create platform-specific menu (Win32/Cocoa)
- [ ] Implement Media menu (Open File/Folder, Quit)
- [ ] Implement Playback menu (Speed control)
- [ ] Implement Audio menu (Track selection)
- [ ] Implement Video menu (Aspect ratio, Crop)

#### Step 4.2: Advanced Video Controls
- [ ] Aspect ratio presets (16:9, 4:3, Original)
- [ ] Crop controls (Top/Bottom/Left/Right)
- [ ] Zoom controls

#### Step 4.3: Hardware Acceleration
- [ ] Enable DXVA2 (Windows) for H.264/H.265
- [ ] Enable VideoToolbox (macOS) for H.264/H.265
- [ ] Fallback to software decode if unavailable

#### Step 4.4: Performance Optimization
- [ ] Multi-threaded decode
- [ ] Frame buffer pool (reduce allocations)
- [ ] GPU upload optimization

**Deliverable**: Production-ready media player with all features

---

### Phase 5: Development Tools (Ongoing)

#### Hot Reload Setup
- [ ] Create UI as separate DLL/dylib
- [ ] Implement file watcher (Windows/Mac)
- [ ] Auto-reload on UI code changes
- [ ] Preserve app state during reload

#### CI/CD Pipeline
- [ ] GitHub Actions workflow for Windows builds
- [ ] GitHub Actions workflow for macOS builds
- [ ] Automated testing (basic smoke tests)
- [ ] Release artifact generation

#### Build Scripts
- [ ] `dev_mac.sh` - Auto-rebuild on file change (Mac)
- [ ] `dev_windows.bat` - Auto-rebuild on file change (Windows)
- [ ] `build.sh` / `build.bat` - One-command build

**Deliverable**: Fast development workflow with 1-2 second iteration times

---

## 🚀 Getting Started

### Prerequisites

**macOS:**
```bash
brew install cmake ninja ffmpeg
```

**Windows:**
```powershell
# Install CMake and Ninja
winget install Kitware.CMake Ninja-build.Ninja

# Install Visual Studio Build Tools 2019 (for MSVC compiler)
winget install Microsoft.VisualStudio.2019.BuildTools

# Note: FFmpeg not required for Phase 1 (GUI only)
```

### Build Instructions

```bash
# Clone repository
git clone https://github.com/ArjunBiswas-99/simple-media-player-v2.git
cd simple-media-player-v2

# Download Dear ImGui
git clone https://github.com/ocornut/imgui.git external/imgui

# Build
cmake -G Ninja -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build

# Run
./build/MediaPlayer  # macOS
./build/MediaPlayer.exe  # Windows
```

### Development Mode (Hot Reload)

**macOS:**
```bash
./scripts/dev_mac.sh
# Edit files in src/ui/ → Auto-rebuilds in 1-2 seconds
```

**Windows:**
```powershell
.\scripts\dev_windows.bat
# Edit files in src\ui\ → Auto-rebuilds in 2-3 seconds
```

---

## 🎨 Current Implementation (Phase 1 Complete)

### ✅ What's Working

**Netflix-Style UI:**
- ✓ Proper gradient overlay (300px height, smooth transition)
- ✓ Netflix typography with proper sizing (28px title, 16px time)
- ✓ Geometric outlined icons (play, pause, skip, volume, settings, subtitles, fullscreen)
- ✓ 8px grid spacing system (40-60px edge margins, 16-32px element spacing)
- ✓ Netflix red (#E50914) accent color throughout
- ✓ Auto-hide controls with 3-second timer
- ✓ Smooth fade animations (200ms fade-in, 300ms fade-out)
- ✓ Progress bar with proper styling (4px height, 6px on hover, red scrubber)
- ✓ Play/pause button (48×48px) with custom icons
- ✓ Skip -10/+10 seconds buttons (40×40px)
- ✓ Volume control with icon and slider
- ✓ Settings, subtitles, and fullscreen buttons (32×32px)
- ✓ "Next in Folder" button (200×50px, Netflix white style)
- ✓ Click anywhere to play/pause
- ✓ Mouse movement detection for control visibility

**VLC-Style Menu Bar:**
- ✓ Comprehensive menu system with all standard options
- ✓ Media menu (Open File, Open Folder, Recent, Network Stream, Quit)
- ✓ Playback menu (Play/Pause, Stop, Speed control, Jump Forward/Backward)
- ✓ Audio menu (Track selection, Volume control, Mute)
- ✓ Video menu (Track selection, Fullscreen, Aspect Ratio, Crop, Snapshot)
- ✓ Subtitles menu (Track selection, Load external)
- ✓ Tools menu (Media info, Codec info, Playlist, Preferences)
- ✓ View menu (Playlist panel, Control bar visibility)
- ✓ Help menu (Documentation, Shortcuts, About)
- ✓ Auto-hide with controls (appears on mouse at top 50px)
- ✓ Netflix-style menu appearance (dark background, smooth hover states)

---

## 📦 Project Structure

```
simple-media-player-v2/
├── src/
│   ├── main.cpp                    # Entry point
│   ├── video_decoder.cpp           # FFmpeg video decoding
│   ├── audio_output.cpp            # WASAPI/CoreAudio
│   ├── platform_window.cpp         # Win32/Cocoa window
│   └── ui/                         # Hot-reloadable UI
│       ├── player_ui.cpp           # Main UI renderer
│       ├── controls.cpp            # Control bar components
│       ├── progress_bar.cpp        # Netflix-style progress bar
│       └── playlist_panel.cpp      # Directory playlist
├── external/
│   └── imgui/                      # Dear ImGui (git submodule)
├── scripts/
│   ├── dev_mac.sh                  # Mac hot reload script
│   └── dev_windows.bat             # Windows hot reload script
├── .github/
│   └── workflows/
│       ├── build-windows.yml       # Windows CI
│       └── build-macos.yml         # macOS CI
├── CMakeLists.txt                  # Main build configuration
└── README.md                       # This file
```

---

## 🎯 Roadmap

- [x] Technical specification complete
- [x] Development plan finalized
- [x] **Phase 1: GUI Foundation - COMPLETE** ✅
  - [x] Netflix-style UI with proper gradient overlay
  - [x] Geometric outlined icons
  - [x] 8px grid spacing system
  - [x] VLC-style comprehensive menu bar
  - [x] Auto-hide controls with smooth animations
  - [x] All control buttons (play, pause, skip, volume, settings, etc.)
- [ ] Phase 2: FFmpeg Integration
  - [ ] Video decoder implementation
  - [ ] Audio output (WASAPI/CoreAudio)
  - [ ] Hardware acceleration (DXVA2/VideoToolbox)
  - [ ] Real video playback
- [ ] Phase 3: Advanced Features
  - [ ] All format support (.ts, .mov, .wmv, .mp3, .wav)
  - [ ] Directory playlist
  - [ ] Keyboard shortcuts
  - [ ] Click-and-hold scrubbing
- [ ] Phase 4: Menu Bar & Polish
  - [ ] Implement all menu actions
  - [ ] Aspect ratio controls
  - [ ] Crop controls
  - [ ] Advanced settings
- [ ] Phase 5: Development Tools
  - [ ] Hot reload DLL architecture
  - [ ] Auto-rebuild scripts optimization

---

## � Debugging Crash Issues

### Systematic Approach to Diagnosing Segmentation Faults

When encountering crashes (segfaults, exit code 139), follow this structured debugging methodology:

#### 1. Identify the Pattern
- **Reproduce consistently**: Note exact steps to trigger crash (e.g., "crashes on 2nd/4th seek operation")
- **Check for timing**: Does it happen immediately or after repeated actions?
- **Isolate the feature**: Does crash occur with specific operations (seeking, file loading, playback)?

#### 2. Add Strategic Debug Logging
```cpp
// Log at function entry/exit
std::cout << "[DEBUG ClassName::methodName] Entry, this=" << (void*)this << std::endl;

// Log before/after critical operations
std::cout << "[DEBUG] About to call FFmpeg function" << std::endl;
functionCall();
std::cout << "[DEBUG] FFmpeg function completed" << std::endl;

// Log mutex locks/unlocks
std::cout << "[DEBUG] Acquiring mutex" << std::endl;
std::lock_guard<std::mutex> lock(myMutex);
std::cout << "[DEBUG] Mutex acquired" << std::endl;

// Log thread IDs for multi-threaded issues
std::cout << "[DEBUG] Thread ID: " << std::this_thread::get_id() << std::endl;
```

#### 3. Identify Crash Location
From debug logs, find the **last successful log** before crash - the crash happens in the next operation.

Example:
```
[DEBUG] About to sleep for 50ms     ← Last log
zsh: segmentation fault             ← Crash here
```
**Conclusion**: Crash happens during or immediately after the sleep operation.

#### 4. Analyze Root Cause Categories

**Race Conditions (Multi-threaded)**
- Symptoms: Crash happens after N iterations, timing-dependent
- Signs: Multiple threads accessing shared data (FFmpeg contexts, queues, member variables)
- Solution: Add mutex protection around shared resource access
- Key insight: Checking a flag (`if (m_seeking)`) doesn't prevent TOCTOU (Time-Of-Check-Time-Of-Use) bugs

**Memory Corruption**
- Symptoms: Crash in unrelated system calls (sleep, malloc, etc.)
- Signs: Crash location changes between runs, heap corruption messages
- Solution: Check for double-free, use-after-free, buffer overflows
- Tool: Use AddressSanitizer (`-fsanitize=address`)

**Thread-Unsafe Library Usage**
- Symptoms: Crash when calling library functions from multiple threads
- Signs: FFmpeg, OpenGL, or other C libraries accessed concurrently
- Solution: Serialize access with mutexes or use thread-local contexts
- Example: FFmpeg's `AVFormatContext` is NOT thread-safe

#### 5. Implement Fix with Verification
```cpp
// Example: Protecting FFmpeg contexts with mutex
std::mutex m_ffmpegMutex;

// In decode thread:
{
    std::lock_guard<std::mutex> lock(m_ffmpegMutex);
    av_read_frame(m_formatCtx, packet);  // Protected
    decodePacket(packet);                 // Protected
}

// In main thread (seek):
{
    std::lock_guard<std::mutex> lock(m_ffmpegMutex);
    av_seek_frame(m_formatCtx, ...);     // Protected
    avcodec_flush_buffers(...);          // Protected
}
```

#### 6. Common Pitfalls Solved in This Project

**Seeking Crash (Race Condition)**
- **Problem**: Main thread modified FFmpeg contexts while decode thread was using them
- **Symptom**: Crash on 2nd-6th seek, during `clearQueues()` sleep
- **Root Cause**: `av_read_frame()` in decode thread overlapped with `av_seek_frame()` in main thread
- **Solution**: Added `m_ffmpegMutex` to serialize all FFmpeg API calls

**Seek Position Jump-Back**
- **Problem**: After seeking forward, position immediately jumped back
- **Symptom**: Video seeks to +5s, then resets to original position
- **Root Cause**: Old frames in pipeline had old PTS, which overwrote `currentTime`
- **Solution**: Added `justSeeked` flag to ignore frame timestamps until reaching target position

#### 7. Debugging Tools
```bash
# Run with debugger to get backtrace
lldb ./build/MediaPlayer
(lldb) run
# After crash:
(lldb) bt all           # Backtrace of all threads
(lldb) thread list      # Show all threads
(lldb) frame variable   # Show local variables

# Check for memory issues
cmake -DCMAKE_CXX_FLAGS="-fsanitize=address" -B build
cmake --build build
./build/MediaPlayer

# Monitor system calls (macOS)
sudo dtruss -p <PID>

# Check crash logs (macOS)
log show --predicate 'process == "MediaPlayer"' --last 5m
```

#### 8. Prevention Strategies
- **Minimize shared mutable state** between threads
- **Document thread ownership** of data structures
- **Use RAII** for mutex locks (std::lock_guard)
- **Atomic flags** for boolean state (`std::atomic<bool>`)
- **Validate pointers** before dereferencing (`if (ptr)`)
- **Clear after delete** to catch use-after-free (`ptr = nullptr`)

---

## �📄 License

MIT License - Feel free to use and modify

---

## 🙏 Acknowledgments

- **Dear ImGui** by Omar Cornut - Fantastic immediate-mode GUI
- **FFmpeg** - The backbone of media playback
- **Netflix** - UI/UX inspiration
