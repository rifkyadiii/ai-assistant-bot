"""Backward-compatible wrapper for HandTracker -> VisionService."""

from src.services.vision_service import VisionService as HandTracker, vision_service

__all__ = ["HandTracker", "vision_service"]
