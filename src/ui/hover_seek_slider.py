from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QEnterEvent, QMouseEvent
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionSlider


class HoverSeekSlider(QSlider):
    """Horizontal timeline slider with YouTube-like hover preview and click-to-seek.

    - Emits preview positions (value + x coordinate) without needing to change the value.
    - Groove-click jumps to exact click position (not pageStep).
    """

    preview_moved = Signal(int, int, bool)  # value, x_local, dragging
    preview_left = Signal()

    def __init__(self, orientation: Qt.Orientation, parent=None) -> None:
        super().__init__(orientation, parent)
        self.setMouseTracking(True)

        # When user clicks on groove (not handle), we simulate a drag so existing
        # scrub wiring (sliderPressed/sliderMoved/sliderReleased) still works.
        self._groove_drag_active = False

    def leaveEvent(self, event) -> None:  # noqa: N802
        try:
            self.preview_left.emit()
        except Exception:
            pass
        super().leaveEvent(event)

    def enterEvent(self, event: QEnterEvent) -> None:  # noqa: N802
        super().enterEvent(event)
        try:
            p = self.mapFromGlobal(self.cursor().pos())
            self._emit_preview_at_x(int(p.x()), dragging=self.isSliderDown())
        except Exception:
            pass

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        try:
            if event.button() == Qt.MouseButton.LeftButton and self.orientation() == Qt.Orientation.Horizontal:
                opt = QStyleOptionSlider()
                self.initStyleOption(opt)
                handle = self.style().subControlRect(
                    QStyle.ComplexControl.CC_Slider,
                    opt,
                    QStyle.SubControl.SC_SliderHandle,
                    self,
                )

                x = int(event.position().x())
                v = self._value_from_x(x)

                # If groove click (not on handle): jump exactly to click and start drag.
                if v is not None and not handle.contains(int(event.position().x()), int(event.position().y())):
                    self._groove_drag_active = True
                    # IMPORTANT ordering: set value first, then setSliderDown.
                    # setSliderDown(True) will emit sliderPressed internally.
                    self.setSliderPosition(int(v))
                    self.setValue(int(v))
                    self.setSliderDown(True)

                    self._emit_preview_at_x(x, dragging=True)
                    event.accept()
                    return
        except Exception:
            self._groove_drag_active = False

        super().mousePressEvent(event)
        try:
            self._emit_preview_at_x(int(event.position().x()), dragging=self.isSliderDown())
        except Exception:
            pass

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._groove_drag_active and self.isSliderDown():
            try:
                x = int(event.position().x())
                v = self._value_from_x(x)
                if v is not None:
                    self.setSliderPosition(int(v))
                    self.setValue(int(v))
                    # Keep QSlider drag semantics (lets our scrub labels update).
                    try:
                        self.sliderMoved.emit(int(v))
                    except Exception:
                        pass
                self._emit_preview_at_x(x, dragging=True)
                event.accept()
                return
            except Exception:
                self._groove_drag_active = False

        super().mouseMoveEvent(event)
        try:
            self._emit_preview_at_x(int(event.position().x()), dragging=self.isSliderDown())
        except Exception:
            pass

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self._groove_drag_active:
            try:
                self.setSliderDown(False)  # emits sliderReleased internally
                self._groove_drag_active = False
                event.accept()
                return
            except Exception:
                self._groove_drag_active = False

        super().mouseReleaseEvent(event)

    def _emit_preview_at_x(self, x_local: int, *, dragging: bool) -> None:
        v = self._value_from_x(x_local)
        if v is None:
            return
        self.preview_moved.emit(int(v), int(x_local), bool(dragging))

    def _value_from_x(self, x_local: int) -> Optional[int]:
        if self.orientation() != Qt.Orientation.Horizontal:
            return None

        mn = int(self.minimum())
        mx = int(self.maximum())
        if mx <= mn:
            return mn

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        style = self.style()

        groove = style.subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self)
        handle = style.subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self)

        span = int(groove.width() - handle.width())
        if span <= 0:
            span = max(1, int(groove.width()))

        pos = int(x_local - groove.x() - (handle.width() // 2))
        pos = max(0, min(pos, span))

        v = QStyle.sliderValueFromPosition(mn, mx, pos, span, opt.upsideDown)
        return int(v)
