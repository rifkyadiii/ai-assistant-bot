"""Backward-compatible wrapper for SystemController -> SystemService."""

from src.services.system_service import SystemService as SystemController, system_service

__all__ = ["SystemController", "system_service"]
