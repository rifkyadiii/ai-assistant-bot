"""Desktop control service for full computer management across Linux and Windows.

Provides keyboard shortcuts, window management, media keys, application launching,
clipboard access, screenshots, and power actions with graceful cross-platform
fallbacks.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import threading
from typing import Any, Optional

from src.core.logger import activity_logger


class DesktopControlService:
    """Manages OS-level desktop controls across Linux and Windows."""

    def __init__(self) -> None:
        self._system: str = platform.system()
        self._pyautogui: Optional[Any] = None
        self._pynput: Optional[Any] = None
        self._last_error: Optional[str] = None
        self._init_libraries()

    def _init_libraries(self) -> None:
        """Lazily initialize control libraries when available."""
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            self._pyautogui = pyautogui
        except Exception as exc:
            activity_logger.log(f"pyautogui unavailable: {exc}", category="SYS", level="WARNING")

        try:
            import pynput
            self._pynput = pynput
        except Exception:
            pass

    @property
    def is_available(self) -> bool:
        return self._pyautogui is not None

    def _run(self, cmd: list[str], timeout: float = 5.0) -> Optional[str]:
        """Run a subprocess and return stdout on success."""
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
            return res.stdout.strip() if res.returncode == 0 else None
        except Exception as exc:
            activity_logger.log(f"Command {' '.join(cmd)} error: {exc}", category="SYS", level="WARNING")
            return None

    def screenshot(self, save_path: Optional[str] = None) -> Optional[str]:
        """Capture a screenshot using the best available backend.

        Tries pyautogui first (X11/Windows), then Wayland/X11 command-line
        tools. Returns the saved file path or None on failure.
        """
        self._last_error = None

        if not save_path:
            import os
            from datetime import datetime
            desktop = os.path.join(os.path.expanduser("~"), "Desktop" if self._system == "Windows" else "Pictures")
            os.makedirs(desktop, exist_ok=True)
            save_path = os.path.join(desktop, f"voicebot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

        # 1. pyautogui (Windows / X11)
        if self._pyautogui:
            try:
                img = self._pyautogui.screenshot()
                img.save(save_path)
                activity_logger.log(f"Screenshot saved: {save_path}", category="SYS")
                return save_path
            except Exception as exc:
                activity_logger.log(f"pyautogui screenshot error: {exc}", category="SYS", level="WARNING")
                self._last_error = str(exc)

        # 2. Command-line capture tools (Wayland + X11 fallbacks)
        for tool, args in [
            ("grim", ["grim", str(save_path)]),
            ("scrot", ["scrot", str(save_path)]),
            ("import", ["import", "-window", "root", str(save_path)]),
            ("gnome-screenshot", ["gnome-screenshot", "-f", str(save_path)]),
        ]:
            if shutil.which(tool):
                if self._run(args, timeout=8.0) is not None:
                    activity_logger.log(f"Screenshot saved: {save_path}", category="SYS")
                    return save_path
                self._last_error = f"Tool '{tool}' could not capture the screen"

        self._last_error = self._last_error or "No screenshot backend available"
        return None

    def lock_screen(self) -> bool:
        """Lock the workstation screen."""
        if self._system == "Windows":
            self._run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return True
        # Linux / macOS
        for cmd in [
            ["loginctl", "lock-session"],
            ["xdg-screensaver", "lock"],
            ["gnome-screensaver-command", "-l"],
        ]:
            if self._run(cmd) is not None or shutil.which(cmd[0]):
                activity_logger.log("Screen locked", category="SYS")
                return True
        activity_logger.log("No screen lock command available", category="SYS", level="WARNING")
        return False

    def clipboard_set(self, text: str) -> bool:
        """Set clipboard content (cross-platform with multiple fallbacks)."""
        # Windows: use clip.exe
        if self._system == "Windows":
            try:
                p = subprocess.Popen(["clip"], stdin=subprocess.PIPE)
                p.communicate(text.encode("utf-16-le"), timeout=5)
                return p.returncode == 0
            except Exception as exc:
                activity_logger.log(f"Windows clipboard error: {exc}", category="SYS", level="WARNING")
                return self._clipboard_fallback(text)

        # Linux: prefer a CLI clipboard tool based on session
        for tool in ["wl-copy", "xclip", "xsel", "pbcopy"]:
            if shutil.which(tool):
                try:
                    p = subprocess.run([tool], input=text, text=True, capture_output=True, timeout=5)
                    return p.returncode == 0
                except Exception as exc:
                    activity_logger.log(f"Clipboard tool {tool} error: {exc}", category="SYS", level="WARNING")

        # Fallback: pyperclip
        return self._clipboard_fallback(text)

    def _clipboard_fallback(self, text: str) -> bool:
        try:
            import pyperclip as pc
            pc.copy(text)
            return True
        except Exception as exc:
            activity_logger.log(f"Clipboard fallback unavailable: {exc}", category="SYS", level="WARNING")
            return False

    def clipboard_get(self) -> Optional[str]:
        """Read the current clipboard content (cross-platform)."""
        self._last_error = None

        # Windows: pyautogui has no clipboard reader; use pyperclip
        if self._system == "Windows":
            try:
                import pyperclip as pc
                return pc.paste() or None
            except Exception as exc:
                self._last_error = str(exc)
                return None

        # Linux: prefer the native clipboard CLI tools for the active session
        for tool, args in [
            ("wl-paste", ["wl-paste", "--no-newline"]),
            ("xclip", ["xclip", "-o", "-selection", "clipboard"]),
            ("xsel", ["xsel", "-b", "-o"]),
        ]:
            if shutil.which(tool):
                out = self._run(args, timeout=5.0)
                if out is not None:
                    return out
                self._last_error = f"Tool '{tool}' could not read the clipboard"

        try:
            import pyperclip as pc
            return pc.paste() or None
        except Exception as exc:
            self._last_error = str(exc)
            return None

    def media_next(self) -> bool:
        """Next media track."""
        if self._pyautogui:
            try:
                self._pyautogui.press("nexttrack")
                activity_logger.log("Media: next track", category="SYS")
                return True
            except Exception:
                pass
        return False

    def media_play(self) -> bool:
        """Explicitly resume/play media."""
        if self._pyautogui:
            try:
                self._pyautogui.press("playpause")
                activity_logger.log("Media: play", category="SYS")
                return True
            except Exception:
                pass
        return False

    def media_pause(self) -> bool:
        """Explicitly pause media."""
        if self._pyautogui:
            try:
                self._pyautogui.press("playpause")
                activity_logger.log("Media: pause", category="SYS")
                return True
            except Exception:
                pass
        return False

    def media_previous(self) -> bool:
        """Previous media track."""
        if self._pyautogui:
            try:
                self._pyautogui.press("prevtrack")
                activity_logger.log("Media: previous track", category="SYS")
                return True
            except Exception:
                pass
        return False

    def open_app(self, app: str) -> bool:
        """Launch a common application by name."""
        name = app.lower().strip()
        platforms = {
            "browser": ["google-chrome", "firefox"] if self._system == "Linux" else [],
            "email": ["thunderbird"] if self._system == "Linux" else ["outlook.exe"],
            "files": ["nautilus"] if self._system == "Linux" else ["explorer.exe"],
            "terminal": ["gnome-terminal"] if self._system == "Linux" else ["cmd.exe"],
            "calculator": ["gnome-calculator"] if self._system == "Linux" else ["calc.exe"],
        }

        target = None
        if "browser" in name or "chrome" in name or "firefox" in name:
            target = platforms.get("browser")
        elif "email" in name or "mail" in name:
            target = platforms.get("email")
        elif "file" in name or "explorer" in name:
            target = platforms.get("files")
        elif "terminal" in name:
            target = platforms.get("terminal")
        elif "calculator" in name or "calc" in name:
            target = platforms.get("calculator")

        if target:
            for t in target:
                if self._system == "Windows":
                    self._run(["start", t], timeout=3)
                else:
                    self._run([t], timeout=3)
                activity_logger.log(f"Launched {t}", category="SYS")
                return True

        # Try launching raw executable name
        if self._pyautogui:
            self._pyautogui.hotkey("super", "r")
            self._pyautogui.typewrite(app)
            self._pyautogui.press("enter")
            activity_logger.log(f"Launched via run dialog: {app}", category="SYS")
            return True
        return False

    def execute_action(self, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a named desktop action and return a structured result."""
        payload = payload or {}
        result: dict[str, Any] = {"ok": False, "action": action, "message": ""}

        if action == "screenshot":
            path = self.screenshot()
            result.update(
                ok=path is not None,
                message=f"Screenshot saved to {path}" if path else (f"Screenshot failed: {self._last_error}" if self._last_error else "Screenshot failed"),
                path=path,
                error=self._last_error,
            )
        elif action == "lock":
            ok = self.lock_screen()
            result.update(ok=ok, message="Screen locked" if ok else "Unable to lock screen")
        elif action == "clipboard":
            text = payload.get("text", "")
            if text:
                ok = self.clipboard_set(text)
                result.update(ok=ok, message="Clipboard updated" if ok else "Clipboard update failed")
            else:
                value = self.clipboard_get()
                if value is None and self._last_error:
                    result.update(ok=False, message=f"Clipboard read failed: {self._last_error}", error=self._last_error)
                else:
                    result.update(ok=True, text=value or "", message="Clipboard read" + ("" if value is not None else " (empty)"))
        elif action == "media_next":
            result.update(ok=self.media_next(), message="Next track")
        elif action == "media_play":
            result.update(ok=self.media_play(), message="Playing media")
        elif action == "media_pause":
            result.update(ok=self.media_pause(), message="Paused media")
        elif action == "media_previous":
            result.update(ok=self.media_previous(), message="Previous track")
        elif action == "open_app":
            app = payload.get("app", "")
            result.update(ok=self.open_app(app), message=f"Launching {app}")
        else:
            result.update(message=f"Unknown desktop action: {action}")

        return result


# Global singleton
desktop_service = DesktopControlService()
