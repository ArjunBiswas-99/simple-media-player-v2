from __future__ import annotations

from pathlib import Path
from typing import Optional
import time

import os
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtGui import QIcon
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QFileDialog, QMenu

from playback.controller import PlaybackController
from ui.controls import ControlsState
from ui.icons import ICONS, IconSpec
from ui.video_pane import VideoPane


class MainWindow(QMainWindow):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("ArjunMediaPlayer")
        self.setStyleSheet("QMainWindow{background:#0b0b0b;}")

        # Window icon (title bar / Alt-Tab)
        try:
            icon_path = Path(__file__).resolve().parent / "Assets" / "Icon.png"
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass

        self.pane = VideoPane()
        self.video = self.pane.video
        self.controls = self.pane.controls

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.pane, stretch=1)
        self.setCentralWidget(root)

        self._act_fullscreen: Optional[QAction] = None
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
        self.controls.volume_changed.connect(self._on_volume_slider_changed)
        self.controls.rewind_clicked.connect(self._skip_backward)
        self.controls.fast_forward_clicked.connect(self._skip_forward)

        self.controls.fullscreen_btn.clicked.connect(self._toggle_fullscreen_with_feedback)

        # Click behaviors on video
        self.pane.single_clicked.connect(self._on_video_toggle_play_pause)
        self.pane.double_clicked.connect(self._on_video_toggle_fullscreen)
        self.pane.hold_fast_forward_started.connect(self._on_video_hold_fast_forward_start)
        self.pane.hold_fast_forward_ended.connect(self._on_video_hold_fast_forward_end)
        self.pane.context_menu_requested.connect(self._on_video_context_menu)
        self.pane.user_activity.connect(self._on_user_activity)

        # Keyboard shortcuts
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, activated=self._on_shortcut_toggle_play_pause)
        QShortcut(QKeySequence("F"), self, activated=self._on_shortcut_toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, activated=self._skip_backward)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, activated=self._skip_forward)
        QShortcut(QKeySequence(Qt.Key.Key_Up), self, activated=self._volume_up)
        QShortcut(QKeySequence(Qt.Key.Key_Down), self, activated=self._volume_down)

        self._is_playing = False
        self._playback_rate = 1.0
        self._pos_ms = 0
        self._dur_ms = 0
        self._volume = 80
        self._current_filename = ""

        # Audio menu state.
        self._audio_tracks = []
        self._audio_track_index = 0
        self._mute_restore_volume = 80

        # Skip accumulator state (YouTube-like quick repeated taps).
        self._skip_step_ms = 5000
        self._skip_accum_window_s = 0.38
        self._skip_last_dir = 0
        self._skip_last_ts = 0.0
        self._skip_steps = 0

        # Track list updates for Audio menu.
        self.controller.audio_tracks_changed.connect(self._on_audio_tracks)



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

    def _on_audio_tracks(self, tracks) -> None:
        # tracks: list[AudioTrackInfo]
        try:
            self._audio_tracks = list(tracks) if tracks is not None else []
        except Exception:
            self._audio_tracks = []
        if self._audio_track_index >= len(self._audio_tracks):
            self._audio_track_index = 0

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

    def _skip_backward(self) -> None:
        self._perform_skip(-1)

    def _skip_forward(self) -> None:
        self._perform_skip(+1)

    def _perform_skip(self, direction: int) -> None:
        now = time.monotonic()
        if direction == self._skip_last_dir and (now - self._skip_last_ts) <= self._skip_accum_window_s:
            self._skip_steps += 1
        else:
            self._skip_steps = 1
        self._skip_last_dir = direction
        self._skip_last_ts = now

        total_delta_ms = self._skip_steps * self._skip_step_ms * direction
        target = self._pos_ms + total_delta_ms
        if self._dur_ms > 0:
            target = max(0, min(target, self._dur_ms))
        else:
            target = max(0, target)

        self.controller.seek_ms(int(target))
        self.pane.show_skip_feedback(direction, self._skip_steps * (self._skip_step_ms // 1000))

    def _toggle_play_pause_with_feedback(self) -> None:
        # Determine what the *next* state will be.
        next_playing = not self._is_playing
        self.controller.toggle_play_pause()

        # YouTube-like center HUD.
        self.pane.show_play_pause_feedback(next_playing)

        # Keep bottom bar feeling responsive even when triggered from keyboard/video.
        try:
            self.controls.play_btn.pulse()
        except Exception:
            pass

    def _on_video_toggle_play_pause(self) -> None:
        self._toggle_play_pause_with_feedback()

    def _on_shortcut_toggle_play_pause(self) -> None:
        self._toggle_play_pause_with_feedback()

    def _on_video_hold_fast_forward_start(self) -> None:
        # Switch to true 2x mode (rate-aware clock + audio tempo).
        self._playback_rate = 2.0
        self.controller.set_playback_rate(self._playback_rate)
        self.pane.show_speed_feedback("2×")

    def _on_video_hold_fast_forward_end(self) -> None:
        self._playback_rate = 1.0
        self.controller.set_playback_rate(self._playback_rate)
        self.pane.hide_speed_feedback()

    def _stop_with_feedback(self) -> None:
        """Stop = pause + seek to start (VLC-like)."""
        self.controller.pause()
        self.controller.seek_ms(0)
        # If you want we can show a HUD later; for now keep it consistent.

    def _set_speed_with_feedback(self, rate: float) -> None:
        r = float(rate)
        self._playback_rate = r
        self.controller.set_playback_rate(r)
        # Brief HUD feedback like YouTube.
        if abs(r - 1.0) < 1e-3:
            self.pane.hide_speed_feedback()
        else:
            # Use × glyph for polish.
            label = f"{r:g}×"
            self.pane.show_speed_feedback(label)

        # Keep menu checkmarks in sync if menu is open.
        try:
            self._sync_speed_checks()
        except Exception:
            pass

    def _sync_speed_checks(self) -> None:
        if not hasattr(self, "_speed_actions"):
            return
        acts = getattr(self, "_speed_actions")
        for rate, act in acts.items():
            try:
                act.setChecked(abs(float(rate) - float(self._playback_rate)) < 1e-3)
            except Exception:
                pass

    def _toggle_mute(self) -> None:
        if self._volume > 0:
            self._mute_restore_volume = int(self._volume)
            self._apply_volume(0, show_hud=True)
        else:
            self._apply_volume(max(5, int(self._mute_restore_volume or 80)), show_hud=True)

    def _audio_volume_up(self) -> None:
        self._change_volume_by(+5)

    def _audio_volume_down(self) -> None:
        self._change_volume_by(-5)

    def _select_audio_track(self, index: int) -> None:
        self._audio_track_index = int(max(0, index))
        self.controller.select_audio_track(self._audio_track_index)

    def _select_audio_device_by_index(self, idx: int) -> None:
        devs = self.controller.available_audio_output_devices()
        if not devs:
            return
        i = int(idx)
        if i < 0 or i >= len(devs):
            i = 0
        self.controller.set_audio_output_device(devs[i])

    def _select_stereo_mode(self, mode: str) -> None:
        self.controller.set_stereo_mode(mode)

    @staticmethod
    def _audio_device_id(dev) -> str:
        try:
            return str(dev.id())
        except Exception:
            try:
                return str(dev.description())
            except Exception:
                return ""

    def _populate_audio_tracks_menu(self, menu: QMenu) -> None:
        menu.clear()
        tracks = self._audio_tracks or []
        if not tracks:
            a = QAction("No audio tracks", self)
            a.setEnabled(False)
            menu.addAction(a)
            return

        group = QActionGroup(self)
        group.setExclusive(True)

        for t in tracks:
            try:
                idx = int(getattr(t, "index", 0))
                label = str(getattr(t, "label", f"Track {idx+1}"))
            except Exception:
                idx = 0
                label = "Track"
            a = QAction(label, self)
            a.setCheckable(True)
            a.setChecked(int(idx) == int(self._audio_track_index))
            group.addAction(a)
            a.triggered.connect(lambda _checked=False, i=idx: self._select_audio_track(i))
            menu.addAction(a)

    def _populate_audio_devices_menu(self, menu: QMenu) -> None:
        menu.clear()

        devs = self.controller.available_audio_output_devices() or []
        default_dev = self.controller.default_audio_output_device()
        current_dev = self.controller.current_audio_output_device()

        group = QActionGroup(self)
        group.setExclusive(True)

        act_default = QAction("System Default", self)
        act_default.setCheckable(True)
        is_default = current_dev is None or (
            default_dev is not None and self._audio_device_id(current_dev) == self._audio_device_id(default_dev)
        )
        act_default.setChecked(bool(is_default))
        group.addAction(act_default)
        act_default.triggered.connect(lambda: self.controller.set_audio_output_device(None))
        menu.addAction(act_default)
        menu.addSeparator()

        if not devs:
            a = QAction("No audio devices found", self)
            a.setEnabled(False)
            menu.addAction(a)
            return

        for i, d in enumerate(devs):
            try:
                name = str(d.description())
            except Exception:
                name = f"Device {i+1}"

            a = QAction(name, self)
            a.setCheckable(True)
            try:
                a.setChecked(current_dev is not None and self._audio_device_id(current_dev) == self._audio_device_id(d))
            except Exception:
                a.setChecked(False)
            group.addAction(a)
            a.triggered.connect(lambda _checked=False, idx=i: self._select_audio_device_by_index(idx))
            menu.addAction(a)

    def _populate_stereo_mode_menu(self, menu: QMenu) -> None:
        menu.clear()
        current = str(self.controller.stereo_mode() or "stereo").lower()

        group = QActionGroup(self)
        group.setExclusive(True)

        options = [
            ("Stereo", "stereo"),
            ("Mono", "mono"),
            ("Left", "left"),
            ("Right", "right"),
        ]
        for label, mode in options:
            a = QAction(label, self)
            a.setCheckable(True)
            a.setChecked(current == mode)
            group.addAction(a)
            a.triggered.connect(lambda _checked=False, m=mode: self._select_stereo_mode(m))
            menu.addAction(a)

    def _on_video_context_menu(self, global_pos) -> None:
        menu = QMenu(self)

        # Make this particular menu translucent (YouTube-like).
        # Using RGBA is more reliable than setWindowOpacity across platforms.
        menu.setStyleSheet(
            """
            QMenu {
                background: rgba(10, 10, 12, 200);
                color: #ffffff;
                border: 1px solid rgba(255,255,255,38);
                border-radius: 12px;
                padding: 8px;
            }
            QMenu::item {
                padding: 9px 34px 9px 30px;
                border-radius: 10px;
                margin: 3px 4px;
                border-left: 3px solid transparent;
            }
            QMenu::item:selected {
                background: rgba(229, 9, 20, 46);
                border-left: 3px solid rgba(229, 9, 20, 255);
            }
            QMenu::separator {
                height: 1px;
                margin: 8px 14px;
                background: rgba(255,255,255,20);
            }
            """
        )

        # Prevent the click that dismisses the menu from being replayed into the
        # underlying VideoWidget (which would toggle play/pause).
        try:
            menu.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay, True)
        except Exception:
            pass

        # Dynamic Play/Pause label.
        act_play_pause = QAction("Pause" if self._is_playing else "Play", self)
        act_play_pause.setIcon(ICONS.icon(IconSpec("fa5s.pause" if self._is_playing else "fa5s.play")))
        act_play_pause.setShortcut(QKeySequence(Qt.Key.Key_Space))
        act_play_pause.triggered.connect(self._toggle_play_pause_with_feedback)
        menu.addAction(act_play_pause)

        act_stop = QAction("Stop", self)
        act_stop.setIcon(ICONS.icon(IconSpec("fa5s.stop")))
        act_stop.triggered.connect(self._stop_with_feedback)
        menu.addAction(act_stop)

        menu.addSeparator()

        # For Phase 1 we don't have a playlist yet.
        # Map Previous/Next to consistent skip steps.
        act_prev = QAction("Previous", self)
        act_prev.setIcon(ICONS.icon(IconSpec("fa5s.step-backward")))
        act_prev.setShortcut(QKeySequence(Qt.Key.Key_Left))
        act_prev.triggered.connect(self._skip_backward)
        menu.addAction(act_prev)

        act_next = QAction("Next", self)
        act_next.setIcon(ICONS.icon(IconSpec("fa5s.step-forward")))
        act_next.setShortcut(QKeySequence(Qt.Key.Key_Right))
        act_next.triggered.connect(self._skip_forward)
        menu.addAction(act_next)

        menu.addSeparator()

        act_fs = QAction("Exit Fullscreen" if self.isFullScreen() else "Fullscreen", self)
        act_fs.setIcon(ICONS.icon(IconSpec("fa5s.compress" if self.isFullScreen() else "fa5s.expand")))
        act_fs.setShortcut(QKeySequence("F"))
        act_fs.triggered.connect(self._toggle_fullscreen_with_feedback)
        menu.addAction(act_fs)

        act_open = QAction("Open File...", self)
        act_open.setIcon(ICONS.icon(IconSpec("fa5s.folder-open")))
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self._open_file)
        menu.addAction(act_open)

        menu.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.setIcon(ICONS.icon(IconSpec("fa5s.times-circle")))
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)
        menu.addAction(act_quit)

        try:
            menu.exec(global_pos)
        except Exception:
            # Some Qt builds may want QPoint explicitly.
            menu.exec(menu.mapToGlobal(self.mapFromGlobal(global_pos)))

    def _toggle_fullscreen_with_feedback(self) -> None:
        entering = not self.isFullScreen()
        self._toggle_fullscreen()
        self.pane.show_fullscreen_feedback(entering)
        try:
            self.controls.fullscreen_btn.pulse()
        except Exception:
            pass

    def _on_video_toggle_fullscreen(self) -> None:
        self._toggle_fullscreen_with_feedback()

    def _on_shortcut_toggle_fullscreen(self) -> None:
        self._toggle_fullscreen_with_feedback()

    def _on_volume_slider_changed(self, vol: int) -> None:
        self._apply_volume(int(vol), show_hud=True)

    def _volume_up(self) -> None:
        self._change_volume_by(+5)

    def _volume_down(self) -> None:
        self._change_volume_by(-5)

    def _change_volume_by(self, delta: int) -> None:
        self._apply_volume(self._volume + int(delta), show_hud=True)

    def _apply_volume(self, vol: int, *, show_hud: bool) -> None:
        v = max(0, min(100, int(vol)))
        self._volume = v
        self.controller.set_volume(v)

        # Keep slider in sync when volume changed from keyboard.
        if self.controls.volume.value() != v:
            self.controls.volume.blockSignals(True)
            self.controls.volume.setValue(v)
            self.controls.volume.blockSignals(False)

        if show_hud:
            self.pane.show_volume_feedback(v)

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

        # Playback menu (real actions).
        playback = bar.addMenu("Playback")

        act_play_pause = QAction("Play/Pause", self)
        act_play_pause.setShortcut(QKeySequence(Qt.Key.Key_Space))
        act_play_pause.triggered.connect(self._toggle_play_pause_with_feedback)
        playback.addAction(act_play_pause)

        act_stop = QAction("Stop", self)
        act_stop.triggered.connect(self._stop_with_feedback)
        playback.addAction(act_stop)

        playback.addSeparator()

        # Phase 1: no playlist yet, so Previous/Next map to skip back/forward.
        act_prev = QAction("Previous", self)
        act_prev.setShortcut(QKeySequence(Qt.Key.Key_Left))
        act_prev.triggered.connect(self._skip_backward)
        playback.addAction(act_prev)

        act_next = QAction("Next", self)
        act_next.setShortcut(QKeySequence(Qt.Key.Key_Right))
        act_next.triggered.connect(self._skip_forward)
        playback.addAction(act_next)

        playback.addSeparator()

        act_jump_back = QAction("Jump Backward", self)
        act_jump_back.triggered.connect(self._skip_backward)
        playback.addAction(act_jump_back)

        act_jump_fwd = QAction("Jump Forward", self)
        act_jump_fwd.triggered.connect(self._skip_forward)
        playback.addAction(act_jump_fwd)

        # Speed submenu.
        speed = playback.addMenu("Speed")
        speed.aboutToShow.connect(self._sync_speed_checks)
        speed_group = QActionGroup(self)
        speed_group.setExclusive(True)
        self._speed_actions = {}
        for rate in (0.5, 1.0, 1.5, 2.0):
            a = QAction(f"{rate:g}×", self)
            a.setCheckable(True)
            speed_group.addAction(a)
            self._speed_actions[float(rate)] = a
            a.triggered.connect(lambda _checked=False, r=rate: self._set_speed_with_feedback(r))
            speed.addAction(a)

        # Audio menu (dynamic submenus).
        audio = bar.addMenu("Audio")

        audio_track_menu = audio.addMenu("Audio Track")
        audio_track_menu.aboutToShow.connect(lambda: self._populate_audio_tracks_menu(audio_track_menu))

        audio_device_menu = audio.addMenu("Audio Device")
        audio_device_menu.aboutToShow.connect(lambda: self._populate_audio_devices_menu(audio_device_menu))

        stereo_menu = audio.addMenu("Stereo Mode")
        stereo_menu.aboutToShow.connect(lambda: self._populate_stereo_mode_menu(stereo_menu))

        viz_menu = audio.addMenu("Visualizations")
        for text in ("Off", "Spectrum", "Waveform"):
            a = QAction(text, self)
            a.setEnabled(False)
            viz_menu.addAction(a)

        audio.addSeparator()
        act_vol_up = QAction("Increase Volume", self)
        act_vol_up.triggered.connect(self._audio_volume_up)
        audio.addAction(act_vol_up)

        act_vol_down = QAction("Decrease Volume", self)
        act_vol_down.triggered.connect(self._audio_volume_down)
        audio.addAction(act_vol_down)

        act_mute = QAction("Mute", self)
        act_mute.setCheckable(True)
        act_mute.triggered.connect(self._toggle_mute)
        audio.aboutToShow.connect(lambda: act_mute.setChecked(self._volume <= 0))
        audio.addAction(act_mute)

        # Other menus are placeholders for later phases.
        def add_placeholder_menu(name: str, items: list[str]) -> None:
            menu = bar.addMenu(name)
            for text in items:
                act = QAction(text, self)
                act.setEnabled(False)
                menu.addAction(act)

        add_placeholder_menu("Video", ["Track", "Aspect Ratio", "Crop", "Rotate", "Filters"])
        add_placeholder_menu("Subtitle", ["Track", "Load External...", "Delay"])
        add_placeholder_menu("Tools", ["Media Info", "Diagnostics"])

        # View menu with a real fullscreen action.
        view = bar.addMenu("View")
        self._act_fullscreen = QAction("Fullscreen", self)
        self._act_fullscreen.setCheckable(True)
        self._act_fullscreen.setShortcut(QKeySequence("F"))
        self._act_fullscreen.triggered.connect(self._toggle_fullscreen_with_feedback)
        view.addAction(self._act_fullscreen)

        act_top = QAction("Always on Top", self)
        act_top.setEnabled(False)
        view.addAction(act_top)

        add_placeholder_menu("Help", ["About", "Shortcuts"])

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self.menuBar().setVisible(True)
            self.pane.force_controls_visible()
            self._hide_timer.stop()
        else:
            self.showFullScreen()
            self.menuBar().setVisible(False)
            self.pane.animate_show()
            self._hide_timer.start()

        # Keep menu action state synchronized.
        if self._act_fullscreen is not None:
            self._act_fullscreen.blockSignals(True)
            self._act_fullscreen.setChecked(self.isFullScreen())
            self._act_fullscreen.blockSignals(False)

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
        # Double-click toggle is handled by VideoPane to avoid duplicate toggles
        # from overlapping event paths.
        super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event) -> None:  # noqa: N802
        # VLC-like: mouse wheel controls volume.
        delta_y = int(event.angleDelta().y())
        if delta_y == 0:
            super().wheelEvent(event)
            return

        # 120 is one wheel notch in Qt; keep behavior predictable.
        notches = int(delta_y / 120)
        if notches == 0:
            notches = 1 if delta_y > 0 else -1

        self._change_volume_by(notches * 5)
        event.accept()
