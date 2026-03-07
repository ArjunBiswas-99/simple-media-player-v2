from __future__ import annotations

import threading
from array import array
from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QIODevice, QObject
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices

from playback.clock import AudioClock
from util.debug_log import log_event


@dataclass(frozen=True)
class PCMConfig:
    sample_rate: int
    channels: int


class _PCMIODevice(QIODevice):
    """Qt pulls audio bytes from this device on an internal audio thread."""

    def __init__(self, fmt: QAudioFormat, clock: AudioClock, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._fmt = fmt
        self._clock = clock
        self._bytes_per_frame = fmt.bytesPerSample() * fmt.channelCount()

        self._lock = threading.Lock()
        self._buffer = bytearray()
        self._max_bytes = int(fmt.sampleRate() * self._bytes_per_frame * 0.75)  # ~750ms

        self._consumed_total = 0
        self._base_seconds = 0.0

    def reset_timeline(self, base_seconds: float) -> None:
        with self._lock:
            self._buffer.clear()
            self._consumed_total = 0
            self._base_seconds = float(base_seconds)
        # Keep this for now as a fallback/telemetry, but the authoritative
        # master clock comes from QAudioSink.processedUSecs().
        self._clock.set(base_seconds)

    def push(self, data: bytes) -> None:
        if not data:
            return
        with self._lock:
            # Keep internal buffer frame-aligned to avoid channel/sample
            # misalignment (which can sound like chipmunk/garble).
            bpf = int(self._bytes_per_frame)
            if bpf > 0:
                aligned = (len(data) // bpf) * bpf
                if aligned <= 0:
                    return
                data = data[:aligned]

            if len(self._buffer) + len(data) > self._max_bytes:
                drop = (len(self._buffer) + len(data)) - self._max_bytes
                if drop > 0:
                    # Drop whole frames only.
                    if bpf > 0:
                        drop = (drop // bpf) * bpf
                    del self._buffer[: min(drop, len(self._buffer))]
            self._buffer.extend(data)

    def bytesAvailable(self) -> int:  # noqa: N802
        # IMPORTANT:
        # Even if our internal buffer is empty, we can always synthesize
        # silence in readData(). Many Qt audio backends will stop pulling if
        # bytesAvailable() returns 0, which can put QAudioSink into IdleState
        # and stall the master clock.
        with self._lock:
            buffered = len(self._buffer) + super().bytesAvailable()
        return buffered + 4096

    def readData(self, maxlen: int) -> bytes:  # noqa: N802
        # Qt may request any byte count; we must return frame-aligned data.
        bpf = int(self._bytes_per_frame)
        if bpf <= 0:
            return b""

        req = (int(maxlen) // bpf) * bpf
        if req <= 0:
            return b""

        with self._lock:
            if not self._buffer:
                out = bytes(req)  # silence
            else:
                n = min(req, len(self._buffer))
                n = (n // bpf) * bpf
                if n <= 0:
                    out = bytes(req)
                else:
                    out = bytes(self._buffer[:n])
                    del self._buffer[:n]
                    # If Qt requested more than we have, pad with silence.
                    if n < req:
                        out += bytes(req - n)

            self._consumed_total += len(out)
            frames = self._consumed_total / float(self._bytes_per_frame)
            seconds = self._base_seconds + (frames / float(self._fmt.sampleRate()))
            self._clock.set(seconds)
            return out

    def writeData(self, data: bytes) -> int:  # noqa: N802
        return 0


class AudioOutput(QObject):
    """Audio sink (master clock)."""

    class StereoMode:
        STEREO = "stereo"
        MONO = "mono"
        LEFT = "left"
        RIGHT = "right"

    def __init__(self, clock: AudioClock, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._clock = clock
        self._sink: Optional[QAudioSink] = None
        self._device: Optional[_PCMIODevice] = None
        self._volume = 0.8

        self._output_device = None  # QAudioDevice | None (default)
        self._stereo_mode = AudioOutput.StereoMode.STEREO

        # Master clock anchor.
        self._base_seek_seconds = 0.0
        self._base_processed_us = 0

        self._current_cfg = PCMConfig(sample_rate=48000, channels=2)

    def preferred_config(self) -> PCMConfig:
        """Best-effort selection of a stable output format for the system."""
        try:
            dev = QMediaDevices.defaultAudioOutput()
            pref = dev.preferredFormat()
            sr = int(pref.sampleRate()) or 48000
            ch = int(pref.channelCount()) or 2
            ch = 2 if ch >= 2 else 1
            return PCMConfig(sample_rate=sr, channels=ch)
        except Exception:
            return PCMConfig(sample_rate=48000, channels=2)

    def available_output_devices(self) -> list:
        """Return list of QAudioDevice outputs (value types)."""
        try:
            return list(QMediaDevices.audioOutputs())
        except Exception:
            return []

    def default_output_device(self):
        try:
            return QMediaDevices.defaultAudioOutput()
        except Exception:
            return None

    def current_output_device(self):
        return self._output_device

    def set_output_device(self, dev) -> None:
        """Switch output audio device (recreates sink)."""
        self._output_device = dev
        # Recreate sink preserving current time anchor.
        base = 0.0
        try:
            base = float(self._clock.get())
        except Exception:
            base = 0.0

        # If we haven't been set up yet, do nothing.
        cfg = self._current_cfg
        self.setup(cfg)
        self.reset_clock_and_flush(base)

    def set_stereo_mode(self, mode: str) -> None:
        m = str(mode or "").strip().lower()
        if m not in (
            AudioOutput.StereoMode.STEREO,
            AudioOutput.StereoMode.MONO,
            AudioOutput.StereoMode.LEFT,
            AudioOutput.StereoMode.RIGHT,
        ):
            m = AudioOutput.StereoMode.STEREO
        self._stereo_mode = m

    def stereo_mode(self) -> str:
        return str(self._stereo_mode)

    def current_config(self) -> PCMConfig:
        return self._current_cfg

    def setup(self, cfg: PCMConfig) -> None:
        # Use the explicit config provided by controller/decoder pairing.
        chosen = cfg
        self._current_cfg = chosen

        fmt = QAudioFormat()
        fmt.setSampleRate(int(chosen.sample_rate))
        fmt.setChannelCount(int(chosen.channels))
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        if self._sink is not None:
            try:
                self._sink.stop()
            except Exception:
                pass

        # Create sink for selected device (or system default).
        try:
            if self._output_device is not None:
                self._sink = QAudioSink(self._output_device, fmt)
            else:
                self._sink = QAudioSink(fmt)
        except Exception:
            # Fallback.
            self._sink = QAudioSink(fmt)
        try:
            # Smaller buffer for lower latency.
            self._sink.setBufferSize(int(chosen.sample_rate * fmt.bytesPerFrame() * 0.20))
        except Exception:
            pass
        self._sink.setVolume(self._volume)

        self._device = _PCMIODevice(fmt, self._clock)
        self._device.open(QIODevice.OpenModeFlag.ReadOnly)
        self._sink.start(self._device)

        state_name = self._sink.state().name if self._sink is not None else "NONE"
        log_event(
            "audio",
            f"setup sr={chosen.sample_rate} ch={chosen.channels} bpf={fmt.bytesPerFrame()} sink_state={state_name}",
        )

        # Reset anchor when (re)creating the sink.
        self._base_seek_seconds = 0.0
        self._base_processed_us = int(self._sink.processedUSecs()) if self._sink is not None else 0

    def set_volume_percent(self, vol: int) -> None:
        self._volume = max(0.0, min(1.0, float(vol) / 100.0))
        if self._sink is not None:
            self._sink.setVolume(self._volume)

    def reset_clock_and_flush(self, base_seconds: float) -> None:
        # Anchor the master clock to the sink's processed timeline.
        self._base_seek_seconds = float(base_seconds)
        if self._sink is not None:
            self._base_processed_us = int(self._sink.processedUSecs())
        if self._device is not None:
            self._device.reset_timeline(base_seconds)
        else:
            self._clock.set(base_seconds)
        log_event(
            "audio",
            f"reset base={base_seconds:.3f}s processed_us={self._base_processed_us}",
        )

    def clock_seconds(self) -> float:
        """Authoritative audio master clock (seconds).

        We intentionally use the internally tracked consumed-byte clock updated
        in _PCMIODevice.readData() for deterministic behavior across backends.
        """

        sec = float(self._clock.get())
        if self._sink is not None:
            log_event(
                "audio",
                f"clock sec={sec:.3f} state={self._sink.state().name}",
                throttle_key="audio_clock",
                throttle_seconds=0.25,
            )
        return sec

    def push_pcm(self, data: bytes) -> None:
        if self._device is None or not data:
            return

        # Optional stereo routing (VLC-like) without external deps.
        # Data is s16 packed interleaved: L, R, L, R...
        try:
            if int(self._current_cfg.channels) == 2:
                mode = str(self._stereo_mode)
                if mode != AudioOutput.StereoMode.STEREO:
                    samples = array("h")
                    samples.frombytes(data)
                    n = len(samples)
                    if n >= 2:
                        # Ensure even length.
                        if (n % 2) == 1:
                            n -= 1
                        if mode == AudioOutput.StereoMode.MONO:
                            for i in range(0, n, 2):
                                l = int(samples[i])
                                r = int(samples[i + 1])
                                m = (l + r) // 2
                                samples[i] = m
                                samples[i + 1] = m
                        elif mode == AudioOutput.StereoMode.LEFT:
                            for i in range(0, n, 2):
                                l = samples[i]
                                samples[i + 1] = l
                        elif mode == AudioOutput.StereoMode.RIGHT:
                            for i in range(0, n, 2):
                                r = samples[i + 1]
                                samples[i] = r
                        data = samples.tobytes()
        except Exception:
            # Fail open: do not break audio if routing fails.
            pass

        self._device.push(data)

    def stop(self) -> None:
        if self._sink is not None:
            self._sink.stop()

    def pause(self) -> None:
        """Pause pulling audio from the device (keeps buffers)."""
        if self._sink is not None:
            try:
                # Only suspend if currently running.
                if self._sink.state() == QAudioSink.State.ActiveState:
                    self._sink.suspend()
                log_event("audio", f"pause state={self._sink.state().name}")
            except Exception:
                pass

    def resume(self) -> None:
        if self._sink is not None:
            try:
                if self._sink.state() in (QAudioSink.State.SuspendedState, QAudioSink.State.IdleState):
                    self._sink.resume()
                log_event("audio", f"resume state={self._sink.state().name}")
            except Exception:
                pass
