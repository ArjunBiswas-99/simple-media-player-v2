from __future__ import annotations

import time


class VideoScheduler:
    """Audio-master scheduler for video presentation (Phase 1 minimal)."""

    def __init__(self, max_lag_seconds: float = 0.150) -> None:
        self._max_lag = float(max_lag_seconds)

    def should_drop(self, video_pts: float, audio_clock: float) -> bool:
        return (audio_clock - video_pts) > self._max_lag

    def sleep_until_present(self, video_pts: float, audio_clock: float) -> None:
        delay = video_pts - audio_clock
        if delay <= 0:
            return
        time.sleep(min(delay, 0.02))
