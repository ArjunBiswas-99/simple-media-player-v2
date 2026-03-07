from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import time

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QWidget

from util.debug_log import log_event


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
        self._hold_active = False

        # Custom click disambiguation window (avoid depending on OS interval;
        # keep behavior consistent and prevent slow double-click from firing a
        # single-click play/pause first).
        self._click_count = 0
        self._click_first_ts = 0.0
        self._click_pos = None
        self._double_click_window_ms = 380

        self._hold_threshold_ms = 330
        self._hold_timer = QTimer(self)
        self._hold_timer.setSingleShot(True)
        self._hold_timer.timeout.connect(self._on_hold_timeout)

        self._single_click_timer = QTimer(self)
        self._single_click_timer.setSingleShot(True)
        self._single_click_timer.timeout.connect(self._emit_single_click)

        # Single click is emitted only after the double-click window.
        self._single_click_delay_ms = int(self._double_click_window_ms)

        # Render cache: scaling every paint is expensive.
        self._cache_src_size = None  # (w, h)
        self._cache_target_size = None  # (w, h)
        self._cache_scaled: Optional[QImage] = None

        # Suppress an immediate "click" after a context menu closes.
        # (On Windows, Qt can replay the mouse event that dismissed the menu.)
        self._suppress_click_until_ts = 0.0

    user_activity = Signal()
    single_clicked = Signal()
    double_clicked = Signal()
    hold_fast_forward_started = Signal()
    hold_fast_forward_ended = Signal()
    context_menu_requested = Signal(object)  # global_pos: QPoint

    def set_frame(self, frame: Optional[VideoFrame]) -> None:
        self._frame = frame
        # Invalidate scaled cache; new source image.
        self._cache_src_size = None
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: N802
        # Invalidate scaled cache; target size changed.
        self._cache_target_size = None
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        if not self._frame or self._frame.image.isNull():
            painter.end()
            return

        img = self._frame.image
        target = self.rect()

        src_size = (img.width(), img.height())
        tgt_size = (target.width(), target.height())
        if self._cache_scaled is None or self._cache_src_size != src_size or self._cache_target_size != tgt_size:
            self._cache_scaled = img.scaled(
                target.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                # Smooth looks nicer but is expensive; caching makes it OK.
                Qt.TransformationMode.SmoothTransformation,
            )
            self._cache_src_size = src_size
            self._cache_target_size = tgt_size

        scaled = self._cache_scaled
        x = (target.width() - scaled.width()) // 2
        y = (target.height() - scaled.height()) // 2
        painter.drawImage(x, y, scaled)
        painter.end()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        self.user_activity.emit()
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            # If a context menu just closed, ignore this press entirely.
            try:
                if time.monotonic() < float(self._suppress_click_until_ts):
                    event.accept()
                    return
            except Exception:
                pass

            self._pressed = True
            log_event("pane", "mouse:left_press")
            self._hold_consumed = False
            self._hold_active = False
            self._hold_timer.stop()
            self._hold_timer.start(self._hold_threshold_ms)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            suppress = False
            try:
                suppress = time.monotonic() < float(self._suppress_click_until_ts)
            except Exception:
                suppress = False

            # Always clear press/hold state on release.
            self._pressed = False
            self._hold_timer.stop()

            log_event("pane", f"mouse:left_release hold_active={self._hold_active} hold_consumed={self._hold_consumed}")

            if self._hold_active:
                # End hold gesture (used for "2x while held" behaviors).
                self._hold_active = False
                log_event("pane", "gesture:hold_fast_forward_end")
                self.hold_fast_forward_ended.emit()

            if suppress:
                # Menu-dismiss click: do not trigger play/pause or click gestures.
                event.accept()
                return

            # If hold gesture already fired, do nothing else.
            if not self._hold_consumed:
                # Custom single/double-click window.
                now = time.monotonic()
                pos = event.pos()

                if self._click_count == 0:
                    self._click_count = 1
                    self._click_first_ts = now
                    self._click_pos = pos
                    self._single_click_timer.stop()
                    self._single_click_timer.start(max(1, int(self._single_click_delay_ms)))
                else:
                    dt_ms = (now - float(self._click_first_ts)) * 1000.0
                    same_spot = True
                    try:
                        if self._click_pos is not None:
                            dx = pos.x() - self._click_pos.x()
                            dy = pos.y() - self._click_pos.y()
                            same_spot = (dx * dx + dy * dy) <= (14 * 14)
                    except Exception:
                        same_spot = True

                    if dt_ms <= float(self._double_click_window_ms) and same_spot:
                        self._single_click_timer.stop()
                        self._click_count = 0
                        self._click_pos = None
                        log_event("pane", "gesture:double_click")
                        self.double_clicked.emit()
                    else:
                        # Too slow / far: treat as a new first click.
                        self._click_count = 1
                        self._click_first_ts = now
                        self._click_pos = pos
                        self._single_click_timer.stop()
                        self._single_click_timer.start(max(1, int(self._single_click_delay_ms)))

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        # We implement our own double-click logic in mouseReleaseEvent.
        event.accept()
        return

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        # Right-click context menu request.
        try:
            log_event("pane", "gesture:context_menu")
            self.context_menu_requested.emit(event.globalPos())
            # Prevent the menu-dismiss click from toggling playback.
            self._suppress_click_until_ts = time.monotonic() + 0.25
        except Exception:
            pass
        event.accept()
        return

    def _on_hold_timeout(self) -> None:
        if not self._pressed:
            return
        # Consume this press; no single-click will be emitted.
        self._hold_consumed = True
        self._hold_active = True
        self._click_count = 0
        self._click_pos = None
        self._single_click_timer.stop()
        log_event("pane", "gesture:hold_fast_forward_start")
        self.hold_fast_forward_started.emit()

    def _emit_single_click(self) -> None:
        # Extra guard: don't emit if the press was consumed by hold/double.
        if self._hold_consumed:
            return
        self._click_count = 0
        self._click_pos = None
        log_event("pane", "gesture:single_click")
        self.single_clicked.emit()
