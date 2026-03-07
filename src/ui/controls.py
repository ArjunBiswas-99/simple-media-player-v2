from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QSize
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSlider,
    QLabel,
    QSizePolicy,
    QToolButton,
    QGraphicsOpacityEffect,
)

from ui.icons import ICONS, IconSpec
from ui.animated_button import AnimatedToolButton


@dataclass
class ControlsState:
    is_playing: bool
    position_ms: int
    duration_ms: int
    volume: int


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


class OverlayControls(QWidget):
    play_pause_clicked = Signal()
    rewind_clicked = Signal()
    fast_forward_clicked = Signal()
    open_clicked = Signal()
    seek_requested = Signal(int)  # position_ms
    scrub_started = Signal(int)  # position_ms
    scrub_finished = Signal(int)  # position_ms
    volume_changed = Signal(int)  # 0-100

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            """
            OverlayControls {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(24, 27, 34, 228),
                    stop:0.45 rgba(16, 19, 25, 236),
                    stop:1 rgba(9, 11, 15, 245)
                );
                border-top: 1px solid rgba(255,255,255,34);
                border-left: 1px solid rgba(255,255,255,16);
                border-right: 1px solid rgba(255,255,255,16);
                border-top-left-radius: 18px;
                border-top-right-radius: 18px;
            }
            QLabel { color: #f4f4f4; font-size: 13px; }
            QLabel#timeChip {
                color: #ffffff;
                background: rgba(255,255,255,4);
                border: 1px solid rgba(255,255,255,12);
                border-radius: 8px;
                font-size: 15px;
                font-weight: 600;
                font-family: 'Inter', 'Segoe UI';
                padding: 1px 6px;
            }
            QLabel#fileLabel {
                color: rgba(255,255,255,186);
                padding-left: 8px;
                font-size: 14px;
                font-family: 'Inter', 'Segoe UI';
            }
            QLabel#volLabel {
                color: rgba(255,255,255,182);
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 0.8px;
                font-family: 'Inter', 'Segoe UI';
            }
            QToolButton {
                background: rgba(255,255,255,9);
                border: 1px solid rgba(255,255,255,24);
                border-radius: 12px;
                padding: 6px;
                color: #f2f2f2;
            }
            QToolButton:hover {
                background: rgba(229, 9, 20, 48);
                border: 1px solid rgba(229, 9, 20, 170);
            }
            QToolButton:pressed {
                background: rgba(229, 9, 20, 78);
                border: 1px solid rgba(229, 9, 20, 200);
            }

            QSlider::groove:horizontal {
                height: 7px;
                border-radius: 4px;
                background: rgba(255,255,255,30);
                border: 1px solid rgba(255,255,255,16);
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #b80812,
                    stop:1 #ff2735
                );
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qradialgradient(
                    cx:0.45, cy:0.35, radius:0.9,
                    fx:0.35, fy:0.3,
                    stop:0 #ffffff,
                    stop:1 #f0f0f0
                );
                border: 2px solid #e50914;
                width: 16px;
                height: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            """
        )
        # NOTE: Avoid widget-level drop shadow here because it gets clipped
        # by the pane/window edges. The cinematic scrim + translucent surface
        # provides the depth.

        # Row 1: timeline + timer
        self.timeline = QSlider(Qt.Orientation.Horizontal)
        self.timeline.setRange(0, 0)
        self.timeline.setSingleStep(1000)
        self.timeline.setPageStep(5000)
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("timeChip")
        # Keep this compact; the text itself will size it.
        self.time_label.setMinimumWidth(0)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        row1 = QHBoxLayout()
        row1.setContentsMargins(18, 8, 18, 2)
        row1.setSpacing(10)
        row1.addWidget(self.timeline, stretch=1)
        row1.addWidget(self.time_label)

        # Row 2: icons
        self.play_btn = AnimatedToolButton()
        self.play_btn.setIcon(ICONS.icon(IconSpec("fa5s.play")))
        self.play_btn.setToolTip("Play/Pause (Space)")
        self.play_btn.setIconSize(QSize(18, 18))

        self.rewind_btn = AnimatedToolButton()
        self.rewind_btn.setIcon(ICONS.icon(IconSpec("fa5s.backward")))
        self.rewind_btn.setToolTip("Rewind")
        self.rewind_btn.setIconSize(QSize(18, 18))

        self.ff_btn = AnimatedToolButton()
        self.ff_btn.setIcon(ICONS.icon(IconSpec("fa5s.forward")))
        self.ff_btn.setToolTip("Fast forward")
        self.ff_btn.setIconSize(QSize(18, 18))

        self.open_btn = AnimatedToolButton()
        self.open_btn.setIcon(ICONS.icon(IconSpec("fa5s.folder-open")))
        self.open_btn.setToolTip("Open file")
        self.open_btn.setIconSize(QSize(18, 18))

        self.volume = QSlider(Qt.Orientation.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(80)
        self.volume.setFixedWidth(132)
        self.volume.setFixedHeight(22)

        self.file_label = QLabel("")
        self.file_label.setObjectName("fileLabel")
        self.file_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.file_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        self.info_btn = AnimatedToolButton()
        self.info_btn.setIcon(ICONS.icon(IconSpec("fa5s.info-circle")))
        self.info_btn.setToolTip("Info")
        self.info_btn.setIconSize(QSize(18, 18))

        self.next_btn = AnimatedToolButton()
        self.next_btn.setIcon(ICONS.icon(IconSpec("fa5s.step-forward")))
        self.next_btn.setToolTip("Next")
        self.next_btn.setIconSize(QSize(18, 18))

        self.folder_btn = AnimatedToolButton()
        self.folder_btn.setIcon(ICONS.icon(IconSpec("fa5s.folder")))
        self.folder_btn.setToolTip("Folder")
        self.folder_btn.setIconSize(QSize(18, 18))

        self.fullscreen_btn = AnimatedToolButton()
        self.fullscreen_btn.setIcon(ICONS.icon(IconSpec("fa5s.expand")))
        self.fullscreen_btn.setToolTip("Fullscreen")
        self.fullscreen_btn.setIconSize(QSize(18, 18))

        # Keep icon buttons at a consistent hit-target size.
        for btn in (
            self.play_btn,
            self.rewind_btn,
            self.ff_btn,
            self.open_btn,
            self.info_btn,
            self.next_btn,
            self.folder_btn,
            self.fullscreen_btn,
        ):
            btn.setFixedSize(42, 42)
            btn.setBaseIconSize(QSize(20, 20))
            btn.setHoverIconSize(QSize(23, 23))
            btn.setPressIconSize(QSize(18, 18))
            btn.setPopIconSize(QSize(25, 25))

        row2 = QHBoxLayout()
        row2.setContentsMargins(18, 2, 18, 12)
        row2.setSpacing(8)
        row2.addWidget(self.play_btn)
        row2.addWidget(self.rewind_btn)
        row2.addWidget(self.ff_btn)
        row2.addSpacing(4)
        vol_lbl = QLabel("VOL")
        vol_lbl.setObjectName("volLabel")
        row2.addWidget(vol_lbl)
        row2.addWidget(self.volume)
        row2.addSpacing(8)
        row2.addWidget(self.file_label, stretch=1)
        row2.addWidget(self.info_btn)
        row2.addWidget(self.next_btn)
        row2.addWidget(self.folder_btn)
        row2.addWidget(self.fullscreen_btn)
        row2.addWidget(self.open_btn)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(1)
        content_layout.addLayout(row1)
        content_layout.addLayout(row2)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._scrubbing = False

        self.play_btn.clicked.connect(self.play_pause_clicked.emit)
        self.rewind_btn.clicked.connect(self.rewind_clicked.emit)
        self.ff_btn.clicked.connect(self.fast_forward_clicked.emit)
        self.open_btn.clicked.connect(self.open_clicked.emit)
        self.timeline.sliderPressed.connect(self._on_scrub_start)
        self.timeline.sliderReleased.connect(self._on_scrub_end)
        self.timeline.sliderMoved.connect(self._on_scrub_move)
        self.volume.valueChanged.connect(self.volume_changed.emit)

        # Fade animation support (works for child widgets via opacity effect)
        # Chain effects: apply opacity to a child container instead of self.
        # (Qt only allows one graphics effect per widget.)
        self._container = QWidget(self)
        self._container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self._container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._container.setStyleSheet("background: transparent;")

        self._container.setLayout(content_layout)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._container)

        self._opacity = QGraphicsOpacityEffect(self._container)
        self._opacity.setOpacity(1.0)
        self._container.setGraphicsEffect(self._opacity)

        self._fade = QPropertyAnimation(self._opacity, b"opacity")
        self._fade.setDuration(200)

    def set_state(self, state: ControlsState) -> None:
        if state.is_playing:
            self.play_btn.setIcon(ICONS.icon(IconSpec("fa5s.pause")))
        else:
            self.play_btn.setIcon(ICONS.icon(IconSpec("fa5s.play")))
        self.timeline.setRange(0, max(0, state.duration_ms))

        if not self._scrubbing:
            self.timeline.setValue(max(0, min(state.position_ms, state.duration_ms)))

        self.time_label.setText(f"{_format_ms(state.position_ms)} / {_format_ms(state.duration_ms)}")

        if self.volume.value() != state.volume:
            self.volume.blockSignals(True)
            self.volume.setValue(state.volume)
            self.volume.blockSignals(False)

    def set_filename(self, name: str) -> None:
        self.file_label.setText(name)

    def fade_in(self) -> None:
        self._fade.stop()
        self._fade.setStartValue(self._opacity.opacity())
        self._fade.setEndValue(1.0)
        self._fade.start()

    def force_visible(self) -> None:
        """Immediate visibility (used in windowed mode)."""
        self._fade.stop()
        self._opacity.setOpacity(1.0)

    def fade_out(self) -> None:
        self._fade.stop()
        self._fade.setStartValue(self._opacity.opacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _on_scrub_start(self) -> None:
        self._scrubbing = True
        self.scrub_started.emit(int(self.timeline.value()))

    def _on_scrub_move(self, value: int) -> None:
        total = self.timeline.maximum()
        self.time_label.setText(f"{_format_ms(value)} / {_format_ms(total)}")

    def _on_scrub_end(self) -> None:
        self._scrubbing = False
        pos = int(self.timeline.value())
        self.scrub_finished.emit(pos)
        # Back-compat signal (older wiring). New wiring should use scrub_finished.
        self.seek_requested.emit(pos)
