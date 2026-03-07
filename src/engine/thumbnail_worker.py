from __future__ import annotations

import time
from collections import OrderedDict, deque
from dataclasses import dataclass
from typing import Optional

import av
import av.error
from PySide6.QtCore import QObject, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QImage

from util.debug_log import log_event


@dataclass(frozen=True)
class ThumbnailConfig:
    # Display size for thumbnails (scaled down in worker to save RAM).
    thumb_w: int = 160
    thumb_h: int = 90

    # Coarse cache: sample interval (seconds). Lower = more RAM/CPU.
    coarse_interval_s: float = 15.0

    # Fine cache: bucket size (seconds) for refined thumbs.
    fine_bucket_s: float = 1.0

    # Bounded in-RAM refined cache.
    max_fine_cache: int = 600

    # Work pacing
    tick_ms: int = 15
    coarse_per_tick: int = 1


class ThumbnailWorker(QObject):
    """Qt-thread thumbnail generator.

    Runs inside a QThread *with an event loop*.
    Requests arrive via queued signals (open_media / request_fine).
    We use a QTimer to do small chunks of work so UI/playback remain smooth.
    """

    coarse_ready = Signal(int, object)  # bucket_ms, QImage
    fine_ready = Signal(int, object, float)  # bucket_ms, QImage, actual_pts_s
    coarse_progress = Signal(int, int)  # done, total
    error = Signal(str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._cfg = ThumbnailConfig()

        self._running = False
        self._timer: Optional[QTimer] = None

        self._path: str = ""
        self._duration_s: float = 0.0

        self._container: Optional[av.container.InputContainer] = None
        self._vstream = None
        self._video_tb = 0.0

        # Caches
        self._coarse: dict[int, QImage] = {}
        # bucket_ms -> (img, pts_s)
        self._fine_lru: OrderedDict[int, tuple[QImage, float]] = OrderedDict()

        # Coarse build state
        self._coarse_total = 0
        self._coarse_anchor_mid = 0
        self._coarse_rr = 0
        self._coarse_done = False

        # Coarse scheduler cursors
        # Each cursor is an index; ranges are defined by step/bounds.
        self._a_fwd = 0
        self._b_left = 0
        self._b_right = 0
        self._c_left = 0

        # Priority coarse work injected from UI hover.
        self._coarse_priority: deque[int] = deque()

        # Fine request state (latest only)
        self._pending_fine_bucket_ms: Optional[int] = None
        self._pending_fine_req_id = 0

        # While user is actively hovering/scrubbing, we want fine thumbnails to
        # feel instant. Coarse prebuild seeks can interfere (seek thrash + long
        # GOP decode). We therefore pause coarse work for a short window after
        # any fine activity.
        self._fine_activity_until_wall: float = 0.0

    # ------------------------- lifecycle -------------------------

    @Slot()
    def start(self) -> None:
        if self._running:
            return
        self._running = True

        self._timer = QTimer(self)
        self._timer.setInterval(int(max(5, self._cfg.tick_ms)))
        self._timer.timeout.connect(self._on_tick)
        self._timer.start()
        log_event("thumb", "worker:start")

    @Slot()
    def stop(self) -> None:
        self._running = False
        try:
            if self._timer is not None:
                self._timer.stop()
        except Exception:
            pass
        self._timer = None

        try:
            if self._container is not None:
                self._container.close()
        except Exception:
            pass
        self._container = None
        self._vstream = None
        self._video_tb = 0.0

        log_event("thumb", "worker:stop")

    # ------------------------- configuration -------------------------

    @Slot(object)
    def set_config(self, cfg_obj: object) -> None:
        if isinstance(cfg_obj, ThumbnailConfig):
            self._cfg = cfg_obj
            # Update timer pacing if already started.
            try:
                if self._timer is not None:
                    self._timer.setInterval(int(max(5, self._cfg.tick_ms)))
            except Exception:
                pass

    # ------------------------- API from UI -------------------------

    @Slot(str, float)
    def open_media(self, path: str, duration_s: float) -> None:
        p = str(path)
        d = float(max(0.0, duration_s))

        changed = (p != self._path)
        self._path = p
        # Duration might become known later.
        self._duration_s = max(self._duration_s if not changed else 0.0, d)

        if changed:
            self._reset_for_new_media()

        prev_total = int(self._coarse_total)
        self._recompute_coarse_total()
        if int(self._coarse_total) != prev_total:
            self._reset_coarse_schedule()
        log_event("thumb", f"open_media changed={changed} dur={self._duration_s:.3f}s")

    @Slot(int)
    def request_fine(self, time_ms: int) -> None:
        cfg = self._cfg
        bucket_ms = int(max(0, int(time_ms)) // int(cfg.fine_bucket_s * 1000.0)) * int(cfg.fine_bucket_s * 1000.0)

        # If cached, emit immediately.
        if bucket_ms in self._fine_lru:
            img, pts = self._fine_lru[bucket_ms]
            self._fine_lru.move_to_end(bucket_ms)
            self.fine_ready.emit(bucket_ms, img, float(pts))
            return

        self._pending_fine_bucket_ms = bucket_ms
        self._pending_fine_req_id += 1

        # Pause coarse work for a bit.
        try:
            self._fine_activity_until_wall = max(float(self._fine_activity_until_wall), float(time.monotonic()) + 0.75)
        except Exception:
            pass

    @Slot(int)
    def prioritize_time(self, time_ms: int) -> None:
        """Hint from UI: user is hovering around time_ms.

        We enqueue the coarse bucket for that time (plus neighbors) so the
        placeholder is less likely to be shown even before the sequential build
        reaches that region.
        """
        if self._coarse_total <= 0:
            return
        step_ms = int(max(1, self._cfg.coarse_interval_s * 1000.0))
        idx = int(max(0, int(time_ms)) // step_ms)
        idx = max(0, min(idx, int(self._coarse_total) - 1))
        # Add center + near buckets.
        for j in (idx - 1, idx, idx + 1):
            if 0 <= j < int(self._coarse_total):
                self._coarse_priority.append(int(j))

        # Also count as activity so coarse doesn't steal cycles during hover.
        try:
            self._fine_activity_until_wall = max(float(self._fine_activity_until_wall), float(time.monotonic()) + 0.30)
        except Exception:
            pass

    def get_coarse(self, time_ms: int) -> Optional[QImage]:
        cfg = self._cfg
        step_ms = int(max(1, cfg.coarse_interval_s * 1000.0))
        bucket = int(max(0, int(time_ms)) // step_ms) * step_ms
        return self._coarse.get(bucket)

    # ------------------------- internal -------------------------

    def _reset_for_new_media(self) -> None:
        # Close container.
        try:
            if self._container is not None:
                self._container.close()
        except Exception:
            pass

        self._container = None
        self._vstream = None
        self._video_tb = 0.0
        self._coarse.clear()
        self._fine_lru.clear()
        self._coarse_total = 0
        self._reset_coarse_schedule()
        self._pending_fine_bucket_ms = None
        self._pending_fine_req_id += 1

    def _recompute_coarse_total(self) -> None:
        cfg = self._cfg
        if self._duration_s <= 0 or cfg.coarse_interval_s <= 0:
            self._coarse_total = 0
            return
        self._coarse_total = int(self._duration_s // float(cfg.coarse_interval_s)) + 1

    def _reset_coarse_schedule(self) -> None:
        # Scheduler reset; does not clear already-built coarse cache (that is
        # handled by _reset_for_new_media).
        n = int(self._coarse_total)
        self._coarse_done = False
        self._coarse_rr = 0
        self._coarse_priority.clear()

        if n <= 0:
            self._coarse_anchor_mid = 0
            self._a_fwd = 0
            self._b_left = 0
            self._b_right = 0
            self._c_left = 0
            return

        self._coarse_anchor_mid = int(n // 2)
        self._a_fwd = 0
        self._b_left = int(self._coarse_anchor_mid)
        self._b_right = int(self._coarse_anchor_mid)
        self._c_left = int(n - 1)

    def _next_coarse_index(self) -> Optional[int]:
        """Return next coarse bucket index to generate.

        Strategy:
        1) Serve any hover-priority indices first.
        2) Otherwise, round-robin across 4 expanding fronts:
           - start -> mid
           - mid -> start
           - mid -> end
           - end -> mid
        """
        n = int(self._coarse_total)
        if n <= 0 or self._coarse_done:
            return None

        # 1) Priority queue.
        while self._coarse_priority:
            idx = int(self._coarse_priority.popleft())
            if idx < 0 or idx >= n:
                continue
            bucket_ms = int(idx * self._cfg.coarse_interval_s * 1000.0)
            if bucket_ms in self._coarse:
                continue
            return idx

        # 2) Round-robin across cursors.
        order = ("a_fwd", "b_left", "b_right", "c_left")
        tried = 0
        while tried < len(order):
            name = order[int(self._coarse_rr) % len(order)]
            self._coarse_rr = (int(self._coarse_rr) + 1) % len(order)
            tried += 1

            idx = None
            if name == "a_fwd":
                if self._a_fwd <= int(self._coarse_anchor_mid):
                    idx = int(self._a_fwd)
                    self._a_fwd += 1
            elif name == "b_left":
                if self._b_left >= 0:
                    idx = int(self._b_left)
                    self._b_left -= 1
            elif name == "b_right":
                if self._b_right <= (n - 1):
                    idx = int(self._b_right)
                    self._b_right += 1
            elif name == "c_left":
                if self._c_left >= int(self._coarse_anchor_mid):
                    idx = int(self._c_left)
                    self._c_left -= 1

            if idx is None:
                continue
            if idx < 0 or idx >= n:
                continue

            bucket_ms = int(idx * self._cfg.coarse_interval_s * 1000.0)
            if bucket_ms in self._coarse:
                # Keep searching.
                continue
            return idx

        # If none found in this cycle, we might be complete.
        if len(self._coarse) >= n:
            self._coarse_done = True
        return None

    def _ensure_container(self) -> bool:
        if not self._path:
            return False
        if self._container is not None and self._vstream is not None:
            return True
        try:
            self._container = av.open(self._path)
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
            if self._vstream is None:
                raise RuntimeError("No video stream")
            if self._vstream.time_base is not None:
                self._video_tb = float(self._vstream.time_base)
            return True
        except Exception as e:
            self.error.emit(str(e))
            self._container = None
            self._vstream = None
            return False

    @Slot()
    def _on_tick(self) -> None:
        if not self._running:
            return
        if not self._path:
            return

        if not self._ensure_container():
            return

        # 1) Serve fine request first (best UX).
        if self._pending_fine_bucket_ms is not None:
            bucket_ms = int(self._pending_fine_bucket_ms)
            req_id = int(self._pending_fine_req_id)
            # Clear pending so repeated ticks don't redo if decode is slow.
            self._pending_fine_bucket_ms = None
            img, pts = self._decode_near_time(
                float(bucket_ms) / 1000.0,
                any_frame=True,
                max_frames=180,
            )
            if img is not None and req_id == self._pending_fine_req_id:
                self._fine_lru[bucket_ms] = (img, float(pts))
                self._fine_lru.move_to_end(bucket_ms)
                while len(self._fine_lru) > int(self._cfg.max_fine_cache):
                    self._fine_lru.popitem(last=False)
                self.fine_ready.emit(bucket_ms, img, float(pts))

        # 2) Build coarse incrementally.
        if self._coarse_total <= 0:
            return

        # If there was recent fine activity, don't do coarse work.
        try:
            if float(time.monotonic()) < float(self._fine_activity_until_wall):
                return
        except Exception:
            pass

        per_tick = int(max(1, self._cfg.coarse_per_tick))
        done_before = len(self._coarse)

        for _ in range(per_tick):
            idx = self._next_coarse_index()
            if idx is None:
                break

            t = float(idx) * float(self._cfg.coarse_interval_s)
            bucket_ms = int(t * 1000.0)

            img, _pts = self._decode_near_time(
                float(t),
                any_frame=False,
                max_frames=90,
            )
            if img is None:
                continue
            self._coarse[bucket_ms] = img
            self.coarse_ready.emit(bucket_ms, img)

        try:
            if len(self._coarse) != done_before:
                self.coarse_progress.emit(len(self._coarse), int(self._coarse_total))
        except Exception:
            pass

    def _decode_near_time(self, time_s: float, *, any_frame: bool, max_frames: int) -> tuple[Optional[QImage], float]:
        if self._container is None or self._vstream is None:
            return None, 0.0

        target = float(max(0.0, time_s))
        try:
            # Seek near target.
            # any_frame=True is usually faster for interactive preview because it
            # can seek closer than keyframe-only, reducing decode work.
            self._container.seek(int(target * 1_000_000), any_frame=bool(any_frame), backward=True)

            chosen = None
            chosen_pts = 0.0
            last = None
            last_pts = 0.0

            # Bound decode effort.
            max_frames = int(max(1, max_frames))
            decoded = 0
            for packet in self._container.demux((self._vstream,)):
                for frame in packet.decode():
                    if not isinstance(frame, av.video.frame.VideoFrame):
                        continue
                    decoded += 1

                    pts_s = 0.0
                    if frame.pts is not None:
                        if frame.time_base is not None:
                            pts_s = float(frame.pts * frame.time_base)
                        elif self._video_tb:
                            pts_s = float(frame.pts) * float(self._video_tb)

                    last = frame
                    last_pts = pts_s

                    if pts_s >= target:
                        chosen = frame
                        chosen_pts = pts_s
                        break

                    if decoded >= max_frames:
                        break

                if chosen is not None or decoded >= max_frames:
                    break

            if chosen is None:
                chosen = last
                chosen_pts = last_pts

            if chosen is None:
                return None, 0.0

            rgb = chosen.to_rgb()
            plane0 = rgb.planes[0]
            img = QImage(bytes(plane0), rgb.width, rgb.height, int(plane0.line_size), QImage.Format.Format_RGB888).copy()
            img = img.scaled(
                int(self._cfg.thumb_w),
                int(self._cfg.thumb_h),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            log_event(
                "thumb",
                f"thumb_decode target={target:.3f}s pts={chosen_pts:.3f}s delta={(chosen_pts - target):+.3f}s",
                throttle_key="thumb_decode",
                throttle_seconds=0.35,
            )
            return img, float(chosen_pts)

        except av.error.FFmpegError as e:
            log_event("thumb", f"decode ffmpeg err: {e}", throttle_key="fferr", throttle_seconds=1.0)
            return None, 0.0
        except Exception as e:
            log_event("thumb", f"decode err: {e}", throttle_key="err", throttle_seconds=1.0)
            return None, 0.0
