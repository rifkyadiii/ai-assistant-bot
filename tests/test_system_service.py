"""Tests for SystemService volume and brightness logic."""

import pytest
from src.services.system_service import SystemService


@pytest.fixture
def mock_system_service():
    service = SystemService()
    # Force mock backend for isolated deterministic testing
    service._volume_backend = "mock"
    service._brightness_backend = "mock"
    service._cached_volume = 50
    service._cached_muted = False
    service._cached_brightness = 50
    return service


def test_volume_set_clamping(mock_system_service):
    mock_system_service.set_volume(150)
    assert mock_system_service.get_volume() == 100

    mock_system_service.set_volume(-20)
    assert mock_system_service.get_volume() == 0

    mock_system_service.set_volume(62)
    assert mock_system_service.get_volume() == 62


def test_volume_up_down(mock_system_service):
    mock_system_service.set_volume(50)
    mock_system_service.volume_up(5)
    assert mock_system_service.get_volume() == 55

    mock_system_service.volume_down(10)
    assert mock_system_service.get_volume() == 45


def test_mute_unmute(mock_system_service):
    mock_system_service.mute()
    assert mock_system_service.is_muted() is True

    mock_system_service.unmute()
    assert mock_system_service.is_muted() is False

    mock_system_service.toggle_mute()
    assert mock_system_service.is_muted() is True


def test_brightness_set_clamping(mock_system_service):
    mock_system_service.set_brightness(120)
    assert mock_system_service.get_brightness() == 100

    mock_system_service.set_brightness(-10)
    assert mock_system_service.get_brightness() == 0

    mock_system_service.set_brightness(75)
    assert mock_system_service.get_brightness() == 75


def test_brightness_up_down(mock_system_service):
    mock_system_service.set_brightness(50)
    mock_system_service.brightness_up(10)
    assert mock_system_service.get_brightness() == 60

    mock_system_service.brightness_down(20)
    assert mock_system_service.get_brightness() == 40


def test_system_status(mock_system_service):
    status = mock_system_service.get_status()
    assert "volume" in status
    assert "muted" in status
    assert "brightness" in status
    assert "volume_backend" in status
    assert "brightness_backend" in status
