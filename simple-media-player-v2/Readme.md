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

### Phase 1: Project Setup & Complete UI/UX Mockup
- [ ] **Step 1: Project Initialization:** Set up the directory structure (`src`) and dependencies (`requirements.txt`).
- [ ] **Step 2: Main Application Window:** Create the basic window and the full top-level menu bar.
- [ ] **Step 3: Static UI Elements:** Build the static (non-functional) interface, including the video display area and the complete Netflix-style control bar overlay (Play/Pause, Seek buttons, Volume, Timeline, Timestamps, Playlist button, Fullscreen button).
- [ ] **Step 4: UI Animations & Transitions:** Implement the UI behaviors, such as the auto-hiding of the control bar on inactivity and the smooth slide-in transition for the (initially static) playlist panel.

### Phase 2: Core Playback & Control Wiring
- [ ] **Step 5: Video Playback Integration:** Embed the core video playback engine into the designated video area.
- [ ] **Step 6: Implement "Open File":** Wire up the "Media -> Open File..." menu option to load and play a video file.
- [ ] **Step 7: Connect UI Controls:** Activate the UI by connecting the buttons and sliders (Play, Pause, Volume, Seek) to the video playback engine.

### Phase 3: Advanced Behaviors & Features
- [ ] **Step 8: Interactive Video Behaviors:** Implement YouTube-style interactions (click-to-play/pause, arrow keys to seek, click-hold to fast-forward).
- [ ] **Step 9: Playlist Functionality:** Make the playlist panel dynamic, populating it with media files from the current directory and enabling playback from it.
- [ ] **Step 10: Advanced Menu Features:** Implement the remaining menu functionalities (e.g., Aspect Ratio, Crop).

### Phase 4: Finalization
- [ ] **Step 11: Performance Optimization:** Focus on improving seeking performance, especially for `.ts` files.
- [ ] **Step 12: Application Packaging:** Bundle the application and all its dependencies into a single, distributable `.exe` file.