"""
Speed Indicator Widget - YouTube-style 2x overlay
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import pyqtProperty
from constants import NETFLIX_RED


class SpeedIndicator(QLabel):
    """2x speed indicator overlay for YouTube-style hold-to-speed"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("2×")
        self.setStyleSheet(f"""
            QLabel {{
                color: white;
                background-color: rgba(229, 9, 20, 220);
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 28px;
                font-weight: bold;
            }}
        """)
        self.hide()
        self._opacity = 1.0
        
    def get_opacity(self):
        return self._opacity
    
    def set_opacity(self, value):
        self._opacity = value
        self.setWindowOpacity(value)
    
    opacity = pyqtProperty(float, get_opacity, set_opacity)
