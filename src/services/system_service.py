"""Robust cross-platform system control service for Volume and Brightness."""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
from typing import Any

from config.settings import VOLUME_STEP, BRIGHTNESS_STEP
from src.core.logger import activity_logger


class SystemService:
    """Controls audio volume, mute status, and display brightness across platforms."""

    def __init__(self) -> None:
        self._system: str = platform.system()
        self._volume_backend: str = self._detect_volume_backend()
        self._brightness_backend: str = self._detect_brightness_backend()

        # Cached fallbacks in case system commands fail or hardware lacks support
        self._cached_volume: int = 50
        self._cached_muted: bool = False
        self._cached_brightness: int = 50

        # Initialize current values
        self.refresh()
        activity_logger.log(
            f"SystemController initialized (Vol: {self._volume_backend}, Bri: {self._brightness_backend})",
            category="SYS",
        )

    @property
    def volume_backend(self) -> str:
        return self._volume_backend

    @property
    def brightness_backend(self) -> str:
        return self._brightness_backend

    def _detect_volume_backend(self) -> str:
        """Detect available volume backend."""
        if self._system == "Windows":
            return "windows"
        if self._system == "Darwin":
            return "osascript"
        # Linux / Unix
        for cmd in ["pactl", "amixer"]:
            if shutil.which(cmd):
                return cmd
        return "mock"

    def _detect_brightness_backend(self) -> str:
        """Detect available brightness backend."""
        if self._system == "Windows":
            return "windows"
        if self._system == "Darwin":
            return "osascript"
        # Linux / Unix
        for cmd in ["brightnessctl", "light", "xbacklight"]:
            if shutil.which(cmd):
                return cmd
        # Try screen_brightness_control python package
        try:
            import screen_brightness_control as sbc
            if sbc.get_brightness():
                return "sbc"
        except Exception:
            pass
        return "mock"

    def refresh(self) -> None:
        """Query hardware and refresh cached states."""
        self._cached_volume = self._query_volume()
        self._cached_muted = self._query_muted()
        self._cached_brightness = self._query_brightness()

    # ==========================================
    # Volume Controls
    # ==========================================

    def _query_volume(self) -> int:
        """Query hardware for current volume (0-100)."""
        if self._volume_backend == "pactl":
            try:
                res = subprocess.run(
                    ["pactl", "get-sink-volume", "@DEFAULT_SINK@"],
                    capture_output=True, text=True, timeout=3, check=False,
                )
                if res.returncode == 0 and res.stdout:
                    # Parse percentage like '30%'
                    matches = re.findall(r"(\d+)%", res.stdout)
                    if matches:
                        return int(matches[0])
            except Exception as exc:
                activity_logger.log(f"pactl get-volume error: {exc}", category="SYS", level="WARNING")

        elif self._volume_backend == "amixer":
            try:
                res = subprocess.run(
                    ["amixer", "get", "Master"],
                    capture_output=True, text=True, timeout=3, check=False,
                )
                if res.returncode == 0 and res.stdout:
                    matches = re.findall(r"\[(\d+)%\]", res.stdout)
                    if matches:
                        return int(matches[0])
            except Exception as exc:
                activity_logger.log(f"amixer get-volume error: {exc}", category="SYS", level="WARNING")

        elif self._volume_backend == "osascript":
            try:
                res = subprocess.run(
                    ["osascript", "-e", "output volume of (get volume settings)"],
                    capture_output=True, text=True, timeout=3, check=False,
                )
                if res.returncode == 0 and res.stdout.strip().isdigit():
                    return int(res.stdout.strip())
            except Exception:
                pass

        return self._cached_volume

    def _query_muted(self) -> bool:
        """Query hardware for mute status."""
        if self._volume_backend == "pactl":
            try:
                res = subprocess.run(
                    ["pactl", "get-sink-mute", "@DEFAULT_SINK@"],
                    capture_output=True, text=True, timeout=3, check=False,
                )
                if res.returncode == 0:
                    return "yes" in res.stdout.lower()
            except Exception:
                pass

        elif self._volume_backend == "amixer":
            try:
                res = subprocess.run(
                    ["amixer", "get", "Master"],
                    capture_output=True, text=True, timeout=3, check=False,
                )
                if res.returncode == 0:
                    return "[off]" in res.stdout.lower()
            except Exception:
                pass

        elif self._volume_backend == "osascript":
            try:
                res = subprocess.run(
                    ["osascript", "-e", "output muted of (get volume settings)"],
                    capture_output=True, text=True, timeout=3, check=False,
                )
                if res.returncode == 0:
                    return "true" in res.stdout.lower()
            except Exception:
                pass

        return self._cached_muted

    def get_volume(self) -> int:
        """Get current volume (0-100)."""
        self._cached_volume = self._query_volume()
        return self._cached_volume

    def is_muted(self) -> bool:
        """Get current mute state."""
        self._cached_muted = self._query_muted()
        return self._cached_muted

    def set_volume(self, level: int) -> bool:
        """Set volume to a specific percentage (0-100)."""
        clamped = max(0, min(100, int(level)))
        success = False

        if self._volume_backend == "pactl":
            try:
                res = subprocess.run(
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{clamped}%"],
                    timeout=3, check=False,
                )
                success = (res.returncode == 0)
                # Auto unmute if volume is raised above 0
                if clamped > 0 and self._cached_muted:
                    self.unmute()
            except Exception as exc:
                activity_logger.log(f"Failed setting volume via pactl: {exc}", category="SYS", level="WARNING")

        elif self._volume_backend == "amixer":
            try:
                res = subprocess.run(
                    ["amixer", "set", "Master", f"{clamped}%"],
                    timeout=3, check=False,
                )
                success = (res.returncode == 0)
            except Exception as exc:
                activity_logger.log(f"Failed setting volume via amixer: {exc}", category="SYS", level="WARNING")

        elif self._volume_backend == "osascript":
            try:
                res = subprocess.run(
                    ["osascript", "-e", f"set volume output volume {clamped}"],
                    timeout=3, check=False,
                )
                success = (res.returncode == 0)
            except Exception:
                pass

        else:
            # Fallback mock mode
            success = True

        self._cached_volume = clamped
        activity_logger.log(f"Volume adjusted to {clamped}%", category="SYS")
        return success

    def volume_up(self, step: int = VOLUME_STEP) -> bool:
        """Increase volume by step amount."""
        current = self.get_volume()
        return self.set_volume(current + step)

    def volume_down(self, step: int = VOLUME_STEP) -> bool:
        """Decrease volume by step amount."""
        current = self.get_volume()
        return self.set_volume(current - step)

    def mute(self) -> bool:
        """Mute system audio."""
        success = False
        if self._volume_backend == "pactl":
            try:
                res = subprocess.run(
                    ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"],
                    timeout=3, check=False,
                )
                success = (res.returncode == 0)
            except Exception:
                pass
        elif self._volume_backend == "amixer":
            try:
                res = subprocess.run(["amixer", "set", "Master", "mute"], timeout=3, check=False)
                success = (res.returncode == 0)
            except Exception:
                pass
        elif self._volume_backend == "osascript":
            try:
                res = subprocess.run(
                    ["osascript", "-e", "set volume output muted true"],
                    timeout=3, check=False,
                )
                success = (res.returncode == 0)
            except Exception:
                pass
        else:
            success = True

        self._cached_muted = True
        activity_logger.log("Audio muted", category="SYS")
        return success

    def unmute(self) -> bool:
        """Unmute system audio."""
        success = False
        if self._volume_backend == "pactl":
            try:
                res = subprocess.run(
                    ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"],
                    timeout=3, check=False,
                )
                success = (res.returncode == 0)
            except Exception:
                pass
        elif self._volume_backend == "amixer":
            try:
                res = subprocess.run(["amixer", "set", "Master", "unmute"], timeout=3, check=False)
                success = (res.returncode == 0)
            except Exception:
                pass
        elif self._volume_backend == "osascript":
            try:
                res = subprocess.run(
                    ["osascript", "-e", "set volume output muted false"],
                    timeout=3, check=False,
                )
                success = (res.returncode == 0)
            except Exception:
                pass
        else:
            success = True

        self._cached_muted = False
        activity_logger.log("Audio unmuted", category="SYS")
        return success

    def toggle_mute(self) -> bool:
        """Toggle mute state."""
        if self.is_muted():
            return self.unmute()
        return self.mute()

    # ==========================================
    # Brightness Controls
    # ==========================================

    def _query_brightness(self) -> int:
        """Query hardware for current brightness (0-100)."""
        if self._brightness_backend == "brightnessctl":
            try:
                get_res = subprocess.run(
                    ["brightnessctl", "get"],
                    capture_output=True, text=True, timeout=3, check=False,
                )
                max_res = subprocess.run(
                    ["brightnessctl", "max"],
                    capture_output=True, text=True, timeout=3, check=False,
                )
                if get_res.returncode == 0 and max_res.returncode == 0:
                    curr_val = int(get_res.stdout.strip())
                    max_val = int(max_res.stdout.strip())
                    if max_val > 0:
                        return int(round((curr_val / max_val) * 100))
            except Exception as exc:
                activity_logger.log(f"brightnessctl query error: {exc}", category="SYS", level="WARNING")

        elif self._brightness_backend == "light":
            try:
                res = subprocess.run(
                    ["light", "-G"],
                    capture_output=True, text=True, timeout=3, check=False,
                )
                if res.returncode == 0:
                    return int(round(float(res.stdout.strip())))
            except Exception:
                pass

        elif self._brightness_backend == "xbacklight":
            try:
                res = subprocess.run(
                    ["xbacklight", "-get"],
                    capture_output=True, text=True, timeout=3, check=False,
                )
                if res.returncode == 0:
                    return int(round(float(res.stdout.strip())))
            except Exception:
                pass

        elif self._brightness_backend == "sbc":
            try:
                import screen_brightness_control as sbc
                b = sbc.get_brightness()
                if b and isinstance(b, list):
                    return int(b[0])
            except Exception:
                pass

        return self._cached_brightness

    def get_brightness(self) -> int:
        """Get current screen brightness (0-100)."""
        self._cached_brightness = self._query_brightness()
        return self._cached_brightness

    def set_brightness(self, level: int) -> bool:
        """Set screen brightness (0-100)."""
        clamped = max(0, min(100, int(level)))
        success = False

        if self._brightness_backend == "brightnessctl":
            try:
                res = subprocess.run(
                    ["brightnessctl", "set", f"{clamped}%"],
                    timeout=3, check=False,
                )
                success = (res.returncode == 0)
            except Exception as exc:
                activity_logger.log(f"brightnessctl set error: {exc}", category="SYS", level="WARNING")

        elif self._brightness_backend == "light":
            try:
                res = subprocess.run(
                    ["light", "-S", str(clamped)],
                    timeout=3, check=False,
                )
                success = (res.returncode == 0)
            except Exception:
                pass

        elif self._brightness_backend == "xbacklight":
            try:
                res = subprocess.run(
                    ["xbacklight", "-set", str(clamped)],
                    timeout=3, check=False,
                )
                success = (res.returncode == 0)
            except Exception:
                pass

        elif self._brightness_backend == "sbc":
            try:
                import screen_brightness_control as sbc
                sbc.set_brightness(clamped)
                success = True
            except Exception:
                pass
        else:
            success = True

        self._cached_brightness = clamped
        activity_logger.log(f"Brightness adjusted to {clamped}%", category="SYS")
        return success

    def brightness_up(self, step: int = BRIGHTNESS_STEP) -> bool:
        """Increase screen brightness by step."""
        current = self.get_brightness()
        return self.set_brightness(current + step)

    def brightness_down(self, step: int = BRIGHTNESS_STEP) -> bool:
        """Decrease screen brightness by step."""
        current = self.get_brightness()
        return self.set_brightness(current - step)

    def get_status(self) -> dict[str, Any]:
        """Return full snapshot of audio and brightness status."""
        return {
            "volume": self.get_volume(),
            "muted": self.is_muted(),
            "brightness": self.get_brightness(),
            "volume_backend": self._volume_backend,
            "brightness_backend": self._brightness_backend,
        }


# Global singleton instance
system_service = SystemService()
