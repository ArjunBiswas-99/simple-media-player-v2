"""
Animated Button with Ripple Effect
Advanced button component for CEO-ready demos
"""

from PyQt6.QtWidgets import QPushButton, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation, QSize, QEasingCurve, QPoint, pyqtProperty
from PyQt6.QtGui import QPainter, QColor
import qtawesome as qta
from constants import THEME_PRIMARY
from styles import get_button_style


class AnimatedButton(QPushButton):
    """Button with ripple effect, glow, and smooth animations"""
    
    def __init__(self, icon_name, button_size, icon_size, tooltip, parent=None):
        super().__init__(parent)
        self.setFixedSize(button_size, button_size)
        self.setStyleSheet(get_button_style(button_size))
        self.setToolTip(tooltip)
        
        # Store properties
        self.icon_name = icon_name
        self.icon_size = icon_size
        self.button_size = button_size
        self._ripple_radius = 0
        self.ripple_center = QPoint(button_size // 2, button_size // 2)
        
        # Create icon with primary red color
        self.setIcon(qta.icon(icon_name, color=THEME_PRIMARY))
        self.setIconSize(QSize(icon_size, icon_size))
        
    @pyqtProperty(float)
    def ripple_radius(self):
        return self._ripple_radius
    
    @ripple_radius.setter
    def ripple_radius(self, value):
        self._ripple_radius = value
        self.update()
    
    def paintEvent(self, event):
        """Custom paint with ripple effect"""
        super().paintEvent(event)
        
        if self._ripple_radius > 0:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Ripple color fades out as it expands
            opacity = int(80 * (1 - self._ripple_radius / (self.button_size * 0.7)))
            color = QColor(255, 255, 255, max(0, opacity))
            
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(self.ripple_center, int(self._ripple_radius), int(self._ripple_radius))
    
    def enterEvent(self, event):
        """Enhanced hover effect with icon glow and scale"""
        # Icon color change to white
        self.setIcon(qta.icon(self.icon_name, color='white'))
        
        # Scale up animation with bounce
        if not hasattr(self, '_scale_anim'):
            self._scale_anim = QPropertyAnimation(self, b"iconSize")
        self._scale_anim.stop()
        self._scale_anim.setDuration(200)
        self._scale_anim.setStartValue(self.iconSize())
        self._scale_anim.setEndValue(QSize(int(self.icon_size * 1.2), int(self.icon_size * 1.2)))
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self._scale_anim.start()
        
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Scale back down when mouse leaves"""
        self.setIcon(qta.icon(self.icon_name, color=THEME_PRIMARY))
        
        if not hasattr(self, '_scale_anim'):
            self._scale_anim = QPropertyAnimation(self, b"iconSize")
        self._scale_anim.stop()
        self._scale_anim.setDuration(200)
        self._scale_anim.setStartValue(self.iconSize())
        self._scale_anim.setEndValue(QSize(self.icon_size, self.icon_size))
        self._scale_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scale_anim.start()
        
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Ripple effect + punch animation on click"""
        self.ripple_center = event.position().toPoint()
        self._ripple_radius = 0
        
        # Animate ripple expansion
        if not hasattr(self, '_ripple_anim'):
            self._ripple_anim = QPropertyAnimation(self, b"ripple_radius")
        self._ripple_anim.stop()
        self._ripple_anim.setDuration(400)
        self._ripple_anim.setStartValue(0)
        self._ripple_anim.setEndValue(self.button_size * 0.7)
        self._ripple_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._ripple_anim.start()
        
        # Punch effect - scale down then bounce back
        if not hasattr(self, '_punch_anim'):
            self._punch_anim = QPropertyAnimation(self, b"iconSize")
        self._punch_anim.stop()
        self._punch_anim.setDuration(200)
        self._punch_anim.setStartValue(self.iconSize())
        self._punch_anim.setEndValue(QSize(int(self.icon_size * 0.85), int(self.icon_size * 0.85)))
        self._punch_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        
        # Spring back after punch
        if not hasattr(self, '_spring_anim'):
            self._spring_anim = QPropertyAnimation(self, b"iconSize")
        self._spring_anim.setDuration(300)
        self._spring_anim.setStartValue(QSize(int(self.icon_size * 0.85), int(self.icon_size * 0.85)))
        # If hovering, spring back to hover size, otherwise normal size
        target_size = int(self.icon_size * 1.2) if self.underMouse() else self.icon_size
        self._spring_anim.setEndValue(QSize(target_size, target_size))
        self._spring_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        # Chain the animations: punch down → spring back
        self._punch_anim.finished.connect(self._spring_anim.start)
        self._punch_anim.start()
        
        super().mousePressEvent(event)
