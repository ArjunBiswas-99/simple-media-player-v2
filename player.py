#!/usr/bin/env python3
"""
Netflix-Style Professional Media Player
Built with PyQt6 and QtMultimedia
Following SOLID principles for clean, maintainable code
"""

import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QFileDialog, QMenu,
    QListWidget, QListWidgetItem, QRadioButton, QButtonGroup, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QPropertyAnimation, pyqtProperty, QPoint
from PyQt6.QtGui import QPalette, QColor, QCursor, QFont, QAction
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget


class SpeedIndicator(QLabel):
    """2x speed indicator overlay for YouTube-style hold-to-speed"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("2×")
        self.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(229, 9, 20, 200);
                border-radius: 8px;
                padding: 15px 25px;
                font-size: 32px;
                font-weight: bold;
            }
        """)
        self.hide()
        self._opacity = 1.0
        
    def get_opacity(self):
        return self._opacity
    
    def set_opacity(self, value):
        self._opacity = value
        self.setWindowOpacity(value)
    
    opacity = pyqtProperty(float, get_opacity, set_opacity)


class PlaylistPopover(QWidget):
    """Netflix-style playlist popover showing videos in current folder"""
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.media_player_ref = None
        self.video_files = []
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup popover UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Container with rounded corners
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 20, 250);
                border-radius: 8px;
                border: 1px solid #e50914;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Videos in This Folder")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: 600;")
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 24px;
                border: none;
                border-radius: 15px;
            }
            QPushButton:hover { background-color: #e50914; }
        """)
        close_btn.clicked.connect(self.hide)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        container_layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 30);")
        separator.setFixedHeight(1)
        container_layout.addWidget(separator)
        
        # Video list
        self.video_list = QListWidget()
        self.video_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
                color: white;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 12px 8px;
                border-radius: 4px;
                margin: 2px 0px;
            }
            QListWidget::item:hover {
                background-color: rgba(255, 255, 255, 10);
            }
            QListWidget::item:selected {
                background-color: rgba(229, 9, 20, 30);
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(255, 255, 255, 50);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(255, 255, 255, 80);
            }
        """)
        self.video_list.setMaximumHeight(400)
        self.video_list.setMinimumWidth(380)
        self.video_list.itemClicked.connect(self._on_video_selected)
        container_layout.addWidget(self.video_list)
        
        layout.addWidget(container)
        
    def load_videos(self, current_file_path):
        """Scan folder for video files"""
        self.video_list.clear()
        self.video_files = []
        
        if not current_file_path:
            return
            
        folder_path = Path(current_file_path).parent
        current_filename = Path(current_file_path).name
        
        video_exts = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', 
                     '.webm', '.m4v', '.mpg', '.mpeg', '.m2ts', '.ts'}
        
        try:
            for file_path in sorted(folder_path.iterdir()):
                if file_path.is_file() and file_path.suffix.lower() in video_exts:
                    self.video_files.append(str(file_path))
                    
                    item = QListWidgetItem()
                    is_current = file_path.name == current_filename
                    
                    icon = "▶" if is_current else "□"
                    item.setText(f"{icon}  {file_path.name}")
                    item.setData(Qt.ItemDataRole.UserRole, str(file_path))
                    
                    if is_current:
                        item.setForeground(QColor("#e50914"))
                        font = item.font()
                        font.setBold(True)
                        item.setFont(font)
                    
                    self.video_list.addItem(item)
        except Exception as e:
            print(f"Error loading videos: {e}")
            
    def _on_video_selected(self, item):
        """Handle video selection"""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and self.media_player_ref:
            self.media_player_ref.load_video(file_path)
            self.hide()
            
    def show_at_button(self, button):
        """Position popover above button"""
        self.adjustSize()
        button_pos = button.mapToGlobal(QPoint(0, 0))
        x = button_pos.x() - self.width() + button.width()
        y = button_pos.y() - self.height() - 10
        self.move(x, y)
        self.show()
        self.raise_()


class SettingsPopover(QWidget):
    """Netflix-style settings popover for playback options"""
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.media_player_ref = None
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup popover UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Container
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background-color: rgba(20, 20, 20, 250);
                border-radius: 8px;
                border: 1px solid #e50914;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.setSpacing(15)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Settings")
        title.setStyleSheet("color: white; font-size: 16px; font-weight: 600;")
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 24px;
                border: none;
                border-radius: 15px;
            }
            QPushButton:hover { background-color: #e50914; }
        """)
        close_btn.clicked.connect(self.hide)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        container_layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 30);")
        separator.setFixedHeight(1)
        container_layout.addWidget(separator)
        
        # Playback Speed Section
        speed_label = QLabel("Playback Speed")
        speed_label.setStyleSheet("""
            color: rgba(255, 255, 255, 180);
            font-size: 13px;
            font-weight: 600;
        """)
        container_layout.addWidget(speed_label)
        
        # Speed radio buttons
        self.speed_group = QButtonGroup(self)
        speeds = [
            ("0.25×", 0.25), ("0.5×", 0.5), ("0.75×", 0.75),
            ("Normal", 1.0), ("1.25×", 1.25), ("1.5×", 1.5), ("2×", 2.0)
        ]
        
        for label, rate in speeds:
            rb = QRadioButton(label)
            rb.setStyleSheet("""
                QRadioButton {
                    color: white;
                    font-size: 14px;
                    padding: 5px;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                }
                QRadioButton::indicator:unchecked {
                    border: 2px solid rgba(255, 255, 255, 50);
                    border-radius: 8px;
                    background-color: transparent;
                }
                QRadioButton::indicator:checked {
                    border: 2px solid #e50914;
                    border-radius: 8px;
                    background-color: #e50914;
                }
            """)
            if rate == 1.0:
                rb.setChecked(True)
            rb.toggled.connect(
                lambda checked, r=rate: self._on_speed_changed(r) if checked else None
            )
            self.speed_group.addButton(rb)
            container_layout.addWidget(rb)
        
        container.setMinimumWidth(280)
        layout.addWidget(container)
        
    def _on_speed_changed(self, rate):
        """Handle speed change"""
        if self.media_player_ref:
            self.media_player_ref.set_playback_rate(rate)
            
    def show_at_button(self, button):
        """Position popover above button"""
        self.adjustSize()
        button_pos = button.mapToGlobal(QPoint(0, 0))
        x = button_pos.x() - self.width() + button.width()
        y = button_pos.y() - self.height() - 10
        self.move(x, y)
        self.show()
        self.raise_()


class MediaPlayer(QMainWindow):
    """Netflix-style professional media player with VLC menus and YouTube features"""
    
    # Netflix color scheme
    NETFLIX_RED = "#e50914"
    NETFLIX_BLACK = "#141414"
    NETFLIX_DARK_GRAY = "#2f2f2f"
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Netflix Media Player")
        self.setGeometry(100, 100, 1280, 720)
        self.setMinimumSize(800, 600)
        
        # State variables
        self.is_seeking = False
        self.is_2x_speed = False
        self.normal_rate = 1.0
        self.current_file = None
        
        # Setup components in correct order
        self._setup_media_player()
        self._setup_video_area()
        self._setup_menu_bar()
        self._setup_popovers()
        self._connect_signals()
        self._setup_timers()
        
        self.apply_stylesheet()
        self.show_controls()
        
    def _setup_media_player(self):
        """Initialize media player and audio output"""
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.5)
        
    def _setup_video_area(self):
        """Setup video display area with controls"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet(f"background-color: {self.NETFLIX_BLACK};")
        self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.player.setVideoOutput(self.video_widget)
        layout.addWidget(self.video_widget)
        
        # 2x speed indicator
        self.speed_indicator = SpeedIndicator(self.video_widget)
        self.speed_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Controls container
        self.controls_widget = QWidget()
        self.controls_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:1, x2:0, y2:0,
                    stop:0 rgba(20, 20, 20, 240),
                    stop:0.3 rgba(20, 20, 20, 180),
                    stop:1 rgba(20, 20, 20, 0)
                );
            }
        """)
        layout.addWidget(self.controls_widget)
        
        self._setup_controls()
        
    def _setup_controls(self):
        """Setup Netflix-style controls"""
        layout = QVBoxLayout(self.controls_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Timeline slider
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setRange(0, 0)
        self.timeline.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 30);
                border-radius: 2px;
            }
            QSlider::groove:horizontal:hover {
                height: 6px;
            }
            QSlider::handle:horizontal {
                background: #e50914;
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
                border: 2px solid white;
            }
            QSlider::sub-page:horizontal {
                background: #e50914;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.timeline)
        
        # Time labels
        time_layout = QHBoxLayout()
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setStyleSheet(
            "color: white; font-size: 13px; font-weight: 500;"
        )
        self.duration_label = QLabel("0:00")
        self.duration_label.setStyleSheet(
            "color: rgba(255, 255, 255, 180); font-size: 13px; font-weight: 500;"
        )
        self.file_name_label = QLabel("")
        self.file_name_label.setStyleSheet(
            "color: white; font-size: 14px; font-weight: 600;"
        )
        
        time_layout.addWidget(self.current_time_label)
        time_layout.addStretch()
        time_layout.addWidget(self.file_name_label)
        time_layout.addStretch()
        time_layout.addWidget(self.duration_label)
        layout.addLayout(time_layout)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(8)
        
        button_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 15);
                color: white;
                border: none;
                border-radius: 25px;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e50914;
            }
            QPushButton:pressed {
                background-color: #b8070f;
            }
        """
        
        self.open_btn = self._create_button("📁", 50, button_style, "Open File (Ctrl+O)")
        self.skip_back_btn = self._create_button("⏪", 50, button_style, "Rewind 10s")
        self.play_pause_btn = self._create_button(
            "▶", 60, 
            button_style.replace("25px", "30px").replace("18px", "24px"),
            "Play/Pause (Space)"
        )
        self.skip_forward_btn = self._create_button("⏩", 50, button_style, "Forward 10s")
        self.stop_btn = self._create_button("⏹", 50, button_style, "Stop (S)")
        
        volume_label = QLabel("🔊")
        volume_label.setStyleSheet("color: white; font-size: 20px;")
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(120)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 30);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: white;
                width: 12px;
                height: 12px;
                margin: -4px 0;
                border-radius: 6px;
            }
            QSlider::sub-page:horizontal {
                background: white;
                border-radius: 2px;
            }
        """)
        
        self.speed_label = QLabel("1×")
        self.speed_label.setStyleSheet("""
            color: white;
            font-size: 13px;
            font-weight: 600;
            padding: 5px 10px;
            background-color: rgba(255, 255, 255, 15);
            border-radius: 4px;
        """)
        
        self.playlist_btn = self._create_button("☰", 50, button_style, "Playlist")
        self.settings_btn = self._create_button("⚙", 50, button_style, "Settings")
        self.fullscreen_btn = self._create_button("⛶", 50, button_style, "Fullscreen (F11)")
        
        controls_layout.addWidget(self.open_btn)
        controls_layout.addWidget(self.skip_back_btn)
        controls_layout.addWidget(self.play_pause_btn)
        controls_layout.addWidget(self.skip_forward_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(volume_label)
        controls_layout.addWidget(self.volume_slider)
        controls_layout.addWidget(self.speed_label)
        controls_layout.addWidget(self.playlist_btn)
        controls_layout.addWidget(self.settings_btn)
        controls_layout.addWidget(self.fullscreen_btn)
        
        layout.addLayout(controls_layout)
        
    def _create_button(self, text, size, style, tooltip):
        """Helper to create styled button"""
        btn = QPushButton(text)
        btn.setFixedSize(size, size)
        btn.setStyleSheet(style)
        btn.setToolTip(tooltip)
        return btn
        
    def _setup_menu_bar(self):
        """Create VLC-style menu bar"""
        menubar = self.menuBar()
        menubar.setStyleSheet(f"""
            QMenuBar {{
                background-color: {self.NETFLIX_BLACK};
                color: white;
                font-size: 13px;
                padding: 4px;
            }}
            QMenuBar::item:selected {{
                background-color: {self.NETFLIX_RED};
            }}
            QMenu {{
                background-color: {self.NETFLIX_DARK_GRAY};
                color: white;
                border: 1px solid {self.NETFLIX_RED};
            }}
            QMenu::item:selected {{
                background-color: {self.NETFLIX_RED};
            }}
        """)
        
        # File Menu
        file_menu = menubar.addMenu("&File")
        self._add_action(file_menu, "&Open File...", "Ctrl+O", self.open_file)
        file_menu.addSeparator()
        self._add_action(file_menu, "E&xit", "Ctrl+Q", self.close)
        
        # Playback Menu
        playback_menu = menubar.addMenu("&Playback")
        self._add_action(playback_menu, "&Play/Pause", "Space", self.toggle_play_pause)
        self._add_action(playback_menu, "&Stop", "S", self.player.stop)
        playback_menu.addSeparator()
        
        # Speed submenu
        speed_menu = playback_menu.addMenu("&Speed")
        for label, rate in [("0.25×", 0.25), ("0.5×", 0.5), ("0.75×", 0.75),
                           ("Normal (1×)", 1.0), ("1.25×", 1.25), ("1.5×", 1.5), ("2×", 2.0)]:
            self._add_action(speed_menu, label, None, 
                           lambda checked, r=rate: self.set_playback_rate(r))
        
        playback_menu.addSeparator()
        self._add_action(playback_menu, "Jump Forward", "Right", 
                        lambda: self.seek_relative(5000))
        self._add_action(playback_menu, "Jump Backward", "Left", 
                        lambda: self.seek_relative(-5000))
        
        # Audio Menu
        audio_menu = menubar.addMenu("&Audio")
        self._add_action(audio_menu, "&Mute", "M", self.toggle_mute)
        audio_menu.addSeparator()
        self._add_action(audio_menu, "Volume &Up", "Up", lambda: self.adjust_volume(5))
        self._add_action(audio_menu, "Volume &Down", "Down", lambda: self.adjust_volume(-5))
        
        # Video Menu
        video_menu = menubar.addMenu("&Video")
        self._add_action(video_menu, "&Fullscreen", "F11", self.toggle_fullscreen)
        video_menu.addSeparator()
        
        # Aspect ratio submenu
        aspect_menu = video_menu.addMenu("&Aspect Ratio")
        for label, mode in [("Default", Qt.AspectRatioMode.KeepAspectRatio),
                           ("16:9", Qt.AspectRatioMode.KeepAspectRatio),
                           ("4:3", Qt.AspectRatioMode.KeepAspectRatio),
                           ("Stretch", Qt.AspectRatioMode.IgnoreAspectRatio)]:
            self._add_action(aspect_menu, label, None,
                           lambda checked, m=mode: self.video_widget.setAspectRatioMode(m))
        
        # Help Menu
        help_menu = menubar.addMenu("&Help")
        self._add_action(help_menu, "&About", None, self.show_about)
        
    def _add_action(self, menu, text, shortcut, callback):
        """Helper to add menu action"""
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(callback)
        menu.addAction(action)
        
    def _setup_popovers(self):
        """Create popover widgets"""
        self.playlist_popover = PlaylistPopover(self)
        self.playlist_popover.media_player_ref = self
        
        self.settings_popover = SettingsPopover(self)
        self.settings_popover.media_player_ref = self
        
    def _connect_signals(self):
        """Connect all signals"""
        # Player signals
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        
        # Button signals
        self.open_btn.clicked.connect(self.open_file)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.stop_btn.clicked.connect(self.player.stop)
        self.skip_back_btn.clicked.connect(lambda: self.seek_relative(-10000))
        self.skip_forward_btn.clicked.connect(lambda: self.seek_relative(10000))
        self.playlist_btn.clicked.connect(self._show_playlist)
        self.settings_btn.clicked.connect(self._show_settings)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        
        # Slider signals
        self.timeline.sliderPressed.connect(self._on_timeline_pressed)
        self.timeline.sliderMoved.connect(self._on_timeline_moved)
        self.timeline.sliderReleased.connect(self._on_timeline_released)
        self.volume_slider.valueChanged.connect(self._set_volume)
        
    def _setup_timers(self):
        """Setup control hide timer"""
        self.hide_timer = QTimer(self)
        self.hide_timer.timeout.connect(self._hide_controls)
        self.hide_timer.setSingleShot(True)
        
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_ui)
        self.update_timer.start(100)
        
    def apply_stylesheet(self):
        """Apply global stylesheet"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.NETFLIX_BLACK};
            }}
            QToolTip {{
                background-color: {self.NETFLIX_DARK_GRAY};
                color: white;
                border: 1px solid {self.NETFLIX_RED};
                padding: 5px;
                font-size: 12px;
            }}
        """)
        
    # Public Methods - File Operations
    
    def open_file(self):
        """Open file dialog and load video"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Video File", "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.m4v *.mpg *.mpeg);;All Files (*.*)"
        )
        if filename:
            self.load_video(filename)
            
    def load_video(self, file_path):
        """Load and play a video file"""
        self.current_file = file_path
        self.file_name_label.setText(os.path.basename(file_path))
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.player.play()
        
    # Public Methods - Playback Control
    
    def toggle_play_pause(self):
        """Toggle play/pause"""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()
            
    def seek_relative(self, ms):
        """Seek relative to current position"""
        new_position = self.player.position() + ms
        new_position = max(0, min(new_position, self.player.duration()))
        self.player.setPosition(new_position)
        self.show_controls()
        
    def set_playback_rate(self, rate):
        """Set playback rate"""
        self.normal_rate = rate
        self.player.setPlaybackRate(rate)
        self.speed_label.setText(f"{rate}×")
        
    def toggle_mute(self):
        """Toggle mute"""
        self.audio_output.setMuted(not self.audio_output.isMuted())
        
    def adjust_volume(self, delta):
        """Adjust volume by delta"""
        current = self.volume_slider.value()
        new_value = max(0, min(100, current + delta))
        self.volume_slider.setValue(new_value)
        self.show_controls()
        
    def toggle_fullscreen(self):
        """Toggle fullscreen"""
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().show()
        else:
            self.showFullScreen()
            self.menuBar().hide()
            
    def show_about(self):
        """Show about dialog"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self, "About Netflix Media Player",
            "<h2>Netflix Media Player</h2>"
            "<p>Professional media player built with PyQt6</p>"
            "<p>Version 2.0</p>"
            "<p>Features perfect A/V synchronization</p>"
        )
        
    # Public Methods - UI Control
    
    def show_controls(self):
        """Show controls"""
        self.controls_widget.show()
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.hide_timer.start(3000)
        
    # Private Methods - UI Updates
    
    def _hide_controls(self):
        """Hide controls when playing (fullscreen only)"""
        if not self.isFullScreen():
            return  # Keep controls visible in windowed mode
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.controls_widget.hide()
            self.setCursor(QCursor(Qt.CursorShape.BlankCursor))
            
    def _show_playlist(self):
        """Show playlist popover"""
        if self.current_file:
            self.playlist_popover.load_videos(self.current_file)
            self.playlist_popover.show_at_button(self.playlist_btn)
            
    def _show_settings(self):
        """Show settings popover"""
        self.settings_popover.show_at_button(self.settings_btn)
        
    def _update_ui(self):
        """Periodic UI updates"""
        pass  # Position updates handled by signals
        
    # Private Methods - Timeline Control
    
    def _on_timeline_pressed(self):
        """Handle timeline press"""
        self.is_seeking = True
        
    def _on_timeline_moved(self, position):
        """Handle timeline drag"""
        if self.is_seeking:
            self.current_time_label.setText(self._format_time(position))
            
    def _on_timeline_released(self):
        """Handle timeline release"""
        self.player.setPosition(self.timeline.value())
        self.is_seeking = False
        
    def _set_volume(self, value):
        """Set volume (0-100)"""
        self.audio_output.setVolume(value / 100.0)
        
    # Private Methods - Player Signals
    
    def _on_position_changed(self, position):
        """Update timeline when position changes"""
        if not self.is_seeking:
            self.timeline.setValue(position)
            self.current_time_label.setText(self._format_time(position))
            
    def _on_duration_changed(self, duration):
        """Update timeline range when duration changes"""
        self.timeline.setRange(0, duration)
        self.duration_label.setText(self._format_time(duration))
        
    def _on_state_changed(self, state):
        """Update play/pause button when state changes"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_btn.setText("⏸")
        else:
            self.play_pause_btn.setText("▶")
            
    def _format_time(self, ms):
        """Format milliseconds to H:MM:SS or MM:SS"""
        seconds = ms // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
        
    # Event Handlers - Keyboard
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        key = event.key()
        
        if key == Qt.Key.Key_Space:
            self.toggle_play_pause()
        elif key == Qt.Key.Key_Left:
            self.seek_relative(-5000)
        elif key == Qt.Key.Key_Right:
            self.seek_relative(5000)
        elif key in (Qt.Key.Key_F, Qt.Key.Key_F11):
            self.toggle_fullscreen()
        elif key == Qt.Key.Key_O:
            self.open_file()
        elif key == Qt.Key.Key_Escape and self.isFullScreen():
            self.showNormal()
            self.menuBar().show()
        elif key == Qt.Key.Key_Up:
            self.adjust_volume(5)
        elif key == Qt.Key.Key_Down:
            self.adjust_volume(-5)
        elif key == Qt.Key.Key_M:
            self.toggle_mute()
        elif key == Qt.Key.Key_S:
            self.player.stop()
            
        self.show_controls()
        
    # Event Handlers - Mouse
    
    def mousePressEvent(self, event):
        """Handle mouse press for YouTube-style 2x speed"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.video_widget.underMouse():
                self._start_2x_speed()
                
    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop 2x speed"""
        if event.button() == Qt.MouseButton.LeftButton:
            if self.is_2x_speed:
                self._stop_2x_speed()
                
    def mouseMoveEvent(self, event):
        """Show controls on mouse move"""
        self.show_controls()
        
    def mouseDoubleClickEvent(self, event):
        """Toggle fullscreen on double click"""
        if self.video_widget.underMouse():
            self.toggle_fullscreen()
            
    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)
        if self.speed_indicator.isVisible():
            self._position_speed_indicator()
            
    # Private Methods - YouTube-style 2x Speed
    
    def _start_2x_speed(self):
        """Start 2x playback speed"""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState and not self.is_2x_speed:
            self.is_2x_speed = True
            self.player.setPlaybackRate(2.0)
            self._position_speed_indicator()
            self.speed_indicator.show()
            
    def _stop_2x_speed(self):
        """Stop 2x playback speed"""
        if self.is_2x_speed:
            self.is_2x_speed = False
            self.player.setPlaybackRate(self.normal_rate)
            
            # Fade out
            anim = QPropertyAnimation(self.speed_indicator, b"opacity")
            anim.setDuration(200)
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)
            anim.finished.connect(self.speed_indicator.hide)
            anim.start()
            
    def _position_speed_indicator(self):
        """Position speed indicator in center of video"""
        video_rect = self.video_widget.geometry()
        indicator_width = self.speed_indicator.sizeHint().width()
        indicator_height = self.speed_indicator.sizeHint().height()
        x = (video_rect.width() - indicator_width) // 2
        y = (video_rect.height() - indicator_height) // 2
        self.speed_indicator.move(x, y)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(20, 20, 20))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(40, 40, 40))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, QColor(229, 9, 20))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(229, 9, 20))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    app.setPalette(palette)
    
    # Application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    player = MediaPlayer()
    player.show()
    
    # Open file dialog on start
    QTimer.singleShot(500, player.open_file)
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
