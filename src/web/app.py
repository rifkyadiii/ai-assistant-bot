"""Flask application factory and server startup manager."""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify

from config.settings import BASE_DIR, SERVER_HOST, SERVER_PORT, VOICE_BACKGROUND_ENABLED
from src.core.logger import activity_logger
from src.services.voice_service import voice_service
from src.web.camera_stream import camera_manager
from src.web.routes import web_bp


def create_app() -> Flask:
    """Create and configure the Flask application."""
    templates_path = BASE_DIR / "templates"
    static_path = BASE_DIR / "static"

    app = Flask(
        __name__,
        template_folder=str(templates_path),
        static_folder=str(static_path),
        static_url_path="/static",
    )

    # Register modular blueprints
    app.register_blueprint(web_bp)

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"ok": False, "error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(err):
        activity_logger.log(f"Internal server error: {err}", category="SYS", level="ERROR")
        return jsonify({"ok": False, "error": "Internal server error"}), 500

    return app


# Default application instance
app = create_app()


def start_web_server(host: str = SERVER_HOST, port: int = SERVER_PORT) -> None:
    """Start the Flask server and background services."""
    # 1. Start camera streaming manager in background
    camera_manager.start()

    # 2. Start background voice listener if enabled by config
    if VOICE_BACKGROUND_ENABLED:
        voice_service.start_listening()

    # 3. Start web server in background thread
    server_thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    server_thread.start()
    activity_logger.log(f"Web server started at http://{host}:{port}", category="SYS")
