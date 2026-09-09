"""Tests for VisionService."""

import numpy as np
import pytest
from src.services.vision_service import VisionService


@pytest.fixture
def vision_service_instance():
    svc = VisionService()
    return svc


def test_vision_initialization(vision_service_instance):
    assert vision_service_instance.is_ready is True


def test_cursor_toggle(vision_service_instance):
    initial = vision_service_instance.cursor_control_enabled
    toggled = vision_service_instance.toggle_cursor_control()
    assert toggled != initial
    assert vision_service_instance.cursor_control_enabled == toggled


def test_process_blank_frame(vision_service_instance):
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    out_frame, meta = vision_service_instance.process_frame(frame)
    assert out_frame.shape == (480, 640, 3)
    assert meta["hand_detected"] is False
    assert meta["gesture"] == "NO_HAND"


def test_release_resets_cursor_and_gesture_state(vision_service_instance):
    vision_service_instance._is_clicking = True
    vision_service_instance._is_dragging = True
    vision_service_instance._prev_x = 320.0
    vision_service_instance._prev_y = 240.0
    vision_service_instance._pinch_start_time = 123.0
    vision_service_instance._last_scroll_time = 456.0
    vision_service_instance._last_click_time = 789.0

    vision_service_instance.release()

    assert vision_service_instance._is_clicking is False
    assert vision_service_instance._is_dragging is False
    assert vision_service_instance._prev_x is None
    assert vision_service_instance._prev_y is None
    assert vision_service_instance._pinch_start_time == 0.0
    assert vision_service_instance._last_scroll_time == 0.0
    assert vision_service_instance._last_click_time == 0.0
