"""
Main Media Player Window
Orchestrates all components following SOLID principles
"""

import os
import qtawesome as qta
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QSlider, QLabel, QFileDialog, QMessageBox, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QPropertyAnimation, QSize, QEasingCurve, QSequentialAnimationGroup, QParallelAnimationGroup
from PyQt6.QtGui import QCursor, QAction
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

from constants import *
from styles import *
from widgets import SpeedIndicator, PlaylistPopover, SettingsPopover


class MediaPlayer(QMainWindow):
    """Professional media player with VLC menus and YouTube features by Arjun Biswas"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Media Player")
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
        
        self.setStyleSheet(get_main_window_style())
        self.show_controls()
        
    def _setup_media_player(self):
        """Initialize media player and audio output"""
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.5)
        
    def _setup_video_area(self):
        """Setup video display area with minimal controls"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Video widget
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet(f"background-color: {THEME_BLACK};")
        self.video_widget.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        self.player.setVideoOutput(self.video_widget)
        layout.addWidget(self.video_widget)
        
        # 2x speed indicator
        self.speed_indicator = SpeedIndicator(self.video_widget)
        self.speed_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Filename overlay label
        self.filename_label = QLabel(self.video_widget)
        self.filename_label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 12px 24px;
                font-size: {FONT_SIZE_LARGE}px;
                font-weight: {FONT_WEIGHT_SEMIBOLD};
                border-radius: 6px;
            }}
        """)
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filename_label.hide()
        
        # Filename fade animation
        self.filename_anim = QPropertyAnimation(self.filename_label, b"windowOpacity")
        self.filename_anim.setDuration(500)
        
        # Play/Pause overlay (YouTube-style)
        self.play_pause_overlay = QLabel(self)  # Parent to main window, not video widget
        self.play_pause_overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.play_pause_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.play_pause_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.play_pause_overlay.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(0, 0, 0, 180);
                color: white;
                border-radius: 50px;
            }}
        """)
        self.play_pause_overlay.setFixedSize(100, 100)
        self.play_pause_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.play_pause_overlay_effect = QGraphicsOpacityEffect()
        self.play_pause_overlay.setGraphicsEffect(self.play_pause_overlay_effect)
        self.play_pause_overlay.hide()
        
        # Volume feedback overlay (top-right)
        self.volume_overlay = QWidget(self)
        self.volume_overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.volume_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.volume_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.volume_overlay.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(0, 0, 0, 200);
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        volume_overlay_layout = QVBoxLayout(self.volume_overlay)
        volume_overlay_layout.setSpacing(8)
        volume_overlay_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.volume_overlay_icon = QLabel()
        self.volume_overlay_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.volume_overlay_icon.setStyleSheet("color: white; font-size: 32px;")
        volume_overlay_layout.addWidget(self.volume_overlay_icon)
        
        self.volume_overlay_bar = QWidget()
        self.volume_overlay_bar.setFixedSize(40, 150)
        self.volume_overlay_fill = QWidget(self.volume_overlay_bar)
        self.volume_overlay_fill.setStyleSheet(f"background-color: {THEME_PRIMARY}; border-radius: 3px;")
        volume_overlay_layout.addWidget(self.volume_overlay_bar)
        
        self.volume_overlay_text = QLabel("50")
        self.volume_overlay_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.volume_overlay_text.setStyleSheet(f"color: white; font-size: {FONT_SIZE_LARGE}px; font-weight: {FONT_WEIGHT_BOLD};")
        volume_overlay_layout.addWidget(self.volume_overlay_text)
        
        self.volume_overlay.setFixedSize(80, 250)
        self.volume_overlay_effect = QGraphicsOpacityEffect()
        self.volume_overlay.setGraphicsEffect(self.volume_overlay_effect)
        self.volume_overlay.hide()
        
        # Skip feedback overlay (center)
        self.skip_overlay = QLabel(self)
        self.skip_overlay.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.skip_overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.skip_overlay.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.skip_overlay.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(0, 0, 0, 180);
                color: white;
                padding: 16px 32px;
                font-size: {FONT_SIZE_LARGE * 1.5}px;
                font-weight: {FONT_WEIGHT_BOLD};
                border-radius: 8px;
            }}
        """)
        self.skip_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.skip_overlay_effect = QGraphicsOpacityEffect()
        self.skip_overlay.setGraphicsEffect(self.skip_overlay_effect)
        self.skip_overlay.hide()
        
        # Timer for detecting click vs hold (for 2x speed)
        self.click_timer = QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self._start_2x_speed)
        self.video_press_pos = None
        
        # Add mouse click handler with hold detection
        def video_mouse_press(event):
            if event.button() == Qt.MouseButton.LeftButton:
                self.video_press_pos = event.position()
                # Start timer for 2x speed - if released before timeout, it's a click
                self.click_timer.start(200)  # 200ms threshold
            QVideoWidget.mousePressEvent(self.video_widget, event)
        
        def video_mouse_release(event):
            if event.button() == Qt.MouseButton.LeftButton:
                if self.click_timer.isActive():
                    # Released before timer - it's a click, toggle play/pause
                    self.click_timer.stop()
                    self.toggle_play_pause()
                else:
                    # Timer already fired - it was a hold, stop 2x speed
                    if self.is_2x_speed:
                        self._stop_2x_speed()
                self.video_press_pos = None
            QVideoWidget.mouseReleaseEvent(self.video_widget, event)
        
        self.video_widget.mousePressEvent = video_mouse_press
        self.video_widget.mouseReleaseEvent = video_mouse_release
        
        # Add mouse wheel handler for volume control
        def video_wheel_event(event):
            delta = event.angleDelta().y()
            if delta > 0:
                # Scroll up - increase volume
                new_volume = min(100, self.volume_slider.value() + 5)
            else:
                # Scroll down - decrease volume
                new_volume = max(0, self.volume_slider.value() - 5)
            self.volume_slider.setValue(new_volume)
            event.accept()
        
        self.video_widget.wheelEvent = video_wheel_event
        
        # Minimal controls container with smooth gradient
        self.controls_widget = QWidget()
        self.controls_widget.setFixedHeight(CONTROL_BAR_HEIGHT)
        self.controls_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1:0, y1:1, x2:0, y2:0,
                    stop:0 rgba(18, 18, 18, 245),
                    stop:0.5 rgba(22, 22, 22, 200),
                    stop:0.8 rgba(25, 25, 25, 120),
                    stop:1 rgba(20, 20, 20, 0)
                );
            }
        """)
        layout.addWidget(self.controls_widget)
        
        self._setup_controls()
        
    def _setup_controls(self):
        """Setup minimal VLC-style controls"""
        layout = QVBoxLayout(self.controls_widget)
        layout.setContentsMargins(CONTROL_PADDING, CONTROL_PADDING, CONTROL_PADDING, CONTROL_PADDING_BOTTOM)
        layout.setSpacing(0)
        
        # Timeline slider with click-to-seek support
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setRange(0, 0)
        self.timeline.setStyleSheet(get_timeline_style())
        
        # Enable click-to-seek by overriding mouse press behavior
        def timeline_mouse_press(event):
            if event.button() == Qt.MouseButton.LeftButton:
                # Calculate clicked position as percentage of slider width
                click_pos = event.position().x()
                slider_width = self.timeline.width()
                percentage = click_pos / slider_width
                
                # Set slider value based on percentage
                new_value = int(self.timeline.minimum() + percentage * (self.timeline.maximum() - self.timeline.minimum()))
                self.timeline.setValue(new_value)
                
                # Seek to the position
                self.player.setPosition(new_value)
                self.is_seeking = True
            
            # Call original handler for other mouse buttons
            QSlider.mousePressEvent(self.timeline, event)
        
        self.timeline.mousePressEvent = timeline_mouse_press
        
        # Timeline with duration at the end
        timeline_row = QHBoxLayout()
        timeline_row.setSpacing(8)
        timeline_row.addWidget(self.timeline, stretch=1)
        
        # Duration label at the end of seek bar
        self.duration_label = QLabel("0:00")
        self.duration_label.setStyleSheet(
            f"color: rgba(255, 255, 255, 150); font-size: {FONT_SIZE_SMALL}px;"
        )
        timeline_row.addWidget(self.duration_label)
        
        layout.addLayout(timeline_row)
        layout.addSpacing(TIMELINE_BOTTOM_MARGIN)
        
        # Bottom row: time labels and controls
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(BUTTON_SPACING)
        bottom_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Current time label
        self.current_time_label = QLabel("0:00")
        self.current_time_label.setStyleSheet(
            f"color: white; font-size: {FONT_SIZE_SMALL}px; font-weight: 500;"
        )
        
        # Play/pause button (FIRST - most important)
        self.play_pause_btn = self._create_icon_button(
            'fa5s.play', BUTTON_SIZE_LARGE, ICON_SIZE_LARGE,
            "Play/Pause (Space)"
        )
        
        # Playback controls
        self.skip_back_btn = self._create_icon_button('fa5s.backward', BUTTON_SIZE_SMALL, ICON_SIZE_SMALL, "Rewind 10s")
        self.skip_forward_btn = self._create_icon_button('fa5s.forward', BUTTON_SIZE_SMALL, ICON_SIZE_SMALL, "Forward 10s")
        self.stop_btn = self._create_icon_button('fa5s.stop', BUTTON_SIZE_SMALL, ICON_SIZE_SMALL, "Stop (S)")
        
        # Volume controls
        self.volume_icon = QPushButton()
        self.volume_icon.setIcon(qta.icon('fa5s.volume-up', color='white'))
        self.volume_icon.setIconSize(QSize(16, 16))
        self.volume_icon.setFixedSize(24, 24)
        self.volume_icon.setStyleSheet("background: transparent; border: none;")
        self.volume_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.volume_icon.setToolTip("Mute/Unmute (M)")
        self.volume_icon.clicked.connect(self.toggle_mute)
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setMaximumWidth(100)
        self.volume_slider.setStyleSheet(get_volume_slider_style())
        
        # Speed indicator label
        self.speed_label = QLabel("1×")
        self.speed_label.setStyleSheet(f"""
            color: white;
            font-size: {FONT_SIZE_SMALL}px;
            font-weight: 600;
            padding: 3px 8px;
            background-color: rgba(255, 255, 255, 10);
            border-radius: 3px;
        """)
        
        # Tool buttons
        self.playlist_btn = self._create_icon_button('fa5s.folder-open', BUTTON_SIZE_SMALL, ICON_SIZE_TINY, "Playlist")
        self.settings_btn = self._create_icon_button('fa5s.cog', BUTTON_SIZE_SMALL, ICON_SIZE_TINY, "Settings")
        self.fullscreen_btn = self._create_icon_button('fa5s.expand', BUTTON_SIZE_SMALL, ICON_SIZE_TINY, "Fullscreen (F11)")
        
        # Layout: play/pause | controls | current time | spacer | volume | speed | tools | fullscreen
        bottom_layout.addWidget(self.play_pause_btn)
        bottom_layout.addWidget(self.skip_back_btn)
        bottom_layout.addWidget(self.skip_forward_btn)
        bottom_layout.addWidget(self.stop_btn)
        bottom_layout.addSpacing(8)
        bottom_layout.addWidget(self.current_time_label)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.volume_icon)
        bottom_layout.addWidget(self.volume_slider)
        bottom_layout.addSpacing(8)
        bottom_layout.addWidget(self.speed_label)
        bottom_layout.addWidget(self.playlist_btn)
        bottom_layout.addWidget(self.settings_btn)
        bottom_layout.addSpacing(8)
        bottom_layout.addSpacing(4)
        bottom_layout.addWidget(self.fullscreen_btn)
        
        layout.addLayout(bottom_layout)
        
    def _create_button(self, text, size, style, tooltip):
        """Helper to create styled button"""
        btn = QPushButton(text)
        btn.setFixedSize(size, size)
        btn.setStyleSheet(style)
        btn.setToolTip(tooltip)
        return btn
    
    def _create_icon_button(self, icon_name, button_size, icon_size, tooltip):
        """Create a button with Font Awesome icon"""
        btn = QPushButton()
        btn.setFixedSize(button_size, button_size)
        btn.setStyleSheet(get_button_style(button_size))
        btn.setToolTip(tooltip)
        
        # Store icon name and sizes for hover effects
        btn.icon_name = icon_name
        btn.icon_size = icon_size
        
        # Create icon with primary red color (normal state)
        btn.setIcon(qta.icon(icon_name, color=THEME_PRIMARY))
        btn.setIconSize(QSize(icon_size, icon_size))
        
        # Add hover/press event handlers for icon color change only
        def on_enter(event):
            btn.setIcon(qta.icon(btn.icon_name, color='white'))
            QPushButton.enterEvent(btn, event)
        
        def on_leave(event):
            btn.setIcon(qta.icon(btn.icon_name, color=THEME_PRIMARY))
            QPushButton.leaveEvent(btn, event)
        
        btn.enterEvent = on_enter
        btn.leaveEvent = on_leave
        
        return btn
        
    def _setup_menu_bar(self):
        """Create professional menu bar"""
        menubar = self.menuBar()
        menubar.setStyleSheet(get_menubar_style())
        
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
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.stop_btn.clicked.connect(self.player.stop)
        self.skip_back_btn.clicked.connect(lambda: self.seek_relative(-10000))
        self.skip_forward_btn.clicked.connect(lambda: self.seek_relative(10000))
        self.playlist_btn.clicked.connect(self._show_playlist)
        self.settings_btn.clicked.connect(self._show_settings)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        
        # Slider signals (FIX: Click to seek)
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
        self.player.setSource(QUrl.fromLocalFile(file_path))
        self.player.play()
        
        # Show filename overlay
        import os
        filename = os.path.basename(file_path)
        self.filename_label.setText(filename)
        self.filename_label.adjustSize()
        
        # Center the label
        label_x = (self.video_widget.width() - self.filename_label.width()) // 2
        label_y = self.video_widget.height() - CONTROL_BAR_HEIGHT - self.filename_label.height() - 20
        self.filename_label.move(label_x, label_y)
        
        self.filename_label.setWindowOpacity(1.0)
        self.filename_label.show()
        
        # Fade out after 2.5 seconds
        QTimer.singleShot(2500, lambda: self._fade_filename_label())
        
    # Public Methods - Playback Control
    
    def toggle_play_pause(self):
        """Toggle play/pause with overlay animation"""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            # Paused state - show play icon in red
            self.play_pause_btn.setIcon(qta.icon('fa5s.play', color=THEME_PRIMARY))
            self.play_pause_btn.icon_name = 'fa5s.play'
            self._show_play_pause_overlay('▶')
        else:
            self.player.play()
            # Playing state - show pause icon in white (active state)
            self.play_pause_btn.setIcon(qta.icon('fa5s.pause', color='white'))
            self.play_pause_btn.icon_name = 'fa5s.pause'
            self._show_play_pause_overlay('⏸')
            
    def seek_relative(self, ms):
        """Seek relative to current position with feedback animation"""
        new_position = self.player.position() + ms
        new_position = max(0, min(new_position, self.player.duration()))
        self.player.setPosition(new_position)
        
        # Show skip feedback
        seconds = abs(ms) // 1000
        direction = '+' if ms > 0 else '-'
        self._show_skip_overlay(f"{direction}{seconds}s")
        self.show_controls()
        
    def set_playback_rate(self, rate):
        """Set playback rate"""
        self.normal_rate = rate
        self.player.setPlaybackRate(rate)
        self.speed_label.setText(f"{rate}×")
        
    def adjust_volume(self, delta):
        """Adjust volume by delta"""
        current = self.volume_slider.value()
        new_value = max(0, min(100, current + delta))
        self.volume_slider.setValue(new_value)
        self.show_controls()
        
    def toggle_fullscreen(self):
        """Toggle fullscreen with smooth transition"""
        # Fade out controls during transition
        self.controls_widget.setStyleSheet(self.controls_widget.styleSheet() + " QWidget { opacity: 0.5; }")
        
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().show()
            self.fullscreen_btn.setIcon(qta.icon('fa5s.expand', color=THEME_PRIMARY))
        else:
            self.showFullScreen()
            self.menuBar().hide()
            self.fullscreen_btn.setIcon(qta.icon('fa5s.compress', color=THEME_PRIMARY))
        
        # Fade controls back in
        QTimer.singleShot(200, lambda: self.controls_widget.setStyleSheet(self.controls_widget.styleSheet().replace(" QWidget { opacity: 0.5; }", "")))
    
    def toggle_mute(self):
        """Toggle mute/unmute"""
        if self.audio_output.volume() > 0:
            self.previous_volume = self.volume_slider.value()
            self.volume_slider.setValue(0)
            self.volume_icon.setIcon(qta.icon('fa5s.volume-mute', color='white'))
        else:
            restore_vol = getattr(self, 'previous_volume', 50)
            self.volume_slider.setValue(restore_vol)
            self._update_volume_icon(restore_vol)
    
    def _update_volume_icon(self, volume):
        """Update volume icon based on volume level"""
        if volume == 0:
            icon_name = 'fa5s.volume-mute'
        elif volume < 33:
            icon_name = 'fa5s.volume-off'
        elif volume < 66:
            icon_name = 'fa5s.volume-down'
        else:
            icon_name = 'fa5s.volume-up'
        self.volume_icon.setIcon(qta.icon(icon_name, color='white'))
    
    def _fade_filename_label(self):
        """Fade out the filename label"""
        self.filename_anim.setStartValue(1.0)
        self.filename_anim.setEndValue(0.0)
        self.filename_anim.finished.connect(self.filename_label.hide)
        self.filename_anim.start()
            
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self, "About Simple Media Player",
            "<h2>Simple Media Player</h2>"
            "<p>Professional media player built with PyQt6</p>"
            "<p>By Arjun Biswas</p>"
            "<p>Version 2.1</p>"
            "<p>Features perfect A/V synchronization</p>"
        )
        
    # Public Methods - UI Control
    
    def show_controls(self):
        """Show controls"""
        self.controls_widget.show()
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.hide_timer.start(CONTROL_HIDE_DELAY)
        
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
        
    # Private Methods - Timeline Control (FIX: Click to seek)
    
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
        """Set volume (0-100) and update icon"""
        self.audio_output.setVolume(value / 100.0)
        self._update_volume_icon(value)
        
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
            self.play_pause_btn.setIcon(qta.icon('fa5s.pause', color='white'))
            self.play_pause_btn.icon_name = 'fa5s.pause'
        else:
            self.play_pause_btn.setIcon(qta.icon('fa5s.play', color=THEME_PRIMARY))
            self.play_pause_btn.icon_name = 'fa5s.play'
            
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
        """Start 2x playback speed with pulse animation"""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState and not self.is_2x_speed:
            self.is_2x_speed = True
            self.player.setPlaybackRate(2.0)
            self._position_speed_indicator()
            self.speed_indicator.show()
            
            # Start pulse animation
            self.speed_pulse_timer = QTimer(self)
            self.speed_pulse_timer.timeout.connect(self._pulse_speed_indicator)
            self.speed_pulse_timer.start(1000)  # Pulse every second
            
    def _stop_2x_speed(self):
        """Stop 2x playback speed and pulse animation"""
        if self.is_2x_speed:
            self.is_2x_speed = False
            self.player.setPlaybackRate(self.normal_rate)
            
            # Stop pulse timer
            if hasattr(self, 'speed_pulse_timer'):
                self.speed_pulse_timer.stop()
            
            # Fade out
            anim = QPropertyAnimation(self.speed_indicator, b"opacity")
            anim.setDuration(FADE_DURATION)
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
    
    def _pulse_speed_indicator(self):
        """Create pulse animation for 2x speed indicator"""
        # Subtle scale pulse: 1.0 → 1.05 → 1.0
        original_size = self.speed_indicator.sizeHint()
        # This is visual feedback, no actual size change needed in Qt
        # The CSS handles this via font size variations
        pass
    
    def _show_play_pause_overlay(self, icon_text):
        """Show play/pause overlay animation (YouTube-style)"""
        self.play_pause_overlay.setText(icon_text)
        self.play_pause_overlay.setStyleSheet(f"""
            QLabel {{
                background-color: rgba(0, 0, 0, 180);
                color: white;
                border-radius: 50px;
                font-size: 48px;
            }}
        """)
        
        # Position in center of video widget in global coordinates
        video_global_pos = self.video_widget.mapToGlobal(self.video_widget.rect().center())
        x = video_global_pos.x() - self.play_pause_overlay.width() // 2
        y = video_global_pos.y() - self.play_pause_overlay.height() // 2
        self.play_pause_overlay.move(x, y)
        
        # Fade in, stay, fade out using QGraphicsOpacityEffect
        self.play_pause_overlay_effect.setOpacity(0)
        self.play_pause_overlay.show()
        
        # Store animations as instance variables to prevent garbage collection
        self.pp_fade_in = QPropertyAnimation(self.play_pause_overlay_effect, b"opacity")
        self.pp_fade_in.setDuration(100)
        self.pp_fade_in.setStartValue(0.0)
        self.pp_fade_in.setEndValue(1.0)
        
        self.pp_fade_out = QPropertyAnimation(self.play_pause_overlay_effect, b"opacity")
        self.pp_fade_out.setDuration(300)
        self.pp_fade_out.setStartValue(1.0)
        self.pp_fade_out.setEndValue(0.0)
        self.pp_fade_out.finished.connect(self.play_pause_overlay.hide)
        
        # Sequence: fade in → wait 400ms → fade out
        self.pp_fade_in.start()
        QTimer.singleShot(500, self.pp_fade_out.start)  # 100ms fade in + 400ms wait
    
    def _show_volume_overlay(self, volume):
        """Show volume feedback overlay with bar"""
        # Update icon based on volume
        if volume == 0:
            icon = '🔇'
        elif volume < 33:
            icon = '🔉'
        else:
            icon = '🔊'
        
        self.volume_overlay_icon.setText(icon)
        self.volume_overlay_text.setText(str(volume))
        
        # Update volume bar fill height
        bar_height = int(150 * (volume / 100))
        self.volume_overlay_fill.setFixedSize(40, bar_height)
        self.volume_overlay_fill.move(0, 150 - bar_height)
        
        # Position in top-right corner in global coordinates
        video_global_rect = self.video_widget.mapToGlobal(self.video_widget.rect().topRight())
        x = video_global_rect.x() - self.volume_overlay.width() - 20
        y = video_global_rect.y() + 20
        self.volume_overlay.move(x, y)
        
        # Fade in using QGraphicsOpacityEffect
        self.volume_overlay_effect.setOpacity(0)
        self.volume_overlay.show()
        
        # Store animation as instance variable
        self.vol_fade_in = QPropertyAnimation(self.volume_overlay_effect, b"opacity")
        self.vol_fade_in.setDuration(150)
        self.vol_fade_in.setStartValue(0.0)
        self.vol_fade_in.setEndValue(1.0)
        self.vol_fade_in.start()
        
        # Auto-hide after 1 second
        QTimer.singleShot(1150, self._hide_volume_overlay)
    
    def _hide_volume_overlay(self):
        """Fade out volume overlay"""
        self.vol_fade_out = QPropertyAnimation(self.volume_overlay_effect, b"opacity")
        self.vol_fade_out.setDuration(300)
        self.vol_fade_out.setStartValue(1.0)
        self.vol_fade_out.setEndValue(0.0)
        self.vol_fade_out.finished.connect(self.volume_overlay.hide)
        self.vol_fade_out.start()
    
    def _show_skip_overlay(self, text):
        """Show skip feedback overlay (+10s/-10s)"""
        self.skip_overlay.setText(text)
        self.skip_overlay.adjustSize()
        
        # Position in center of video widget in global coordinates
        video_global_pos = self.video_widget.mapToGlobal(self.video_widget.rect().center())
        x = video_global_pos.x() - self.skip_overlay.width() // 2
        y = video_global_pos.y() - self.skip_overlay.height() // 2
        self.skip_overlay.move(x, y)
        
        # Bounce + fade animation using QGraphicsOpacityEffect
        self.skip_overlay_effect.setOpacity(0)
        self.skip_overlay.show()
        
        # Store animations as instance variables
        self.skip_fade_in = QPropertyAnimation(self.skip_overlay_effect, b"opacity")
        self.skip_fade_in.setDuration(150)
        self.skip_fade_in.setStartValue(0.0)
        self.skip_fade_in.setEndValue(1.0)
        
        self.skip_fade_out = QPropertyAnimation(self.skip_overlay_effect, b"opacity")
        self.skip_fade_out.setDuration(200)
        self.skip_fade_out.setStartValue(1.0)
        self.skip_fade_out.setEndValue(0.0)
        self.skip_fade_out.finished.connect(self.skip_overlay.hide)
        
        # Sequence: fade in → wait 300ms → fade out
        self.skip_fade_in.start()
        QTimer.singleShot(450, self.skip_fade_out.start)  # 150ms fade in + 300ms wait
