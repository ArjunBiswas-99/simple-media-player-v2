"""
Menu Bar - VLC-style comprehensive menu system.

Responsibilities:
- Create native menu bar with all VLC-style menus
- Handle menu action signals
- Apply Netflix styling where possible
- Provide access to all player features
"""

from PySide6.QtWidgets import QMenuBar, QMenu
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Signal, Qt
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import Colors, Shortcuts


class MenuBar(QMenuBar):
    """
    VLC-style menu bar with Netflix-inspired styling.
    
    Responsibilities:
    - Create all menu items matching VLC functionality
    - Emit signals for menu actions
    - Apply Netflix color scheme
    - Organize menus logically
    
    Signals:
        Various signals for each menu action
    """
    
    # File/Media signals
    openFileRequested = Signal()
    openMultipleFilesRequested = Signal()
    openFolderRequested = Signal()
    openDirectoryRequested = Signal()
    quitRequested = Signal()
    
    # Playback signals
    playPauseRequested = Signal()
    stopRequested = Signal()
    previousRequested = Signal()
    nextRequested = Signal()
    seekForwardRequested = Signal()
    seekBackwardRequested = Signal()
    speedChanged = Signal(float)
    
    # Audio signals
    audioTrackSelected = Signal(int)
    audioDeviceSelected = Signal(str)
    volumeUpRequested = Signal()
    volumeDownRequested = Signal()
    muteRequested = Signal()
    
    # Video signals
    videoTrackSelected = Signal(int)
    fullscreenRequested = Signal()
    alwaysOnTopToggled = Signal(bool)
    aspectRatioChanged = Signal(str)
    cropChanged = Signal(str)
    snapshotRequested = Signal()
    
    # Subtitle signals
    subtitleTrackSelected = Signal(int)
    loadSubtitleRequested = Signal()
    
    # Tools signals
    effectsFiltersRequested = Signal()
    mediaInfoRequested = Signal()
    codecInfoRequested = Signal()
    preferencesRequested = Signal()
    
    # View signals
    playlistRequested = Signal()
    directoryViewRequested = Signal()
    minimalInterfaceToggled = Signal(bool)
    
    def __init__(self, parent=None):
        """Initialize menu bar."""
        super().__init__(parent)
        
        # State tracking
        self._always_on_top = False
        self._minimal_interface = False
        
        # Apply Netflix styling
        self._apply_style()
        
        # Create all menus
        self._create_media_menu()
        self._create_playback_menu()
        self._create_audio_menu()
        self._create_video_menu()
        self._create_subtitles_menu()
        self._create_tools_menu()
        self._create_view_menu()
        self._create_help_menu()
        
    def _apply_style(self):
        """Apply Netflix-inspired menu styling."""
        self.setStyleSheet(f"""
            QMenuBar {{
                background: {Colors.MENU_BACKGROUND};
                color: {Colors.TEXT_SECONDARY};
                font-size: 13px;
                spacing: 8px;
                padding: 4px 8px;
            }}
            
            QMenuBar::item {{
                background: transparent;
                padding: 4px 12px;
            }}
            
            QMenuBar::item:selected {{
                background: {Colors.MENU_HOVER};
                color: {Colors.TEXT_PRIMARY};
            }}
            
            QMenu {{
                background: {Colors.MENU_DROPDOWN_BACKGROUND};
                border: 1px solid {Colors.MENU_BORDER};
                color: {Colors.TEXT_SECONDARY};
            }}
            
            QMenu::item {{
                padding: 8px 32px 8px 16px;
                min-width: 200px;
            }}
            
            QMenu::item:selected {{
                background: {Colors.MENU_HOVER};
                color: {Colors.TEXT_PRIMARY};
            }}
            
            QMenu::separator {{
                height: 1px;
                background: {Colors.MENU_SEPARATOR};
                margin: 4px 0px;
            }}
        """)
        
    def _create_media_menu(self):
        """Create Media menu (File operations)."""
        media_menu = self.addMenu("Media")
        
        # Open File
        open_file = QAction("Open File...", self)
        open_file.setShortcut(QKeySequence(Shortcuts.OPEN_FILE))
        open_file.triggered.connect(self.openFileRequested.emit)
        media_menu.addAction(open_file)
        
        # Open Multiple Files
        open_multiple = QAction("Open Multiple Files...", self)
        open_multiple.setShortcut(QKeySequence("Ctrl+Shift+O"))
        open_multiple.triggered.connect(self.openMultipleFilesRequested.emit)
        media_menu.addAction(open_multiple)
        
        # Open Folder
        open_folder = QAction("Open Folder...", self)
        open_folder.setShortcut(QKeySequence(Shortcuts.OPEN_FOLDER))
        open_folder.triggered.connect(self.openFolderRequested.emit)
        media_menu.addAction(open_folder)
        
        # Open Directory
        open_dir = QAction("Open Directory...", self)
        open_dir.setShortcut(QKeySequence(Shortcuts.OPEN_DIRECTORY))
        open_dir.triggered.connect(self.openDirectoryRequested.emit)
        media_menu.addAction(open_dir)
        
        media_menu.addSeparator()
        
        # Recent Media (placeholder submenu)
        recent_menu = media_menu.addMenu("Recent Media")
        clear_recent = QAction("Clear Recent", self)
        recent_menu.addAction(clear_recent)
        
        media_menu.addSeparator()
        
        # Save Playlist
        save_playlist = QAction("Save Playlist to File...", self)
        media_menu.addAction(save_playlist)
        
        media_menu.addSeparator()
        
        # Quit
        quit_action = QAction("Quit", self)
        quit_action.setShortcut(QKeySequence(Shortcuts.QUIT))
        quit_action.triggered.connect(self.quitRequested.emit)
        media_menu.addAction(quit_action)
        
    def _create_playback_menu(self):
        """Create Playback menu."""
        playback_menu = self.addMenu("Playback")
        
        # Play/Pause
        play_pause = QAction("Play/Pause", self)
        play_pause.setShortcut(QKeySequence(Shortcuts.PLAY_PAUSE))
        play_pause.triggered.connect(self.playPauseRequested.emit)
        playback_menu.addAction(play_pause)
        
        # Stop
        stop = QAction("Stop", self)
        stop.setShortcut(QKeySequence(Shortcuts.STOP))
        stop.triggered.connect(self.stopRequested.emit)
        playback_menu.addAction(stop)
        
        # Previous/Next
        previous = QAction("Previous", self)
        previous.setShortcut(QKeySequence(Shortcuts.PREVIOUS))
        previous.triggered.connect(self.previousRequested.emit)
        playback_menu.addAction(previous)
        
        next_action = QAction("Next", self)
        next_action.setShortcut(QKeySequence(Shortcuts.NEXT))
        next_action.triggered.connect(self.nextRequested.emit)
        playback_menu.addAction(next_action)
        
        playback_menu.addSeparator()
        
        # Jump Forward/Backward
        jump_forward = QAction("Jump Forward (10s)", self)
        jump_forward.setShortcut(QKeySequence(Shortcuts.SEEK_FORWARD))
        jump_forward.triggered.connect(self.seekForwardRequested.emit)
        playback_menu.addAction(jump_forward)
        
        jump_backward = QAction("Jump Backward (10s)", self)
        jump_backward.setShortcut(QKeySequence(Shortcuts.SEEK_BACKWARD))
        jump_backward.triggered.connect(self.seekBackwardRequested.emit)
        playback_menu.addAction(jump_backward)
        
        playback_menu.addSeparator()
        
        # Speed submenu
        speed_menu = playback_menu.addMenu("Speed")
        
        slower = QAction("Slower", self)
        slower.setShortcut(QKeySequence(Shortcuts.SPEED_SLOWER))
        slower.triggered.connect(lambda: self.speedChanged.emit(0.9))
        speed_menu.addAction(slower)
        
        normal = QAction("Normal", self)
        normal.setShortcut(QKeySequence(Shortcuts.SPEED_NORMAL))
        normal.triggered.connect(lambda: self.speedChanged.emit(1.0))
        speed_menu.addAction(normal)
        
        faster = QAction("Faster", self)
        faster.setShortcut(QKeySequence(Shortcuts.SPEED_FASTER))
        faster.triggered.connect(lambda: self.speedChanged.emit(1.1))
        speed_menu.addAction(faster)
        
        speed_menu.addSeparator()
        
        # Preset speeds
        for speed in [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]:
            speed_action = QAction(f"{speed}x", self)
            speed_action.triggered.connect(lambda s=speed: self.speedChanged.emit(s))
            speed_menu.addAction(speed_action)
        
    def _create_audio_menu(self):
        """Create Audio menu."""
        audio_menu = self.addMenu("Audio")
        
        # Audio Track submenu
        track_menu = audio_menu.addMenu("Audio Track")
        track1 = QAction("Track 1 - English", self)
        track1.triggered.connect(lambda: self.audioTrackSelected.emit(1))
        track_menu.addAction(track1)
        
        # Audio Device submenu
        device_menu = audio_menu.addMenu("Audio Device")
        default_device = QAction("Default", self)
        default_device.triggered.connect(lambda: self.audioDeviceSelected.emit("default"))
        device_menu.addAction(default_device)
        
        audio_menu.addSeparator()
        
        # Volume controls
        volume_up = QAction("Increase Volume", self)
        volume_up.setShortcut(QKeySequence(Shortcuts.VOLUME_UP_ALT))
        volume_up.triggered.connect(self.volumeUpRequested.emit)
        audio_menu.addAction(volume_up)
        
        volume_down = QAction("Decrease Volume", self)
        volume_down.setShortcut(QKeySequence(Shortcuts.VOLUME_DOWN_ALT))
        volume_down.triggered.connect(self.volumeDownRequested.emit)
        audio_menu.addAction(volume_down)
        
        mute = QAction("Mute", self)
        mute.setShortcut(QKeySequence(Shortcuts.MUTE))
        mute.triggered.connect(self.muteRequested.emit)
        audio_menu.addAction(mute)
        
    def _create_video_menu(self):
        """Create Video menu."""
        video_menu = self.addMenu("Video")
        
        # Video Track
        track_menu = video_menu.addMenu("Video Track")
        track1 = QAction("Track 1", self)
        track1.triggered.connect(lambda: self.videoTrackSelected.emit(1))
        track_menu.addAction(track1)
        
        video_menu.addSeparator()
        
        # Fullscreen
        fullscreen = QAction("Fullscreen", self)
        fullscreen.setShortcut(QKeySequence(Shortcuts.FULLSCREEN))
        fullscreen.triggered.connect(self.fullscreenRequested.emit)
        video_menu.addAction(fullscreen)
        
        # Always on Top
        always_top = QAction("Always on Top", self)
        always_top.setShortcut(QKeySequence(Shortcuts.ALWAYS_ON_TOP))
        always_top.setCheckable(True)
        always_top.triggered.connect(self._on_always_on_top)
        video_menu.addAction(always_top)
        self._always_on_top_action = always_top
        
        video_menu.addSeparator()
        
        # Aspect Ratio submenu
        aspect_menu = video_menu.addMenu("Aspect Ratio")
        for ratio in ["Default", "16:9", "4:3", "1:1", "16:10", "2.35:1"]:
            action = QAction(ratio, self)
            action.triggered.connect(lambda r=ratio: self.aspectRatioChanged.emit(r))
            aspect_menu.addAction(action)
        
        # Crop submenu
        crop_menu = video_menu.addMenu("Crop")
        for crop in ["Default", "16:9", "4:3", "1:1"]:
            action = QAction(crop, self)
            action.triggered.connect(lambda c=crop: self.cropChanged.emit(c))
            crop_menu.addAction(action)
        
        video_menu.addSeparator()
        
        # Snapshot
        snapshot = QAction("Take Snapshot", self)
        snapshot.setShortcut(QKeySequence(Shortcuts.SNAPSHOT))
        snapshot.triggered.connect(self.snapshotRequested.emit)
        video_menu.addAction(snapshot)
        
    def _create_subtitles_menu(self):
        """Create Subtitles menu."""
        subtitles_menu = self.addMenu("Subtitles")
        
        # Subtitle Track
        track_menu = subtitles_menu.addMenu("Subtitle Track")
        disable = QAction("Disable", self)
        disable.triggered.connect(lambda: self.subtitleTrackSelected.emit(0))
        track_menu.addAction(disable)
        
        subtitles_menu.addSeparator()
        
        # Load Subtitle File
        load_sub = QAction("Load Subtitle File...", self)
        load_sub.setShortcut(QKeySequence("Ctrl+Shift+S"))
        load_sub.triggered.connect(self.loadSubtitleRequested.emit)
        subtitles_menu.addAction(load_sub)
        
    def _create_tools_menu(self):
        """Create Tools menu."""
        tools_menu = self.addMenu("Tools")
        
        # Effects and Filters
        effects = QAction("Effects and Filters", self)
        effects.setShortcut(QKeySequence(Shortcuts.EFFECTS_FILTERS))
        effects.triggered.connect(self.effectsFiltersRequested.emit)
        tools_menu.addAction(effects)
        
        tools_menu.addSeparator()
        
        # Media Information
        media_info = QAction("Media Information", self)
        media_info.setShortcut(QKeySequence(Shortcuts.MEDIA_INFO))
        media_info.triggered.connect(self.mediaInfoRequested.emit)
        tools_menu.addAction(media_info)
        
        # Codec Information
        codec_info = QAction("Codec Information", self)
        codec_info.setShortcut(QKeySequence(Shortcuts.CODEC_INFO))
        codec_info.triggered.connect(self.codecInfoRequested.emit)
        tools_menu.addAction(codec_info)
        
        tools_menu.addSeparator()
        
        # Preferences
        prefs = QAction("Preferences", self)
        prefs.setShortcut(QKeySequence("Ctrl+P"))
        prefs.triggered.connect(self.preferencesRequested.emit)
        tools_menu.addAction(prefs)
        
    def _create_view_menu(self):
        """Create View menu."""
        view_menu = self.addMenu("View")
        
        # Playlist
        playlist = QAction("Playlist", self)
        playlist.setShortcut(QKeySequence(Shortcuts.PLAYLIST))
        playlist.triggered.connect(self.playlistRequested.emit)
        view_menu.addAction(playlist)
        
        # Directory View
        directory = QAction("Directory View", self)
        directory.setShortcut(QKeySequence(Shortcuts.OPEN_DIRECTORY))
        directory.triggered.connect(self.directoryViewRequested.emit)
        view_menu.addAction(directory)
        
        view_menu.addSeparator()
        
        # Minimal Interface
        minimal = QAction("Minimal Interface", self)
        minimal.setShortcut(QKeySequence(Shortcuts.MINIMAL_INTERFACE))
        minimal.setCheckable(True)
        minimal.triggered.connect(self._on_minimal_interface)
        view_menu.addAction(minimal)
        self._minimal_interface_action = minimal
        
    def _create_help_menu(self):
        """Create Help menu."""
        help_menu = self.addMenu("Help")
        
        # Documentation
        docs = QAction("Documentation", self)
        help_menu.addAction(docs)
        
        # Keyboard Shortcuts
        shortcuts = QAction("Keyboard Shortcuts", self)
        shortcuts.setShortcut(QKeySequence("Ctrl+?"))
        help_menu.addAction(shortcuts)
        
        help_menu.addSeparator()
        
        # About
        about = QAction("About", self)
        about.setShortcut(QKeySequence("Shift+F1"))
        help_menu.addAction(about)
        
    def _on_always_on_top(self, checked):
        """Handle always on top toggle."""
        self._always_on_top = checked
        self.alwaysOnTopToggled.emit(checked)
        
    def _on_minimal_interface(self, checked):
        """Handle minimal interface toggle."""
        self._minimal_interface = checked
        self.minimalInterfaceToggled.emit(checked)
