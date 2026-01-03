"""
Speed Indicator Widget - 2x speed overlay
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import pyqtProperty
from constants import THEME_PRIMARY


class SpeedIndicator(QLabel):
    """2x speed indicator overlay for hold-to-speed feature"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("2×")
        self.setStyleSheet(f"""
            QLabel {{
                color: white;
                background-color: {THEME_PRIMARY};
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
