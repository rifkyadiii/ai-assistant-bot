"""Entry point for VoiceBot OS multimodal voice and gesture system."""

from __future__ import annotations

import atexit
import signal
import sys
import threading
import time
import webbrowser

from config.settings import SERVER_HOST, SERVER_PORT
from src.core.logger import activity_logger
from src.services.search_service import search_service
from src.services.tts_service import tts_service
from src.services.vision_service import vision_service
from src.services.voice_service import voice_service
from src.web.app import start_web_server
from src.web.camera_stream import camera_manager


def open_browser() -> None:
    """Open default browser after web server starts."""
    time.sleep(1.2)
    url = f"http://localhost:{SERVER_PORT}"
    try:
        webbrowser.open(url)
    except Exception as exc:
        activity_logger.log(f"Browser launch note: {exc}", category="SYS")


def shutdown_handler(sig=None, frame=None) -> None:
    """Gracefully stop background threads and hardware resources."""
    print("\nShutting down VoiceBot OS gracefully...")
    _cleanup_services()
    sys.exit(0)


def _cleanup_services() -> None:
    """Stop all background threads and reset application state."""
    try:
        camera_manager.stop()
        vision_service.release()
        voice_service.stop_listening()
        tts_service.stop()
        search_service.clear_history()
        activity_logger.log("VoiceBot application stopped", category="SYS")
    except Exception as exc:
        print(f"Cleanup warning: {exc}")


# Ensure the clean shutdown path also runs for unexpected exits
atexit.register(_cleanup_services)


def main() -> None:
    """Application entry point."""
    print("=" * 60)
    print("   🎙️  VoiceBot OS — Multimodal Voice & Gesture Console")
    print("=" * 60)
    print()
    print(f"  ⚡ Web App & PWA:  http://localhost:{SERVER_PORT}")
    print(f"  ⚡ Network Access: http://{SERVER_HOST}:{SERVER_PORT}")
    print("  ⚡ Press Ctrl+C to stop")
    print("=" * 60)
    print()

    # Register OS signal handlers
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Start Flask web server & background threads
    start_web_server(host=SERVER_HOST, port=SERVER_PORT)

    # Open local browser
    threading.Thread(target=open_browser, daemon=True).start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown_handler()


if __name__ == "__main__":
    main()
