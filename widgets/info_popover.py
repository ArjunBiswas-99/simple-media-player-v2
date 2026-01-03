"""
Info Popover Widget - Video technical details
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor
from constants import *
from styles import get_popover_container_style


class InfoPopover(QWidget):
    """Professional info popover for video technical details"""
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
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
        title = QLabel("Video Information")
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
        
        # Info labels (will be populated dynamically)
        self.info_labels = {}
        info_items = [
            ("File", "filename"),
            ("Resolution", "resolution"),
            ("Duration", "duration"),
            ("Video Codec", "video_codec"),
            ("Audio Codec", "audio_codec"),
            ("Frame Rate", "frame_rate"),
            ("Bit Rate", "bit_rate"),
            ("File Size", "file_size"),
        ]
        
        for label_text, key in info_items:
            row = QHBoxLayout()
            row.setSpacing(8)
            
            label = QLabel(f"{label_text}:")
            label.setStyleSheet(f"""
                color: rgba(255, 255, 255, 180);
                font-size: {FONT_SIZE_SMALL}px;
                font-weight: 500;
            """)
            label.setMinimumWidth(90)
            
            value = QLabel("—")
            value.setStyleSheet(f"""
                color: white;
                font-size: {FONT_SIZE_SMALL}px;
                font-weight: 400;
            """)
            value.setWordWrap(True)
            
            self.info_labels[key] = value
            
            row.addWidget(label)
            row.addWidget(value, stretch=1)
            container_layout.addLayout(row)
        
        container.setMinimumWidth(320)
        layout.addWidget(container)
        
        # Add shadow effect
        from PyQt6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 4)
        container.setGraphicsEffect(shadow)
    
    def update_info(self, info_dict):
        """Update video information"""
        for key, value in info_dict.items():
            if key in self.info_labels:
                self.info_labels[key].setText(str(value))
        
    def show_at_button(self, button):
        """Position popover above button"""
        self.adjustSize()
        button_pos = button.mapToGlobal(QPoint(0, 0))
        x = button_pos.x() - self.width() + button.width()
        y = button_pos.y() - self.height() - 10
        self.move(x, y)
        self.show()
        self.raise_()
