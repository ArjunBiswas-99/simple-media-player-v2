from __future__ import annotations

import threading


class AudioClock:
    """Thread-safe audio clock in seconds."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seconds = 0.0

    def set(self, seconds: float) -> None:
        with self._lock:
            self._seconds = float(seconds)

    def get(self) -> float:
        with self._lock:
            return float(self._seconds)
