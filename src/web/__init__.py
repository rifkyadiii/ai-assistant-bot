"""Web application package."""

from src.web.app import app, create_app, start_web_server
from src.web.camera_stream import camera_manager

__all__ = [
    "app",
    "create_app",
    "start_web_server",
    "camera_manager",
]
