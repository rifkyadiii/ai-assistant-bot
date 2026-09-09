"""Tests for DesktopControlService screenshot and clipboard backends."""

import shutil

import pytest
from src.services.desktop_service import DesktopControlService


@pytest.fixture
def desktop_service():
    return DesktopControlService()


def test_screenshot_falls_back_to_cli_tool(desktop_service, monkeypatch, tmp_path):
    monkeypatch.setattr(desktop_service, "_pyautogui", None)
    monkeypatch.setattr("shutil.which", lambda tool: tool == "grim")
    monkeypatch.setattr(desktop_service, "_run", lambda args, timeout=5: "ok")

    target = tmp_path / "shot.png"
    result = desktop_service.screenshot(str(target))
    assert result == str(target)


def test_screenshot_best_tool_preferred_over_fallback(desktop_service, monkeypatch, tmp_path):
    monkeypatch.setattr(desktop_service, "_pyautogui", None)
    calls = []
    real_which = shutil.which

    def fake_which(tool):
        return tool in {"grim", "scrot"}

    monkeypatch.setattr("shutil.which", fake_which)

    def fake_run(args, timeout=5):
        calls.append(args[0])
        return None

    monkeypatch.setattr(desktop_service, "_run", fake_run)

    target = tmp_path / "shot.png"
    result = desktop_service.screenshot(str(target))
    assert result is None
    assert calls == ["grim", "scrot"]
    assert desktop_service._last_error

    monkeypatch.setattr("shutil.which", real_which)


def test_screenshot_failure_surfaces_error(desktop_service, monkeypatch, tmp_path):
    monkeypatch.setattr(desktop_service, "_pyautogui", None)
    monkeypatch.setattr("shutil.which", lambda tool: False)

    target = tmp_path / "shot.png"
    assert desktop_service.screenshot(str(target)) is None
    assert desktop_service._last_error is not None


def test_execute_action_screenshot_reports_error(desktop_service, monkeypatch, tmp_path):
    monkeypatch.setattr(desktop_service, "_pyautogui", None)
    monkeypatch.setattr("shutil.which", lambda tool: False)

    result = desktop_service.execute_action("screenshot", {})
    assert result["ok"] is False
    assert result["path"] is None
    assert "Screenshot failed" in result["message"]


def test_clipboard_get_reads_from_native_tool(desktop_service, monkeypatch):
    monkeypatch.setattr(desktop_service, "_system", "Linux")
    monkeypatch.setattr("shutil.which", lambda tool: tool == "wl-paste")
    monkeypatch.setattr(desktop_service, "_run", lambda args, timeout=5: "clip content")

    assert desktop_service.clipboard_get() == "clip content"


def test_clipboard_get_empty_is_valid(desktop_service, monkeypatch):
    monkeypatch.setattr(desktop_service, "_system", "Linux")
    monkeypatch.setattr("shutil.which", lambda tool: tool == "xclip")
    monkeypatch.setattr(desktop_service, "_run", lambda args, timeout=5: "")

    assert desktop_service.clipboard_get() == ""


def test_execute_action_clipboard_read_text(desktop_service, monkeypatch):
    monkeypatch.setattr(desktop_service, "clipboard_get", lambda: "clip content")
    result = desktop_service.execute_action("clipboard", {})
    assert result["ok"] is True
    assert result["text"] == "clip content"


def test_execute_action_clipboard_set(desktop_service, monkeypatch):
    monkeypatch.setattr(desktop_service, "clipboard_set", lambda text: True)
    result = desktop_service.execute_action("clipboard", {"text": "new value"})
    assert result["ok"] is True
    assert result["message"] == "Clipboard updated"