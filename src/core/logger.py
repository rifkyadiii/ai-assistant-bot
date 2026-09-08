"""Thread-safe activity logger and ring-buffer for VoiceBot."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any


class ActivityLogger:
    """Thread-safe in-memory ring buffer for activity and system logs."""

    def __init__(self, max_entries: int = 100) -> None:
        self._max_entries = max_entries
        self._lock = threading.Lock()
        self._entries: list[dict[str, Any]] = []

        # Standard Python logger
        self._logger = logging.getLogger("voicebot")
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S")
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def log(self, message: str, category: str = "SYS", level: str = "INFO") -> dict[str, Any]:
        """Record a log message with timestamp and category."""
        now = datetime.now(timezone.utc)
        entry = {
            "time": now.strftime("%H:%M:%S"),
            "iso": now.isoformat(),
            "category": category.upper(),
            "message": message,
            "level": level.upper(),
        }

        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries.pop(0)

        # Output to terminal
        log_method = getattr(self._logger, level.lower(), self._logger.info)
        log_method(f"[{category.upper()}] {message}")

        return entry

    def get_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return the most recent log entries."""
        with self._lock:
            return list(self._entries[-limit:])

    def clear(self) -> None:
        """Clear all logged entries."""
        with self._lock:
            self._entries.clear()


# Global singleton instance
activity_logger = ActivityLogger()
