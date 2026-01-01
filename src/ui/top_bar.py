"""
Top Overlay Bar - Netflix-inspired title and action buttons.

Responsibilities:
- Display video title
- Provide back, settings, and fullscreen buttons
- Auto-hide/show with animations
- Netflix visual styling
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import Colors, Dimensions, Timings, Fonts, MockData


class TopBarButton(QPushButton):
    """
    Custom button for top bar with Netflix styling.
    
    Responsibilities:
    - Display icon/text
    - Netflix hover effects
    """
    
    def __init__(self, text, parent=None):
        """
        Initialize top bar button.
        
        Args:
            text: Button text/icon
            parent: Parent widget
        """
        super().__init__(text, parent)
        
        # Apply Netflix styling
        self._apply_style()
        
        # Set fixed size
        self.setFixedSize(40, 40)
        
    def _apply_style(self):
        """Apply Netflix button styling."""
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.TEXT_PRIMARY};
                border: none;
                border-radius: 4px;
                font-size: 18px;
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


class TopBar(QWidget):
    """
    Top overlay bar with title and action buttons.
    
    Responsibilities:
    - Display video title
    - Provide navigation buttons
    - Auto-hide with animations
    - Match Netflix aesthetic
    
    Signals:
        backClicked: User clicked back button
        directoryClicked: User clicked directory/playlist button
        settingsClicked: User clicked settings button
        fullscreenClicked: User clicked fullscreen button
    """
    
    # Signals
    backClicked = Signal()
    directoryClicked = Signal()
    settingsClicked = Signal()
    fullscreenClicked = Signal()
    
    def __init__(self, parent=None):
        """Initialize top bar."""
        super().__init__(parent)
        
        # Setup UI
        self._setup_ui()
        
        # Setup animations
        self._setup_animations()
        
    def _setup_ui(self):
        """Create and layout top bar elements."""
        # Set fixed height
        self.setFixedHeight(Dimensions.TOP_BAR_HEIGHT)
        
        # Apply background with gradient (fade to transparent)
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {Colors.CONTROL_BACKGROUND},
                    stop:1 rgba(0, 0, 0, 0)
                );
            }}
        """)
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            Dimensions.TOP_BAR_PADDING_H,
            Dimensions.TOP_BAR_PADDING_H,
            Dimensions.TOP_BAR_PADDING_H,
            Dimensions.TOP_BAR_PADDING_H
        )
        layout.setSpacing(Dimensions.BUTTON_SPACING)
        
        # Back button
        self._back_btn = TopBarButton("←")
        self._back_btn.clicked.connect(self.backClicked.emit)
        self._back_btn.hide()  # Hidden until navigation feature is implemented
        layout.addWidget(self._back_btn)
        
        # Title label
        self._title_label = QLabel("")  # Empty until video loads
        self._title_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: {Fonts.VIDEO_TITLE}px;
                font-weight: {Fonts.MEDIUM};
                font-family: {Fonts.FAMILY};
                background: transparent;
            }}
        """)
        layout.addWidget(self._title_label)
        
        # Spacer to push right buttons to the right
        layout.addStretch()
        
        # Directory/playlist button
        self._directory_btn = TopBarButton("📁")
        self._directory_btn.setToolTip("Directory Playlist")
        self._directory_btn.clicked.connect(self.directoryClicked.emit)
        layout.addWidget(self._directory_btn)
        
        # Settings button
        self._settings_btn = TopBarButton("⚙")
        self._settings_btn.setToolTip("Settings")
        self._settings_btn.clicked.connect(self.settingsClicked.emit)
        layout.addWidget(self._settings_btn)
        
        # Fullscreen button
        self._fullscreen_btn = TopBarButton("⛶")
        self._fullscreen_btn.setToolTip("Fullscreen")
        self._fullscreen_btn.clicked.connect(self.fullscreenClicked.emit)
        layout.addWidget(self._fullscreen_btn)
        
    def _setup_animations(self):
        """Setup opacity animation for auto-hide effect."""
        # Create opacity effect
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        
        # Create fade animation
        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_animation.setDuration(Timings.FADE_OUT)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
    def fade_in(self):
        """Animate top bar fade in."""
        self._fade_animation.stop()
        self._fade_animation.setStartValue(self._opacity_effect.opacity())
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setDuration(Timings.FADE_IN)
        self._fade_animation.start()
        
    def fade_out(self):
        """Animate top bar fade out."""
        self._fade_animation.stop()
        self._fade_animation.setStartValue(self._opacity_effect.opacity())
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.setDuration(Timings.FADE_OUT)
        self._fade_animation.start()
        
    def set_title(self, title):
        """
        Update the video title display.
        
        Args:
            title: Video title string
        """
        self._title_label.setText(title)
        
    def set_fullscreen_icon(self, is_fullscreen):
        """
        Update fullscreen button icon based on state.
        
        Args:
            is_fullscreen: Boolean indicating if in fullscreen mode
        """
        self._fullscreen_btn.setText("□" if is_fullscreen else "⛶")
