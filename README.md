# Simple Media Player V2

A modern, high-performance desktop media player with Netflix-inspired UI and VLC-style functionality. Built for Windows, macOS, and Linux.

---

## 📋 Functional Requirements

### Core Playback Features
- **Media Playback Control**
  - Play, pause, and stop media files
  - Seek/scrub through media timeline with instant response
  - **Lightning-fast seeking in .ts (Transport Stream) files** - A major improvement over VLC's slow .ts seeking
  - Smooth frame-accurate seeking across all formats
  - Real-time scrubbing during click-and-hold
  
- **Audio Control**
  - Volume adjustment with slider
  - Mute/unmute toggle
  - Multiple audio track selection
  - Audio device selection (default, headphones, HDMI, etc.)
  - Stereo mode options (stereo, mono, left, right)
  
- **Video Control**
  - Multiple video track selection
  - Change aspect ratio (16:9, 4:3, 1:1, 16:10, 2.35:1, custom)
  - Video cropping options
  - Deinterlacing
  - Zoom levels (1:4, 1:2, 1:1, 2:1, fill screen)
  - Take snapshots
  
- **Display Modes**
  - Full-screen mode with auto-hide controls
  - Always on top option
  - Minimal interface mode

### Supported Media Formats
- **Video:** `.mp4`, `.mov`, `.wmv`, `.ts`, `.mpeg`
- **Audio:** `.mp3`, `.wav`

### Advanced Features

#### Netflix-Inspired UI Behavior
- **Auto-Hide Controls:** Player controls automatically hide during playback and reappear on mouse movement
- **Smooth Animations:** All UI transitions use Netflix-style fade and slide animations
- **Progress Bar:** 
  - Hover to enlarge scrubber
  - Visual feedback during seeking
  - Shows current time and total duration
  
#### YouTube-Inspired Interactions
- **Click-to-Play:** Clicking anywhere on the video surface toggles play/pause
- **Keyboard Navigation:**
  - `Left Arrow` / `Right Arrow`: Seek backward/forward 10 seconds
  - `Ctrl+Left` / `Ctrl+Right`: Seek backward/forward 1 minute
  - `Space`: Play/pause toggle
  - `F`: Fullscreen toggle
  - `M`: Mute toggle
  - `Up Arrow` / `Down Arrow`: Volume control
  - `[` / `]`: Decrease/increase playback speed
- **Click-and-Hold Scrubbing:** Press and hold mouse on video to rapidly skim/fast-forward through content

#### Directory Playlist
- **Quick Access Panel:** Netflix-style "Next Episode" button opens a side panel
- **File Browser:** Displays all playable media files from the current file's directory
- **One-Click Switching:** Click any file to immediately start playback
- **Visual Indicators:** Shows currently playing file

#### VLC-Style Menu Bar
Comprehensive native menu bar providing access to all features:

- **Media Menu**
  - Open File, Open Multiple Files, Open Folder
  - Recent Media list
  - Save Playlist
  - Quit application

- **Playback Menu**
  - Play/Pause, Stop, Previous, Next
  - Jump forward/backward (10s, 1min)
  - Playback speed control (0.25x - 2.0x)
  - Recording functionality

- **Audio Menu**
  - Audio track selection
  - Audio device selection
  - Stereo mode options
  - Volume controls
  - Audio visualizations (spectrum, waveform)

- **Video Menu**
  - Video track selection
  - Fullscreen and always on top
  - Aspect ratio and crop settings
  - Deinterlacing options
  - Snapshot capture
  - Zoom controls

- **Subtitles Menu**
  - Subtitle track selection
  - Load external subtitle files
  - Download subtitles
  - Subtitle synchronization
  - Text size adjustment

- **Tools Menu**
  - Audio and video effects/filters
  - Track synchronization
  - Media information and codec details
  - Messages and logs
  - Preferences/Settings

- **View Menu**
  - Playlist view
  - Directory view
  - Minimal interface toggle
  - Advanced controls
  - Status bar

- **Help Menu**
  - Documentation
  - Keyboard shortcuts reference
  - Check for updates
  - About

### Performance Requirements

**Critical Performance Goals:**
- **Ultra-Fast .ts File Seeking:** Near-instantaneous seeking in Transport Stream files
  - Current VLC has notoriously slow .ts seeking (often 2-5+ seconds)
  - **Our target: < 100ms seek response time** for .ts files
  - Achieved through optimized libmpv configuration and stream indexing
  
- **Hardware-Accelerated Playback:**
  - GPU-accelerated video decoding (NVDEC, VideoToolbox, VA-API, DXVA2)
  - Smooth 4K playback with minimal CPU usage
  - Automatic hardware decoder detection and selection
  
- **Responsive User Interface:**
  - < 50ms response time for all UI interactions
  - Smooth 60fps animations for control transitions
  - No UI blocking during file operations
  
- **Efficient Resource Usage:**
  - Low memory footprint (< 200MB for 1080p playback)
  - Minimal CPU usage when hardware decoding is active
  - Fast application startup time (< 1 second)

---

## 🛠️ Tech Stack

### Core Technologies
- **Language:** Python 3.10+
- **UI Framework:** PySide6 (Qt for Python)
- **Media Backend:** python-mpv (libmpv bindings)
  - MPV provides excellent hardware-accelerated playback
  - Superior format support and codec handling
  - Fast seeking performance
  - Cross-platform compatibility

### Key Libraries
- **PySide6:** Qt-based UI framework for native desktop applications
  - QtWidgets for UI components
  - QtCore for signals/slots and core functionality
  - QtGui for graphics and styling
  - QtMultimedia (fallback/supplementary)
  
- **python-mpv:** Python bindings for libmpv
  - Hardware-accelerated video decoding
  - Extensive format support
  - Advanced playback control
  - Low-level access to video rendering

### Platform Support
1. **Windows** (Primary target)
   - Native Windows UI integration
   - DirectX/D3D11 hardware acceleration
   
2. **macOS** (Secondary target)
   - Native macOS menu bar
   - Metal/VideoToolbox hardware acceleration
   
3. **Linux** (Tertiary target)
   - Native Linux desktop integration
   - VA-API/VDPAU hardware acceleration

---

## 🎨 UX Design Specification

### Design Philosophy
**"VLC functionality with Netflix aesthetics"** - Combine the comprehensive feature set of VLC with the polished, modern user experience of Netflix.

### Visual Design System

#### Color Palette
```
Primary Colors:
- Background Overlay:      rgba(0, 0, 0, 0.7)
- Control Background:      rgba(20, 20, 20, 0.9)
- Text Primary:            #FFFFFF
- Text Secondary:          #E5E5E5

Accent Colors:
- Netflix Red (Primary):   #E50914
- Active Red (Pressed):    #B20710
- Hover Gray:              rgba(255, 255, 255, 0.1)

UI Elements:
- Progress Bar Background: rgba(255, 255, 255, 0.3)
- Progress Bar Filled:     #E50914
- Progress Bar Buffered:   rgba(255, 255, 255, 0.5)
- Scrubber Dot:            #E50914 (12px diameter)

Shadows:
- Control Bar Shadow:      0px -10px 30px rgba(0, 0, 0, 0.8)
- Button Hover Shadow:     0px 2px 8px rgba(229, 9, 20, 0.5)
```

#### Typography
```
Font Family: "Netflix Sans" (fallback: "Segoe UI", "Roboto", sans-serif)

Hierarchy:
- Video Title:             18px, Medium (500), White
- Control Labels:          14px, Regular (400), White
- Time Stamps:             14px, Regular (400), White
- Directory Items:         16px, Regular (400), White
- Menu Items:              14px, Regular (400), Off-white
- Hover States:            Bold (700)
```

#### Iconography
- **Style:** Material Design inspired, Netflix-refined
- **Line Weight:** 2px strokes
- **Sizes:** 24x24px (controls), 32x32px (main play button)
- **Colors:** White default, Netflix Red on hover

**Icon Set:**
- ▶ Play, ❚❚ Pause, ⏮ Back 10s, ⏭ Forward 10s
- 🔊 Volume, 🔇 Mute, ⚙ Settings
- □ Fullscreen, ⛶ Exit Fullscreen
- 📁 Directory/Playlist, ← Back

#### Layout Structure

**Screen Regions:**
```
┌────────────────────────────────────────────────────────┐
│ Media  Playback  Audio  Video  Subtitles  Tools  Help │ ← Menu Bar (32px)
├────────────────────────────────────────────────────────┤
│                                                        │
│                  VIDEO PLAYBACK AREA                   │
│                                                        │
│ ┌──────────────────────────────────────────────────┐  │
│ │ ← Title                      [□] [📁] [⚙]       │  │ ← Top Overlay
│ └──────────────────────────────────────────────────┘  │
│                                                        │
│ ┌──────────────────────────────────────────────────┐  │
│ │ ━━━━━━━●━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │  │ ← Progress Bar
│ │ 0:45:23                              1:32:45    │  │
│ │ [▶] [⏮10] [⏭10] [🔊━●━] [⚙] [□] [⛶]           │  │ ← Bottom Controls
│ └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

**Control Bar Specifications:**
- Height: 80px
- Padding: 20px horizontal, 16px vertical
- Button spacing: 16px between controls
- Progress bar margin: 12px from edges
- Progress bar height: 4px (6px on hover)

**Menu Bar Styling:**
- Background: rgba(0, 0, 0, 0.95)
- Height: 32px (Windows/Linux), Native (macOS)
- Dropdown background: rgba(20, 20, 20, 0.98)
- Dropdown shadow: 0px 8px 24px rgba(0, 0, 0, 0.9)
- Menu item height: 32px
- Hover background: rgba(229, 9, 20, 0.15)

#### Animation Timing
```
Control Bar Fade:
- Fade in:              200ms ease-out
- Fade out:             300ms ease-in
- Auto-hide delay:      3000ms (3 seconds)

Button Interactions:
- Hover scale:          1.1 (100ms ease-out)
- Click scale:          0.95 (50ms ease-in)
- Color transition:     150ms ease-out

Progress Bar:
- Scrubber hover scale: 1.5 (150ms ease-out)
- Preview appear:       200ms ease-out

Directory Panel:
- Slide in from right:  300ms ease-out
- Slide out:            250ms ease-in

Menu Animations:
- Dropdown open:        200ms ease-out
- Hover highlight:      150ms ease-out
```

### Interaction Patterns

#### Auto-Hide Behavior
1. Controls visible on mouse movement
2. Auto-hide after 3 seconds of inactivity
3. Controls stay visible when hovering over them
4. Pause state shows controls persistently
5. Menu bar auto-hides in fullscreen (shows on mouse-to-top)

#### Keyboard Shortcuts
```
Playback:
  Space          Play/Pause
  S              Stop
  N              Next
  P              Previous
  [              Slower
  ]              Faster
  =              Normal speed

Seeking:
  Left/Right     -10s / +10s
  Ctrl+Left      -1min
  Ctrl+Right     +1min

Display:
  F              Fullscreen
  F11            Fullscreen Interface
  Ctrl+H         Minimal Interface
  Ctrl+T         Always on Top

Audio:
  M              Mute
  Up/Down        Volume Up/Down
  Ctrl+Up        Increase Volume
  Ctrl+Down      Decrease Volume

File Operations:
  Ctrl+O         Open File
  Ctrl+F         Open Folder
  Ctrl+D         Open Directory
  Ctrl+L         Playlist
  Ctrl+Q         Quit

Tools:
  Ctrl+E         Effects and Filters
  Ctrl+I         Media Information
  Ctrl+J         Codec Information
  Shift+S        Take Snapshot
```

#### Mouse Interactions
- **Single Click on Video:** Play/Pause toggle
- **Click and Hold:** Fast scrubbing/skimming
- **Progress Bar Click:** Jump to position
- **Progress Bar Hover:** Enlarge scrubber, show preview
- **Volume Slider:** Click or drag to adjust
- **Button Hover:** Scale up + red highlight

### Directory Panel Design
```
┌──────────────────────────┐
│  📁 Current Folder       │ ← Header
│  ────────────────────    │
│  ▶ video1.mp4           │
│  ▶ video2.ts     ← Now  │ ← Currently playing (highlighted)
│  ▶ video3.mov           │
│  ▶ audio1.mp3           │
│  ▶ movie.wmv            │
│  ...                     │
└──────────────────────────┘
```

**Styling:**
- Width: 320px
- Background: rgba(20, 20, 20, 0.95)
- Item height: 48px
- Item padding: 12px
- Active item background: rgba(229, 9, 20, 0.2)
- Hover background: rgba(255, 255, 255, 0.05)

---

## 📁 Project Structure (Planned)

```
simple-media-player-v2/
├── src/
│   ├── main.py                 # Application entry point
│   ├── player/
│   │   ├── __init__.py
│   │   ├── mpv_player.py       # MPV backend integration
│   │   ├── video_widget.py     # Video rendering widget
│   │   └── playback_manager.py # Playback state management
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py      # Main application window
│   │   ├── controls.py         # Bottom control bar
│   │   ├── top_bar.py          # Top overlay bar
│   │   ├── menu_bar.py         # VLC-style menu
│   │   ├── directory_panel.py  # Playlist/directory panel
│   │   └── dialogs.py          # Settings, effects, etc.
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── file_manager.py     # File operations
│   │   ├── shortcuts.py        # Keyboard shortcut handler
│   │   └── settings.py         # Application settings
│   └── resources/
│       ├── icons/              # UI icons
│       ├── fonts/              # Netflix Sans font
│       └── styles/             # QSS stylesheets
├── tests/
│   └── ...                     # Unit tests
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── .gitignore
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- libmpv installed on your system
  - **Windows:** Download from https://mpv.io
  - **macOS:** `brew install mpv`
  - **Linux:** `sudo apt install libmpv-dev` (Ubuntu/Debian)

### Installation
```bash
# Clone the repository
git clone https://github.com/ArjunBiswas-99/simple-media-player-v2.git
cd simple-media-player-v2

# Install dependencies
pip install -r requirements.txt

# Run the application
python src/main.py
```

---

## 📝 Development Roadmap

### Phase 1: Core Foundation
- [ ] Project setup and structure
- [ ] MPV integration and basic playback
- [ ] Main window and video widget
- [ ] Basic play/pause/seek controls

### Phase 2: Netflix-Style UI
- [ ] Bottom control bar with auto-hide
- [ ] Top overlay bar
- [ ] Progress bar with hover effects
- [ ] Custom styling (colors, fonts, shadows)

### Phase 3: YouTube-Style Interactions
- [ ] Click-to-play functionality
- [ ] Keyboard shortcuts (arrows, space, etc.)
- [ ] Click-and-hold scrubbing
- [ ] Volume controls

### Phase 4: VLC-Style Menu Bar
- [ ] Native menu bar implementation
- [ ] All menu items and submenus
- [ ] Menu functionality integration
- [ ] Keyboard shortcut display

### Phase 5: Advanced Features
- [ ] Directory playlist panel
- [ ] Audio/video track selection
- [ ] Aspect ratio and crop options
- [ ] Effects and filters
- [ ] Settings/preferences dialog

### Phase 6: Performance & Polish
- [ ] Hardware acceleration optimization
- [ ] Fast seeking optimization (.ts files)
- [ ] Animation polish
- [ ] Bug fixes and testing

### Phase 7: Distribution
- [ ] Windows installer (PyInstaller/Nuitka)
- [ ] macOS .app bundle
- [ ] Linux AppImage/deb package
- [ ] Documentation and user guide

---

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License
[To be determined]

## 🙏 Acknowledgments
- **MPV:** For the excellent media playback engine
- **Qt/PySide6:** For the powerful UI framework
- **Netflix:** For UI/UX inspiration
- **VLC:** For comprehensive feature set inspiration
