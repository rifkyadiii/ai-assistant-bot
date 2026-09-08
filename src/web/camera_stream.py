"""Webcam streaming manager with low-latency drop-frame queue."""

from __future__ import annotations

import queue
import threading
import time
from typing import Generator, Optional

import cv2
import numpy as np

from src.core.logger import activity_logger
from src.services.vision_service import vision_service


class CameraStreamManager:
    """Manages background webcam frame capture and MJPEG generation."""

    def __init__(self, camera_index: int = 0) -> None:
        self._camera_index = camera_index
        self._camera: Optional[cv2.VideoCapture] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._frame_queue: queue.Queue[bytes] = queue.Queue(maxsize=2)
        self._is_running = False
        self._last_telemetry: dict = {
            "hand_detected": False,
            "gesture": "NO_HAND",
            "x": 0.0,
            "y": 0.0,
            "pinch": False,
            "scroll": 0,
        }

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def telemetry(self) -> dict:
        return self._last_telemetry

    def start(self) -> bool:
        """Start the camera capture thread."""
        if self._is_running:
            return True

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        self._is_running = True
        return True

    def stop(self) -> None:
        """Stop camera capture and release device."""
        self._is_running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._release_camera()

    def toggle(self) -> bool:
        """Toggle camera streaming state."""
        if self._is_running:
            self.stop()
            return False
        return self.start()

    def _release_camera(self) -> None:
        if self._camera:
            try:
                self._camera.release()
            except Exception:
                pass
            self._camera = None

    def _generate_placeholder_frame(self, message: str = "Webcam Inactive") -> bytes:
        """Create a placeholder frame when camera is unavailable."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Gradient background
        for y in range(480):
            frame[y, :] = (20 + int(y * 0.03), 18 + int(y * 0.03), 24 + int(y * 0.04))

        cv2.putText(
            frame, message, (180, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (120, 140, 160), 2, cv2.LINE_AA
        )
        cv2.putText(
            frame, "Connect a USB webcam or toggle camera in UI",
            (140, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 95, 110), 1, cv2.LINE_AA
        )
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        return buffer.tobytes()

    def _capture_loop(self) -> None:
        """Main webcam acquisition and landmark processing loop."""
        activity_logger.log("Attempting to open camera device...", category="GESTURE")
        self._camera = cv2.VideoCapture(self._camera_index)

        # Set lower buffer size to avoid frame lag
        self._camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self._camera.isOpened():
            activity_logger.log("Camera device could not be opened (no webcam detected)", category="GESTURE", level="WARNING")
            placeholder = self._generate_placeholder_frame("No Camera Detected")
            while not self._stop_event.is_set():
                self._push_frame(placeholder)
                time.sleep(0.5)
            self._release_camera()
            self._is_running = False
            return

        activity_logger.log("Camera capture started successfully", category="GESTURE")

        while not self._stop_event.is_set():
            if not self._camera or not self._camera.isOpened():
                break

            ret, frame = self._camera.read()
            if not ret:
                time.sleep(0.03)
                continue

            # Process frame through vision service for hand landmarks & gestures
            annotated_frame, meta = vision_service.process_frame(frame)
            self._last_telemetry = meta

            _, buffer = cv2.imencode(".jpg", annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
            if buffer is not None:
                self._push_frame(buffer.tobytes())

            time.sleep(0.01)

        self._release_camera()
        activity_logger.log("Camera capture stopped", category="GESTURE")

    def _push_frame(self, frame_bytes: bytes) -> None:
        """Push a frame to the queue, dropping the previous frame if full to prevent latency."""
        if self._frame_queue.full():
            try:
                self._frame_queue.get_nowait()
            except queue.Empty:
                pass
        self._frame_queue.put(frame_bytes)

    def generate_stream(self) -> Generator[bytes, None, None]:
        """Yield multipart MJPEG stream to browser clients."""
        while True:
            try:
                frame_bytes = self._frame_queue.get(timeout=2.0)
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
            except queue.Empty:
                # If no frame received, yield placeholder frame
                placeholder = self._generate_placeholder_frame("Waiting for video feed...")
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + placeholder + b"\r\n"
                )


# Global singleton camera stream manager
camera_manager = CameraStreamManager()
