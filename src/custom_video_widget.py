"""
Custom Video Widget for FFmpeg Frame Rendering
Efficiently renders decoded video frames from FFmpeg/PyAV.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QImage, QPaintEvent


class CustomVideoWidget(QWidget):
    """Widget for rendering video frames from FFmpeg."""
    
    # Signal emitted when widget is resized (for player to adjust rendering)
    resized = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._current_frame = None  # QImage
        self._aspect_ratio = 16 / 9  # Default aspect ratio
        self._video_size = None  # Original video size (width, height)
        
        # Set widget properties for efficient rendering
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAutoFillBackground(False)
        
        # Black background
        self.setStyleSheet("background-color: black;")
    
    def set_frame(self, frame_data, width, height, format=QImage.Format.Format_RGB888):
        """
        Set the current video frame to display.
        
        Args:
            frame_data: Raw frame bytes (RGB or RGBA)
            width: Frame width
            height: Frame height
            format: QImage format (default RGB888)
        """
        if frame_data is None:
            self._current_frame = None
            self.update()
            return
        
        # Create QImage from frame data
        bytes_per_line = width * (3 if format == QImage.Format.Format_RGB888 else 4)
        self._current_frame = QImage(
            frame_data,
            width,
            height,
            bytes_per_line,
            format
        )
        
        # Update aspect ratio
        if width > 0 and height > 0:
            self._aspect_ratio = width / height
            self._video_size = (width, height)
        
        # Trigger repaint
        self.update()
    
    def clear_frame(self):
        """Clear the current frame (show black screen)."""
        self._current_frame = None
        self.update()
    
    def get_video_size(self):
        """Get original video dimensions."""
        return self._video_size
    
    def get_aspect_ratio(self):
        """Get video aspect ratio."""
        return self._aspect_ratio
    
    def paintEvent(self, event: QPaintEvent):
        """Paint the video frame with aspect ratio preservation."""
        painter = QPainter(self)
        
        # Fill background with black
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        
        # If no frame, just show black
        if self._current_frame is None:
            return
        
        # Calculate destination rectangle to preserve aspect ratio
        dest_rect = self._calculate_aspect_rect()
        
        # Draw the frame
        painter.drawImage(dest_rect, self._current_frame)
    
    def _calculate_aspect_rect(self):
        """Calculate the rectangle for drawing with aspect ratio preserved."""
        widget_width = self.width()
        widget_height = self.height()
        
        if widget_width <= 0 or widget_height <= 0:
            return QRect(0, 0, widget_width, widget_height)
        
        widget_aspect = widget_width / widget_height
        
        if widget_aspect > self._aspect_ratio:
            # Widget is wider than video - add black bars on sides
            new_width = int(widget_height * self._aspect_ratio)
            x_offset = (widget_width - new_width) // 2
            return QRect(x_offset, 0, new_width, widget_height)
        else:
            # Widget is taller than video - add black bars on top/bottom
            new_height = int(widget_width / self._aspect_ratio)
            y_offset = (widget_height - new_height) // 2
            return QRect(0, y_offset, widget_width, new_height)
    
    def resizeEvent(self, event):
        """Handle widget resize."""
        super().resizeEvent(event)
        self.resized.emit()
        self.update()
    
    def sizeHint(self):
        """Provide a reasonable default size."""
        from PyQt6.QtCore import QSize
        return QSize(800, 450)  # 16:9 aspect ratio
