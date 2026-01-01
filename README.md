# Simple Media Player v2

A modern, high-performance desktop media player that combines the feature-set of VLC with the user experience of Netflix and YouTube.

---

## Technology Stack

This project uses a carefully selected stack to prioritize developer productivity and meet all functional and performance requirements.

-   **Core Application Logic:** **Python**
    -   Acts as the "brain" of the application, connecting the user interface to the video player engine. Chosen for its fast and simple development cycle.

-   **UI Framework:** **PySide6 (Qt6 / QML)**
    -   The official Python bindings for the powerful Qt6 framework. We will use QML, Qt's declarative language, to build the fluid, animated, Netflix-style user interface. This allows us to build a rich, custom UI without the complexity of traditional C++ development.

-   **Video Playback Engine:** **`libmpv`**
    -   A high-performance, native C library that handles all video and audio decoding and rendering. We will control it via the `python-mpv` wrapper library. This gives us world-class playback performance, including fast seeking in `.ts` files.

-   **Packaging:** **PyInstaller**
    -   This tool will bundle our Python code, all required libraries (PySide6, python-mpv), and the `mpv` engine into a single, standalone `.exe` file for easy distribution.

This stack was chosen because it offers the fastest development path while meeting all technical requirements. It avoids the slow compile times of C++ and completely bypasses the complex Qt SDK installation by using a simple `pip install PySide6` command.

---

## Features (Functional Requirements)

### Core Playback
- Play, pause, and seek media files.
- Adjust volume and mute audio.
- Change aspect ratio and crop video.
- Full-screen mode.

### Supported Formats
- **Video:** `.mp4`, `.mov`, `.wmv`, `.ts`, `.mpeg`
- **Audio:** `.mp3`, `.wav`

### Player UI & Behavior
- **Netflix-Inspired UI:** The player controls (play/pause, seek, volume, progress bar) are a pixel-perfect replica of the Netflix player UI. Controls auto-hide during playback and reappear on mouse movement.
- **YouTube-Inspired Interactions:**
    - Clicking anywhere on the video toggles play/pause.
    - Pressing the `Left` and `Right` arrow keys seeks backward and forward.
    - Clicking and holding the mouse on the video surface rapidly skims/fast-forwards through the content.
- **Directory Playlist:** A button on the control bar, styled like Netflix's "Next Episode" button, opens a panel displaying all other playable media files from the currently open file's directory.

### Menu Bar
A comprehensive, VLC-style native menu bar provides access to all features:
- **Media:** Open File, Open Folder, Quit.
- **Playback:** Control playback speed.
- **Audio:** Select audio tracks.
- **Video:** Select video tracks, change aspect ratio, and crop.
- **Tools:** Placeholder for future features.

### Performance
- Optimized for GPU-accelerated hardware decoding for smooth playback.
- Extremely fast and responsive seeking, especially in `.ts` (Transport Stream) files.

---

## User Experience (UX) Design

### Color Palette
- **Primary Background:** Near-black (`#141414`)
- **Primary Text/Icons:** White (`#FFFFFF`)
- **Accent/Highlight:** Netflix Red (`#E50914`)
- **Secondary Text:** Light grey (`#AAAAAA`)

### Typography
- **Font:** A clean, standard sans-serif font (e.g., Segoe UI on Windows).
- **Style:** Legible, with a subtle drop-shadow when overlaid on video to ensure readability.

### Iconography
- **Style:** Minimalist, solid, and universally understood icons.

### Animations & Behavior
- **Control Fade:** The control overlay will fade in and out smoothly (~300ms).
- **Button Feedback:** Subtle scale/opacity change on hover and click.
- **Panel Slide:** The directory playlist panel will slide in smoothly from the side.

---

## Development Plan

This checklist outlines the detailed steps for building the application, focusing on completing the user interface first.

### Phase 1: Complete UI/UX Mockup (GUI First) ✨
- [ ] **Step 1.1: Project Setup**
  - Initialize project structure (`src/`, `assets/`, `main.py`)
  - Create `requirements.txt` with PySide6
  - Set up basic Python entry point

- [ ] **Step 1.2: Main Window & Menu Bar**
  - Create main QML application window (dark theme #141414)
  - Implement full VLC-style native menu bar with all items (Media, Playback, Audio, Video, Tools)
  - Menu items non-functional at this stage (just UI)

- [ ] **Step 1.3: Netflix-Style Control Overlay (Static)**
  - Design control bar at bottom with all elements:
    - Play/Pause button (center-left)
    - Previous/Next seek buttons
    - Volume slider with mute button
    - Progress bar/timeline with hover preview
    - Current time / Total time labels
    - Playlist button (Netflix "Episodes" style)
    - Fullscreen button (right)
  - Use Netflix red (#E50914) for accents
  - Position as overlay on video area

- [ ] **Step 1.4: Video Display Area (Placeholder)**
  - Create central black rectangle as video placeholder
  - Ensure controls overlay properly on top

- [ ] **Step 1.5: Playlist Panel UI (Static)**
  - Design slide-in panel (right side, Netflix style)
  - Show mock playlist items with thumbnails
  - Add close button

- [ ] **Step 1.6: UI Animations & Behaviors**
  - Implement auto-hide control bar (fade out after 3s of inactivity, fade in on mouse move)
  - Add hover effects on buttons (scale/opacity)
  - Implement playlist panel slide-in/out animation (300ms smooth)
  - Add button click feedback animations

- [ ] **Step 1.7: UI Polish & Testing**
  - Test all animations and transitions
  - Verify responsive layout
  - Ensure pixel-perfect Netflix aesthetic
  - **Milestone: Fully functional, beautiful GUI with no video playback yet**

---

### Phase 2: Video Engine Integration 🎬
- [ ] **Step 2.1: libmpv Setup**
  - Add `python-mpv` to requirements
  - Create mpv player instance wrapper class
  - Integrate mpv rendering into QML video area (OpenGL surface)

- [ ] **Step 2.2: Basic Playback**
  - Wire "Media → Open File" to load video
  - Test basic play functionality
  - Verify video renders in display area

- [ ] **Step 2.3: Connect Core Controls**
  - Wire Play/Pause button → mpv
  - Wire seek buttons (±10s) → mpv
  - Wire volume slider → mpv
  - Wire progress bar scrubbing → mpv seek
  - Update timestamps in real-time

- [ ] **Step 2.4: Test & Debug Core Playback**
  - Test with all supported formats (.mp4, .ts, etc.)
  - Verify seeking performance

---

### Phase 3: Advanced Features & Interactions 🚀
- [ ] **Step 3.1: YouTube-Style Interactions**
  - Click anywhere on video → toggle play/pause
  - Arrow keys (←/→) → seek backward/forward
  - Click-and-hold → fast-forward/skim

- [ ] **Step 3.2: Dynamic Playlist**
  - Scan current file's directory for media
  - Populate playlist panel dynamically
  - Click playlist item → play that file

- [ ] **Step 3.3: Menu Functionality**
  - Implement "Open Folder" dialog
  - Implement aspect ratio menu
  - Implement crop menu
  - Implement playback speed control
  - Implement audio/video track selection

- [ ] **Step 3.4: Fullscreen Mode**
  - Wire fullscreen button
  - Handle ESC key to exit fullscreen

---

### Phase 4: Optimization & Packaging 📦
- [ ] **Step 4.1: Performance Tuning**
  - Enable hardware acceleration
  - Optimize .ts file seeking
  - Profile and fix any lag/stuttering

- [ ] **Step 4.2: PyInstaller Packaging**
  - Create `.spec` file
  - Bundle libmpv binaries
  - Test standalone .exe
  - Create application icon

- [ ] **Step 4.3: Final Testing & Release**
  - Cross-test all features
  - Document known issues
  - Create README for end users
