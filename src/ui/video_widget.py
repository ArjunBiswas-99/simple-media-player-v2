from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class VideoFrame:
    image: QImage
    pts_seconds: float


class VideoWidget(QWidget):
    """Central video canvas.

    Phase 1: QWidget paint of QImage.
    Phase 2: can be replaced with QOpenGLWidget-based renderer.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)
        self._frame: Optional[VideoFrame] = None
        self.setMouseTracking(True)

    user_activity = Signal()
    single_clicked = Signal()
    double_clicked = Signal()

    def set_frame(self, frame: Optional[VideoFrame]) -> None:
        self._frame = frame
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        if not self._frame or self._frame.image.isNull():
            painter.end()
            return

        img = self._frame.image
        target = self.rect()
        scaled = img.scaled(
            target.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (target.width() - scaled.width()) // 2
        y = (target.height() - scaled.height()) // 2
        painter.drawImage(x, y, scaled)
        painter.end()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        self.user_activity.emit()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.single_clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)
