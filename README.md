# Netflix-Style Media Player v2.1

A professional, Netflix-inspired media player with minimal VLC-style controls, built with Python and PyQt6.

## ✨ Features

### Core Playback
- 🎬 **Perfect A/V Sync** - Powered by Qt Multimedia with FFmpeg 7.1.2
- 🎯 **Click-to-Seek** - Click anywhere on timeline to jump instantly
- ⚡ **YouTube 2x Speed** - Hold mouse on video for 2× playback
- 🎞️ **Format Support** - MP4, MKV, AVI, MOV, WMV, FLV, WebM, MPG, MPEG

### UX Excellence
- 🎨 **Minimal Controls** - VLC-inspired compact design (~65px height)
- 📁 **Playlist Popover** - Browse all videos in current folder
- ⚙️ **Speed Control** - 0.25× to 2× with glass-effect popover
- 🌙 **Auto-Hide Controls** - Fade after 3s in fullscreen
- 🎭 **Netflix Aesthetics** - Professional red/black color scheme

### Professional Features
- 🎹 **VLC Menu Bar** - File, Playback, Audio, Video, Help menus
- ⌨️ **Full Keyboard Control** - Space, arrows, F11, volume, mute
- 🖱️ **Smart Mouse Gestures** - Double-click fullscreen, hold for 2×
- ⛶ **Dual-Mode Behavior** - Controls stay in windowed, hide in fullscreen

## 🚀 Quick Start

```bash
# Install dependencies
pip install PyQt6 PyQt6-Multimedia

# Run the player
python main.py
```

## 📁 Project Structure (SOLID Principles)

```
simple-media-player-v2/
├── main.py                    # Entry point with Qt application setup
├── media_player.py            # Main window orchestration
├── constants.py               # Netflix colors, sizes, dimensions
├── styles.py                  # Reusable stylesheet generators
└── widgets/
    ├── __init__.py
    ├── speed_indicator.py     # YouTube-style 2× overlay
    ├── playlist_popover.py    # Netflix folder video list
    └── settings_popover.py    # Speed control popover
```

### Architecture Highlights
- **Single Responsibility**: Each module has one clear purpose
- **Open/Closed**: Styles/constants easily extended
- **DRY**: Reusable style generators, no duplication
- **Separation of Concerns**: UI, logic, and styling separated

## ⌨️ Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Space** | Play/Pause |
| **Left/Right** | Seek ±5s |
| **Up/Down** | Volume ±5% |
| **F / F11** | Toggle fullscreen |
| **M** | Mute/Unmute |
| **S** | Stop |
| **O** | Open file dialog |
| **Esc** | Exit fullscreen |

## 🎮 Controls

```
[▶/⏸] [⏪] [⏩] [⏹] | [🔊][━━━━] [1×] [☰] [⚙] | [0:00] [⛶]
  ^     ^    ^    ^      ^     ^    ^   ^   ^      ^    ^
  |     |    |    |      |     |    |   |   |      |    └─ Fullscreen
  |     |    |    |      |     |    |   |   |      └────── Time
  |     |    |    |      |     |    |   |   └───────────── Settings
  |     |    |    |      |     |    |   └───────────────── Playlist
  |     |    |    |      |     |    └───────────────────── Speed
  |     |    |    |      |     └────────────────────────── Volume
  |     |    |    |      └──────────────────────────────── Mute
  |     |    |    └─────────────────────────────────────── Stop
  |     |    └──────────────────────────────────────────── Forward 10s
  |     └───────────────────────────────────────────────── Rewind 10s
  └─────────────────────────────────────────────────────── Play/Pause (PRIMARY)
```

## 🛠️ Technical Stack

- **UI Framework**: PyQt6 6.x
- **Video Backend**: Qt Multimedia (QMediaPlayer + FFmpeg 7.1.2)
- **A/V Sync**: Native Qt synchronization (no manual code)
- **Python**: 3.10+ required
- **Platform**: Cross-platform (macOS, Windows, Linux)

## Why Python + MPV?

- MPV handles all A/V synchronization internally
- No need for manual audio/video sync logic
- Professional-grade playback quality
- Simple, maintainable codebase (~300 lines)
- Zero setup hell - just pip install

## License

MIT
