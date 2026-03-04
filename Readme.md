# Phase 1 Minimal Media Player (PySide6 + PyAV)

This repository contains **Phase 1** of a production-grade media player:

- Python 3.11+
- PySide6 (Qt 6)
- PyAV (FFmpeg bindings)
- FFmpeg installed on the system

Strictly minimal feature set (no playlists, no menus, no TS indexing).

## Setup (Windows)

### 1) Create venv

```bat
python -m venv .venv
```

### 2) Install deps

```bat
.venv\Scripts\python -m pip install -r requirements.txt
```

### 3) Run

```bat
.venv\Scripts\python src\app.py
```

## Usage

- Click **Open** and select an `.mp4` file.
- Use **Play/Pause**, timeline seek, and volume.

## Architecture (Phase 1)

- `src/ui/`: widgets, theme, main window (no decode logic)
- `src/playback/`: controller + audio clock/output
- `src/engine/`: decode worker (runs on a separate thread), bounded queues
