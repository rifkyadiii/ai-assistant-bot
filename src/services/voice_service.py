"""Voice recognition and natural language command parsing service."""

from __future__ import annotations

import re
import threading
from typing import Any, Callable, Optional

import numpy as np
import speech_recognition as sr

from config.settings import (
    COMMANDS,
    VOICE_LANGUAGE,
    VOICE_PHRASE_LIMIT,
    VOICE_TIMEOUT,
)
from src.core.logger import activity_logger
from src.services.desktop_service import desktop_service
from src.services.search_service import search_service
from src.services.system_service import system_service
from src.services.tts_service import tts_service


def _has_phrase(text: str, phrases: list[str]) -> bool:
    """Check if any phrase is present in text using word boundaries."""
    for p in phrases:
        pattern = r"\b" + re.escape(p) + r"\b"
        if re.search(pattern, text):
            return True
    return False


class VoiceService:
    """Handles voice transcription, semantic command parsing, and microphone listening."""

    def __init__(self) -> None:
        self._recognizer = sr.Recognizer()
        self._recognizer.energy_threshold = 300
        self._recognizer.dynamic_energy_threshold = True

        self._backend: str = "none"
        self._microphone: Optional[sr.Microphone] = None
        self._init_microphone()

        # Background listener state
        self._is_listening: bool = False
        self._stop_listener_event = threading.Event()
        self._listener_thread: Optional[threading.Thread] = None

        # Callbacks for UI updates on voice commands
        self._listeners: list[Callable[[dict[str, Any]], None]] = []

    def _init_microphone(self) -> None:
        """Attempt to initialize PyAudio or SoundDevice as audio source."""
        # Try PyAudio standard microphone
        try:
            mic = sr.Microphone()
            with mic as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
            self._microphone = mic
            self._backend = "pyaudio"
            activity_logger.log("Local microphone initialized via PyAudio", category="VOICE")
            return
        except Exception:
            pass

        # Try SoundDevice fallback
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            if devices:
                self._backend = "sounddevice"
                activity_logger.log("Local microphone initialized via SoundDevice", category="VOICE")
                return
        except Exception as exc:
            activity_logger.log(f"SoundDevice not available: {exc}", category="VOICE", level="WARNING")

        self._backend = "none"
        activity_logger.log("No local audio recording backend found (web voice still supported)", category="VOICE", level="INFO")

    @property
    def is_mic_available(self) -> bool:
        return self._backend != "none"

    @property
    def backend(self) -> str:
        return self._backend

    @property
    def is_listening(self) -> bool:
        return self._is_listening

    def add_listener(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback to be notified when a voice command executes."""
        self._listeners.append(callback)

    def _notify_listeners(self, result: dict[str, Any]) -> None:
        """Notify all registered listeners."""
        for cb in self._listeners:
            try:
                cb(result)
            except Exception as exc:
                activity_logger.log(f"Voice callback error: {exc}", category="VOICE", level="WARNING")

    # ==========================================
    # Voice Command Parsing & Execution
    # ==========================================

    def process_text(self, text: str) -> dict[str, Any]:
        """Parse text and execute the corresponding command.

        Returns a structured result containing action details and speech response.
        """
        raw = text.strip()
        cleaned = raw.lower()
        if not cleaned:
            return {
                "ok": False,
                "raw_text": raw,
                "command_type": "unknown",
                "action": "none",
                "message": "No voice input detected.",
                "speech": "I did not catch that.",
            }

        activity_logger.log(f"Voice command: \"{raw}\"", category="VOICE")

        # 1. Volume Set by Number (e.g. "volume 50", "set volume to 80%", "volume up to 80", "increase volume to 70 percent")
        vol_set_match = re.search(
            r"(?:set\s+|increase\s+|decrease\s+|raise\s+|lower\s+|turn\s+)?"
            r"volume\s+(?:up\s+|down\s+)?(?:to\s+|at\s+)?(\d{1,3})\s*(?:%|percent)?",
            cleaned,
        )
        if vol_set_match:
            val = int(vol_set_match.group(1))
            val = max(0, min(100, val))
            system_service.set_volume(val)
            msg = f"Volume set to {val}%"
            res = {
                "ok": True,
                "raw_text": raw,
                "command_type": "volume",
                "action": "set_volume",
                "message": msg,
                "speech": f"Volume set to {val} percent.",
                "value": val,
            }
            self._notify_listeners(res)
            return res

        # 2. Brightness Set by Number (e.g. "brightness 70", "set brightness to 90%", "brightness up to 80")
        bri_set_match = re.search(
            r"(?:set\s+|increase\s+|decrease\s+|raise\s+|lower\s+|turn\s+)?"
            r"brightness\s+(?:up\s+|down\s+)?(?:to\s+|at\s+)?(\d{1,3})\s*(?:%|percent)?",
            cleaned,
        )
        if bri_set_match:
            val = int(bri_set_match.group(1))
            val = max(0, min(100, val))
            system_service.set_brightness(val)
            msg = f"Brightness set to {val}%"
            res = {
                "ok": True,
                "raw_text": raw,
                "command_type": "brightness",
                "action": "set_brightness",
                "message": msg,
                "speech": f"Brightness set to {val} percent.",
                "value": val,
            }
            self._notify_listeners(res)
            return res

        # 3. Volume Up
        if _has_phrase(cleaned, COMMANDS["volume_up"]):
            system_service.volume_up()
            new_vol = system_service.get_volume()
            msg = f"Volume increased to {new_vol}%"
            res = {
                "ok": True,
                "raw_text": raw,
                "command_type": "volume",
                "action": "volume_up",
                "message": msg,
                "speech": f"Volume increased to {new_vol} percent.",
                "value": new_vol,
            }
            self._notify_listeners(res)
            return res

        # 4. Volume Down
        if _has_phrase(cleaned, COMMANDS["volume_down"]):
            system_service.volume_down()
            new_vol = system_service.get_volume()
            msg = f"Volume decreased to {new_vol}%"
            res = {
                "ok": True,
                "raw_text": raw,
                "command_type": "volume",
                "action": "volume_down",
                "message": msg,
                "speech": f"Volume decreased to {new_vol} percent.",
                "value": new_vol,
            }
            self._notify_listeners(res)
            return res

        # 5. Unmute (checked BEFORE mute to avoid substring matching!)
        if _has_phrase(cleaned, COMMANDS["unmute"]):
            system_service.unmute()
            res = {
                "ok": True,
                "raw_text": raw,
                "command_type": "volume",
                "action": "unmute",
                "message": "Audio unmuted",
                "speech": "Audio unmuted.",
            }
            self._notify_listeners(res)
            return res

        # 6. Mute
        if _has_phrase(cleaned, COMMANDS["mute"]):
            system_service.mute()
            res = {
                "ok": True,
                "raw_text": raw,
                "command_type": "volume",
                "action": "mute",
                "message": "Audio muted",
                "speech": "Audio muted.",
            }
            self._notify_listeners(res)
            return res

        # 7. Brightness Up
        if _has_phrase(cleaned, COMMANDS["brightness_up"]):
            system_service.brightness_up()
            new_bri = system_service.get_brightness()
            msg = f"Brightness increased to {new_bri}%"
            res = {
                "ok": True,
                "raw_text": raw,
                "command_type": "brightness",
                "action": "brightness_up",
                "message": msg,
                "speech": f"Brightness increased to {new_bri} percent.",
                "value": new_bri,
            }
            self._notify_listeners(res)
            return res

        # 8. Brightness Down
        if _has_phrase(cleaned, COMMANDS["brightness_down"]):
            system_service.brightness_down()
            new_bri = system_service.get_brightness()
            msg = f"Brightness decreased to {new_bri}%"
            res = {
                "ok": True,
                "raw_text": raw,
                "command_type": "brightness",
                "action": "brightness_down",
                "message": msg,
                "speech": f"Brightness decreased to {new_bri} percent.",
                "value": new_bri,
            }
            self._notify_listeners(res)
            return res

        # 9. Cursor Toggle
        if _has_phrase(cleaned, COMMANDS["cursor_toggle"]):
            res = {
                "ok": True,
                "raw_text": raw,
                "command_type": "cursor",
                "action": "toggle_cursor",
                "message": "Toggling cursor control",
                "speech": "Toggling desktop cursor control.",
            }
            self._notify_listeners(res)
            return res

        # 9.5 Desktop Control Commands
        desktop_actions = {
            "screenshot": ("take a screenshot", "screenshot"),
            "lock_screen": ("lock the screen", "lock screen"),
            "open_browser": ("opening the web browser", "open browser"),
            "open_email": ("opening email client", "open email"),
            "open_files": ("opening file manager", "open files"),
            "open_terminal": ("opening terminal", "open terminal"),
            "open_calculator": ("opening calculator", "open calculator"),
            "media_play": ("playing media", "play"),
            "media_pause": ("pausing media", "pause"),
            "media_next": ("skipping to next track", "next song"),
            "media_previous": ("going to previous track", "previous song"),
            "copy_clipboard": ("copying to clipboard", "copy"),
        }

        for cmd_key, (action_msg, speech_msg) in desktop_actions.items():
            if _has_phrase(cleaned, COMMANDS.get(cmd_key, [])):
                action_map = {
                    "screenshot": "screenshot",
                    "lock_screen": "lock",
                    "open_browser": "open_app",
                    "open_email": "open_app",
                    "open_files": "open_app",
                    "open_terminal": "open_app",
                    "open_calculator": "open_app",
                    "media_play": "media_play",
                    "media_pause": "media_pause",
                    "media_next": "media_next",
                    "media_previous": "media_previous",
                    "copy_clipboard": "clipboard",
                }
                payload = {}
                if cmd_key in ("open_browser", "open_email", "open_files", "open_terminal", "open_calculator"):
                    payload["app"] = cmd_key.replace("open_", "")
                if cmd_key == "copy_clipboard":
                    payload["text"] = " ".join(cleaned.split()[1:]) or raw

                exec_result = desktop_service.execute_action(action_map[cmd_key], payload)
                res = {
                    "ok": exec_result.get("ok", False),
                    "raw_text": raw,
                    "command_type": "desktop",
                    "action": cmd_key,
                    "message": exec_result.get("message") or f"{action_msg}",
                    "speech": exec_result.get("message") or f"{speech_msg}",
                }
                self._notify_listeners(res)
                return res

        # 9.75 Interface Navigation Commands (UI actions handled client-side)
        ui_commands = [
            ("show_camera", COMMANDS.get("camera_show", []), "Showing camera preview."),
            ("hide_camera", COMMANDS.get("camera_hide", []), "Hiding camera preview."),
            ("show_chat", COMMANDS.get("chat_show", []), "Showing chat transcript."),
            ("hide_chat", COMMANDS.get("chat_hide", []), "Hiding chat transcript."),
            ("open_settings", COMMANDS.get("open_settings", []), "Opening controls."),
            ("close_settings", COMMANDS.get("close_settings", []), "Closing controls."),
            ("clear_chat", COMMANDS.get("clear_chat", []), "Cleared the conversation."),
        ]
        for action, phrases, speech_msg in ui_commands:
            if phrases and _has_phrase(cleaned, phrases):
                res = {
                    "ok": True,
                    "raw_text": raw,
                    "command_type": "ui",
                    "action": action,
                    "message": speech_msg,
                    "speech": speech_msg,
                }
                self._notify_listeners(res)
                return res

        # 10. Search Trigger
        query = self.extract_search_query(cleaned)
        if query:
            search_result = search_service.search_and_respond(query)
            snippet = search_result["response"].split("\n")[0][:140]
            res = {
                "ok": True,
                "raw_text": raw,
                "command_type": "search",
                "action": "search",
                "query": query,
                "message": f"Searched: {query}",
                "speech": snippet,
                "search_result": search_result,
            }
            self._notify_listeners(res)
            return res

        # 11. Fallback: Multi-word phrase as search
        if len(cleaned.split()) >= 2:
            search_result = search_service.search_and_respond(raw)
            snippet = search_result["response"].split("\n")[0][:140]
            res = {
                "ok": True,
                "raw_text": raw,
                "command_type": "search",
                "action": "natural_query",
                "query": raw,
                "message": f"Query: {raw}",
                "speech": snippet,
                "search_result": search_result,
            }
            self._notify_listeners(res)
            return res

        res = {
            "ok": False,
            "raw_text": raw,
            "command_type": "unknown",
            "action": "none",
            "message": f"Command not recognized: '{raw}'",
            "speech": "I did not recognize that command. Try 'volume up', 'brightness 80', or 'search latest AI news'.",
        }
        self._notify_listeners(res)
        return res

    def extract_search_query(self, text: str) -> Optional[str]:
        """Extract the core search query from a voice command string."""
        search_triggers = COMMANDS.get("search", [])
        for trigger in search_triggers:
            if trigger in text:
                parts = text.split(trigger, 1)
                if len(parts) > 1 and parts[1].strip():
                    return parts[1].strip().strip("?.,!")

        question_prefixes = ["what is", "who is", "why is", "how do i", "how to", "tell me about"]
        for prefix in question_prefixes:
            if text.startswith(prefix):
                return text[len(prefix):].strip().strip("?.,!")

        return None

    # ==========================================
    # Audio Capture & Local Microphone
    # ==========================================

    def listen_once(self) -> Optional[str]:
        """Listen for a single spoken phrase on the local server microphone."""
        if self._backend == "pyaudio" and self._microphone:
            try:
                with self._microphone as source:
                    activity_logger.log("Listening for voice input...", category="VOICE")
                    audio = self._recognizer.listen(
                        source,
                        timeout=VOICE_TIMEOUT,
                        phrase_time_limit=VOICE_PHRASE_LIMIT,
                    )
                text = self._recognizer.recognize_google(audio, language=VOICE_LANGUAGE)
                return text.strip()
            except (sr.WaitTimeoutError, sr.UnknownValueError):
                return None
            except Exception as exc:
                activity_logger.log(f"Voice recognition error: {exc}", category="VOICE", level="WARNING")
                return None

        elif self._backend == "sounddevice":
            try:
                import sounddevice as sd
                samplerate = 16000
                duration = 4.0
                activity_logger.log("Listening via SoundDevice (4s)...", category="VOICE")
                recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype="int16")
                sd.wait()

                energy = np.abs(recording).mean()
                if energy < 150:
                    return None

                audio_data = sr.AudioData(recording.tobytes(), samplerate, 2)
                text = self._recognizer.recognize_google(audio_data, language=VOICE_LANGUAGE)
                return text.strip()
            except (sr.UnknownValueError, sr.WaitTimeoutError):
                return None
            except Exception as exc:
                activity_logger.log(f"SoundDevice recognition error: {exc}", category="VOICE", level="WARNING")
                return None

        return None

    def start_listening(self) -> bool:
        """Start the background listener loop if microphone is available."""
        if not self.is_mic_available:
            activity_logger.log("Cannot start listener: no local microphone backend available", category="VOICE", level="WARNING")
            return False

        if self._is_listening:
            return True

        self._stop_listener_event.clear()
        self._is_listening = True
        self._listener_thread = threading.Thread(target=self._background_listener_loop, daemon=True)
        self._listener_thread.start()
        activity_logger.log(f"Background voice listener started ({self._backend})", category="VOICE")
        return True

    def stop_listening(self) -> None:
        """Stop the background listener thread."""
        self._is_listening = False
        self._stop_listener_event.set()
        if self._listener_thread and self._listener_thread.is_alive():
            # The loop can be blocked in listen_once (up to VOICE_TIMEOUT); wait briefly
            self._listener_thread.join(timeout=2.0)
        self._listener_thread = None
        activity_logger.log("Background voice listener stopped", category="VOICE")

    def toggle_listening(self) -> bool:
        """Toggle background listener on/off."""
        if self._is_listening:
            self.stop_listening()
            return False
        return self.start_listening()

    def _background_listener_loop(self) -> None:
        """Continuously listen for audio and process commands."""
        while not self._stop_listener_event.is_set():
            text = self.listen_once()
            if text:
                self.process_text(text)


# Global singleton instance
voice_service = VoiceService()
