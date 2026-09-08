"""Backward-compatible wrapper for VoiceHandler -> VoiceService."""

from src.services.voice_service import VoiceService as VoiceHandler, voice_service

__all__ = ["VoiceHandler", "voice_service"]
