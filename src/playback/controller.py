from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtGui import QImage

from engine.av_sync import VideoScheduler
from engine.decoder_worker import DecoderWorker, StreamConfig, AudioTrackInfo, VideoTrackInfo
from engine.frame_queue import BoundedQueue, DecodedVideo
from playback.audio_output import AudioOutput, PCMConfig
from playback.clock import AudioClock
from ui.video_widget import VideoFrame
from util.debug_log import log_event


class PlaybackController(QObject):
    """UI-facing playback controller.

    - UI sends commands here (open/play/pause/seek/volume)
    - Controller dispatches commands to decode thread via signals
    - Controller pumps decoded queues on the UI thread (no blocking)
    """

    video_frame_ready = Signal(object)  # VideoFrame | None
    playback_state_changed = Signal(bool)
    position_changed = Signal(int)  # ms
    duration_changed = Signal(int)  # ms
    error_occurred = Signal(str)
    audio_tracks_changed = Signal(object)  # list[AudioTrackInfo]
    video_tracks_changed = Signal(object)  # list[VideoTrackInfo]

    # Commands are invoked as direct method calls on the worker.
    # The worker methods are thread-safe (lock-protected) and return immediately.

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._clock = AudioClock()
        self._audio = AudioOutput(self._clock, self)
        self._scheduler = VideoScheduler()

        # Determine stable output audio config once.
        self._out_cfg = self._audio.preferred_config()

        self._video_q: BoundedQueue[DecodedVideo] = BoundedQueue(maxsize=16)
        self._audio_q: BoundedQueue[bytes] = BoundedQueue(maxsize=32)

        self._is_playing = False
        self._duration_ms = 0
        self._volume = 80

        # Playback rate (1.0 normal, 2.0 fast, etc.).
        # The audio sink clock measures *output time*. To turn it into media
        # time, we scale by playback rate using anchors.
        self._playback_rate = 1.0
        self._rate_anchor_media_s = 0.0
        self._rate_anchor_audio_s = 0.0

        # After seek, drop video frames until we catch up to the new audio clock.
        self._drop_video_until: Optional[float] = None

        # Pending frame that is "too early". We keep it and present it later
        # when the audio clock catches up. This avoids UI-thread sleeping and
        # prevents fast-forward playback.
        self._pending_video: Optional[DecodedVideo] = None

        # When paused, freeze the media clock here so UI doesn't advance.
        self._paused_media_s: Optional[float] = None

        # Frames that are extremely far ahead of the current media clock after a seek
        # are almost certainly stale (from the pre-seek decode). We drop them.
        self._stale_frame_threshold_s = 12.0

        # Video pacing policy.
        # Normal playback: allow a small lag so motion is smooth.
        # Fast playback (>1x): drop more aggressively so the motion *feels* faster
        # (YouTube-style hold-to-2x).
        self._max_video_lag_normal_s = 0.150
        self._max_video_lag_fast_s = 0.050
        self._fast_mode_rate_threshold = 1.05
        self._fast_mode_allow_ahead_s = 0.030

        # Decode thread
        self._worker = DecoderWorker(self._video_q, self._audio_q)
        # Tell decoder what PCM format to produce.
        self._worker.set_output_audio_config(self._out_cfg.sample_rate, self._out_cfg.channels)

        class _DecodeThread(QThread):
            def __init__(self, worker: DecoderWorker, parent: Optional[QObject] = None) -> None:
                super().__init__(parent)
                self._worker = worker

            def run(self) -> None:  # noqa: N802
                # Run the decode loop entirely in this thread.
                self._worker.run()

        self._thread = _DecodeThread(self._worker, self)
        self._worker.moveToThread(self._thread)

        # Worker signals -> controller slots
        self._worker.media_opened.connect(self._on_media_opened)
        self._worker.audio_tracks_changed.connect(self.audio_tracks_changed)
        self._worker.video_tracks_changed.connect(self.video_tracks_changed)
        self._worker.error.connect(self._on_error)
        self._worker.eof_reached.connect(self._on_eof)

        self._thread.start()

        # UI thread pump
        self._pump = QTimer(self)
        self._pump.setInterval(10)
        self._pump.timeout.connect(self._tick)
        self._pump.start()

        self.set_volume(self._volume)

    def open_media(self, path: str) -> None:
        log_event("controller", f"open_media path={path}")
        # Reset rate when opening new media.
        # IMPORTANT: opening new media must start from 0 and must not inherit
        # paused-media anchors from the previous file.
        self.set_playback_rate(1.0)

        # Stop decoding + audio immediately.
        self._is_playing = False
        try:
            self._worker.set_playing(False)
        except Exception:
            pass
        try:
            self._audio.pause()
        except Exception:
            pass

        # Reset clocks/anchors to 0.
        self._paused_media_s = None
        self._rate_anchor_media_s = 0.0
        self._rate_anchor_audio_s = float(self._audio.clock_seconds())
        try:
            self._audio.reset_clock_and_flush(0.0)
        except Exception:
            pass

        # Clear any buffered frames from previous media.
        self._video_q.clear()
        self._audio_q.clear()
        self.video_frame_ready.emit(None)
        self._pending_video = None
        self._drop_video_until = None
        self._worker.open(path)

    def unload_media(self) -> None:
        """Unload current media so playback cannot resume until open_media()."""
        log_event("controller", "unload_media")

        # Stop everything immediately.
        self._is_playing = False
        try:
            self._worker.set_playing(False)
        except Exception:
            pass
        try:
            self._audio.pause()
        except Exception:
            pass

        # Reset clocks/anchors.
        self._paused_media_s = None
        self._rate_anchor_media_s = 0.0
        self._rate_anchor_audio_s = float(self._audio.clock_seconds())
        try:
            self._audio.reset_clock_and_flush(0.0)
        except Exception:
            pass

        # Clear queued decoded data.
        self._pending_video = None
        self._drop_video_until = None
        self._video_q.clear()
        self._audio_q.clear()

        # Clear duration.
        self._duration_ms = 0
        try:
            self.duration_changed.emit(0)
            self.position_changed.emit(0)
        except Exception:
            pass

        # Clear frame.
        try:
            self.video_frame_ready.emit(None)
        except Exception:
            pass

        # Ask worker to close the container.
        try:
            self._worker.close_media()
        except Exception:
            pass

        # Notify UI state.
        try:
            self.playback_state_changed.emit(False)
        except Exception:
            pass

    def set_playback_rate(self, rate: float) -> None:
        """Set the playback rate (1.0 = normal).

        For Phase 1 we clamp to [0.5, 2.0]. Rate changes flush audio/video
        buffers to avoid mixing old-rate audio with new-rate audio.
        """

        r = float(rate)
        if r <= 0:
            r = 1.0
        r = max(0.5, min(2.0, r))

        log_event(
            "controller",
            f"set_playback_rate req={float(rate):.3f} clamped={r:.3f} current={self._playback_rate:.3f}",
        )

        # Compute current media time before switching.
        audio_clock = self._audio.clock_seconds()
        current_media = self._rate_anchor_media_s + (audio_clock - self._rate_anchor_audio_s) * float(self._playback_rate)

        self._playback_rate = r

        # Flush audio sink buffer and anchor clock at current media time.
        self._audio.reset_clock_and_flush(current_media)
        audio_clock = self._audio.clock_seconds()
        self._rate_anchor_media_s = current_media
        self._rate_anchor_audio_s = audio_clock

        # Reset pending video state; decoder will also flush its queues.
        self._pending_video = None
        self._drop_video_until = current_media

        # Tell decoder to tempo-scale audio.
        self._worker.set_playback_rate(r)

    def toggle_play_pause(self) -> None:
        if self._is_playing:
            self.pause()
        else:
            self.play()

    def play(self) -> None:
        log_event("controller", "play")

        # If we were paused, re-anchor the media clock so resume doesn't jump.
        if self._paused_media_s is not None:
            try:
                paused_media = float(self._paused_media_s)
            except Exception:
                paused_media = 0.0
            self._rate_anchor_media_s = max(0.0, paused_media)
            self._rate_anchor_audio_s = float(self._audio.clock_seconds())
            self._drop_video_until = self._rate_anchor_media_s
            self._pending_video = None
            self._paused_media_s = None

        self._is_playing = True
        self._audio.resume()
        self._worker.set_playing(True)
        self.playback_state_changed.emit(True)

    def pause(self) -> None:
        log_event("controller", "pause")

        # Freeze current media time so UI doesn't keep ticking.
        try:
            audio_clock = float(self._audio.clock_seconds())
            media_clock = self._rate_anchor_media_s + (audio_clock - self._rate_anchor_audio_s) * float(self._playback_rate)
            self._paused_media_s = max(0.0, float(media_clock))
        except Exception:
            # Fallback: keep previous paused value.
            if self._paused_media_s is None:
                self._paused_media_s = float(self._rate_anchor_media_s)

        self._is_playing = False
        self._worker.set_playing(False)
        self._audio.pause()
        self._pending_video = None
        self.playback_state_changed.emit(False)

    def set_volume(self, vol: int) -> None:
        self._volume = int(max(0, min(100, vol)))
        self._audio.set_volume_percent(self._volume)

    def seek_ms(self, position_ms: int) -> None:
        log_event("controller", f"seek_ms req={position_ms}")
        pos_s = max(0.0, float(position_ms) / 1000.0)
        # Reset clock immediately to keep UI responsive.
        self._audio.reset_clock_and_flush(pos_s)

        # Reset rate anchors to the new position.
        audio_clock = self._audio.clock_seconds()
        self._rate_anchor_media_s = pos_s
        self._rate_anchor_audio_s = audio_clock

        self._drop_video_until = pos_s
        self._pending_video = None
        self._paused_media_s = None

        # Clear queues immediately on the UI thread so we cannot accidentally
        # consume stale far-ahead frames before the worker processes the seek.
        self._video_q.clear()
        self._audio_q.clear()

        self._worker.seek(pos_s)
        self.position_changed.emit(int(position_ms))

    def select_audio_track(self, index: int) -> None:
        """Select audio track (0-based).

        We resync by seeking to current media time to ensure A/V alignment.
        """
        idx = int(index)

        # Compute current media time to keep switching deterministic.
        audio_clock = self._audio.clock_seconds()
        media_clock = self._rate_anchor_media_s + (audio_clock - self._rate_anchor_audio_s) * float(self._playback_rate)
        media_clock = max(0.0, float(media_clock))

        # Apply track selection + flush audio in worker.
        self._worker.select_audio_track(idx)

        # Force a resync seek to avoid drift / decoder priming differences.
        self.seek_ms(int(media_clock * 1000.0))

    def select_video_track(self, index: int) -> None:
        """Select video track (0-based).

        We resync by seeking to current media time (same strategy as audio).
        """
        idx = int(index)

        audio_clock = self._audio.clock_seconds()
        media_clock = self._rate_anchor_media_s + (audio_clock - self._rate_anchor_audio_s) * float(self._playback_rate)
        media_clock = max(0.0, float(media_clock))

        self._worker.select_video_track(idx)
        self.seek_ms(int(media_clock * 1000.0))

    def available_audio_output_devices(self) -> list:
        return self._audio.available_output_devices()

    def default_audio_output_device(self):
        return self._audio.default_output_device()

    def current_audio_output_device(self):
        return self._audio.current_output_device()

    def set_audio_output_device(self, dev) -> None:
        # Keep UI responsive: no seek, just recreate sink and keep current anchor.
        self._audio.set_output_device(dev)

    def set_stereo_mode(self, mode: str) -> None:
        self._audio.set_stereo_mode(mode)

    def stereo_mode(self) -> str:
        return self._audio.stereo_mode()

    def shutdown(self) -> None:
        try:
            self.pause()
        except Exception:
            pass
        try:
            self._audio.stop()
        except Exception:
            pass

        self._worker.stop()
        self._thread.wait(3000)

    def __del__(self) -> None:
        # Best-effort cleanup to avoid QThread warnings in edge cases.
        try:
            self.shutdown()
        except Exception:
            pass

    def _on_media_opened(self, duration_s: float, cfg_obj: object) -> None:
        cfg = cfg_obj if isinstance(cfg_obj, StreamConfig) else None
        self._duration_ms = int(max(0.0, duration_s) * 1000.0)
        self.duration_changed.emit(self._duration_ms)
        log_event("controller", f"media_opened dur_ms={self._duration_ms}")

        # Configure audio sink using stable output config.
        # (Decoder is already configured to resample to this.)
        self._audio.setup(self._out_cfg)
        self._audio.reset_clock_and_flush(0.0)

        # Reset rate anchors on open.
        self._playback_rate = 1.0
        self._rate_anchor_media_s = 0.0
        self._rate_anchor_audio_s = self._audio.clock_seconds()
        self._worker.set_playback_rate(1.0)

        # Defensive: ensure we never resume at old paused position after open.
        self._paused_media_s = None
        self.play()

    def _on_error(self, msg: str) -> None:
        log_event("controller", f"error={msg}")
        self.error_occurred.emit(msg)

    def _on_eof(self) -> None:
        log_event("controller", "eof")
        # Stop cleanly at end of file.
        self.pause()
        # Clamp UI position to duration.
        if self._duration_ms > 0:
            self._clock.set(self._duration_ms / 1000.0)
            self.position_changed.emit(self._duration_ms)

    def _tick(self) -> None:
        # Feed audio chunks first (master clock).
        for _ in range(6):
            chunk = self._audio_q.get_nowait()
            if chunk is None:
                break
            self._audio.push_pcm(chunk)

        if not self._is_playing:
            # Freeze UI time on pause.
            mc = float(self._paused_media_s) if self._paused_media_s is not None else float(self._rate_anchor_media_s)
            self.position_changed.emit(int(mc * 1000.0))
            return

        audio_clock = self._audio.clock_seconds()
        media_clock = self._rate_anchor_media_s + (audio_clock - self._rate_anchor_audio_s) * float(self._playback_rate)
        self.position_changed.emit(int(media_clock * 1000.0))
        log_event(
            "controller",
            f"tick ac={audio_clock:.3f} mc={media_clock:.3f} rate={self._playback_rate:.2f} qv={self._video_q.qsize()} qa={self._audio_q.qsize()} pending={self._pending_video is not None}",
            throttle_key="tick",
            throttle_seconds=0.25,
        )

        # Frame pacing:
        # Prefer *smooth* catch-up over bursty multi-present. When we're behind,
        # drain queued frames up to (<= media_clock), then present the latest.

        latest_eligible: Optional[DecodedVideo] = None

        fast_mode = float(self._playback_rate) >= float(self._fast_mode_rate_threshold)
        max_lag = float(self._max_video_lag_fast_s if fast_mode else self._max_video_lag_normal_s)
        allow_ahead = float(self._fast_mode_allow_ahead_s if fast_mode else 0.0)

        # Start with pending, if any.
        if self._pending_video is not None:
            v = self._pending_video
            # If pending is absurdly far ahead, it's stale; drop it.
            try:
                if float(v.pts_seconds) - float(media_clock) > float(self._stale_frame_threshold_s):
                    log_event(
                        "controller",
                        f"drop_stale_pending pts={v.pts_seconds:.3f} mc={media_clock:.3f}",
                        throttle_key="drop_stale_pending",
                        throttle_seconds=0.25,
                    )
                    self._pending_video = None
                    v = None
            except Exception:
                pass

            if v is None:
                return

            if v.pts_seconds > media_clock and (v.pts_seconds - media_clock) > allow_ahead:
                # Still early.
                log_event("controller", f"pending pts={v.pts_seconds:.3f} mc={media_clock:.3f}", throttle_key="pending", throttle_seconds=0.15)
                return

            # Pending is eligible.
            self._pending_video = None
            latest_eligible = v

        # Drain frames from the queue.
        # In fast mode we drain more per tick so we can skip ahead more clearly.
        drain_limit = 6 if not fast_mode else 18
        for _ in range(int(drain_limit)):
            v = self._video_q.get_nowait()
            if v is None:
                break

            # Drop stale far-ahead frames (happens after seeking backwards).
            try:
                if float(v.pts_seconds) - float(media_clock) > float(self._stale_frame_threshold_s):
                    log_event(
                        "controller",
                        f"drop_stale pts={v.pts_seconds:.3f} mc={media_clock:.3f}",
                        throttle_key="drop_stale",
                        throttle_seconds=0.25,
                    )
                    continue
            except Exception:
                pass

            if self._drop_video_until is not None and v.pts_seconds < self._drop_video_until:
                continue
            if self._drop_video_until is not None and v.pts_seconds >= self._drop_video_until:
                self._drop_video_until = None

            # Drop if video is too far behind the media clock.
            if (float(media_clock) - float(v.pts_seconds)) > float(max_lag):
                log_event(
                    "controller",
                    f"drop pts={v.pts_seconds:.3f} mc={media_clock:.3f} lag={(media_clock - v.pts_seconds):.3f} max_lag={max_lag:.3f}",
                    throttle_key="drop",
                    throttle_seconds=0.15,
                )
                continue

            if v.pts_seconds > media_clock and (v.pts_seconds - media_clock) > allow_ahead:
                # Keep the first early frame for next tick.
                self._pending_video = v
                break

            latest_eligible = v

        if latest_eligible is None:
            return

        # Present the latest eligible frame (smooth catch-up).
        img = QImage(
            latest_eligible.rgb_bytes,
            latest_eligible.width,
            latest_eligible.height,
            latest_eligible.bytes_per_line,
            QImage.Format.Format_RGB888,
        ).copy()
        self.video_frame_ready.emit(VideoFrame(image=img, pts_seconds=latest_eligible.pts_seconds))
        log_event(
            "controller",
            f"present pts={latest_eligible.pts_seconds:.3f} mc={media_clock:.3f}",
            throttle_key="present",
            throttle_seconds=0.15,
        )
        return
