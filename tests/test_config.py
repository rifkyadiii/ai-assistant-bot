"""Tests for configuration settings."""

from config.settings import (
    BASE_DIR,
    COMMANDS,
    SERVER_PORT,
    VOLUME_STEP,
    BRIGHTNESS_STEP,
    HAND_LANDMARKER_MODEL_PATH,
)


def test_base_dir_exists():
    assert BASE_DIR.exists()
    assert (BASE_DIR / "requirements.txt").exists()


def test_commands_structure():
    expected_keys = [
        "volume_up",
        "volume_down",
        "mute",
        "unmute",
        "brightness_up",
        "brightness_down",
        "search",
        "cursor_toggle",
    ]
    for key in expected_keys:
        assert key in COMMANDS
        assert isinstance(COMMANDS[key], list)
        assert len(COMMANDS[key]) > 0


def test_system_steps():
    assert VOLUME_STEP > 0
    assert BRIGHTNESS_STEP > 0
    assert SERVER_PORT > 0
