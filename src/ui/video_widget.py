"""
Video Widget - MPV video playback area with interaction handling.

Responsibilities:
- Embed MPV player for video rendering
- Handle mouse events (click-to-play, click-and-hold)
- Emit signals for user interactions
- Display video content
"""

from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt, Signal, QTimer, QPoint
from PySide6.QtGui import QPainter, QColor, QFont


class VideoWidget(QWidget):
    """
    Video display widget with MPV integration.
    
    Signals:
        clicked: Emitted when user clicks on video area (for play/pause toggle)
        mouseMovedOnVideo: Emitted when mouse moves over video (for showing controls)
        scrubbing: Emitted with horizontal mouse delta when click-and-hold scrubbing
    """
    
    # Signals
    clicked = Signal()
    mouseMovedOnVideo = Signal()
    scrubbing = Signal(int)  # horizontal delta for scrubbing
    
    def __init__(self, parent=None):
        """
        Initialize the video widget.
        
        Args:
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        
        # State variables
        self._is_mouse_pressed = False
        self._last_mouse_pos = QPoint()
        self._has_video = False
        
        # Setup UI
        self._setup_ui()
        
    def _setup_ui(self):
        """Configure the widget's appearance and behavior."""
        # Set minimum size
        self.setMinimumSize(640, 360)
        
        # Enable mouse tracking
        self.setMouseTracking(True)
        
        # Set black background
        self.setStyleSheet("background-color: black;")
        
        # Create placeholder label (shown when no video)
        self._placeholder_label = QLabel("No media loaded\n\nOpen a file from Media menu or press Ctrl+O", self)
        self._placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder_label.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.5);
                font-size: 18px;
                font-weight: 300;
            }
        """)
        self._placeholder_label.setGeometry(0, 0, self.width(), self.height())
        
    def show_placeholder(self):
        """Show the placeholder label (when no video)."""
        self._has_video = False
        self._placeholder_label.show()
        
    def hide_placeholder(self):
        """Hide the placeholder label (when video is playing)."""
        self._placeholder_label.hide()
        
    def resizeEvent(self, event):
        """
        Handle resize to keep placeholder centered and MPV sized.
        
        Args:
            event: Resize event
        """
        super().resizeEvent(event)
        
        # Resize placeholder
        if hasattr(self, '_placeholder_label'):
            self._placeholder_label.setGeometry(0, 0, self.width(), self.height())
    
    def mousePressEvent(self, event):
        """
        Handle mouse press for click-to-play and scrubbing initiation.
        
        Args:
            event: Mouse event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_mouse_pressed = True
            self._last_mouse_pos = event.pos()
            
    def mouseReleaseEvent(self, event):
        """
        Handle mouse release for click-to-play.
        
        Args:
            event: Mouse event
        """
        if event.button() == Qt.MouseButton.LeftButton and self._is_mouse_pressed:
            # Calculate movement distance
            delta = event.pos() - self._last_mouse_pos
            movement_distance = (delta.x() ** 2 + delta.y() ** 2) ** 0.5
            
            # If movement is small, treat as click
            if movement_distance < 10:
                self.clicked.emit()
            
            self._is_mouse_pressed = False
            
    def mouseMoveEvent(self, event):
        """
        Handle mouse movement for control visibility and scrubbing.
        
        Args:
            event: Mouse event
        """
        # Always emit mouse moved signal
        self.mouseMovedOnVideo.emit()
        
        # If mouse is pressed, handle scrubbing
        if self._is_mouse_pressed:
            delta = event.pos() - self._last_mouse_pos
            if abs(delta.x()) > 2:
                self.scrubbing.emit(delta.x())
                self._last_mouse_pos = event.pos()
