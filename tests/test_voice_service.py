"""Tests for VoiceService command parsing and execution."""

import pytest
from src.services.voice_service import VoiceService


@pytest.fixture
def voice_service_instance():
    svc = VoiceService()
    return svc


def test_volume_up_parsing(voice_service_instance):
    res = voice_service_instance.process_text("please turn volume up")
    assert res["ok"] is True
    assert res["command_type"] == "volume"
    assert res["action"] == "volume_up"


def test_volume_down_parsing(voice_service_instance):
    res = voice_service_instance.process_text("turn it down")
    assert res["ok"] is True
    assert res["command_type"] == "volume"
    assert res["action"] == "volume_down"


def test_set_volume_exact_number(voice_service_instance):
    res = voice_service_instance.process_text("set volume to 75%")
    assert res["ok"] is True
    assert res["command_type"] == "volume"
    assert res["action"] == "set_volume"
    assert res["value"] == 75


def test_mute_unmute_parsing(voice_service_instance):
    res_mute = voice_service_instance.process_text("mute sound")
    assert res_mute["ok"] is True
    assert res_mute["action"] == "mute"

    res_unmute = voice_service_instance.process_text("unmute audio")
    assert res_unmute["ok"] is True
    assert res_unmute["action"] == "unmute"


def test_brightness_up_parsing(voice_service_instance):
    res = voice_service_instance.process_text("increase brightness")
    assert res["ok"] is True
    assert res["command_type"] == "brightness"
    assert res["action"] == "brightness_up"


def test_set_brightness_exact_number(voice_service_instance):
    res = voice_service_instance.process_text("brightness 45")
    assert res["ok"] is True
    assert res["command_type"] == "brightness"
    assert res["action"] == "set_brightness"
    assert res["value"] == 45


def test_cursor_toggle_parsing(voice_service_instance):
    res = voice_service_instance.process_text("toggle cursor")
    assert res["ok"] is True
    assert res["action"] == "toggle_cursor"


def test_extract_search_query(voice_service_instance):
    q1 = voice_service_instance.extract_search_query("search for the tallest mountain")
    assert q1 == "the tallest mountain"

    q2 = voice_service_instance.extract_search_query("what is machine learning")
    assert q2 == "machine learning"
