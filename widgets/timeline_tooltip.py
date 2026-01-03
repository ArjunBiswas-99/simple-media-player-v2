"""
Timeline Tooltip Widget - Shows thumbnail preview + timestamp on hover
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from constants import *
from styles import *


class TimelineTooltip(QWidget):
    """Tooltip showing thumbnail preview and timestamp on timeline hover"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Top-level window for positioning over video
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Thumbnail label
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(160, 90)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet(f"""
            QLabel {{
                background-color: {THEME_BLACK};
                border: 2px solid {THEME_PRIMARY};
                border-radius: 4px;
            }}
        """)
        
        # Timestamp label
        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                background-color: rgba(20, 20, 20, 0.9);
                padding: 4px 12px;
                border-radius: 4px;
                font-size: {FONT_SIZE_MEDIUM}px;
                font-weight: {FONT_WEIGHT_MEDIUM};
            }}
        """)
        
        layout.addWidget(self.thumbnail_label)
        layout.addWidget(self.time_label)
        
        self.setLayout(layout)
        self.hide()
        
        # State
        self.current_timestamp = None
        self.has_thumbnail = False
    
    def show_at_position(self, global_x, global_y, timestamp, formatted_time):
        """Show tooltip at specific position with timestamp"""
        # Only reset if timestamp changed significantly (different interval)
        if self.current_timestamp is None or abs(timestamp - self.current_timestamp) > 2.0:
            self.has_thumbnail = False
        
        self.current_timestamp = timestamp
        self.time_label.setText(formatted_time)
        
        # Show loading state if no thumbnail yet
        if not self.has_thumbnail:
            self.thumbnail_label.setText("Loading...")
            self.thumbnail_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {THEME_BLACK};
                    border: 2px solid {THEME_PRIMARY};
                    border-radius: 4px;
                    color: {THEME_LIGHT_GRAY};
                    font-size: {FONT_SIZE_MEDIUM}px;
                }}
            """)
        
        # Position tooltip above cursor (centered)
        tooltip_width = 160
        tooltip_height = 130  # 90 + 40 for time label
        x = global_x - tooltip_width // 2
        y = global_y - tooltip_height - 10  # 10px above cursor
        
        self.move(x, y)
        self.show()
        self.raise_()
    
    def update_thumbnail(self, jpeg_bytes):
        """Update thumbnail from compressed JPEG bytes"""
        if jpeg_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(jpeg_bytes)
            
            if not pixmap.isNull():
                self.thumbnail_label.setPixmap(pixmap)
                self.thumbnail_label.setText("")  # Clear loading text
                self.thumbnail_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: {THEME_BLACK};
                        border: 2px solid {THEME_PRIMARY};
                        border-radius: 4px;
                    }}
                """)
                self.has_thumbnail = True
    
    def reset(self):
        """Reset tooltip state"""
        self.thumbnail_label.clear()
        self.thumbnail_label.setText("")
        self.time_label.setText("")
        self.has_thumbnail = False
        self.hide()
