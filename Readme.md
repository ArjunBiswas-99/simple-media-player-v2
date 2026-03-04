# ArjunMediaPlayer (Phase 1)

ArjunMediaPlayer is a desktop video player built as Phase 1 of a larger production-grade media player project. The current version focuses on getting the fundamentals right: clean architecture, smooth playback for local MP4 files, responsive UI, and modern media-player interactions like skip feedback, volume HUD, and fullscreen controls. The goal of this phase is not feature quantity, but a solid base that we can confidently build on.

## How to run the app

### Prerequisites

- Python **3.11+**
- FFmpeg installed on your system
- Windows environment (current setup and commands below are Windows-friendly)

### 1) Create a virtual environment

```bat
python -m venv .venv
```

### 2) Install dependencies

```bat
.venv\Scripts\python -m pip install -r requirements.txt
```

### 3) Run the app

```bat
cmd /c "set PYTHONPATH=src&& .venv\Scripts\python src\app.py"
```

## Tech stack

- **Python 3.11+**
- **PySide6 (Qt 6)** for desktop UI, widgets, styling, and animations
- **PyAV** for decoding media streams
- **FFmpeg** (system installed) as the backend codec/media engine

## Features

### Functional features

- Open and play local **MP4** files
- Play / Pause control
- Timeline seek (slider-based)
- Volume control via slider
- Volume control via keyboard (**Up/Down**)
- Volume control via mouse wheel (VLC-like)
- Skip backward / forward in steps (with repeated-tap accumulation)
- Skip controls available through buttons and keyboard (**Left/Right**)
- Top on-screen skip feedback (YouTube-style)
- Right-side on-screen volume indicator (VLC-style)
- Fullscreen toggle via:
  - bottom fullscreen button
  - double-click on video area
  - **View → Fullscreen** menu item
  - **F** key

### Technical features

- Clean separation of layers:
  - `src/ui` (presentation)
  - `src/playback` (control and audio master clock)
  - `src/engine` (decode pipeline)
- Dedicated decode thread to keep UI responsive
- Audio-driven synchronization model (audio as master clock)
- Bounded queues for decoded audio/video frames
- Thread-safe communication and controlled UI updates
- Basic seek implementation using container seek on decoded streams

### Non-functional features

- Non-blocking UI behavior during playback operations
- Smooth transitions and overlays for better user experience
- Predictable control behavior (keyboard, mouse, button parity)
- Readable, modular code designed for future phases
- Focus on maintainability over quick hacks

## Project structure

- `src/ui/` — main window, controls, pane overlays, visual styling, icons
- `src/playback/` — playback controller, audio output, clock logic
- `src/engine/` — decoder worker, AV sync scheduler, frame queue
- `src/util/` — debug/log helpers

---

This is Phase 1, so advanced features like playlists, indexing, hardware decode toggles, and full media-management workflows are intentionally out of scope for now.
