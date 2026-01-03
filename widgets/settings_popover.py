"""
Settings Popover Widget - Playback speed controls
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QRadioButton, QButtonGroup, QFrame
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor
from constants import *
from styles import get_popover_container_style


class SettingsPopover(QWidget):
    """Professional settings popover for playback options"""
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.media_player_ref = None
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup popover UI with modern glass effect"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Container with glass effect
        container = QWidget()
        container.setStyleSheet(get_popover_container_style())
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Playback Speed")
        title.setStyleSheet(f"color: white; font-size: {FONT_SIZE_MEDIUM}px; font-weight: 600;")
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: rgba(255, 255, 255, 180);
                font-size: 20px;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover { 
                background-color: rgba(229, 9, 20, 180); 
                color: white;
            }
        """)
        close_btn.clicked.connect(self.hide)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        container_layout.addLayout(header_layout)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 15);")
        separator.setFixedHeight(1)
        container_layout.addWidget(separator)
        
        # Speed radio buttons
        self.speed_group = QButtonGroup(self)
        speeds = [
            ("0.25×", 0.25), ("0.5×", 0.5), ("0.75×", 0.75),
            ("Normal", 1.0), ("1.25×", 1.25), ("1.5×", 1.5), ("2×", 2.0)
        ]
        
        for label, rate in speeds:
            rb = QRadioButton(label)
            rb.setStyleSheet(f"""
                QRadioButton {{
                    color: white;
                    font-size: {FONT_SIZE_SMALL}px;
                    padding: 6px 4px;
                }}
                QRadioButton::indicator {{
                    width: 14px;
                    height: 14px;
                }}
                QRadioButton::indicator:unchecked {{
                    border: 2px solid rgba(255, 255, 255, 40);
                    border-radius: 7px;
                    background-color: transparent;
                }}
                QRadioButton::indicator:checked {{
                    border: 2px solid {THEME_PRIMARY};
                    border-radius: 7px;
                    background-color: {THEME_PRIMARY};
                }}
                QRadioButton:hover {{
                    background-color: rgba(255, 255, 255, 8);
                    border-radius: 4px;
                }}
            """)
            if rate == 1.0:
                rb.setChecked(True)
            rb.toggled.connect(
                lambda checked, r=rate: self._on_speed_changed(r) if checked else None
            )
            self.speed_group.addButton(rb)
            container_layout.addWidget(rb)
        
        container.setMinimumWidth(240)
        layout.addWidget(container)
        
        # Add shadow effect
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        container.setGraphicsEffect(shadow)
        
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
