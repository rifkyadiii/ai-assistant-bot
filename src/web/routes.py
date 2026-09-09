"""Modular Flask routes and REST API endpoints for VoiceBot."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    render_template,
    request,
    send_file,
    send_from_directory,
)

from config.settings import (
    BASE_DIR,
    COMMANDS,
    SERVER_PORT,
    STATUS_POLL_INTERVAL,
    LOGS_POLL_INTERVAL,
    TTS_ENABLED,
    TTS_VOICE,
    TTS_RATE,
    TTS_VOLUME,
    WAKE_PHRASE,
)
from src.core.logger import activity_logger
from src.services.desktop_service import desktop_service
from src.services.search_service import search_service
from src.services.system_service import system_service
from src.services.tts_service import tts_service
from src.services.vision_service import vision_service
from src.services.voice_service import voice_service
from src.web.camera_stream import camera_manager

web_bp = Blueprint("web", __name__)


def _parse_level(key: str = "level") -> Optional[int]:
    """Parse integer percentage (0-100) from JSON payload."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    val = data.get(key)
    if isinstance(val, bool) or val is None:
        return None
    try:
        level = int(val)
        return level if 0 <= level <= 100 else None
    except (ValueError, TypeError):
        return None


# ==========================================
# Frontend & PWA Routes
# ==========================================

@web_bp.route("/")
def index():
    """Render the modern Tailwind PWA dashboard."""
    return render_template("index.html", commands=COMMANDS)


@web_bp.route("/manifest.json")
def pwa_manifest():
    """Serve PWA Web App Manifest."""
    static_dir = BASE_DIR / "static"
    return send_from_directory(static_dir, "manifest.json", mimetype="application/manifest+json")


@web_bp.route("/sw.js")
def service_worker():
    """Serve PWA Service Worker."""
    static_dir = BASE_DIR / "static"
    response = send_from_directory(static_dir, "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


@web_bp.route("/video_feed")
def video_feed():
    """Stream MJPEG video feed from webcam with hand tracking HUD."""
    return Response(
        camera_manager.generate_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


# ==========================================
# System Telemetry & Status API
# ==========================================

@web_bp.route("/api/config", methods=["GET"])
def api_config():
    """Return safe, non-secret frontend configuration."""
    return jsonify({
        "ok": True,
        "wake_phrase": WAKE_PHRASE,
        "tts_enabled": TTS_ENABLED,
        "tts_voice": TTS_VOICE,
        "tts_rate": TTS_RATE,
        "tts_volume": TTS_VOLUME,
        "poll_status_interval": STATUS_POLL_INTERVAL,
        "poll_logs_interval": LOGS_POLL_INTERVAL,
        "port": SERVER_PORT,
    })


@web_bp.route("/api/gemini/health", methods=["GET"])
def api_gemini_health():
    """Report Gemini configuration status for diagnostics (no secrets)."""
    return jsonify({
        "ok": True,
        "configured": search_service.is_configured,
        "model": search_service._configured_model,
        "supported_models": list(search_service.SUPPORTED_MODELS),
    })


@web_bp.route("/api/status", methods=["GET"])
def api_status():
    """Return consolidated status across all hardware and services."""
    sys_status = system_service.get_status()
    telemetry = camera_manager.telemetry
    return jsonify({
        "ok": True,
        "volume": sys_status["volume"],
        "muted": sys_status["muted"],
        "brightness": sys_status["brightness"],
        "volume_backend": sys_status["volume_backend"],
        "brightness_backend": sys_status["brightness_backend"],
        "camera_active": camera_manager.is_running,
        "cursor_enabled": vision_service.cursor_control_enabled,
        "cursor_available": vision_service.pyautogui_available,
        "voice_listening": voice_service.is_listening,
        "mic_available": voice_service.is_mic_available,
        "mic_backend": voice_service.backend,
        "gemini_configured": search_service.is_configured,
        "gesture_telemetry": telemetry,
    })


# ==========================================
# Volume API
# ==========================================

@web_bp.route("/api/volume", methods=["POST"])
def api_volume():
    """Set absolute volume level."""
    level = _parse_level("level")
    if level is None:
        return jsonify({"ok": False, "error": "Level must be an integer between 0 and 100"}), 400

    system_service.set_volume(level)
    return jsonify({
        "ok": True,
        "volume": level,
        "muted": system_service.is_muted(),
    })


@web_bp.route("/api/volume/up", methods=["POST"])
def api_volume_up():
    """Increase volume by step."""
    system_service.volume_up()
    return jsonify({
        "ok": True,
        "volume": system_service.get_volume(),
        "muted": system_service.is_muted(),
    })


@web_bp.route("/api/volume/down", methods=["POST"])
def api_volume_down():
    """Decrease volume by step."""
    system_service.volume_down()
    return jsonify({
        "ok": True,
        "volume": system_service.get_volume(),
        "muted": system_service.is_muted(),
    })


@web_bp.route("/api/mute", methods=["POST"])
def api_mute():
    """Mute system audio."""
    system_service.mute()
    return jsonify({"ok": True, "muted": True})


@web_bp.route("/api/unmute", methods=["POST"])
def api_unmute():
    """Unmute system audio."""
    system_service.unmute()
    return jsonify({"ok": True, "muted": False})


@web_bp.route("/api/volume/toggle-mute", methods=["POST"])
def api_toggle_mute():
    """Toggle mute state."""
    system_service.toggle_mute()
    return jsonify({"ok": True, "muted": system_service.is_muted()})


# ==========================================
# Brightness API
# ==========================================

@web_bp.route("/api/brightness", methods=["POST"])
def api_brightness():
    """Set absolute brightness level."""
    level = _parse_level("level")
    if level is None:
        return jsonify({"ok": False, "error": "Level must be an integer between 0 and 100"}), 400

    system_service.set_brightness(level)
    return jsonify({"ok": True, "brightness": level})


@web_bp.route("/api/brightness/up", methods=["POST"])
def api_brightness_up():
    """Increase brightness by step."""
    system_service.brightness_up()
    return jsonify({"ok": True, "brightness": system_service.get_brightness()})


@web_bp.route("/api/brightness/down", methods=["POST"])
def api_brightness_down():
    """Decrease brightness by step."""
    system_service.brightness_down()
    return jsonify({"ok": True, "brightness": system_service.get_brightness()})


# ==========================================
# Voice Control API
# ==========================================

@web_bp.route("/api/voice/command", methods=["POST"])
def api_voice_command():
    """Execute a voice command transcribed from browser or client."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "No voice text provided"}), 400

    # Handle cursor toggle command directly if matched
    result = voice_service.process_text(text)
    if result.get("action") == "toggle_cursor":
        enabled = vision_service.toggle_cursor_control()
        result["message"] = f"Desktop cursor control {'enabled' if enabled else 'disabled'}"
        result["speech"] = result["message"]
        result["cursor_enabled"] = enabled

    return jsonify(result)


@web_bp.route("/api/voice/listen", methods=["POST"])
def api_voice_listen_once():
    """Trigger a single phrase listening cycle on the server microphone."""
    if not voice_service.is_mic_available:
        return jsonify({
            "ok": False,
            "error": "Local microphone unavailable on host. Use browser speech input.",
        }), 400

    text = voice_service.listen_once()
    if not text:
        return jsonify({
            "ok": False,
            "error": "No speech recognized or silence timed out",
        })

    result = voice_service.process_text(text)
    return jsonify(result)


@web_bp.route("/api/voice/toggle", methods=["POST"])
def api_voice_toggle():
    """Toggle continuous background voice listening on server."""
    is_active = voice_service.toggle_listening()
    return jsonify({"ok": True, "listening": is_active})


@web_bp.route("/api/tts", methods=["POST"])
def api_tts():
    """Synthesize text to speech using edge-tts and return an MP3 audio file."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "No text provided"}), 400
    if not TTS_ENABLED or not tts_service.is_available:
        return jsonify({"ok": False, "error": "Server TTS unavailable"}), 503

    audio_path = tts_service.generate_audio(text)
    if not audio_path:
        return jsonify({"ok": False, "error": "TTS synthesis failed"}), 500

    try:
        return send_file(
            audio_path,
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name="voicebot_tts.mp3",
        )
    finally:
        # Clean up the temp file after sending (best-effort)
        try:
            audio_path.unlink(missing_ok=True)
        except Exception:
            pass


# ==========================================
# Camera & Vision API
# ==========================================

@web_bp.route("/api/camera/toggle", methods=["POST"])
def api_camera_toggle():
    """Toggle camera capture on/off."""
    active = camera_manager.toggle()
    return jsonify({"ok": True, "camera_active": active})


@web_bp.route("/api/camera/cursor_control", methods=["POST"])
def api_cursor_control():
    """Toggle or explicitly set cursor control enabled state."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    if "enabled" in data:
        vision_service.cursor_control_enabled = bool(data["enabled"])
    else:
        vision_service.toggle_cursor_control()

    return jsonify({
        "ok": True,
        "cursor_enabled": vision_service.cursor_control_enabled,
        "cursor_available": vision_service.pyautogui_available,
    })


# ==========================================
# Gemini Search & Assistant API
# ==========================================

@web_bp.route("/api/search", methods=["POST"])
def api_search():
    """Perform Gemini search / question answering."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"ok": False, "error": "Query cannot be empty"}), 400

    result = search_service.search_and_respond(query)
    return jsonify({"ok": True, "result": result})


@web_bp.route("/api/ask", methods=["POST"])
def api_ask():
    """Alias for direct Gemini inquiry."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"ok": False, "error": "Question cannot be empty"}), 400

    result = search_service.search_and_respond(question)
    return jsonify({"ok": True, "response": result["response"], "result": result})


@web_bp.route("/api/search/history", methods=["GET"])
def api_search_history():
    """Get search history."""
    return jsonify({"ok": True, "results": search_service.get_history()})


@web_bp.route("/api/search/clear", methods=["POST"])
def api_search_clear():
    """Clear search history."""
    search_service.clear_history()
    return jsonify({"ok": True})


# ==========================================
# Desktop Control API
# ==========================================

@web_bp.route("/api/desktop/action", methods=["POST"])
def api_desktop_action():
    """Execute a desktop control action (screenshot, lock, media, apps, etc.)."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    action = data.get("action", "")
    payload = data.get("payload", {})

    if not action:
        return jsonify({"ok": False, "error": "No action specified"}), 400

    result = desktop_service.execute_action(action, payload)
    return jsonify(result)


@web_bp.route("/api/desktop/screenshot", methods=["POST"])
def api_desktop_screenshot():
    """Capture a screenshot."""
    result = desktop_service.execute_action("screenshot")
    return jsonify(result)


@web_bp.route("/api/desktop/keyboard", methods=["POST"])
def api_desktop_keyboard():
    """Send a keyboard hotkey or type text."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    keys = data.get("hotkey") or data.get("keys")
    text = data.get("type")

    if keys and desktop_service._pyautogui:
        try:
            desktop_service._pyautogui.hotkey(*keys)
            activity_logger.log(f"Keyboard hotkey sent: {'+'.join(keys)}", category="SYS")
            return jsonify({"ok": True, "message": f"Hotkey {'+'.join(keys)} sent"})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    if text and desktop_service._pyautogui:
        try:
            desktop_service._pyautogui.typewrite(text)
            activity_logger.log(f"Typed text({len(text)} chars)", category="SYS")
            return jsonify({"ok": True, "message": "Text typed"})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": False, "error": "Provide 'hotkey' or 'type' payload"}), 400


@web_bp.route("/api/desktop/clipboard", methods=["POST"])
def api_desktop_clipboard():
    """Set clipboard content."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    text = data.get("text", "")
    ok = desktop_service.clipboard_set(text)
    return jsonify({"ok": ok, "message": "Clipboard updated" if ok else "Clipboard update failed"})


@web_bp.route("/api/desktop/clipboard", methods=["GET"])
def api_desktop_clipboard_get():
    """Read current clipboard content."""
    value = desktop_service.clipboard_get()
    if value is None and desktop_service._last_error:
        return jsonify({"ok": False, "error": desktop_service._last_error}), 500
    return jsonify({"ok": True, "text": value or ""})


@web_bp.route("/api/desktop/open", methods=["POST"])
def api_desktop_open():
    """Open a common application."""
    data: dict[str, Any] = request.get_json(silent=True) or {}
    app = data.get("app", "")
    result = desktop_service.execute_action("open_app", {"app": app})
    return jsonify(result)


# ==========================================
# Activity Logs API
# ==========================================

@web_bp.route("/api/logs", methods=["GET"])
def api_logs():
    """Return recent activity entries."""
    limit = request.args.get("limit", 50, type=int)
    entries = activity_logger.get_entries(limit=limit)
    # Format legacy string representation for backward compat if needed
    legacy_strings = [f"[{e['time']}] [{e['category']}] {e['message']}" for e in entries]
    return jsonify({
        "ok": True,
        "entries": entries,
        "logs": legacy_strings,
    })


@web_bp.route("/api/logs/clear", methods=["POST"])
def api_logs_clear():
    """Clear activity logs."""
    activity_logger.clear()
    activity_logger.log("Activity log cleared", category="SYS")
    return jsonify({"ok": True})
