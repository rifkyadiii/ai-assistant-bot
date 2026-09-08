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
