# Arjun Media Player

A professional media player for Windows with Netflix-like UI and VLC-like features, built with .NET 8 and WPF.

## Features

- **Netflix-like UI**: Modern, dark-themed interface
- **VLC-like Features**: Comprehensive menu system with media, playback, audio, video, subtitle, tools, view, and help options
- **Smooth TS File Playback**: Optimized for Transport Stream files with smooth seeking
- **No External Dependencies**: Uses Windows Media Foundation (built into Windows)
- **Fast Iteration**: Hot reload support for rapid development

## Supported Formats

- MP4
- MOV
- AVI
- MPEG
- WMV
- TS (Transport Stream)

## Requirements

- Windows 10/11
- .NET 8.0 SDK or later

## Running the App

### Development Mode (with Hot Reload)

```powershell
cd C:\Development\simple-media-player-v2\ArjunMediaPlayer
dotnet watch run
```

### Standard Run

```powershell
cd C:\Development\simple-media-player-v2\ArjunMediaPlayer
dotnet run
```

### Build for Release

```powershell
dotnet build -c Release
dotnet publish -c Release -r win-x64 --self-contained true
```

## Project Structure

```
ArjunMediaPlayer/
├── MediaEngine/          # Core media playback engine
├── UI/
│   ├── Controls/        # Custom UI controls
│   ├── Styles/          # Netflix-inspired styling
│   └── ViewModels/      # MVVM view models
├── Services/            # Business logic services
├── Models/              # Data models
└── Utils/               # Utility classes
```

## Development

The app uses:
- **WPF** for the UI framework
- **Media Foundation** for video playback (via MediaElement)
- **Hot Reload** for fast iteration

## Menu Features

- **Media**: Open files, URLs, exit
- **Playback**: Play, pause, stop, previous, next
- **Audio**: Track selection, stereo mode, device selection
- **Video**: Crop, aspect ratio
- **Subtitle**: Track selection, load subtitle files
- **Tools**: Preferences
- **View**: Fullscreen, always on top
- **Help**: About

## Notes

- Some features are marked as TODO and will be implemented in future iterations
- The app uses Windows Media Foundation which is built into Windows 10/11
- No external codec installation required
