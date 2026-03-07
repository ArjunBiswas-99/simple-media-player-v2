from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

import av
import av.error
import av.filter
from PySide6.QtCore import QObject, Signal, Slot

from engine.frame_queue import BoundedQueue, DecodedVideo
from util.debug_log import log_event


@dataclass(frozen=True)
class StreamConfig:
    audio_sample_rate: int
    audio_channels: int


class DecoderWorker(QObject):
    """Decode engine running in a dedicated thread (UI-agnostic).

    Inputs (thread-safe via Qt queued connections):
    - open(path)
    - seek(seconds)
    - set_playing(bool)
    - stop()

    Outputs:
    - video frames -> BoundedQueue[DecodedVideo]
    - audio pcm (s16 interleaved) -> BoundedQueue[bytes]
    - signals for duration + stream config
    """

    media_opened = Signal(float, object)  # duration_seconds, StreamConfig
    error = Signal(str)
    eof_reached = Signal()

    def __init__(
        self,
        video_queue: BoundedQueue[DecodedVideo],
        audio_queue: BoundedQueue[bytes],
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._video_q = video_queue
        self._audio_q = audio_queue

        self._lock = threading.Lock()
        self._running = True
        self._playing = False

        self._open_path: Optional[str] = None
        self._seek_seconds: Optional[float] = None

        self._container: Optional[av.container.InputContainer] = None
        self._vstream: Optional[av.video.stream.VideoStream] = None
        self._astream: Optional[av.audio.stream.AudioStream] = None
        self._audio_resampler: Optional[av.audio.resampler.AudioResampler] = None

        # Desired output PCM config (what we will feed to Qt audio sink).
        # Keep deterministic defaults; controller can override.
        self._out_sample_rate = 48000
        self._out_channels = 2

        self._video_tb = 0.0

        # Playback rate support (1.0 normal, 2.0 fast, etc.).
        # This affects audio tempo filtering; video timing is handled by the UI
        # controller's rate-aware clock.
        self._playback_rate = 1.0
        self._pending_playback_rate: Optional[float] = None

        self._tempo_graph: Optional[av.filter.Graph] = None
        self._tempo_src: Optional[av.filter.context.FilterContext] = None
        self._tempo_sink: Optional[av.filter.context.FilterContext] = None

    @Slot(str)
    def open(self, path: str) -> None:
        log_event("decoder", f"open requested path={path}")
        with self._lock:
            self._open_path = path
            self._seek_seconds = None

    @Slot(float)
    def seek(self, seconds: float) -> None:
        log_event("decoder", f"seek requested seconds={seconds:.3f}")
        with self._lock:
            self._seek_seconds = float(seconds)

    @Slot(bool)
    def set_playing(self, playing: bool) -> None:
        with self._lock:
            self._playing = bool(playing)

    @Slot(float)
    def set_playback_rate(self, rate: float) -> None:
        # Keep it deterministic; Phase 1 supports only a safe range.
        r = float(rate)
        if r <= 0:
            r = 1.0
        # atempo supports 0.5-2.0; we'll clamp for now.
        r = max(0.5, min(2.0, r))
        with self._lock:
            self._pending_playback_rate = r

    @Slot(int, int)
    def set_output_audio_config(self, sample_rate: int, channels: int) -> None:
        """Set desired output PCM format.

        This must be called before/around open(); the worker will configure its
        resampler to produce PCM matching the Qt sink.
        """

        sr = int(sample_rate)
        ch = int(channels)
        if sr <= 0:
            sr = 48000
        if ch not in (1, 2):
            ch = 2
        with self._lock:
            self._out_sample_rate = sr
            self._out_channels = ch

    @Slot()
    def stop(self) -> None:
        with self._lock:
            self._running = False

    def _apply_open(self, path: str) -> None:
        try:
            if self._container is not None:
                try:
                    self._container.close()
                except Exception:
                    pass

            self._container = av.open(path)

            # Prefer a normal video stream over attached-picture/cover-art stream.
            vstreams = [s for s in self._container.streams if s.type == "video"]
            self._vstream = None
            for s in vstreams:
                disp = getattr(s, "disposition", None)
                is_attached = False
                try:
                    if disp is not None:
                        is_attached = bool(getattr(disp, "attached_pic", False))
                except Exception:
                    is_attached = False
                if not is_attached:
                    self._vstream = s
                    break
            if self._vstream is None:
                self._vstream = vstreams[0] if vstreams else None

            self._astream = next((s for s in self._container.streams if s.type == "audio"), None)

            if self._vstream is None and self._astream is None:
                raise RuntimeError("No audio/video streams found")

            if self._vstream is not None and self._vstream.time_base is not None:
                self._video_tb = float(self._vstream.time_base)
            else:
                self._video_tb = 0.0

            # Resample to match the configured Qt sink format (deterministic).
            with self._lock:
                out_sr = int(self._out_sample_rate)
                out_ch = int(self._out_channels)
                self._playback_rate = float(self._playback_rate) if self._playback_rate else 1.0
            layout = "stereo" if out_ch == 2 else "mono"
            self._audio_resampler = av.audio.resampler.AudioResampler(format="s16", layout=layout, rate=out_sr)

            # (Re)build tempo filter graph based on current playback rate.
            self._configure_tempo_filter(out_sr, layout)

            duration_s = 0.0
            if self._container.duration is not None:
                duration_s = float(self._container.duration) / 1_000_000.0
            else:
                # Fallback: stream duration fields (if present)
                candidates: list[float] = []
                if self._vstream is not None and self._vstream.duration is not None and self._vstream.time_base is not None:
                    candidates.append(float(self._vstream.duration) * float(self._vstream.time_base))
                if self._astream is not None and self._astream.duration is not None and self._astream.time_base is not None:
                    candidates.append(float(self._astream.duration) * float(self._astream.time_base))
                if candidates:
                    duration_s = max(candidates)

            self._video_q.clear()
            self._audio_q.clear()
            self.media_opened.emit(duration_s, StreamConfig(audio_sample_rate=out_sr, audio_channels=out_ch))
            log_event(
                "decoder",
                f"opened duration={duration_s:.3f}s out_sr={out_sr} out_ch={out_ch} "
                f"vstream={self._vstream is not None} astream={self._astream is not None}",
            )
        except Exception as e:
            log_event("decoder", f"open error: {e}")
            self.error.emit(str(e))

    def _apply_seek(self, seconds: float) -> None:
        if self._container is None:
            return
        try:
            self._container.seek(int(seconds * 1_000_000), any_frame=False, backward=True)
            self._video_q.clear()
            self._audio_q.clear()
        except Exception as e:
            self.error.emit(f"seek failed: {e}")

    def _configure_tempo_filter(self, sample_rate: int, layout: str) -> None:
        """Configure/disable atempo filter graph for the current playback rate."""

        rate = float(self._playback_rate)
        # Disable filter when rate ~ 1.0.
        if abs(rate - 1.0) < 1e-3:
            self._tempo_graph = None
            self._tempo_src = None
            self._tempo_sink = None
            return

        try:
            g = av.filter.Graph()
            src = g.add_abuffer(sample_rate=int(sample_rate), format="s16", layout=str(layout))
            tempo = g.add("atempo", args=f"{rate:.3f}")
            sink = g.add("abuffersink")
            src.link_to(tempo)
            tempo.link_to(sink)
            g.configure()
            self._tempo_graph = g
            self._tempo_src = src
            self._tempo_sink = sink
            log_event("decoder", f"tempo_filter configured rate={rate:.3f}")
        except Exception as e:
            # Fail open: if filter graph can't be built, fall back to normal audio.
            self._tempo_graph = None
            self._tempo_src = None
            self._tempo_sink = None
            log_event("decoder", f"tempo_filter error: {e}")

    @staticmethod
    def _audio_frame_to_packed_s16(af: av.audio.frame.AudioFrame, out_channels: int) -> bytes:
        """Convert a (possibly planar/strided) frame to packed s16 bytes.

        IMPORTANT: We emit exactly samples * channels * 2 bytes, avoiding any
        per-plane padding/stride leakage that can corrupt playback speed.
        """

        samples = int(getattr(af, "samples", 0))
        if samples <= 0:
            return b""

        channels = 1 if int(out_channels) == 1 else 2
        sample_width = 2  # s16
        expected_total = samples * channels * sample_width

        planes = [bytes(p) for p in af.planes]
        if not planes:
            return b""

        # Packed/interleaved case (single plane): slice to exact payload.
        if len(planes) == 1:
            raw = planes[0]
            if len(raw) >= expected_total:
                return raw[:expected_total]
            return raw + bytes(expected_total - len(raw))

        # Planar case: interleave from per-channel planes, each with exact
        # samples * sample_width valid bytes (ignore any padding beyond that).
        per_plane = samples * sample_width
        ch_data: list[bytes] = []
        for c in range(channels):
            if c < len(planes):
                p = planes[c]
                if len(p) >= per_plane:
                    ch_data.append(p[:per_plane])
                else:
                    ch_data.append(p + bytes(per_plane - len(p)))
            else:
                ch_data.append(bytes(per_plane))

        out = bytearray(expected_total)
        for i in range(samples):
            src = i * sample_width
            dst = i * channels * sample_width
            for c in range(channels):
                out[dst + (c * sample_width) : dst + ((c + 1) * sample_width)] = ch_data[c][src : src + sample_width]
        return bytes(out)

    def run(self) -> None:
        """Decode loop.

        NOTE: This must be started from the QThread event loop (via a singleShot
        or queued invocation). It runs until stop() is requested.
        """

        while True:
            with self._lock:
                running = self._running
                playing = self._playing
                open_path = self._open_path
                seek_s = self._seek_seconds
                pending_rate = self._pending_playback_rate
                self._open_path = None
                self._seek_seconds = None
                self._pending_playback_rate = None

            if not running:
                break

            if open_path is not None:
                self._apply_open(open_path)

            if seek_s is not None:
                self._apply_seek(seek_s)

            if pending_rate is not None:
                # Apply rate without a seek: flush queues so controller can resync.
                with self._lock:
                    self._playback_rate = float(pending_rate)

                self._video_q.clear()
                self._audio_q.clear()

                # Rebuild filter graph if we have an open stream.
                if self._astream is not None:
                    layout = "stereo" if int(self._out_channels) == 2 else "mono"
                    self._configure_tempo_filter(int(self._out_sample_rate), layout)

            if not playing or self._container is None:
                time.sleep(0.01)
                continue

            try:
                if self._video_q.qsize() > 12 or self._audio_q.qsize() > 24:
                    time.sleep(0.005)
                    continue

                broke_early = False
                backpressure_break = False
                for packet in self._container.demux((self._vstream, self._astream)):
                    with self._lock:
                        running = self._running
                        playing = self._playing
                        pending = self._open_path is not None or self._seek_seconds is not None
                    if not running or not playing or pending:
                        broke_early = True
                        break
                    for frame in packet.decode():
                        if isinstance(frame, av.video.frame.VideoFrame):
                            # Do not keep decoding far ahead of audio; preserve
                            # near-future frames instead of dropping old ones.
                            if self._video_q.qsize() >= 14:
                                backpressure_break = True
                                break

                            pts_s = 0.0
                            if frame.pts is not None:
                                # Use frame time base first (most accurate for decoded frame),
                                # fallback to stream time base.
                                if frame.time_base is not None:
                                    pts_s = float(frame.pts * frame.time_base)
                                elif self._video_tb:
                                    pts_s = float(frame.pts) * self._video_tb
                            rgb = frame.to_rgb()
                            plane0 = rgb.planes[0]
                            self._video_q.put_drop_oldest(
                                DecodedVideo(
                                    rgb_bytes=bytes(plane0),
                                    width=rgb.width,
                                    height=rgb.height,
                                    bytes_per_line=int(plane0.line_size),
                                    pts_seconds=pts_s,
                                )
                            )
                            log_event(
                                "decoder",
                                f"video pts={pts_s:.3f} qv={self._video_q.qsize()}",
                                throttle_key="video_pts",
                                throttle_seconds=0.25,
                            )
                        elif isinstance(frame, av.audio.frame.AudioFrame):
                            if self._audio_q.qsize() >= 30:
                                backpressure_break = True
                                break

                            if self._audio_resampler is None:
                                continue
                            out = self._audio_resampler.resample(frame)
                            frames = out if isinstance(out, list) else [out]
                            for af in frames:
                                if af is None:
                                    continue

                                # Tempo filter (atempo) if enabled.
                                if self._tempo_src is not None and self._tempo_sink is not None:
                                    try:
                                        self._tempo_src.push(af)
                                        while True:
                                            try:
                                                outf = self._tempo_sink.pull()
                                            except av.error.BlockingIOError:
                                                break
                                            if outf is None:
                                                break
                                            pcm = self._audio_frame_to_packed_s16(outf, self._out_channels)
                                            self._audio_q.put_drop_oldest(pcm)
                                    except Exception as e:
                                        # Fail open: if filter breaks, emit unfiltered.
                                        log_event("decoder", f"tempo_filter runtime error: {e}")
                                        pcm = self._audio_frame_to_packed_s16(af, self._out_channels)
                                        self._audio_q.put_drop_oldest(pcm)
                                else:
                                    pcm = self._audio_frame_to_packed_s16(af, self._out_channels)
                                    self._audio_q.put_drop_oldest(pcm)

                                fmt_name = getattr(af.format, "name", "?") if hasattr(af, "format") else "?"
                                log_event(
                                    "decoder",
                                    f"audio fmt={fmt_name} planes={len(af.planes)} samples={af.samples} qa={self._audio_q.qsize()}",
                                    throttle_key="audio_fmt",
                                    throttle_seconds=0.25,
                                )

                    if backpressure_break:
                        broke_early = True
                        break

                if backpressure_break:
                    # Yield to UI/audio consumer quickly, then continue decode.
                    time.sleep(0.002)

                # If we exhausted demux without interruption, we reached EOF.
                if not broke_early:
                    with self._lock:
                        # Only trigger EOF if we're still in a playing state.
                        still_playing = self._playing and self._running
                        pending = self._open_path is not None or self._seek_seconds is not None
                        if still_playing and not pending:
                            self._playing = False
                            self.eof_reached.emit()
                            log_event("decoder", "eof reached")
                    time.sleep(0.02)

            except av.error.FFmpegError:
                log_event("decoder", "ffmpeg transient error", throttle_key="ffmpeg_err", throttle_seconds=1.0)
                time.sleep(0.02)
            except Exception as e:
                log_event("decoder", f"decode error: {e}")
                self.error.emit(str(e))
                time.sleep(0.05)
