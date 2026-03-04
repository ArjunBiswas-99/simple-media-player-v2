from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QPoint, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect, QFrame, QProgressBar

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

        # YouTube-like skip HUD at top center.
        self.skip_hud = QLabel("", self)
        self.skip_hud.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.skip_hud.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.skip_hud.setStyleSheet(
            """
            QLabel {
                color: #ffffff;
                background: rgba(8, 8, 10, 176);
                border: 1px solid rgba(255,255,255,32);
                border-radius: 18px;
                padding: 8px 18px;
                font-size: 18px;
                font-weight: 700;
            }
            """
        )
        self.skip_hud.hide()

        self._hud_opacity = QGraphicsOpacityEffect(self.skip_hud)
        self._hud_opacity.setOpacity(0.0)
        self.skip_hud.setGraphicsEffect(self._hud_opacity)

        self._hud_fade = QPropertyAnimation(self._hud_opacity, b"opacity", self)
        self._hud_fade.setDuration(380)
        self._hud_fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._hud_slide = QPropertyAnimation(self.skip_hud, b"pos", self)
        self._hud_slide.setDuration(210)
        self._hud_slide.setEasingCurve(QEasingCurve.Type.OutCubic)

        # VLC-like volume OSD at right-center.
        self.volume_hud = QFrame(self)
        self.volume_hud.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.volume_hud.setStyleSheet(
            """
            QFrame {
                background: rgba(8, 8, 10, 178);
                border: 1px solid rgba(255,255,255,28);
                border-radius: 14px;
            }
            QLabel#volIcon {
                color: #ffffff;
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#volText {
                color: #ffffff;
                font-size: 12px;
                font-weight: 700;
            }
            QProgressBar {
                border: 1px solid rgba(255,255,255,28);
                border-radius: 5px;
                background: rgba(255,255,255,26);
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:1, x2:0, y2:0,
                    stop:0 #c90a12,
                    stop:1 #ff1f2d
                );
                border-radius: 4px;
            }
            """
        )
        vh_layout = QVBoxLayout(self.volume_hud)
        vh_layout.setContentsMargins(10, 10, 10, 10)
        vh_layout.setSpacing(8)

        self._vol_icon = QLabel("🔊", self.volume_hud)
        self._vol_icon.setObjectName("volIcon")
        self._vol_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._vol_text = QLabel("80%", self.volume_hud)
        self._vol_text.setObjectName("volText")
        self._vol_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._vol_bar = QProgressBar(self.volume_hud)
        self._vol_bar.setOrientation(Qt.Orientation.Vertical)
        self._vol_bar.setRange(0, 100)
        self._vol_bar.setValue(80)
        self._vol_bar.setTextVisible(False)
        self._vol_bar.setFixedSize(14, 86)

        vh_layout.addWidget(self._vol_icon, alignment=Qt.AlignmentFlag.AlignHCenter)
        vh_layout.addWidget(self._vol_bar, alignment=Qt.AlignmentFlag.AlignHCenter)
        vh_layout.addWidget(self._vol_text, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.volume_hud.setFixedWidth(62)
        self.volume_hud.hide()

        self._vol_opacity = QGraphicsOpacityEffect(self.volume_hud)
        self._vol_opacity.setOpacity(0.0)
        self.volume_hud.setGraphicsEffect(self._vol_opacity)

        self._vol_fade = QPropertyAnimation(self._vol_opacity, b"opacity", self)
        self._vol_fade.setDuration(560)
        self._vol_fade.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._vol_hold_timer = QTimer(self)
        self._vol_hold_timer.setSingleShot(True)
        self._vol_hold_timer.setInterval(780)
        self._vol_hold_timer.timeout.connect(self._start_volume_fade)

        self._vol_slide = QPropertyAnimation(self.volume_hud, b"pos", self)
        self._vol_slide.setDuration(180)
        self._vol_slide.setEasingCurve(QEasingCurve.Type.OutCubic)

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

        # Keep HUD centered near the top.
        if self.skip_hud.isVisible():
            self._position_skip_hud()
        if self.volume_hud.isVisible():
            self._position_volume_hud()

    def _position_skip_hud(self) -> None:
        self.skip_hud.adjustSize()
        x = (self.width() - self.skip_hud.width()) // 2
        y = 38
        self.skip_hud.move(max(0, x), max(0, y))

    def show_skip_feedback(self, direction: int, seconds: int) -> None:
        if direction >= 0:
            text = f"+{seconds} >>"
        else:
            text = f"<< -{seconds}"

        self.skip_hud.setText(text)
        self._position_skip_hud()
        self.skip_hud.show()
        self.skip_hud.raise_()

        end_pos = self.skip_hud.pos()
        start_pos = QPoint(end_pos.x(), end_pos.y() + 10)

        self._hud_slide.stop()
        self._hud_slide.setStartValue(start_pos)
        self._hud_slide.setEndValue(end_pos)
        self._hud_slide.start()

        self._hud_fade.stop()
        self._hud_opacity.setOpacity(1.0)
        self._hud_fade.setStartValue(1.0)
        self._hud_fade.setEndValue(0.0)
        self._hud_fade.start()

    def _position_volume_hud(self) -> None:
        x = max(0, self.width() - self.volume_hud.width() - 24)
        y = max(0, (self.height() - self.volume_hud.height()) // 2)
        self.volume_hud.move(x, y)

    def show_volume_feedback(self, volume: int) -> None:
        v = max(0, min(100, int(volume)))
        if v <= 0:
            icon = "🔇"
        elif v < 40:
            icon = "🔉"
        else:
            icon = "🔊"

        self._vol_icon.setText(icon)
        self._vol_text.setText(f"{v}%")
        self._vol_bar.setValue(v)
        self.volume_hud.adjustSize()
        self._position_volume_hud()
        self.volume_hud.show()
        self.volume_hud.raise_()

        end_pos = self.volume_hud.pos()
        start_pos = QPoint(end_pos.x() + 10, end_pos.y())

        self._vol_slide.stop()
        self._vol_slide.setStartValue(start_pos)
        self._vol_slide.setEndValue(end_pos)
        self._vol_slide.start()

        self._vol_hold_timer.stop()
        self._vol_fade.stop()
        self._vol_opacity.setOpacity(1.0)
        self._vol_hold_timer.start()

    def _start_volume_fade(self) -> None:
        self._vol_fade.stop()
        self._vol_fade.setStartValue(self._vol_opacity.opacity())
        self._vol_fade.setEndValue(0.0)
        self._vol_fade.start()

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
