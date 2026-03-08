from __future__ import annotations

from pathlib import Path
from typing import Optional
import time

import os
from PySide6.QtCore import QTimer, Qt, QThread, QObject, QMetaObject, Q_ARG
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtGui import QIcon
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QFileDialog, QMenu

import av

from playback.controller import PlaybackController
from ui.controls import ControlsState
from ui.icons import ICONS, IconSpec
from ui.video_pane import VideoPane
from ui.thumbnail_popup import ThumbnailPopup
from engine.thumbnail_worker import ThumbnailWorker, ThumbnailConfig
from util.debug_log import log_event
from PySide6.QtGui import QImage


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

        # ---------------- Video view + track state (must exist before menus) ----------------
        self._video_tracks = []
        self._video_track_index = 0

        # Folder navigation state (Next button).
        self._current_media_path: str = ""
        self._folder_entries: list[str] = []
        self._folder_index: int = -1

        # Cached info for the info popover (best-effort).
        self._media_info: dict[str, str] = {}

        # View transform defaults.
        self._video_fit_to_window = True
        self._video_zoom = 1.0
        self._video_aspect_override: Optional[float] = None
        self._video_crop_ratio: Optional[float] = None

        try:
            self.video.set_view_transform(
                fit_to_window=self._video_fit_to_window,
                zoom=self._video_zoom,
                aspect_override=self._video_aspect_override,
                crop_ratio=self._video_crop_ratio,
            )
        except Exception:
            pass

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

        # Route through our UX handler so we can ignore play when no media is loaded.
        self.controls.play_pause_clicked.connect(self._toggle_play_pause_with_feedback)
        # Folder button replaces the old right-most open button.
        self.controls.folder_clicked.connect(self._open_file)
        self.controls.next_file_clicked.connect(self._open_next_in_folder)
        self.controls.info_clicked.connect(self._show_info_popover)
        # Standard scrub UX: pause while dragging, seek on release, resume if needed.
        self._was_playing_before_scrub = False
        self.controls.scrub_started.connect(self._on_scrub_started)
        self.controls.scrub_finished.connect(self._on_scrub_finished)
        self.controls.volume_changed.connect(self._on_volume_slider_changed)
        self.controls.mute_clicked.connect(self._toggle_mute)
        self.controls.rewind_clicked.connect(self._skip_backward)
        self.controls.fast_forward_clicked.connect(self._skip_forward)

        # Timeline thumbnail preview.
        self._thumb_popup = ThumbnailPopup(self)
        self._thumb_popup.set_thumbnail_size(160, 90)
        self._thumb_last_hover_ms: int = 0
        # Fine thumbnail requests: throttle (not debounce) so moving hover still
        # produces images quickly even if coarse cache isn't ready.
        self._thumb_last_fine_bucket_ms: int = -1
        self._thumb_last_fine_req_wall: float = 0.0
        self._thumb_fine_min_interval_s: float = 0.12

        # Thumb worker thread (completely separate from playback).
        self._thumb_worker = ThumbnailWorker()
        self._thumb_media_path: str = ""

        # NOTE: Use QThread's *event loop* (do NOT override run) so queued
        # invocations + QTimer inside worker work correctly.
        self._thumb_thread = QThread(self)
        self._thumb_worker.moveToThread(self._thumb_thread)
        self._thumb_worker.coarse_ready.connect(self._on_coarse_thumb)
        self._thumb_worker.fine_ready.connect(self._on_fine_thumb)
        self._thumb_worker.error.connect(lambda m: log_event("thumb", f"err={m}"))
        # Start worker timer once the thread event loop is running.
        try:
            self._thumb_thread.started.connect(
                lambda: QMetaObject.invokeMethod(
                    self._thumb_worker,
                    "start",
                    Qt.ConnectionType.QueuedConnection,
                )
            )
        except Exception:
            pass

        self._thumb_thread.start()

        # Tune config (runtime only).
        try:
            cfg = ThumbnailConfig(thumb_w=160, thumb_h=90, coarse_interval_s=15.0, fine_bucket_s=1.0, max_fine_cache=600)
            self._thumb_worker.set_config(cfg)
        except Exception:
            pass

        self.controls.timeline_preview_moved.connect(self._on_timeline_preview_moved)
        self.controls.timeline_preview_left.connect(self._on_timeline_preview_left)

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
        QShortcut(QKeySequence("Z"), self, activated=self._cycle_video_zoom)
        QShortcut(QKeySequence("A"), self, activated=self._cycle_video_aspect)
        QShortcut(QKeySequence("C"), self, activated=self._cycle_video_crop)

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

        # Hold-to-2x diagnostics: measure effective speed (media seconds per wall second).
        self._hold_ff_wall_start: Optional[float] = None
        self._hold_ff_media_start_s: Optional[float] = None

        # Track list updates for Audio menu.
        self.controller.audio_tracks_changed.connect(self._on_audio_tracks)
        self.controller.video_tracks_changed.connect(self._on_video_tracks)



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
        # Stop worker deterministically in its own thread (prevents
        # QObject::killTimer warnings on shutdown).
        try:
            QMetaObject.invokeMethod(
                self._thumb_worker,
                "stop",
                Qt.ConnectionType.BlockingQueuedConnection,
            )
        except Exception:
            pass

        try:
            self._thumb_thread.quit()
            self._thumb_thread.wait(2000)
        except Exception:
            pass

        # Ensure worker is deleted in the correct thread context.
        try:
            self._thumb_worker.deleteLater()
        except Exception:
            pass
        self.controller.shutdown()
        super().closeEvent(event)

    def _thumb_open_media(self, path: str, duration_s: float) -> None:
        try:
            QMetaObject.invokeMethod(
                self._thumb_worker,
                "open_media",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, str(path)),
                Q_ARG(float, float(duration_s)),
            )
        except Exception:
            # Fallback (still thread-safe via worker lock).
            try:
                self._thumb_worker.open_media(str(path), float(duration_s))
            except Exception:
                pass

    def _on_timeline_preview_moved(self, value_ms: int, x_local: int, dragging: bool) -> None:
        # Show popup immediately with coarse thumb if available.
        v = int(max(0, value_ms))
        self._thumb_last_hover_ms = v

        try:
            # Coarse lookup is thread-safe.
            coarse = self._thumb_worker.get_coarse(v)
        except Exception:
            coarse = None

        log_event(
            "thumb",
            f"hover value_ms={v} coarse={'Y' if coarse is not None else 'N'} dragging={bool(dragging)}",
            throttle_key="thumb_hover",
            throttle_seconds=0.35,
        )

        self._thumb_popup.set_preview(coarse, v)

        # Hint the worker to prioritize coarse buckets around hover.
        try:
            QMetaObject.invokeMethod(
                self._thumb_worker,
                "prioritize_time",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, int(v)),
            )
        except Exception:
            pass

        # Position above the timeline (global coordinates).
        try:
            g = self.controls.timeline.mapToGlobal(self.controls.timeline.rect().topLeft())
            gx = int(g.x() + x_local)
            gy = int(g.y())
            clamp = self.geometry()
            self._thumb_popup.show_at(gx, gy, clamp_rect=clamp)
        except Exception:
            # Best effort
            self._thumb_popup.show()

        # Throttled fine requests (bucketed to 1s).
        self._maybe_request_fine_thumbnail(v)

    def _on_timeline_preview_left(self) -> None:
        try:
            self._thumb_popup.hide()
        except Exception:
            pass

    def _maybe_request_fine_thumbnail(self, hover_ms: int) -> None:
        # Only request if user moved to a new bucket or enough time elapsed.
        try:
            bucket_ms = int((int(hover_ms) // 1000) * 1000)
            now = float(time.monotonic())
            # If the bucket changed, request immediately (best UX).
            if bucket_ms != int(self._thumb_last_fine_bucket_ms):
                self._thumb_last_fine_bucket_ms = int(bucket_ms)
                self._thumb_last_fine_req_wall = float(now)
                self._request_fine_thumbnail()
                return

            # Otherwise (same bucket), throttle repeated requests.
            if (now - float(self._thumb_last_fine_req_wall)) < float(self._thumb_fine_min_interval_s):
                return
            self._thumb_last_fine_req_wall = float(now)
            self._request_fine_thumbnail()
        except Exception:
            pass

    def _request_fine_thumbnail(self) -> None:
        v = int(self._thumb_last_hover_ms)
        log_event(
            "thumb",
            f"request_fine value_ms={v}",
            throttle_key="thumb_req_fine",
            throttle_seconds=0.35,
        )
        try:
            QMetaObject.invokeMethod(
                self._thumb_worker,
                "request_fine",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(int, int(v)),
            )
        except Exception:
            try:
                self._thumb_worker.request_fine(int(v))
            except Exception:
                pass

    def _on_coarse_thumb(self, bucket_ms: int, img_obj: object) -> None:
        # If user is currently hovering near this bucket, refresh instantly.
        try:
            if not self._thumb_popup.isVisible():
                return
            # Only refresh if popup time is near this bucket.
            v = int(self._thumb_last_hover_ms)
            cfg_step = 15000
            if abs(int(bucket_ms) - int((v // cfg_step) * cfg_step)) <= cfg_step:
                img = img_obj if isinstance(img_obj, QImage) else None
                self._thumb_popup.set_preview(img, v)
        except Exception:
            pass

    def _on_fine_thumb(self, bucket_ms: int, img_obj: object, actual_pts_s: float) -> None:
        # If still hovering, swap to refined thumb.
        try:
            if not self._thumb_popup.isVisible():
                return
            v = int(self._thumb_last_hover_ms)
            # Fine bucket is 1s.
            if abs(int(bucket_ms) - int((v // 1000) * 1000)) <= 1000:
                img = img_obj if isinstance(img_obj, QImage) else None
                if img is not None:
                    self._thumb_popup.set_preview(img, v)

                # Diagnostic: how far the decoded frame is from the requested hover time.
                try:
                    target_s = float(v) / 1000.0
                    log_event(
                        "thumb",
                        f"fine_ready target={target_s:.3f}s pts={float(actual_pts_s):.3f}s delta={(float(actual_pts_s)-target_s):+.3f}s",
                        throttle_key="fine_ready",
                        throttle_seconds=0.35,
                    )
                except Exception:
                    pass
        except Exception:
            pass

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

        self._set_current_media_path(str(file_path))

        self._current_filename = os.path.basename(file_path)
        self.controls.set_filename(self._current_filename)
        self._update_title()
        self.controller.open_media(file_path)

        # Kick off thumbnail building.
        self._thumb_media_path = str(file_path)
        # Duration may still be 0 at this moment; worker will still open container.
        self._thumb_open_media(self._thumb_media_path, float(self._dur_ms) / 1000.0)

    def _set_current_media_path(self, file_path: str) -> None:
        """Store path and build folder playlist (for Next navigation)."""
        p = str(file_path)
        self._current_media_path = p
        self._media_info = {}

        try:
            folder = Path(p).resolve().parent
        except Exception:
            self._folder_entries = [p]
            self._folder_index = 0
            return

        exts = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".m4v", ".flv"}
        entries: list[str] = []
        try:
            for f in folder.iterdir():
                try:
                    if not f.is_file():
                        continue
                    if f.suffix.lower() not in exts:
                        continue
                    entries.append(str(f.resolve()))
                except Exception:
                    continue
        except Exception:
            entries = [p]

        # Sort alphabetically by filename (case-insensitive).
        try:
            entries.sort(key=lambda s: Path(s).name.casefold())
        except Exception:
            pass

        self._folder_entries = entries
        try:
            rp = str(Path(p).resolve())
            self._folder_index = self._folder_entries.index(rp)
        except Exception:
            # Fallback: try raw string match.
            try:
                self._folder_index = self._folder_entries.index(p)
            except Exception:
                self._folder_index = 0 if self._folder_entries else -1

    def _open_next_in_folder(self) -> None:
        """Open next media file in the current file's folder (wrap-around)."""
        if not self._folder_entries or self._folder_index < 0:
            self.pane.show_video_osd("Next: no folder")
            return

        if len(self._folder_entries) == 1:
            self.pane.show_video_osd("Next: only one file")
            return

        nxt_i = (int(self._folder_index) + 1) % int(len(self._folder_entries))
        nxt_path = self._folder_entries[nxt_i]
        self.pane.show_video_osd(f"Next: {Path(nxt_path).name}")
        self._on_file_selected(nxt_path)

    def _collect_media_info(self) -> dict[str, str]:
        """Best-effort media info extraction for the Info popover."""
        info: dict[str, str] = {}
        p = str(self._current_media_path or "")
        if not p:
            return info

        try:
            pp = Path(p)
            info["File"] = pp.name
            info["Path"] = str(pp)
        except Exception:
            info["Path"] = p

        try:
            if int(self._dur_ms) > 0:
                info["Duration"] = f"{int(self._dur_ms // 1000)} s"
        except Exception:
            pass

        try:
            c = av.open(p)
            try:
                vstreams = [s for s in c.streams if s.type == "video"]
                astreams = [s for s in c.streams if s.type == "audio"]
                if vstreams:
                    vs = vstreams[0]
                    try:
                        w = int(getattr(vs.codec_context, "width", 0) or 0)
                        h = int(getattr(vs.codec_context, "height", 0) or 0)
                        if w > 0 and h > 0:
                            info["Resolution"] = f"{w}×{h}"
                    except Exception:
                        pass

                    try:
                        fps = getattr(vs, "average_rate", None)
                        if fps is not None:
                            # fps can be Fraction-like.
                            info["FPS"] = f"{float(fps):.3f}".rstrip("0").rstrip(".")
                    except Exception:
                        pass

                    try:
                        codec = str(getattr(getattr(vs, "codec_context", None), "name", "") or "").strip()
                        if codec:
                            info["Video codec"] = codec
                    except Exception:
                        pass

                info["Video tracks"] = str(len(vstreams))
                info["Audio tracks"] = str(len(astreams))

                if astreams:
                    as0 = astreams[0]
                    try:
                        acodec = str(getattr(getattr(as0, "codec_context", None), "name", "") or "").strip()
                        if acodec:
                            info["Audio codec"] = acodec
                    except Exception:
                        pass
                    try:
                        ch = int(getattr(getattr(as0, "codec_context", None), "channels", 0) or 0)
                        if ch:
                            info["Audio channels"] = str(ch)
                    except Exception:
                        pass
            finally:
                try:
                    c.close()
                except Exception:
                    pass
        except Exception:
            pass

        return info

    def _show_info_popover(self) -> None:
        if not self._current_media_path:
            self.pane.show_video_osd("Info: no file")
            return

        if not self._media_info:
            self._media_info = self._collect_media_info()

        menu = QMenu(self)
        menu.setStyleSheet(
            """
            QMenu {
                background: rgba(10, 10, 12, 220);
                color: #ffffff;
                border: 1px solid rgba(255,255,255,38);
                border-radius: 12px;
                padding: 10px;
            }
            QMenu::item {
                padding: 6px 12px;
                border-radius: 8px;
                margin: 2px 2px;
            }
            QMenu::item:disabled {
                color: rgba(255,255,255,210);
            }
            """
        )
        try:
            menu.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay, True)
        except Exception:
            pass

        # Title line.
        try:
            title = Path(self._current_media_path).name
        except Exception:
            title = "Media Info"
        act_title = menu.addAction(f"{title}")
        act_title.setEnabled(False)
        menu.addSeparator()

        # Show key/value info.
        for k, v in (self._media_info or {}).items():
            if k == "File":
                continue
            line = f"{k}: {v}"
            a = menu.addAction(line)
            a.setEnabled(False)

        menu.addSeparator()
        act_copy = menu.addAction("Copy path")
        act_copy.triggered.connect(lambda: self._copy_to_clipboard(self._current_media_path))

        # Anchor to the info button.
        try:
            btn = self.controls.info_btn
            g = btn.mapToGlobal(btn.rect().bottomRight())
            menu.exec(g)
        except Exception:
            # Fallback: show at mouse.
            try:
                menu.exec(self.cursor().pos())
            except Exception:
                pass

    def _copy_to_clipboard(self, text: str) -> None:
        try:
            from PySide6.QtWidgets import QApplication

            cb = QApplication.clipboard()
            cb.setText(str(text))
            self.pane.show_video_osd("Copied")
        except Exception:
            pass

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

    def _on_video_tracks(self, tracks) -> None:
        try:
            self._video_tracks = list(tracks) if tracks is not None else []
        except Exception:
            self._video_tracks = []
        if self._video_track_index >= len(self._video_tracks):
            self._video_track_index = 0

    def _select_video_track(self, index: int) -> None:
        self._video_track_index = int(max(0, index))
        self.controller.select_video_track(self._video_track_index)

    # --------------------- Video view modes ---------------------

    @staticmethod
    def _ratio_label(r: Optional[float]) -> str:
        if r is None:
            return "Auto"
        return f"{r:.3f}".rstrip("0").rstrip(".")

    def _apply_video_view(self, *, osd: str) -> None:
        try:
            self.video.set_view_transform(
                fit_to_window=bool(self._video_fit_to_window),
                zoom=float(self._video_zoom),
                aspect_override=self._video_aspect_override,
                crop_ratio=self._video_crop_ratio,
            )
        except Exception:
            pass

        try:
            self.pane.show_video_osd(osd)
        except Exception:
            pass

        try:
            self._sync_video_menu_checks()
        except Exception:
            pass

    def _set_video_fit_to_window(self, fit: bool) -> None:
        self._video_fit_to_window = bool(fit)
        self._apply_video_view(osd=("Fit: Window" if self._video_fit_to_window else "Fit: Fill"))

    def _set_video_zoom(self, zoom: float) -> None:
        self._video_zoom = float(zoom)
        pct = int(round(float(self._video_zoom) * 100.0))
        self._apply_video_view(osd=f"Zoom: {pct}%")

    def _set_video_aspect(self, ratio: Optional[float]) -> None:
        self._video_aspect_override = ratio
        label = "Auto" if ratio is None else self._format_ratio(ratio)
        self._apply_video_view(osd=f"Aspect Ratio: {label}")

    def _set_video_crop(self, ratio: Optional[float]) -> None:
        self._video_crop_ratio = ratio
        label = "Off" if ratio is None else self._format_ratio(ratio)
        self._apply_video_view(osd=f"Crop: {label}")

    @staticmethod
    def _format_ratio(r: float) -> str:
        # Prefer common display format.
        try:
            rr = float(r)
        except Exception:
            return ""
        # Map exact-ish values back to nicer strings.
        presets = {
            16 / 9: "16:9",
            4 / 3: "4:3",
            1.0: "1:1",
            21 / 9: "21:9",
            2.35: "2.35:1",
        }
        for k, v in presets.items():
            if abs(float(rr) - float(k)) < 1e-3:
                return v
        return f"{rr:.3f}:1".rstrip("0").rstrip(".")

    def _take_snapshot(self) -> None:
        img = None
        try:
            img = self.video.grab_current_image()
        except Exception:
            img = None
        if img is None:
            self.pane.show_video_osd("Snapshot: no frame")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save snapshot",
            str(Path.home() / "snapshot.png"),
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;All Files (*.*)",
        )
        if not file_path:
            return
        ok = False
        try:
            ok = bool(img.save(str(file_path)))
        except Exception:
            ok = False
        self.pane.show_video_osd("Snapshot saved" if ok else "Snapshot failed")

    def _set_wallpaper_from_frame(self) -> None:
        # Best-effort Windows-only. Save a temporary BMP and call SPI.
        img = None
        try:
            img = self.video.grab_current_image()
        except Exception:
            img = None
        if img is None:
            self.pane.show_video_osd("Wallpaper: no frame")
            return

        try:
            import tempfile
            import ctypes

            tmp = Path(tempfile.gettempdir()) / "arjun_player_wallpaper.bmp"
            img.save(str(tmp), "BMP")

            SPI_SETDESKWALLPAPER = 20
            SPIF_UPDATEINIFILE = 0x01
            SPIF_SENDWININICHANGE = 0x02
            r = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER,
                0,
                str(tmp),
                SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE,
            )
            self.pane.show_video_osd("Wallpaper set" if r else "Wallpaper failed")
        except Exception:
            self.pane.show_video_osd("Wallpaper failed")

    def _cycle_video_zoom(self) -> None:
        presets = [0.5, 1.0, 1.25, 1.5, 2.0, 3.0]
        current = float(self._video_zoom)
        idx = 0
        for i, z in enumerate(presets):
            if abs(float(z) - float(current)) < 1e-6:
                idx = i
                break
        nxt = presets[(idx + 1) % len(presets)]
        self._set_video_zoom(float(nxt))

    def _cycle_video_aspect(self) -> None:
        presets: list[Optional[float]] = [None, 16 / 9, 4 / 3, 1.0, 21 / 9, 2.35]
        cur = self._video_aspect_override
        idx = 0
        for i, r in enumerate(presets):
            if r is None and cur is None:
                idx = i
                break
            if r is not None and cur is not None and abs(float(r) - float(cur)) < 1e-6:
                idx = i
                break
        nxt = presets[(idx + 1) % len(presets)]
        self._set_video_aspect(nxt)

    def _cycle_video_crop(self) -> None:
        presets: list[Optional[float]] = [None, 16 / 9, 4 / 3, 1.0, 21 / 9, 2.35]
        cur = self._video_crop_ratio
        idx = 0
        for i, r in enumerate(presets):
            if r is None and cur is None:
                idx = i
                break
            if r is not None and cur is not None and abs(float(r) - float(cur)) < 1e-6:
                idx = i
                break
        nxt = presets[(idx + 1) % len(presets)]
        self._set_video_crop(nxt)

    def _on_position(self, pos_ms: int) -> None:
        self._pos_ms = int(pos_ms)

    def _on_duration(self, dur_ms: int) -> None:
        self._dur_ms = int(dur_ms)
        self._refresh_controls()

        # If media was opened before duration became known, re-send with duration.
        try:
            if self._thumb_media_path:
                self._thumb_open_media(self._thumb_media_path, float(self._dur_ms) / 1000.0)
        except Exception:
            pass

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
        # If no media is loaded, ignore.
        if not self._current_media_path:
            try:
                self.pane.show_video_osd("No media")
            except Exception:
                pass
            return

        # Determine what the *next* state will be.
        next_playing = not self._is_playing
        log_event("ui", f"action:toggle_play_pause next={next_playing}")
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
        log_event("ui", "gesture:hold_fast_forward_start set_rate=2.0")

        try:
            self._hold_ff_wall_start = float(time.monotonic())
            self._hold_ff_media_start_s = float(self._pos_ms) / 1000.0
        except Exception:
            self._hold_ff_wall_start = None
            self._hold_ff_media_start_s = None

        self.controller.set_playback_rate(self._playback_rate)
        self.pane.show_speed_feedback("2×")

    def _on_video_hold_fast_forward_end(self) -> None:
        self._playback_rate = 1.0
        log_event("ui", "gesture:hold_fast_forward_end set_rate=1.0")

        # Diagnostics: compute effective rate during the hold.
        try:
            t0 = self._hold_ff_wall_start
            m0 = self._hold_ff_media_start_s
            t1 = float(time.monotonic())
            m1 = float(self._pos_ms) / 1000.0
            if t0 is not None and m0 is not None:
                wall = max(1e-6, (t1 - float(t0)))
                media = float(m1 - float(m0))
                eff = media / wall
                log_event(
                    "ui",
                    f"diag:hold_2x wall_s={wall:.3f} media_s={media:.3f} effective_rate={eff:.3f}",
                )
        except Exception:
            pass
        finally:
            self._hold_ff_wall_start = None
            self._hold_ff_media_start_s = None

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
        log_event("ui", f"menu:speed_set rate={r:.2f}")
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
        log_event("ui", f"action:toggle_mute current_volume={self._volume}")
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
        act_stop.triggered.connect(self._stop_and_unload_media)
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
        act_quit.triggered.connect(self._quit_clean)
        menu.addAction(act_quit)

        try:
            menu.exec(global_pos)
        except Exception:
            # Some Qt builds may want QPoint explicitly.
            menu.exec(menu.mapToGlobal(self.mapFromGlobal(global_pos)))

    def _reset_ui_to_idle(self) -> None:
        """Clear frame/seek/labels so we don't keep any previous-media state."""
        # Unload media in controller/decoder so Play cannot resume anything.
        try:
            self.controller.unload_media()
        except Exception:
            # Best-effort fallback.
            try:
                self.controller.pause()
            except Exception:
                pass
            try:
                self.controller.seek_ms(0)
            except Exception:
                pass

        # Clear video frame.
        try:
            self.video.set_frame(None)
        except Exception:
            pass

        # Clear labels/state.
        try:
            self._current_filename = ""
            self.controls.set_filename("")
            self._update_title()
        except Exception:
            pass

        self._current_media_path = ""
        self._folder_entries = []
        self._folder_index = -1
        self._media_info = {}

        # Reset local UI vars.
        try:
            self._pos_ms = 0
            self._dur_ms = 0
            self._refresh_controls()
        except Exception:
            pass

        # Clear thumbnail state so hover doesn't reference old media.
        try:
            self._thumb_media_path = ""
        except Exception:
            pass
        try:
            self._thumb_popup.hide()
        except Exception:
            pass

    def _stop_and_unload_media(self) -> None:
        """Stop action (context menu): unload current media from the UI.

        This is intentionally stronger than "pause": it clears the frame and
        wipes all current-file references so the player appears empty.
        """
        self._reset_ui_to_idle()

    def _quit_clean(self) -> None:
        """Quit from context menu: clear UI immediately, then close normally."""
        try:
            self._reset_ui_to_idle()
        except Exception:
            pass
        self.close()

    def _toggle_fullscreen_with_feedback(self) -> None:
        entering = not self.isFullScreen()
        log_event("ui", f"action:toggle_fullscreen entering={entering}")
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

        # Video menu (real actions).
        video = bar.addMenu("Video")

        # Video Track submenu.
        self._video_track_menu = video.addMenu("Video Track")
        self._video_track_menu.aboutToShow.connect(lambda: self._populate_video_tracks_menu(self._video_track_menu))

        video.addSeparator()

        act_fs2 = QAction("Fullscreen", self)
        act_fs2.setShortcut(QKeySequence("F"))
        act_fs2.triggered.connect(self._toggle_fullscreen_with_feedback)
        video.addAction(act_fs2)

        act_wall = QAction("Set as Wallpaper", self)
        act_wall.triggered.connect(self._set_wallpaper_from_frame)
        video.addAction(act_wall)

        self._act_fit_window = QAction("Always Fit Window", self)
        self._act_fit_window.setCheckable(True)
        self._act_fit_window.setChecked(True)
        self._act_fit_window.triggered.connect(lambda checked=False: self._set_video_fit_to_window(bool(checked)))
        video.addAction(self._act_fit_window)

        video.addSeparator()

        # Zoom submenu.
        zoom_menu = video.addMenu("Zoom")
        self._zoom_group = QActionGroup(self)
        self._zoom_group.setExclusive(True)
        self._zoom_actions = {}
        for z in (0.5, 1.0, 1.25, 1.5, 2.0, 3.0):
            a = QAction(f"{z:g}×", self)
            a.setCheckable(True)
            self._zoom_group.addAction(a)
            self._zoom_actions[float(z)] = a
            a.triggered.connect(lambda _checked=False, zz=z: self._set_video_zoom(float(zz)))
            zoom_menu.addAction(a)

        # Aspect Ratio submenu.
        aspect_menu = video.addMenu("Aspect Ratio")
        self._aspect_group = QActionGroup(self)
        self._aspect_group.setExclusive(True)
        self._aspect_actions = {}
        aspect_presets = [
            (None, "Auto"),
            (16 / 9, "16:9"),
            (4 / 3, "4:3"),
            (1.0, "1:1"),
            (21 / 9, "21:9"),
            (2.35, "2.35:1"),
        ]
        for r, label in aspect_presets:
            a = QAction(label, self)
            a.setCheckable(True)
            self._aspect_group.addAction(a)
            self._aspect_actions[r if r is None else float(r)] = a
            a.triggered.connect(lambda _checked=False, rr=r: self._set_video_aspect(rr))
            aspect_menu.addAction(a)

        # Crop submenu.
        crop_menu = video.addMenu("Crop")
        self._crop_group = QActionGroup(self)
        self._crop_group.setExclusive(True)
        self._crop_actions = {}
        crop_presets = [
            (None, "Off"),
            (16 / 9, "16:9"),
            (4 / 3, "4:3"),
            (1.0, "1:1"),
            (21 / 9, "21:9"),
            (2.35, "2.35:1"),
        ]
        for r, label in crop_presets:
            a = QAction(label, self)
            a.setCheckable(True)
            self._crop_group.addAction(a)
            self._crop_actions[r if r is None else float(r)] = a
            a.triggered.connect(lambda _checked=False, rr=r: self._set_video_crop(rr))
            crop_menu.addAction(a)

        video.addSeparator()
        act_snap = QAction("Take Snapshot…", self)
        act_snap.triggered.connect(self._take_snapshot)
        video.addAction(act_snap)

        # Init checks.
        try:
            self._sync_video_menu_checks()
        except Exception:
            pass
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

    def _populate_video_tracks_menu(self, menu: QMenu) -> None:
        menu.clear()
        tracks = self._video_tracks or []
        if not tracks:
            a = QAction("No video tracks", self)
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
            a.setChecked(int(idx) == int(self._video_track_index))
            group.addAction(a)
            a.triggered.connect(lambda _checked=False, i=idx: self._select_video_track(i))
            menu.addAction(a)

    def _sync_video_menu_checks(self) -> None:
        # Fit
        try:
            if hasattr(self, "_act_fit_window"):
                self._act_fit_window.blockSignals(True)
                self._act_fit_window.setChecked(bool(self._video_fit_to_window))
                self._act_fit_window.blockSignals(False)
        except Exception:
            pass

        # Zoom
        try:
            if hasattr(self, "_zoom_actions"):
                for z, act in getattr(self, "_zoom_actions").items():
                    act.setChecked(abs(float(z) - float(self._video_zoom)) < 1e-6)
        except Exception:
            pass

        # Aspect
        try:
            if hasattr(self, "_aspect_actions"):
                key = None if self._video_aspect_override is None else float(self._video_aspect_override)
                for k, act in getattr(self, "_aspect_actions").items():
                    if k is None and key is None:
                        act.setChecked(True)
                    elif k is not None and key is not None and abs(float(k) - float(key)) < 1e-6:
                        act.setChecked(True)
                    else:
                        act.setChecked(False)
        except Exception:
            pass

        # Crop
        try:
            if hasattr(self, "_crop_actions"):
                key = None if self._video_crop_ratio is None else float(self._video_crop_ratio)
                for k, act in getattr(self, "_crop_actions").items():
                    if k is None and key is None:
                        act.setChecked(True)
                    elif k is not None and key is not None and abs(float(k) - float(key)) < 1e-6:
                        act.setChecked(True)
                    else:
                        act.setChecked(False)
        except Exception:
            pass

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
