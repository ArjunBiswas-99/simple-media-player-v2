from __future__ import annotations

import queue
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar


T = TypeVar("T")


class BoundedQueue(Generic[T]):
    """Thread-safe bounded queue with drop-oldest policy."""

    def __init__(self, maxsize: int) -> None:
        self._q: queue.Queue[T] = queue.Queue(maxsize=maxsize)

    def put_drop_oldest(self, item: T) -> None:
        try:
            self._q.put_nowait(item)
        except queue.Full:
            try:
                _ = self._q.get_nowait()
            except queue.Empty:
                pass
            try:
                self._q.put_nowait(item)
            except queue.Full:
                pass

    def get_nowait(self) -> Optional[T]:
        try:
            return self._q.get_nowait()
        except queue.Empty:
            return None

    def clear(self) -> None:
        while True:
            try:
                self._q.get_nowait()
            except queue.Empty:
                break

    def qsize(self) -> int:
        return self._q.qsize()


@dataclass(frozen=True)
class DecodedVideo:
    rgb_bytes: bytes
    width: int
    height: int
    bytes_per_line: int
    pts_seconds: float
