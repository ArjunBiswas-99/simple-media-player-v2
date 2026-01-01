"""
Main Window - Central application window with all UI components.

Responsibilities (Single Responsibility Principle):
- Compose all UI components (video, controls, menu, etc.)
- Handle window-level events (resize, keyboard, mouse)
- Coordinate component interactions
- Manage auto-hide behavior
- Handle fullscreen mode
- Integrate MPV player backend
"""

from PySide6.QtWidgets import QMainWindow, QWidget, QFileDialog, QMessageBox
from PySide6.QtCore import Qt, QTimer, QEvent, QPoint
from PySide6.QtGui import QKeyEvent, QCursor
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import Dimensions, Timings, MockData
from utils.file_manager import FileManager
from ui.video_widget import VideoWidget
from ui.controls import ControlBar
from ui.top_bar import TopBar
from ui.directory_panel import DirectoryPanel
from ui.menu_bar import MenuBar
from player.mpv_player import MPVPlayer


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Responsibilities:
    - Coordinate all UI components
    - Handle keyboard shortcuts
    - Manage control visibility (auto-hide)
    - Handle fullscreen mode
    - Connect signals between components
    
    This class follows the Dependency Inversion Principle by depending
    on abstractions (signals) rather than concrete implementations.
    """
    
    def __init__(self):
        """Initialize main window."""
        super().__init__()
        
        # State variables
        self._is_fullscreen = False
        self._controls_visible = True
        self._mouse_idle_timer = None
        self._current_playlist = []  # List of files in current directory
        self._current_index = -1  # Index of currently playing file
        
        # Create MPV player backend first
        self._mpv_player = MPVPlayer()
        
        # Setup window
        self._setup_window()
        
        # Create UI components
        self._create_components()
        
        # Setup layout
        self._setup_layout()
        
        # Connect signals
        self._connect_signals()
        
        # Setup auto-hide timer
        self._setup_auto_hide()
        
        # Embed MPV into video widget
        self._embed_mpv()
        
        # Set initial volume from MPV
        initial_volume = self._mpv_player.get_volume()
        self._control_bar._volume_slider.setValue(initial_volume)
        
    def _embed_mpv(self):
        """Embed MPV player into video widget."""
        from player.mpv_player import MPV_AVAILABLE
        
        if not MPV_AVAILABLE:
            QMessageBox.critical(self, "MPV Not Available", 
                               "libmpv library not found!\n\n"
                               "To use this media player, you need to install MPV:\n\n"
                               "macOS: brew install mpv\n"
                               "Windows: Download from https://mpv.io/installation/\n"
                               "Linux: sudo apt install libmpv-dev (Ubuntu/Debian)")
            return
            
        try:
            # Get the native window ID of the video widget
            wid = int(self._video_widget.winId())
            
            # Tell MPV to use this window for rendering
            if self._mpv_player._player:
                self._mpv_player._player.wid = wid
                # Mark as embedded
                self._video_widget._has_video = True
            
        except Exception as e:
            print(f"Failed to embed MPV: {e}")
            QMessageBox.warning(self, "MPV Error", 
                              f"Failed to initialize video player: {e}\n\nPlease ensure libmpv is installed.")
        
    def _setup_window(self):
        """Configure window properties."""
        # Set window title
        self.setWindowTitle("Simple Media Player V2")
        
        # Set default window size
        self.resize(Dimensions.DEFAULT_WINDOW_WIDTH, Dimensions.DEFAULT_WINDOW_HEIGHT)
        
        # Enable mouse tracking for auto-hide
        self.setMouseTracking(True)
        
    def _create_components(self):
        """Create all UI components following Open/Closed Principle."""
        # Menu bar
        self._menu_bar = MenuBar(self)
        self.setMenuBar(self._menu_bar)
        
        # Video widget (central)
        self._video_widget = VideoWidget()
        
        # Top bar (overlay)
        self._top_bar = TopBar()
        
        # Control bar (overlay)
        self._control_bar = ControlBar()
        
        # Directory panel (slide-in)
        self._directory_panel = DirectoryPanel()
        
    def _setup_layout(self):
        """Setup widget layout and positioning."""
        # Central widget container - NO layout manager, absolute positioning
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        
        # Video widget - fills entire central widget
        self._video_widget.setParent(self._central_widget)
        
        # Top bar - overlaid at top
        self._top_bar.setParent(self._central_widget)
        
        # Control bar - overlaid at bottom
        self._control_bar.setParent(self._central_widget)
        
        # Directory panel - positioned on right
        self._directory_panel.setParent(self._central_widget)
        
        # Set z-order (raise controls above video)
        self._video_widget.lower()
        self._top_bar.raise_()
        self._control_bar.raise_()
        self._directory_panel.raise_()
        
        # Position all widgets
        self._position_widgets()
        
    def _position_widgets(self):
        """Position all widgets using absolute positioning."""
        # Get central widget dimensions
        width = self._central_widget.width()
        height = self._central_widget.height()
        
        # Video widget fills entire space
        self._video_widget.setGeometry(0, 0, width, height)
        
        # Top bar at the top
        self._top_bar.setGeometry(0, 0, width, Dimensions.TOP_BAR_HEIGHT)
        
        # Control bar at the bottom
        control_y = height - Dimensions.CONTROL_BAR_HEIGHT
        self._control_bar.setGeometry(0, control_y, width, Dimensions.CONTROL_BAR_HEIGHT)
        
        # Directory panel on right edge
        self._position_directory_panel()
        
    def _position_directory_panel(self):
        """Position directory panel on the right edge."""
        width = self._central_widget.width()
        height = self._central_widget.height()
        
        panel_x = width - self._directory_panel.width()
        panel_y = 0
        
        self._directory_panel.setGeometry(
            panel_x, panel_y,
            self._directory_panel.width(), height
        )
        
    def _connect_signals(self):
        """
        Connect signals between components.
        Follows Interface Segregation Principle - components only know
        about signals they need.
        """
        # Video widget signals
        self._video_widget.clicked.connect(self._on_video_clicked)
        self._video_widget.mouseMovedOnVideo.connect(self._on_mouse_moved)
        self._video_widget.scrubbing.connect(self._on_scrubbing)
        
        # Control bar signals
        self._control_bar.playPauseClicked.connect(self._on_play_pause)
        self._control_bar.seekBackwardClicked.connect(self._on_seek_backward)
        self._control_bar.seekForwardClicked.connect(self._on_seek_forward)
        self._control_bar.volumeChanged.connect(self._on_volume_changed)
        self._control_bar.muteToggled.connect(self._on_mute_toggled)
        self._control_bar.settingsClicked.connect(self._on_settings_clicked)
        self._control_bar.fullscreenClicked.connect(self._toggle_fullscreen)
        self._control_bar.progressChanged.connect(self._on_progress_changed)
        
        # Top bar signals
        self._top_bar.backClicked.connect(self._on_back_clicked)
        self._top_bar.directoryClicked.connect(self._on_directory_clicked)
        self._top_bar.settingsClicked.connect(self._on_settings_clicked)
        self._top_bar.fullscreenClicked.connect(self._toggle_fullscreen)
        
        # Directory panel signals
        self._directory_panel.fileSelected.connect(self._on_file_selected)
        
        # Menu bar signals (sample - extend as needed)
        self._menu_bar.openFileRequested.connect(self._on_open_file)
        self._menu_bar.openFolderRequested.connect(self._on_open_folder)
        self._menu_bar.openDirectoryRequested.connect(self._on_open_folder)
        self._menu_bar.quitRequested.connect(self.close)
        self._menu_bar.playPauseRequested.connect(self._on_play_pause)
        self._menu_bar.fullscreenRequested.connect(self._toggle_fullscreen)
        self._menu_bar.directoryViewRequested.connect(self._on_directory_clicked)
        self._menu_bar.alwaysOnTopToggled.connect(self._on_always_on_top)
        self._menu_bar.seekForwardRequested.connect(self._on_seek_forward)
        self._menu_bar.seekBackwardRequested.connect(self._on_seek_backward)
        self._menu_bar.stopRequested.connect(self._on_stop)
        self._menu_bar.nextRequested.connect(self._on_next)
        self._menu_bar.previousRequested.connect(self._on_previous)
        self._menu_bar.speedChanged.connect(self._on_speed_changed)
        self._menu_bar.volumeUpRequested.connect(self._on_volume_up)
        self._menu_bar.volumeDownRequested.connect(self._on_volume_down)
        self._menu_bar.muteRequested.connect(self._on_mute_toggled)
        self._menu_bar.aspectRatioChanged.connect(self._on_aspect_ratio_changed)
        
        # MPV player signals
        self._mpv_player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._mpv_player.positionChanged.connect(self._on_position_changed)
        self._mpv_player.durationChanged.connect(self._on_duration_changed)
        self._mpv_player.volumeChanged.connect(self._on_mpv_volume_changed)
        self._mpv_player.mediaLoaded.connect(self._on_media_loaded)
        self._mpv_player.mediaEnded.connect(self._on_media_ended)
        self._mpv_player.errorOccurred.connect(self._on_mpv_error)
        
    def _setup_auto_hide(self):
        """Setup timer for auto-hiding controls."""
        self._mouse_idle_timer = QTimer(self)
        self._mouse_idle_timer.setSingleShot(True)
        self._mouse_idle_timer.timeout.connect(self._hide_controls)
        
    # ==================== Event Handlers ====================
    
    def _on_video_clicked(self):
        """Handle click on video (play/pause toggle)."""
        # Only toggle if a file is loaded
        if self._mpv_player.get_current_file():
            self._on_play_pause()
        
    def _on_mouse_moved(self):
        """Handle mouse movement (show controls, reset timer)."""
        self._show_controls()
        self._reset_auto_hide_timer()
        
    def _on_scrubbing(self, delta):
        """
        Handle scrubbing gesture (fast seeking while dragging).
        
        Args:
            delta: Horizontal mouse movement in pixels
        """
        # Calculate seek amount based on delta (10 pixels = 1 second)
        seek_amount = delta / 10.0
        self._mpv_player.seek(seek_amount, absolute=False)
        
    def _on_play_pause(self):
        """Handle play/pause toggle."""
        self._mpv_player.toggle_play_pause()
        
    def _on_seek_backward(self):
        """Handle seek backward 10 seconds."""
        self._mpv_player.seek_backward(10)
        
    def _on_seek_forward(self):
        """Handle seek forward 10 seconds."""
        self._mpv_player.seek_forward(10)
        
    def _on_stop(self):
        """Handle stop playback."""
        self._mpv_player.stop()
        
    def _on_next(self):
        """Handle play next file in playlist."""
        if self._current_index >= 0 and self._current_index < len(self._current_playlist) - 1:
            self._current_index += 1
            self._load_file(self._current_playlist[self._current_index])
        
    def _on_previous(self):
        """Handle play previous file in playlist."""
        if self._current_index > 0:
            self._current_index -= 1
            self._load_file(self._current_playlist[self._current_index])
        
    def _on_volume_changed(self, value):
        """
        Handle volume change from slider.
        
        Args:
            value: Volume level (0-100)
        """
        self._mpv_player.set_volume(value)
        
    def _on_volume_up(self):
        """Handle volume up request."""
        current_vol = self._mpv_player.get_volume()
        self._mpv_player.set_volume(min(100, current_vol + 5))
        self._control_bar._volume_slider.setValue(self._mpv_player.get_volume())
        
    def _on_volume_down(self):
        """Handle volume down request."""
        current_vol = self._mpv_player.get_volume()
        self._mpv_player.set_volume(max(0, current_vol - 5))
        self._control_bar._volume_slider.setValue(self._mpv_player.get_volume())
        
    def _on_mute_toggled(self):
        """Handle mute toggle."""
        self._mpv_player.toggle_mute()
        
    def _on_speed_changed(self, speed):
        """
        Handle playback speed change.
        
        Args:
            speed: Speed multiplier (0.25-2.0)
        """
        self._mpv_player.set_speed(speed)
        
    def _on_settings_clicked(self):
        """Handle settings button click."""
        # TODO: Implement settings dialog
        QMessageBox.information(self, "Settings", "Settings dialog will be implemented here.")
        
    def _on_progress_changed(self, value):
        """
        Handle progress bar seek.
        
        Args:
            value: Seek position (0-1000)
        """
        # Convert from 0-1000 to actual position
        duration = self._mpv_player.get_duration()
        if duration > 0:
            position = (value / 1000.0) * duration
            self._mpv_player.seek(position, absolute=True)
        
    def _on_aspect_ratio_changed(self, ratio):
        """
        Handle aspect ratio change.
        
        Args:
            ratio: Aspect ratio string
        """
        self._mpv_player.set_aspect_ratio(ratio)
        
    def _on_back_clicked(self):
        """Handle back button click."""
        # TODO: Implement back functionality
        pass
        
    def _on_directory_clicked(self):
        """Handle directory button click (toggle panel)."""
        self._directory_panel.toggle_visibility()
        
    def _on_file_selected(self, filename):
        """
        Handle file selection from directory panel.
        
        Args:
            filename: Selected filename (not full path)
        """
        # Find full path in current playlist
        for i, filepath in enumerate(self._current_playlist):
            if FileManager.get_filename(filepath) == filename:
                self._current_index = i
                self._load_file(filepath)
                break
        
    def _on_open_file(self):
        """Handle open file dialog."""
        # Build filter string for supported formats
        video_exts = " *".join(MockData.VIDEO_EXTENSIONS)
        audio_exts = " *".join(MockData.AUDIO_EXTENSIONS)
        filter_str = f"Media Files (*{video_exts} *{audio_exts});;All Files (*.*)"
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Media File",
            "",
            filter_str
        )
        
        if filename:
            self._load_file(filename)
            
    def _on_open_folder(self):
        """Handle open folder dialog."""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Open Folder",
            ""
        )
        
        if directory:
            # Scan directory for media files
            files = FileManager.scan_directory(directory)
            if files:
                # Load first file
                self._load_file(files[0])
            else:
                QMessageBox.information(self, "No Media Files", 
                                       "No supported media files found in the selected folder.")
        
    def _on_always_on_top(self, enabled):
        """
        Handle always on top toggle.
        
        Args:
            enabled: Boolean indicating if always on top
        """
        flags = self.windowFlags()
        if enabled:
            self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()
    
    # ==================== MPV Event Handlers ====================
    
    def _on_playback_state_changed(self, is_playing):
        """
        Handle playback state change from MPV.
        
        Args:
            is_playing: Boolean indicating if playing
        """
        self._control_bar.set_playing_state(is_playing)
        
        # Hide placeholder when playing
        if is_playing:
            self._video_widget.hide_placeholder()
        
    def _on_position_changed(self, position):
        """
        Handle position update from MPV.
        
        Args:
            position: Current position in seconds
        """
        # Update progress bar
        duration = self._mpv_player.get_duration()
        if duration > 0:
            progress_value = int((position / duration) * 1000)
            self._control_bar.update_progress(progress_value)
        
        # Update time display
        current_time = FileManager.format_time(position)
        total_time = FileManager.format_time(duration)
        self._control_bar.update_time(current_time, total_time)
        
    def _on_duration_changed(self, duration):
        """
        Handle duration update from MPV.
        
        Args:
            duration: Media duration in seconds
        """
        total_time = FileManager.format_time(duration)
        current_time = FileManager.format_time(0)
        self._control_bar.update_time(current_time, total_time)
        
    def _on_mpv_volume_changed(self, volume):
        """
        Handle volume change from MPV.
        
        Args:
            volume: Volume level 0-100
        """
        # Update volume slider without triggering signal
        self._control_bar._volume_slider.blockSignals(True)
        self._control_bar._volume_slider.setValue(volume)
        self._control_bar._volume_slider.blockSignals(False)
        
    def _on_media_loaded(self):
        """Handle successful media load."""
        # Update title
        current_file = self._mpv_player.get_current_file()
        if current_file:
            filename = FileManager.get_filename(current_file)
            self._top_bar.set_title(filename)
            
            # Scan directory and update playlist
            self._current_playlist = FileManager.get_files_in_same_directory(current_file)
            
            # Update directory panel
            filenames = [FileManager.get_filename(f) for f in self._current_playlist]
            self._directory_panel.update_file_list(filenames)
            self._directory_panel.set_current_file(filename)
            
            # Find current index
            try:
                self._current_index = self._current_playlist.index(current_file)
            except ValueError:
                self._current_index = 0
                
            # Hide placeholder
            self._video_widget.hide_placeholder()
        
    def _on_media_ended(self):
        """Handle media playback end."""
        # Auto-play next file if available
        if self._current_index >= 0 and self._current_index < len(self._current_playlist) - 1:
            self._on_next()
        
    def _on_mpv_error(self, error_msg):
        """
        Handle MPV error.
        
        Args:
            error_msg: Error message string
        """
        QMessageBox.critical(self, "Playback Error", f"Error: {error_msg}")
    
    # ==================== File Loading ====================
    
    def _load_file(self, filepath):
        """
        Load and play a media file.
        
        Args:
            filepath: Absolute path to media file
        """
        success = self._mpv_player.load_file(filepath)
        if success:
            self._mpv_player.play()
        else:
            QMessageBox.critical(self, "Error", f"Failed to load file:\n{filepath}")
        
    # ==================== Control Visibility ====================
    
    def _show_controls(self):
        """Show top bar and control bar with fade-in animation."""
        if not self._controls_visible:
            self._controls_visible = True
            self._top_bar.fade_in()
            self._control_bar.fade_in()
            
    def _hide_controls(self):
        """Hide top bar and control bar with fade-out animation."""
        # Don't hide if video is paused
        if not self._mpv_player.is_playing():
            return
            
        # Don't hide if mouse is over controls
        if self._is_mouse_over_controls():
            self._reset_auto_hide_timer()
            return
            
        if self._controls_visible:
            self._controls_visible = False
            self._top_bar.fade_out()
            self._control_bar.fade_out()
            
    def _is_mouse_over_controls(self):
        """
        Check if mouse is over control areas.
        
        Returns:
            bool: True if mouse is over controls
        """
        mouse_pos = self.mapFromGlobal(QCursor.pos())
        
        # Check top bar
        if self._top_bar.geometry().contains(mouse_pos):
            return True
            
        # Check control bar
        if self._control_bar.geometry().contains(mouse_pos):
            return True
            
        return False
        
    def _reset_auto_hide_timer(self):
        """Reset the auto-hide timer."""
        if self._mouse_idle_timer:
            self._mouse_idle_timer.stop()
            self._mouse_idle_timer.start(Timings.AUTO_HIDE_DELAY)
            
    # ==================== Fullscreen ====================
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        self._is_fullscreen = not self._is_fullscreen
        
        if self._is_fullscreen:
            self.showFullScreen()
            self._menu_bar.hide()
        else:
            self.showNormal()
            self._menu_bar.show()
            
        # Update fullscreen icon
        self._top_bar.set_fullscreen_icon(self._is_fullscreen)
        
    # ==================== Keyboard Shortcuts ====================
    
    def keyPressEvent(self, event: QKeyEvent):
        """
        Handle keyboard shortcuts.
        
        Args:
            event: Key event
        """
        key = event.key()
        modifiers = event.modifiers()
        
        # Space - Play/Pause
        if key == Qt.Key.Key_Space:
            self._on_play_pause()
            
        # Left Arrow - Seek backward
        elif key == Qt.Key.Key_Left:
            self._on_seek_backward()
            
        # Right Arrow - Seek forward
        elif key == Qt.Key.Key_Right:
            self._on_seek_forward()
            
        # Up Arrow - Volume up
        elif key == Qt.Key.Key_Up:
            current_vol = self._control_bar._volume_slider.value()
            self._control_bar._volume_slider.setValue(min(100, current_vol + 5))
            
        # Down Arrow - Volume down
        elif key == Qt.Key.Key_Down:
            current_vol = self._control_bar._volume_slider.value()
            self._control_bar._volume_slider.setValue(max(0, current_vol - 5))
            
        # F - Fullscreen
        elif key == Qt.Key.Key_F:
            self._toggle_fullscreen()
            
        # M - Mute
        elif key == Qt.Key.Key_M:
            self._on_mute_toggled()
            
        # Escape - Exit fullscreen
        elif key == Qt.Key.Key_Escape and self._is_fullscreen:
            self._toggle_fullscreen()
            
        else:
            super().keyPressEvent(event)
            
    # ==================== Window Events ====================
    
    def resizeEvent(self, event):
        """
        Handle window resize.
        
        Args:
            event: Resize event
        """
        super().resizeEvent(event)
        
        # Reposition all widgets on resize
        if hasattr(self, '_central_widget'):
            self._position_widgets()
        
    def mouseMoveEvent(self, event):
        """
        Handle mouse movement at window level.
        
        Args:
            event: Mouse event
        """
        super().mouseMoveEvent(event)
        self._on_mouse_moved()
    
    def mousePressEvent(self, event):
        """Handle mouse clicks to close directory panel when clicking outside."""
        # Close directory panel if clicking outside of it
        if self._directory_panel.isVisible():
            panel_rect = self._directory_panel.geometry()
            if not panel_rect.contains(event.pos()):
                self._directory_panel.toggle_visibility()
        super().mousePressEvent(event)
        
    def enterEvent(self, event):
        """
        Handle mouse entering window.
        
        Args:
            event: Enter event
        """
        super().enterEvent(event)
        self._show_controls()
        self._reset_auto_hide_timer()
        
    def leaveEvent(self, event):
        """
        Handle mouse leaving window.
        
        Args:
            event: Leave event
        """
        super().leaveEvent(event)
        if self._mouse_idle_timer:
            self._mouse_idle_timer.stop()
            
    def closeEvent(self, event):
        """
        Handle window close event - cleanup MPV.
        
        Args:
            event: Close event
        """
        # Shutdown MPV player
        self._mpv_player.shutdown()
        super().closeEvent(event)
