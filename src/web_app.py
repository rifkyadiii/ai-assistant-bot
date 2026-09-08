"""Backward-compatible wrapper for web_app -> src.web."""

from src.web.app import app, start_web_server

__all__ = ["app", "start_web_server"]
