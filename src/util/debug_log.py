from __future__ import annotations

import os
from pathlib import Path
import threading
import time
from typing import Optional


_ENABLED = os.environ.get("DEBUG_SYNC", "0") == "1"
_TERM_ENABLED = os.environ.get("DEBUG_TERMINAL", "1") == "1"
_MAX_BYTES = int(os.environ.get("DEBUG_SYNC_MAX_BYTES", "3000000"))
# Anchor logs/flag to repository root (not process cwd), so Run/Debug in VS Code
# still finds the flag and writes logs consistently.
_ROOT = Path(__file__).resolve().parents[2]
_LOG_PATH = str(_ROOT / "runlog.txt")
_FLAG_FILE = str(_ROOT / "debug_sync.on")

_lock = threading.Lock()
_last_by_key: dict[str, float] = {}
_initialized = False


def _init_if_needed() -> None:
    global _initialized
    if _initialized or not is_enabled():
        return
    with _lock:
        if _initialized:
            return
        # Fresh per-run log by default.
        with open(_LOG_PATH, "w", encoding="utf-8") as f:
            f.write("=== DEBUG_SYNC LOG START ===\n")
        _initialized = True


def is_enabled() -> bool:
    return _ENABLED or os.path.exists(_FLAG_FILE)


def log_event(
    component: str,
    message: str,
    *,
    throttle_key: Optional[str] = None,
    throttle_seconds: float = 0.0,
) -> None:
    file_enabled = is_enabled()
    if not file_enabled and not _TERM_ENABLED:
        return
    if file_enabled:
        _init_if_needed()

    now = time.time()
    if throttle_key:
        key = f"{component}:{throttle_key}"
        prev = _last_by_key.get(key, 0.0)
        if (now - prev) < throttle_seconds:
            return
        _last_by_key[key] = now

    line = f"{time.strftime('%H:%M:%S')} [{component}] {message}\n"

    if _TERM_ENABLED:
        try:
            print(line, end="", flush=True)
        except Exception:
            pass

    if file_enabled:
        with _lock:
            try:
                if os.path.exists(_LOG_PATH) and os.path.getsize(_LOG_PATH) > _MAX_BYTES:
                    return
                with open(_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception:
                # Logging must never break playback.
                pass
