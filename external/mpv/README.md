# mpv Libraries

This folder contains mpv (libmpv) libraries for different platforms.

## What is mpv?

mpv is a media player library that handles video/audio playback with perfect A/V sync.
We use it for playing .ts files which have issues with Qt's default player.

## Directory Structure

```
external/mpv/
├── macos/
│   └── libmpv.2.dylib     (macOS - included in repo)
└── windows/
    └── libmpv-2.dll        (Windows - download required)
```

## Windows Setup (For Development)

**libmpv-2.dll is NOT included in the repo** (too large for git, ~25MB).

### Download libmpv for Windows:

1. Go to: https://sourceforge.net/projects/mpv-player-windows/files/libmpv/
2. Download latest `mpv-dev-x86_64-*.7z` (e.g., `mpv-dev-x86_64-20240101.7z`)
3. Extract the archive
4. Find `libmpv-2.dll` inside
5. Copy to `external/mpv/windows/libmpv-2.dll`

**Or use direct link:**
```bash
# From repo root
cd external/mpv/windows
# Download (replace URL with latest)
curl -L -o libmpv.7z "https://sourceforge.net/projects/mpv-player-windows/files/libmpv/mpv-dev-x86_64-latest.7z"
# Extract (requires 7zip)
7z e libmpv.7z libmpv-2.dll
rm libmpv.7z
```

## macOS Setup (For Development)

**libmpv.2.dylib IS included in the repo** (from Homebrew).

If you need to update it:
```bash
brew install mpv
cp /opt/homebrew/Cellar/mpv/*/lib/libmpv.2.dylib external/mpv/macos/
```

## License

mpv is licensed under LGPL 2.1+. We can redistribute the libraries with our application.

- Website: https://mpv.io/
- Source: https://github.com/mpv-player/mpv
- License: https://github.com/mpv-player/mpv/blob/master/LICENSE.LGPL
