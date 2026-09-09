"""Configuration settings for VoiceBot application.

Provides centralized, typed settings with environment variable support.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Final
from dotenv import load_dotenv

# Base paths
BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Gemini API Configuration
GEMINI_API_KEY: Final[str] = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: Final[str] = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# Model asset paths
HAND_LANDMARKER_MODEL_PATH: Final[Path] = BASE_DIR / "hand_landmarker.task"

# Voice Recognition Settings
VOICE_TIMEOUT: Final[int] = int(os.getenv("VOICE_TIMEOUT", "5"))
VOICE_PHRASE_LIMIT: Final[int] = int(os.getenv("VOICE_PHRASE_LIMIT", "10"))
VOICE_LANGUAGE: Final[str] = os.getenv("VOICE_LANGUAGE", "en-US")
VOICE_BACKGROUND_ENABLED: Final[bool] = os.getenv("VOICE_BACKGROUND_ENABLED", "false").lower() in ("true", "1", "yes")
# Wake word phrase to activate the assistant hands-free (e.g. "Hey Sobot")
WAKE_PHRASE: Final[str] = os.getenv("WAKE_PHRASE", "hey sobot")

# Hand Tracking & Gesture Settings
HAND_DETECTION_CONFIDENCE: Final[float] = float(os.getenv("HAND_DETECTION_CONFIDENCE", "0.7"))
HAND_TRACKING_CONFIDENCE: Final[float] = float(os.getenv("HAND_TRACKING_CONFIDENCE", "0.5"))
CURSOR_SMOOTHING: Final[float] = float(os.getenv("CURSOR_SMOOTHING", "0.45"))
CLICK_DISTANCE_THRESHOLD: Final[float] = float(os.getenv("CLICK_DISTANCE_THRESHOLD", "0.055"))
SCROLL_THRESHOLD: Final[float] = float(os.getenv("SCROLL_THRESHOLD", "0.08"))
DEFAULT_CURSOR_CONTROL_ENABLED: Final[bool] = os.getenv("CURSOR_CONTROL_ENABLED", "false").lower() in ("true", "1", "yes")

# System Control Settings
VOLUME_STEP: Final[int] = int(os.getenv("VOLUME_STEP", "5"))
BRIGHTNESS_STEP: Final[int] = int(os.getenv("BRIGHTNESS_STEP", "5"))

# Text-to-Speech Settings (natural human voices via edge-tts)
TTS_ENGINE: Final[str] = os.getenv("TTS_ENGINE", "edge-tts")
TTS_VOICE: Final[str] = os.getenv("TTS_VOICE", "en-US-JennyNeural")
TTS_RATE: Final[str] = os.getenv("TTS_RATE", "+0%")
TTS_VOLUME: Final[str] = os.getenv("TTS_VOLUME", "+0%")
TTS_ENABLED: Final[bool] = os.getenv("TTS_ENABLED", "true").lower() in ("true", "1", "yes")

# Desktop Control Settings
DESKTOP_CONTROL_ENABLED: Final[bool] = os.getenv("DESKTOP_CONTROL_ENABLED", "true").lower() in ("true", "1", "yes")

# Web Server Settings
SERVER_HOST: Final[str] = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT: Final[int] = int(os.getenv("SERVER_PORT", "5000"))

# Frontend Polling Intervals (milliseconds)
STATUS_POLL_INTERVAL: Final[int] = int(os.getenv("STATUS_POLL_INTERVAL", "2500"))
LOGS_POLL_INTERVAL: Final[int] = int(os.getenv("LOGS_POLL_INTERVAL", "3000"))

# Voice Commands Mapping
COMMANDS: Final[dict[str, list[str]]] = {
    "volume_up": [
        "volume up", "increase volume", "louder", "turn up", "turn it up",
        "raise volume", "boost volume"
    ],
    "volume_down": [
        "volume down", "decrease volume", "quieter", "turn down", "turn it down",
        "lower volume", "reduce volume"
    ],
    "mute": ["mute", "silence", "quiet", "shut up", "turn off sound"],
    "unmute": ["unmute", "sound on", "restore sound", "un-mute"],
    "brightness_up": [
        "brightness up", "increase brightness", "brighter", "turn up brightness",
        "make screen brighter", "raise brightness"
    ],
    "brightness_down": [
        "brightness down", "decrease brightness", "dimmer", "turn down brightness",
        "make screen darker", "lower brightness", "dim screen"
    ],
    "search": [
        "search for", "search", "look up", "find information on", "find",
        "google", "who is", "what is", "how to", "tell me about"
    ],
    "cursor_toggle": [
        "enable cursor", "disable cursor", "toggle cursor", "mouse on", "mouse off",
        "start cursor", "stop cursor"
    ],
    "camera_toggle": [
        "camera on", "camera off", "toggle camera", "start camera", "stop camera"
    ],
    "quit": ["quit", "exit", "stop application", "goodbye", "close voicebot"],
    "screenshot": ["screenshot", "take a screenshot", "capture screen", "screen capture"],
    "lock_screen": ["lock the screen", "lock my screen", "lock computer", "lock my computer", "lock pc", "lock up the screen"],
    "open_browser": ["open browser", "launch browser", "open chrome", "open firefox"],
    "open_email": ["open email", "launch email", "open mail", "open outlook", "open thunderbird"],
    "open_files": ["open files", "open file manager", "show my files", "open explorer"],
    "open_terminal": ["open terminal", "launch terminal", "open command prompt", "open cmd"],
    "open_calculator": ["open calculator", "launch calculator", "open calc"],
    "media_play": ["play music", "play song", "resume music", "start music"],
    "media_pause": ["pause music", "pause the music", "pause song", "stop music", "stop the music"],
    "media_next": ["next song", "next track", "skip song", "skip track"],
    "media_previous": ["previous song", "previous track", "go back a song"],
    "copy_clipboard": ["copy this", "copy to clipboard", "copy text"],
    # Interface navigation commands (mostly handled client-side)
    "camera_show": ["show camera", "open camera", "start camera", "enable camera"],
    "camera_hide": ["hide camera", "close camera", "stop camera", "disable camera"],
    "chat_show": ["show chat", "open chat", "show transcript", "open transcript"],
    "chat_hide": ["hide chat", "close chat", "hide transcript", "close transcript"],
    "open_settings": ["open settings", "open controls", "show settings", "show controls", "open menu"],
    "close_settings": ["close settings", "close controls", "hide settings", "hide controls", "close menu"],
    "clear_chat": ["clear chat", "clear messages", "clear transcript", "clear conversation"],
}
