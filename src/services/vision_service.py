"""MediaPipe hand tracking, gesture recognition, and smoothed cursor control service."""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np

from config.settings import (
    CLICK_DISTANCE_THRESHOLD,
    CURSOR_SMOOTHING,
    DEFAULT_CURSOR_CONTROL_ENABLED,
    HAND_DETECTION_CONFIDENCE,
    HAND_LANDMARKER_MODEL_PATH,
    HAND_TRACKING_CONFIDENCE,
    SCROLL_THRESHOLD,
)
from src.core.logger import activity_logger


class VisionService:
    """Manages hand tracking, gesture interpretation, and OS cursor movement."""

    def __init__(self) -> None:
        self._model_path: Path = HAND_LANDMARKER_MODEL_PATH
        self._landmarker: Optional[Any] = None
        self._pyautogui: Optional[Any] = None
        self._pyautogui_available: bool = False
        self._screen_w: int = 1920
        self._screen_h: int = 1080

        # Cursor control state
        self._cursor_enabled: bool = DEFAULT_CURSOR_CONTROL_ENABLED
        self._mirror: bool = True
        self._prev_x: Optional[float] = None
        self._prev_y: Optional[float] = None
        self._is_clicking: bool = False
        self._is_dragging: bool = False
        self._pinch_start_time: float = 0.0
        self._last_scroll_time: float = 0.0
        self._last_click_time: float = 0.0

        self._init_pyautogui()
        self._init_landmarker()

    def _init_pyautogui(self) -> None:
        """Initialize PyAutoGUI safely without crashing on headless systems."""
        try:
            import pyautogui
            pyautogui.FAILSAFE = False
            pyautogui.PAUSE = 0.001
            # Check if size can be queried (verifies display connection)
            w, h = pyautogui.size()
            self._screen_w = w
            self._screen_h = h
            self._pyautogui = pyautogui
            self._pyautogui_available = True
            activity_logger.log(f"Desktop cursor control active ({w}x{h})", category="GESTURE")
        except Exception as exc:
            self._pyautogui_available = False
            activity_logger.log(f"Desktop display unavailable for cursor: {exc}", category="GESTURE", level="WARNING")

    def _init_landmarker(self) -> None:
        """Initialize MediaPipe HandLandmarker."""
        if not self._model_path.exists():
            activity_logger.log(f"Model file not found at: {self._model_path}", category="GESTURE", level="ERROR")
            return

        try:
            import mediapipe as mp
            from mediapipe.tasks.python import BaseOptions
            from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions

            options = HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(self._model_path)),
                num_hands=1,
                min_hand_detection_confidence=HAND_DETECTION_CONFIDENCE,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=HAND_TRACKING_CONFIDENCE,
            )
            self._landmarker = HandLandmarker.create_from_options(options)
            activity_logger.log("MediaPipe HandLandmarker loaded successfully", category="GESTURE")
        except Exception as exc:
            activity_logger.log(f"Failed to load MediaPipe landmarker: {exc}", category="GESTURE", level="ERROR")

    @property
    def is_ready(self) -> bool:
        return self._landmarker is not None

    @property
    def cursor_control_enabled(self) -> bool:
        return self._cursor_enabled

    @cursor_control_enabled.setter
    def cursor_control_enabled(self, value: bool) -> None:
        self._cursor_enabled = bool(value)
        status = "enabled" if self._cursor_enabled else "disabled"
        activity_logger.log(f"Desktop cursor control {status}", category="GESTURE")

    @property
    def pyautogui_available(self) -> bool:
        return self._pyautogui_available

    def toggle_cursor_control(self) -> bool:
        """Toggle desktop cursor control on or off."""
        self._cursor_enabled = not self._cursor_enabled
        status = "enabled" if self._cursor_enabled else "disabled"
        activity_logger.log(f"Desktop cursor control {status}", category="GESTURE")
        return self._cursor_enabled

    def process_frame(self, frame: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
        """Process a BGR video frame and perform gesture detection + cursor control.

        Returns the annotated frame and a dictionary of gesture telemetry.
        """
        if self._mirror:
            frame = cv2.flip(frame, 1)

        meta: dict[str, Any] = {
            "hand_detected": False,
            "gesture": "NO_HAND",
            "x": 0.0,
            "y": 0.0,
            "pinch": False,
            "scroll": 0,
            "cursor_enabled": self._cursor_enabled,
        }

        if self._landmarker is None:
            return frame, meta

        import mediapipe as mp
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        try:
            result = self._landmarker.detect(mp_image)
        except Exception as exc:
            activity_logger.log(f"Landmarker detect error: {exc}", category="GESTURE", level="WARNING")
            return frame, meta

        if not result.hand_landmarks:
            # Hand lost: release any in-progress drag/click so cursor isn't stuck
            if self._is_dragging or self._is_clicking:
                if self._is_dragging and self._pyautogui:
                    try:
                        self._pyautogui.mouseUp()
                    except Exception:
                        pass
                self._is_dragging = False
                self._is_clicking = False
                self._prev_x = None
                self._prev_y = None
            # Draw HUD: No hand
            self._draw_hud(frame, meta)
            return frame, meta

        hand_landmarks = result.hand_landmarks[0]
        meta["hand_detected"] = True

        h, w, _ = frame.shape

        # Key landmark points
        # 4: Thumb tip, 8: Index tip, 9: Middle MCP, 12: Middle tip
        thumb_tip = hand_landmarks[4]
        index_tip = hand_landmarks[8]
        middle_tip = hand_landmarks[12]
        middle_base = hand_landmarks[9]

        meta["x"] = round(float(index_tip.x), 3)
        meta["y"] = round(float(index_tip.y), 3)

        # 1. Pinch Detection (Thumb tip to Index tip distance)
        dist = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
        is_pinching = dist < CLICK_DISTANCE_THRESHOLD
        meta["pinch"] = is_pinching

        # 2. Scroll Detection (Middle tip relative to knuckle)
        scroll_val = 0
        if middle_tip.y < middle_base.y - SCROLL_THRESHOLD:
            scroll_val = 1   # Scroll Up
        elif middle_tip.y > middle_base.y + SCROLL_THRESHOLD:
            scroll_val = -1  # Scroll Down
        meta["scroll"] = scroll_val

        # Determine gesture label
        if is_pinching:
            meta["gesture"] = "PINCH_CLICK"
        elif scroll_val == 1:
            meta["gesture"] = "SCROLL_UP"
        elif scroll_val == -1:
            meta["gesture"] = "SCROLL_DOWN"
        else:
            meta["gesture"] = "POINTER"

        # 3. Desktop Cursor Movement & Actions (if enabled)
        if self._cursor_enabled and self._pyautogui_available and self._pyautogui:
            self._execute_cursor_actions(index_tip.x, index_tip.y, is_pinching, scroll_val)

        # 4. Draw Hand Skeleton & Interactive HUD
        self._draw_hand_skeleton(frame, hand_landmarks, w, h, is_pinching)
        self._draw_hud(frame, meta)

        return frame, meta

    def _execute_cursor_actions(self, norm_x: float, norm_y: float, is_pinching: bool, scroll_val: int) -> None:
        """Move cursor, click/drag on pinch, and scroll.

        Gesture mapping:
          - Index finger:          move cursor
          - Quick pinch tap:       left click
          - Hold pinch + move:     drag (click-hold, move, release)
          - Middle finger up/down: scroll
        """
        import time
        now = time.time()

        target_x = norm_x * self._screen_w
        target_y = norm_y * self._screen_h

        # Exponential moving average smoothing
        if self._prev_x is not None and self._prev_y is not None:
            # Deadzone check (ignore micro tremors < 3 pixels)
            dx = abs(target_x - self._prev_x)
            dy = abs(target_y - self._prev_y)
            if dx > 3 or dy > 3:
                curr_x = self._prev_x + CURSOR_SMOOTHING * (target_x - self._prev_x)
                curr_y = self._prev_y + CURSOR_SMOOTHING * (target_y - self._prev_y)
            else:
                curr_x = self._prev_x
                curr_y = self._prev_y
        else:
            curr_x = target_x
            curr_y = target_y

        self._prev_x = curr_x
        self._prev_y = curr_y

        try:
            pg = self._pyautogui

            # Detect pinch press transition
            if is_pinching and not self._is_clicking:
                self._is_clicking = True
                self._pinch_start_time = now

            # While holding pinch, drag if we've moved past a threshold
            if is_pinching and self._is_clicking:
                if not self._is_dragging and (now - self._pinch_start_time) > 0.25:
                    # Became a drag (pinch held long enough)
                    pg.mouseDown()
                    self._is_dragging = True
                    activity_logger.log("Gesture drag started", category="GESTURE")

            # On pinch release
            if not is_pinching and self._is_clicking:
                hold_duration = now - self._pinch_start_time
                if self._is_dragging:
                    # Released a drag
                    pg.mouseUp()
                    self._is_dragging = False
                    activity_logger.log("Gesture drag released", category="GESTURE")
                elif hold_duration < 0.25:
                    # Quick tap -> left click
                    pg.click()
                    activity_logger.log(f"Gesture Click at ({int(curr_x)}, {int(curr_y)})", category="GESTURE")
                self._is_clicking = False

            # Always move cursor (inside drag this moves the dragged object)
            pg.moveTo(int(curr_x), int(curr_y))

            # Handle scroll
            if scroll_val != 0:
                if now - self._last_scroll_time > 0.15:  # Debounce scroll
                    pg.scroll(scroll_val * 4)
                    self._last_scroll_time = now
        except Exception:
            pass

    def _draw_hand_skeleton(self, frame: np.ndarray, landmarks: Any, w: int, h: int, is_pinching: bool) -> None:
        """Render high-craft visual hand landmarks and gesture lines."""
        from mediapipe.tasks.python.vision import HandLandmarksConnections

        # Draw bones
        connections = HandLandmarksConnections.HAND_CONNECTIONS
        if connections:
            for conn in connections:
                s = landmarks[conn.start]
                e = landmarks[conn.end]
                pt1 = (int(s.x * w), int(s.y * h))
                pt2 = (int(e.x * w), int(e.y * h))
                cv2.line(frame, pt1, pt2, (140, 100, 255), 2, cv2.LINE_AA)

        # Draw joints
        for idx, lm in enumerate(landmarks):
            cx, cy = int(lm.x * w), int(lm.y * h)
            # Accentuate tips
            if idx in (4, 8, 12, 16, 20):
                cv2.circle(frame, (cx, cy), 6, (0, 230, 255), -1, cv2.LINE_AA)
                cv2.circle(frame, (cx, cy), 8, (255, 255, 255), 1, cv2.LINE_AA)
            else:
                cv2.circle(frame, (cx, cy), 4, (200, 180, 255), -1, cv2.LINE_AA)

        # Pinch line between thumb (4) and index (8)
        p_thumb = (int(landmarks[4].x * w), int(landmarks[4].y * h))
        p_index = (int(landmarks[8].x * w), int(landmarks[8].y * h))
        line_color = (0, 255, 128) if is_pinching else (255, 100, 200)
        cv2.line(frame, p_thumb, p_index, line_color, 3 if is_pinching else 1, cv2.LINE_AA)

        # Target reticle on index finger
        cv2.circle(frame, p_index, 14, (0, 255, 200), 2, cv2.LINE_AA)

    def _draw_hud(self, frame: np.ndarray, meta: dict[str, Any]) -> None:
        """Draw clean status indicators on the video frame."""
        # Top-left Mode Badge
        mode_text = "CURSOR: ACTIVE" if self._cursor_enabled else "CURSOR: VIEW ONLY"
        mode_color = (40, 200, 80) if self._cursor_enabled else (80, 160, 240)
        cv2.rectangle(frame, (14, 14), (190, 42), (20, 20, 20), -1)
        cv2.rectangle(frame, (14, 14), (190, 42), mode_color, 1)
        cv2.putText(frame, mode_text, (22, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.45, mode_color, 1, cv2.LINE_AA)

        # Gesture Badge
        gesture = meta.get("gesture", "NO_HAND")
        g_color = (0, 255, 128) if gesture == "PINCH_CLICK" else ((0, 230, 255) if gesture == "POINTER" else (160, 160, 160))
        cv2.rectangle(frame, (198, 14), (340, 42), (20, 20, 20), -1)
        cv2.rectangle(frame, (198, 14), (340, 42), (60, 60, 60), 1)
        cv2.putText(frame, f"MODE: {gesture}", (206, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.42, g_color, 1, cv2.LINE_AA)

    def release(self) -> None:
        """Free resources."""
        if self._landmarker:
            try:
                self._landmarker.close()
            except Exception:
                pass
            self._landmarker = None


# Global singleton instance
vision_service = VisionService()
