from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout


def _format_ms(ms: int) -> str:
    if ms <= 0:
        return "00:00"
    s = ms // 1000
    m = s // 60
    h = m // 60
    s %= 60
    m %= 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


class ThumbnailPopup(QWidget):
    """Lightweight thumbnail preview popup (YouTube-like)."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.setStyleSheet(
            """
            ThumbnailPopup {
                background: rgba(10, 10, 12, 222);
                border: 1px solid rgba(255,255,255,38);
                border-radius: 10px;
            }
            QLabel#thumbImg {
                background: transparent;
                border: none;
            }
            QLabel#thumbTime {
                color: rgba(255,255,255,235);
                font-size: 12px;
                font-weight: 700;
                padding: 3px 6px 7px 6px;
            }
            """
        )

        self._img = QLabel(self)
        self._img.setObjectName("thumbImg")
        self._img.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._time = QLabel("00:00", self)
        self._time.setObjectName("thumbTime")
        self._time.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 0)
        layout.setSpacing(2)
        layout.addWidget(self._img)
        layout.addWidget(self._time)

        self._thumb_w = 160
        self._thumb_h = 90
        self._last_img: Optional[QImage] = None

        self.hide()

    def set_thumbnail_size(self, w: int, h: int) -> None:
        self._thumb_w = int(max(60, w))
        self._thumb_h = int(max(40, h))

    def set_preview(self, image: Optional[QImage], time_ms: int) -> None:
        self._time.setText(_format_ms(int(time_ms)))
        if image is None or image.isNull():
            # Placeholder: dark rect.
            self._img.setFixedSize(self._thumb_w, self._thumb_h)
            self._img.setPixmap(QPixmap())
            self._img.setStyleSheet(
                "background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,14); border-radius: 6px;"
            )
            self._last_img = None
        else:
            self._img.setStyleSheet("background: transparent; border: none;")
            self._img.setFixedSize(self._thumb_w, self._thumb_h)
            scaled = image.scaled(self._thumb_w, self._thumb_h, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self._img.setPixmap(QPixmap.fromImage(scaled))
            self._last_img = image

        self.adjustSize()

    def show_at(self, global_x: int, global_y: int, *, clamp_rect=None) -> None:
        # Position popup so that its center aligns with global_x, above global_y.
        self.adjustSize()
        x = int(global_x - (self.width() // 2))
        y = int(global_y - self.height() - 10)

        if clamp_rect is not None:
            try:
                left = int(clamp_rect.left())
                right = int(clamp_rect.right())
                x = max(left, min(x, right - self.width()))
            except Exception:
                pass

        self.move(QPoint(x, y))
        if not self.isVisible():
            self.show()
