"""Services module exposing all singleton service instances."""

from src.services.system_service import SystemService, system_service
from src.services.voice_service import VoiceService, voice_service
from src.services.vision_service import VisionService, vision_service
from src.services.search_service import SearchService, search_service
from src.services.desktop_service import DesktopControlService, desktop_service
from src.services.tts_service import TTSService, tts_service

__all__ = [
    "SystemService",
    "system_service",
    "VoiceService",
    "voice_service",
    "VisionService",
    "vision_service",
    "SearchService",
    "search_service",
    "DesktopControlService",
    "desktop_service",
    "TTSService",
    "tts_service",
]
