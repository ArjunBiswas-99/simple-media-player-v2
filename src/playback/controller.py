from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtGui import QImage

from engine.av_sync import VideoScheduler
from engine.decoder_worker import DecoderWorker, StreamConfig
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
        self.set_playback_rate(1.0)
        self.pause()
        self.video_frame_ready.emit(None)
        self._pending_video = None
        self._drop_video_until = None
        self._worker.open(path)

    def set_playback_rate(self, rate: float) -> None:
        """Set the playback rate (1.0 = normal).

        For Phase 1 we clamp to [0.5, 2.0]. Rate changes flush audio/video
        buffers to avoid mixing old-rate audio with new-rate audio.
        """

        r = float(rate)
        if r <= 0:
            r = 1.0
        r = max(0.5, min(2.0, r))

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
        self._is_playing = True
        self._audio.resume()
        self._worker.set_playing(True)
        self.playback_state_changed.emit(True)

    def pause(self) -> None:
        log_event("controller", "pause")
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
        self._worker.seek(pos_s)
        self.position_changed.emit(int(position_ms))

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

        # Start with pending, if any.
        if self._pending_video is not None:
            v = self._pending_video
            if v.pts_seconds > media_clock:
                # Still early.
                log_event("controller", f"pending pts={v.pts_seconds:.3f} mc={media_clock:.3f}", throttle_key="pending", throttle_seconds=0.15)
                return

            # Pending is eligible.
            self._pending_video = None
            latest_eligible = v

        # Drain a few frames from the queue.
        for _ in range(6):
            v = self._video_q.get_nowait()
            if v is None:
                break

            if self._drop_video_until is not None and v.pts_seconds < self._drop_video_until:
                continue
            if self._drop_video_until is not None and v.pts_seconds >= self._drop_video_until:
                self._drop_video_until = None

            if self._scheduler.should_drop(v.pts_seconds, media_clock):
                log_event("controller", f"drop pts={v.pts_seconds:.3f} mc={media_clock:.3f}", throttle_key="drop", throttle_seconds=0.15)
                continue

            if v.pts_seconds > media_clock:
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
