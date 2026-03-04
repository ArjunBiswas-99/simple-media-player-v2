from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtWidgets import QWidget, QVBoxLayout

from ui.controls import OverlayControls
from ui.scrim import BottomScrim
from ui.video_widget import VideoWidget


class VideoPane(QWidget):
    """A video area with an overlay control panel.

    This widget owns only UI composition. Playback is handled elsewhere.
    """

    user_activity = Signal()
    double_clicked = Signal()
    single_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)

        # Base video widget fills the pane.
        self.video = VideoWidget(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.video, stretch=1)

        # Floating overlay widgets (positioned in resizeEvent).
        self.scrim = BottomScrim(self)
        self.controls = OverlayControls(self)
        self.scrim.raise_()
        self.controls.raise_()

        # Ensure they are explicitly visible (some styles can create confusion
        # during early initialization).
        self.scrim.show()
        self.controls.show()

        self._overlay_height = 176
        self._overlay_offset = 18
        self._safe_bottom_inset = 10

        self._slide = QPropertyAnimation(self.controls, b"pos", self)
        self._slide.setDuration(220)
        self._slide.setEasingCurve(QEasingCurve.Type.OutCubic)

        # bubble mouse move from children
        self.video.user_activity.connect(self.user_activity)
        self.video.single_clicked.connect(self.single_clicked)
        self.video.double_clicked.connect(self.double_clicked)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_overlays()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._position_overlays()

    def _position_overlays(self) -> None:
        w = self.width()
        h = self.height()
        oh = self._overlay_height
        y = max(0, h - oh - self._safe_bottom_inset)
        # Scrim can extend slightly more to hide the bottom edge nicely.
        self.scrim.setGeometry(0, y, w, oh + self._safe_bottom_inset)
        self.controls.setGeometry(0, y, w, oh)

    def animate_show(self) -> None:
        """Slide up a bit + fade in."""
        self._position_overlays()
        self.controls.fade_in()
        self._slide.stop()

        end_pos = self.controls.pos()
        start_pos = QPoint(end_pos.x(), end_pos.y() + self._overlay_offset)
        self.controls.move(start_pos)
        self._slide.setStartValue(start_pos)
        self._slide.setEndValue(end_pos)
        self._slide.start()

    def animate_hide(self) -> None:
        """Slide down a bit + fade out."""
        self._slide.stop()
        start_pos = self.controls.pos()
        end_pos = QPoint(start_pos.x(), start_pos.y() + self._overlay_offset)
        self._slide.setStartValue(start_pos)
        self._slide.setEndValue(end_pos)
        self._slide.start()
        self.controls.fade_out()
