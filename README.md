# Netflix-Style Media Player (Python)

A modern, Netflix-inspired media player built with Python, PyQt6, and MPV.

## Features

- 🎬 Perfect A/V synchronization (powered by MPV)
- 🎨 Netflix-style dark UI with smooth animations
- ⌨️ Full keyboard shortcuts
- 🖱️ Auto-hiding controls with fade animations
- 🎯 Timeline scrubbing
- 🔊 Volume control
- ⛶ Fullscreen support
- 🎞️ Supports all major video formats

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the player
python player.py
```

## Keyboard Shortcuts

- **Space** - Play/Pause
- **Left Arrow** - Seek backward 5s
- **Right Arrow** - Seek forward 5s
- **F** - Toggle fullscreen
- **O** - Open file
- **Esc** - Exit fullscreen

## Controls

- **⏸/▶** - Play/Pause
- **⏪** - Skip backward 10s
- **⏩** - Skip forward 10s
- **🔊** - Volume control
- **⛶** - Fullscreen
- **Timeline** - Click/drag to seek

## Technical Details

- **UI Framework**: PyQt6
- **Video Backend**: python-mpv (MPV bindings)
- **A/V Sync**: Handled automatically by MPV
- **No manual sync code needed**
- **Cross-platform**: Windows, macOS, Linux

## Why Python + MPV?

- MPV handles all A/V synchronization internally
- No need for manual audio/video sync logic
- Professional-grade playback quality
- Simple, maintainable codebase (~300 lines)
- Zero setup hell - just pip install

## License

MIT
