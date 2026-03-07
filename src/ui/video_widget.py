from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QApplication
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

        # Gesture disambiguation (single click vs double click vs press+hold).
        # We delay single-click emission until the double-click interval passes,
        # and treat a press+hold as a separate gesture.
        self._pressed = False
        self._hold_consumed = False

        self._hold_threshold_ms = 330
        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._on_hold_timeout)

        self._single_click_timer = QTimer(self)
        self._single_click_timer.setSingleShot(True)
        self._single_click_timer.timeout.connect(self._emit_single_click)

    user_activity = Signal()
    single_clicked = Signal()
    double_clicked = Signal()
    hold_fast_forward_started = Signal()
    hold_fast_forward_ended = Signal()

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
            self._pressed = True
            self._hold_consumed = False
            self._hold_timer.stop()
            self._hold_timer.start(self._hold_threshold_ms)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = False
            self._hold_timer.stop()

            if self._hold_consumed:
                # End hold gesture (used for "2x while held" behaviors).
                self.hold_fast_forward_ended.emit()

            # If hold gesture already fired, do nothing else.
            if not self._hold_consumed:
                # Defer single-click until we know it wasn't a double click.
                interval = int(QApplication.doubleClickInterval())
                self._single_click_timer.stop()
                self._single_click_timer.start(max(1, interval))

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._single_click_timer.stop()
            self._hold_timer.stop()
            self._pressed = False
            self._hold_consumed = True
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)

    def _on_hold_timeout(self) -> None:
        if not self._pressed:
            return
        # Consume this press; no single-click will be emitted.
        self._hold_consumed = True
        self._single_click_timer.stop()
        self.hold_fast_forward_started.emit()

    def _emit_single_click(self) -> None:
        # Extra guard: don't emit if the press was consumed by hold/double.
        if self._hold_consumed:
            return
        self.single_clicked.emit()
