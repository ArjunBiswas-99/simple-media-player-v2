"""
Bottom Control Bar - Netflix-inspired playback controls.

Responsibilities:
- Display playback controls (play/pause, seek buttons, volume)
- Show progress bar with time stamps
- Handle user interactions with controls
- Apply Netflix visual styling
- Auto-hide/show with animations
"""

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, 
                               QSlider, QLabel, QGraphicsOpacityEffect)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QFont
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import Colors, Dimensions, Timings, Fonts, MockData


class ProgressBar(QSlider):
    """
    Custom progress bar with Netflix styling and hover effects.
    
    Responsibilities:
    - Display progress with Netflix red color
    - Enlarge scrubber on hover
    - Emit seek signals
    """
    
    def __init__(self, parent=None):
        """Initialize progress bar."""
        super().__init__(Qt.Orientation.Horizontal, parent)
        
        self.setRange(0, 1000)  # 0-1000 for smooth seeking
        self.setValue(450)  # Mock: 45% progress
        
        # Apply Netflix styling
        self._apply_style()
        
        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)
        
    def _apply_style(self):
        """Apply Netflix-inspired visual styling."""
        self.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: {Dimensions.PROGRESS_BAR_HEIGHT}px;
                background: {Colors.PROGRESS_BAR_BACKGROUND};
                border-radius: 2px;
            }}
            
            QSlider::groove:horizontal:hover {{
                height: {Dimensions.PROGRESS_BAR_HEIGHT_HOVER}px;
            }}
            
            QSlider::sub-page:horizontal {{
                background: {Colors.PROGRESS_BAR_FILLED};
                border-radius: 2px;
            }}
            
            QSlider::handle:horizontal {{
                background: {Colors.SCRUBBER_DOT};
                width: {Dimensions.SCRUBBER_SIZE}px;
                height: {Dimensions.SCRUBBER_SIZE}px;
                border-radius: {Dimensions.SCRUBBER_SIZE // 2}px;
                margin: -{Dimensions.SCRUBBER_SIZE // 2}px 0;
            }}
            
            QSlider::handle:horizontal:hover {{
                width: {Dimensions.SCRUBBER_SIZE_HOVER}px;
                height: {Dimensions.SCRUBBER_SIZE_HOVER}px;
                border-radius: {Dimensions.SCRUBBER_SIZE_HOVER // 2}px;
                margin: -{Dimensions.SCRUBBER_SIZE_HOVER // 2}px 0;
            }}
        """)


class ControlButton(QPushButton):
    """
    Custom button with Netflix hover effects.
    
    Responsibilities:
    - Display icon/text
    - Animate on hover (scale, color)
    - Emit click signals
    """
    
    def __init__(self, text, parent=None):
        """
        Initialize control button.
        
        Args:
            text: Button text/icon
            parent: Parent widget
        """
        super().__init__(text, parent)
        
        # Apply Netflix styling
        self._apply_style()
        
        # Set fixed size for consistent layout
        self.setFixedSize(Dimensions.ICON_SIZE + 16, Dimensions.ICON_SIZE + 16)
        
    def _apply_style(self):
        """Apply Netflix button styling."""
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.TEXT_PRIMARY};
                border: none;
                border-radius: 4px;
                font-size: 16px;
                font-weight: {Fonts.MEDIUM};
            }}
            
            QPushButton:hover {{
                background: {Colors.HOVER_GRAY};
                color: {Colors.NETFLIX_RED};
            }}
            
            QPushButton:pressed {{
                background: {Colors.ACTIVE_RED};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)


class VolumeSlider(QSlider):
    """
    Volume slider with Netflix styling.
    
    Responsibilities:
    - Display volume level
    - Allow volume adjustment
    - Netflix visual styling
    """
    
    def __init__(self, parent=None):
        """Initialize volume slider."""
        super().__init__(Qt.Orientation.Horizontal, parent)
        
        self.setRange(0, 100)
        self.setValue(70)  # Mock: 70% volume
        self.setFixedWidth(80)
        
        # Apply Netflix styling
        self._apply_style()
        
    def _apply_style(self):
        """Apply Netflix slider styling."""
        self.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: {Colors.PROGRESS_BAR_BACKGROUND};
                border-radius: 2px;
            }}
            
            QSlider::sub-page:horizontal {{
                background: {Colors.TEXT_PRIMARY};
                border-radius: 2px;
            }}
            
            QSlider::handle:horizontal {{
                background: {Colors.TEXT_PRIMARY};
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }}
            
            QSlider::handle:horizontal:hover {{
                background: {Colors.NETFLIX_RED};
                width: 14px;
                height: 14px;
                border-radius: 7px;
                margin: -5px 0;
            }}
        """)


class ControlBar(QWidget):
    """
    Main control bar with all playback controls.
    
    Responsibilities:
    - Layout all control elements (play, seek, volume, etc.)
    - Manage progress bar and time display
    - Handle control interactions
    - Provide signals for main window
    
    Signals:
        playPauseClicked: User clicked play/pause button
        seekBackwardClicked: User clicked seek backward button
        seekForwardClicked: User clicked seek forward button
        volumeChanged: User changed volume (int value)
        muteToggled: User clicked mute button
        settingsClicked: User clicked settings button
        fullscreenClicked: User clicked fullscreen button
        progressChanged: User seeked to position (int value 0-1000)
    """
    
    # Signals following Interface Segregation Principle
    playPauseClicked = Signal()
    seekBackwardClicked = Signal()
    seekForwardClicked = Signal()
    volumeChanged = Signal(int)
    muteToggled = Signal()
    settingsClicked = Signal()
    fullscreenClicked = Signal()
    progressChanged = Signal(int)
    
    def __init__(self, parent=None):
        """Initialize control bar."""
        super().__init__(parent)
        
        # State variables
        self._is_playing = False
        self._is_muted = False
        
        # Setup UI components
        self._setup_ui()
        
        # Setup opacity effect for fade animations
        self._setup_animations()
        
    def _setup_ui(self):
        """Create and layout all control elements."""
        # Set fixed height as per Netflix design
        self.setFixedHeight(Dimensions.CONTROL_BAR_HEIGHT)
        
        # Apply background styling
        self.setStyleSheet(f"""
            QWidget {{
                background: {Colors.CONTROL_BACKGROUND};
                border-top: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            Dimensions.CONTROL_BAR_PADDING_H,
            Dimensions.CONTROL_BAR_PADDING_V,
            Dimensions.CONTROL_BAR_PADDING_H,
            Dimensions.CONTROL_BAR_PADDING_V
        )
        main_layout.setSpacing(8)
        
        # Progress bar section
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(Dimensions.PROGRESS_BAR_MARGIN)
        
        # Time labels
        self._current_time_label = QLabel(MockData.MOCK_CURRENT_TIME)
        self._current_time_label.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: {Fonts.TIME_STAMP}px;
            font-family: {Fonts.FAMILY};
        """)
        
        self._total_time_label = QLabel(MockData.MOCK_TOTAL_TIME)
        self._total_time_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-size: {Fonts.TIME_STAMP}px;
            font-family: {Fonts.FAMILY};
        """)
        
        # Progress bar
        self._progress_bar = ProgressBar()
        self._progress_bar.sliderMoved.connect(self.progressChanged.emit)
        
        # Add to progress layout
        progress_layout.addWidget(self._current_time_label)
        progress_layout.addWidget(self._progress_bar, stretch=1)
        progress_layout.addWidget(self._total_time_label)
        
        # Control buttons section
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(Dimensions.BUTTON_SPACING)
        
        # Play/Pause button
        self._play_pause_btn = ControlButton("▶")
        self._play_pause_btn.clicked.connect(self._on_play_pause_clicked)
        
        # Seek backward 10s
        self._seek_back_btn = ControlButton("⏮10")
        self._seek_back_btn.clicked.connect(self.seekBackwardClicked.emit)
        
        # Seek forward 10s
        self._seek_forward_btn = ControlButton("⏭10")
        self._seek_forward_btn.clicked.connect(self.seekForwardClicked.emit)
        
        # Volume button
        self._volume_btn = ControlButton("🔊")
        self._volume_btn.clicked.connect(self._on_volume_clicked)
        
        # Volume slider
        self._volume_slider = VolumeSlider()
        self._volume_slider.valueChanged.connect(self.volumeChanged.emit)
        
        # Spacer
        controls_layout.addWidget(self._play_pause_btn)
        controls_layout.addWidget(self._seek_back_btn)
        controls_layout.addWidget(self._seek_forward_btn)
        controls_layout.addWidget(self._volume_btn)
        controls_layout.addWidget(self._volume_slider)
        controls_layout.addStretch()
        
        # Settings button
        self._settings_btn = ControlButton("⚙")
        self._settings_btn.clicked.connect(self.settingsClicked.emit)
        controls_layout.addWidget(self._settings_btn)
        
        # Fullscreen button
        self._fullscreen_btn = ControlButton("⛶")
        self._fullscreen_btn.clicked.connect(self.fullscreenClicked.emit)
        controls_layout.addWidget(self._fullscreen_btn)
        
        # Add layouts to main layout
        main_layout.addLayout(progress_layout)
        main_layout.addLayout(controls_layout)
        
    def _setup_animations(self):
        """Setup opacity animation for auto-hide effect."""
        # Create opacity effect
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        
        # Create fade animation
        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_animation.setDuration(Timings.FADE_OUT)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
    def _on_play_pause_clicked(self):
        """Handle play/pause button click."""
        self._is_playing = not self._is_playing
        self._play_pause_btn.setText("❚❚" if self._is_playing else "▶")
        self.playPauseClicked.emit()
        
    def _on_volume_clicked(self):
        """Handle volume/mute button click."""
        self._is_muted = not self._is_muted
        self._volume_btn.setText("🔇" if self._is_muted else "🔊")
        self.muteToggled.emit()
        
    def fade_in(self):
        """Animate control bar fade in."""
        self._fade_animation.stop()
        self._fade_animation.setStartValue(self._opacity_effect.opacity())
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setDuration(Timings.FADE_IN)
        self._fade_animation.start()
        
    def fade_out(self):
        """Animate control bar fade out."""
        self._fade_animation.stop()
        self._fade_animation.setStartValue(self._opacity_effect.opacity())
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setDuration(Timings.FADE_OUT)
        self._fade_animation.start()
        
    def set_playing_state(self, is_playing):
        """
        Update play/pause button state.
        
        Args:
            is_playing: Boolean indicating if video is playing
        """
        self._is_playing = is_playing
        self._play_pause_btn.setText("❚❚" if is_playing else "▶")
        
    def update_time(self, current, total):
        """
        Update time display.
        
        Args:
            current: Current time string
            total: Total time string
        """
        self._current_time_label.setText(current)
        self._total_time_label.setText(total)
        
    def update_progress(self, value):
        """
        Update progress bar value.
        
        Args:
            value: Progress value (0-1000)
        """
        self._progress_bar.setValue(value)
