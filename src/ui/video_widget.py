from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import time

from PySide6.QtCore import Qt, Signal, QTimer, QRect
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

        # View transform (VLC-like): fit/fill, zoom, aspect override, crop.
        self._fit_to_window = True  # True=Fit (letterbox), False=Fill (crop-to-fill)
        self._zoom = 1.0
        self._aspect_override: Optional[float] = None  # width/height
        self._crop_ratio: Optional[float] = None  # width/height

        # Cache key includes transform + current frame identity.
        self._cache_frame_key: Optional[int] = None
        self._cache_src_rect: Optional[tuple[int, int, int, int]] = None

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
        self._cache_frame_key = None
        self.update()

    def set_view_transform(
        self,
        *,
        fit_to_window: bool,
        zoom: float,
        aspect_override: Optional[float],
        crop_ratio: Optional[float],
    ) -> None:
        """Set VLC-like view transform parameters.

        aspect_override/crop_ratio are width/height floats (e.g. 16/9).
        Use None for Auto/Off.
        """
        self._fit_to_window = bool(fit_to_window)
        try:
            z = float(zoom)
        except Exception:
            z = 1.0
        if z <= 0:
            z = 1.0
        self._zoom = max(0.1, min(8.0, float(z)))

        def _clean_ratio(r: Optional[float]) -> Optional[float]:
            if r is None:
                return None
            try:
                rr = float(r)
            except Exception:
                return None
            if rr <= 0.0 or rr != rr:
                return None
            return max(0.05, min(20.0, rr))

        self._aspect_override = _clean_ratio(aspect_override)
        self._crop_ratio = _clean_ratio(crop_ratio)

        # Invalidate cache.
        self._cache_src_size = None
        self._cache_target_size = None
        self._cache_scaled = None
        self._cache_frame_key = None
        self._cache_src_rect = None
        self.update()

    def grab_current_image(self) -> Optional[QImage]:
        """Return a copy of the current decoded frame image (for snapshot/wallpaper)."""
        try:
            if self._frame is None or self._frame.image.isNull():
                return None
            return self._frame.image.copy()
        except Exception:
            return None

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

        # Compute crop source rect.
        src_w = int(img.width())
        src_h = int(img.height())
        if src_w <= 0 or src_h <= 0:
            painter.end()
            return

        crop_x = 0
        crop_y = 0
        crop_w = src_w
        crop_h = src_h
        if self._crop_ratio is not None:
            r = float(self._crop_ratio)
            if r > 0:
                src_r = float(src_w) / float(src_h)
                if src_r > r:
                    # Too wide: crop width.
                    crop_w = int(round(float(src_h) * r))
                    crop_w = max(1, min(crop_w, src_w))
                    crop_x = int((src_w - crop_w) // 2)
                else:
                    # Too tall: crop height.
                    crop_h = int(round(float(src_w) / r))
                    crop_h = max(1, min(crop_h, src_h))
                    crop_y = int((src_h - crop_h) // 2)

        src_rect = QRect(int(crop_x), int(crop_y), int(crop_w), int(crop_h))

        # Presentation aspect ratio.
        if self._aspect_override is not None:
            aspect = float(self._aspect_override)
        else:
            aspect = float(crop_w) / float(crop_h)
        if aspect <= 0:
            aspect = 1.0

        # Compute draw rect size using fit/fill + zoom.
        tw = max(1, int(target.width()))
        th = max(1, int(target.height()))
        target_r = float(tw) / float(th)

        if self._fit_to_window:
            # Fit (letterbox): take largest rect that fits inside widget.
            if target_r >= aspect:
                draw_h = float(th)
                draw_w = draw_h * aspect
            else:
                draw_w = float(tw)
                draw_h = draw_w / aspect
        else:
            # Fill (crop-to-fill): take smallest rect that covers widget.
            if target_r >= aspect:
                draw_w = float(tw)
                draw_h = draw_w / aspect
            else:
                draw_h = float(th)
                draw_w = draw_h * aspect

        z = float(self._zoom) if self._zoom else 1.0
        draw_w *= z
        draw_h *= z

        draw_w_i = max(1, int(round(draw_w)))
        draw_h_i = max(1, int(round(draw_h)))

        # Scale/crop image into draw size.
        src_size = (src_w, src_h)
        tgt_size = (draw_w_i, draw_h_i)
        frame_key = None
        try:
            frame_key = int(img.cacheKey())
        except Exception:
            frame_key = None
        src_rect_key = (int(src_rect.x()), int(src_rect.y()), int(src_rect.width()), int(src_rect.height()))

        if (
            self._cache_scaled is None
            or self._cache_src_size != src_size
            or self._cache_target_size != tgt_size
            or self._cache_frame_key != frame_key
            or self._cache_src_rect != src_rect_key
        ):
            # NOTE: copy() is required; QImage views over temporary bytes can get invalid.
            cropped = img.copy(src_rect)
            self._cache_scaled = cropped.scaled(
                draw_w_i,
                draw_h_i,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._cache_src_size = src_size
            self._cache_target_size = tgt_size
            self._cache_frame_key = frame_key
            self._cache_src_rect = src_rect_key

        scaled = self._cache_scaled
        x = int((tw - scaled.width()) // 2)
        y = int((th - scaled.height()) // 2)
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
