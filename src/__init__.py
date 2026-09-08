"""Source package for VoiceBot."""

from src.core.logger import activity_logger
from src.services.search_service import SearchService, search_service
from src.services.system_service import SystemService, system_service
from src.services.vision_service import VisionService, vision_service
from src.services.voice_service import VoiceService, voice_service
from src.web.app import app, create_app, start_web_server

__all__ = [
    "activity_logger",
    "SystemService",
    "system_service",
    "VoiceService",
    "voice_service",
    "VisionService",
    "vision_service",
    "SearchService",
    "search_service",
    "app",
    "create_app",
    "start_web_server",
]
