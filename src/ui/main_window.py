from __future__ import annotations

from pathlib import Path
from typing import Optional

import os
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QFileDialog

from playback.controller import PlaybackController
from ui.controls import ControlsState
from ui.video_pane import VideoPane


class MainWindow(QMainWindow):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ArjunMediaPlayer")
        self.setStyleSheet("QMainWindow{background:#0b0b0b;}")

        self.pane = VideoPane()
        self.video = self.pane.video
        self.controls = self.pane.controls

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.pane, stretch=1)
        self.setCentralWidget(root)

        self._build_menu_shell()

        self.controller = PlaybackController(self)
        self.controller.video_frame_ready.connect(self.video.set_frame)
        self.controller.playback_state_changed.connect(self._on_state)
        self.controller.position_changed.connect(self._on_position)
        self.controller.duration_changed.connect(self._on_duration)
        self.controller.error_occurred.connect(self._on_error)

        self.controls.play_pause_clicked.connect(self.controller.toggle_play_pause)
        # Bottom open button
        self.controls.open_clicked.connect(self._open_file)
        # Standard scrub UX: pause while dragging, seek on release, resume if needed.
        self._was_playing_before_scrub = False
        self.controls.scrub_started.connect(self._on_scrub_started)
        self.controls.scrub_finished.connect(self._on_scrub_finished)
        self.controls.volume_changed.connect(self.controller.set_volume)

        self.controls.fullscreen_btn.clicked.connect(self._toggle_fullscreen)

        # Click behaviors on video
        self.pane.single_clicked.connect(self.controller.toggle_play_pause)
        self.pane.double_clicked.connect(self._toggle_fullscreen)
        self.pane.user_activity.connect(self._on_user_activity)

        # Keyboard shortcuts
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self.controller.toggle_play_pause)
        QShortcut(QKeySequence("F"), self, activated=self._toggle_fullscreen)

        self._is_playing = False
        self._pos_ms = 0
        self._dur_ms = 0
        self._volume = 80
        self._current_filename = ""

        self._open_dialog: Optional[QFileDialog] = None

        # Auto-hide behavior in fullscreen
        self._hide_timer = QTimer(self)
        self._hide_timer.setInterval(2000)
        self._hide_timer.timeout.connect(self._on_hide_timeout)

        self._ui_timer = QTimer(self)
        self._ui_timer.setInterval(100)
        self._ui_timer.timeout.connect(self._refresh_controls)
        self._ui_timer.start()
        self._refresh_controls()

        # Controls visible by default in windowed
        self.controls.force_visible()

    def closeEvent(self, event) -> None:  # noqa: N802
        self.controller.shutdown()
        super().closeEvent(event)

    def _refresh_controls(self) -> None:
        self.controls.set_state(
            ControlsState(
                is_playing=self._is_playing,
                position_ms=self._pos_ms,
                duration_ms=self._dur_ms,
                volume=self._volume,
            )
        )

    def _open_file(self) -> None:
        # Native OS file dialog: normal theme + full navigation.
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open video",
            str(Path.home()),
            "Video Files (*.mp4);;All Files (*.*)",
        )
        if not file_path:
            return
        self._on_file_selected(file_path)

    def _on_file_selected(self, file_path: str) -> None:
        if not file_path:
            return

        self._current_filename = os.path.basename(file_path)
        self.controls.set_filename(self._current_filename)
        self._update_title()
        self.controller.open_media(file_path)

    def _update_title(self) -> None:
        if self._current_filename:
            self.setWindowTitle(f"ArjunMediaPlayer — {self._current_filename}")
        else:
            self.setWindowTitle("ArjunMediaPlayer")

    def _on_state(self, is_playing: bool) -> None:
        self._is_playing = bool(is_playing)
        self._refresh_controls()

    def _on_position(self, pos_ms: int) -> None:
        self._pos_ms = int(pos_ms)

    def _on_duration(self, dur_ms: int) -> None:
        self._dur_ms = int(dur_ms)
        self._refresh_controls()

    def _on_error(self, message: str) -> None:
        # Phase 1: keep UX minimal.
        self.setWindowTitle(f"ArjunMediaPlayer — ERROR: {message}")

    def _on_scrub_started(self, _pos_ms: int) -> None:
        self._was_playing_before_scrub = self._is_playing
        self.controller.pause()

    def _on_scrub_finished(self, pos_ms: int) -> None:
        self.controller.seek_ms(int(pos_ms))
        if self._was_playing_before_scrub:
            self.controller.play()

    def _build_menu_shell(self) -> None:
        bar = self.menuBar()

        media = bar.addMenu("Media")
        act_open = QAction("Open File...", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self._open_file)
        media.addAction(act_open)

        # Placeholders
        for text in ["Open Folder...", "Open Network Stream...", "Open Recent"]:
            act = QAction(text, self)
            act.setEnabled(False)
            media.addAction(act)

        media.addSeparator()
        act_exit = QAction("Exit", self)
        act_exit.setShortcut(QKeySequence.Quit)
        act_exit.triggered.connect(self.close)
        media.addAction(act_exit)

        # Other menus are placeholders for later phases.
        def add_placeholder_menu(name: str, items: list[str]) -> None:
            menu = bar.addMenu(name)
            for text in items:
                act = QAction(text, self)
                act.setEnabled(False)
                menu.addAction(act)

        add_placeholder_menu(
            "Playback",
            [
                "Play/Pause",
                "Stop",
                "Next",
                "Previous",
                "Jump Forward",
                "Jump Backward",
                "Speed",
            ],
        )
        add_placeholder_menu("Audio", ["Track", "Mute", "Volume", "Delay"])
        add_placeholder_menu("Video", ["Track", "Aspect Ratio", "Crop", "Rotate", "Filters"])
        add_placeholder_menu("Subtitle", ["Track", "Load External...", "Delay"])
        add_placeholder_menu("Tools", ["Media Info", "Diagnostics"])
        add_placeholder_menu("View", ["Fullscreen", "Always on Top"])
        add_placeholder_menu("Help", ["About", "Shortcuts"])

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().setVisible(True)
            self.controls.force_visible()
            self._hide_timer.stop()
        else:
            self.showFullScreen()
            self.menuBar().setVisible(False)
            self.pane.animate_show()
            self._hide_timer.start()

    def _on_hide_timeout(self) -> None:
        if self.isFullScreen():
            self.pane.animate_hide()

    def resizeEvent(self, event) -> None:  # noqa: N802
        # Ensure overlay is always visible in windowed mode.
        if not self.isFullScreen():
            self.controls.force_visible()
        super().resizeEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self.isFullScreen():
            self._on_user_activity()
        super().mouseMoveEvent(event)

    def _on_user_activity(self) -> None:
        if self.isFullScreen():
            self.pane.animate_show()
            self._hide_timer.start()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self._toggle_fullscreen()
        super().mouseDoubleClickEvent(event)
