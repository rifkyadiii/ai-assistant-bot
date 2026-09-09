"""Tests for Web Application and REST API endpoints."""

import json
import pytest
from src.web.app import create_app
from src.services.search_service import search_service


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "VoiceBot OS" in html
    assert 'rel="manifest"' in html
    assert "tailwindcss" in html
    # New interface layout elements
    assert 'id="orbContainer"' in html
    assert 'id="chatPanel"' in html
    assert 'id="chatMessages"' in html
    assert 'id="cameraFloat"' in html
    assert 'id="hamburgerBtn"' in html
    assert 'id="controlBar"' in html
    assert 'id="chatInput"' in html
    assert 'id="wakeWordToggle"' in html


def test_manifest_route(client):
    response = client.get("/manifest.json")
    assert response.status_code == 200
    data = json.loads(response.get_data(as_text=True))
    assert data["name"] == "VoiceBot OS - Hands-Free System Console"
    assert data["display"] == "standalone"
    assert len(data["icons"]) > 0


def test_service_worker_route(client):
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert "application/javascript" in response.content_type
    content = response.get_data(as_text=True)
    assert "voicebot-shell" in content


def test_api_status(client):
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.get_json()
    assert data["ok"] is True
    assert "volume" in data
    assert "brightness" in data
    assert "camera_active" in data
    assert "cursor_enabled" in data


def test_api_volume_set(client):
    # Valid level
    res = client.post("/api/volume", json={"level": 42})
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert data["volume"] == 42

    # Invalid level
    res_bad = client.post("/api/volume", json={"level": 150})
    assert res_bad.status_code == 400


def test_api_volume_up_down(client):
    res_up = client.post("/api/volume/up")
    assert res_up.status_code == 200
    assert res_up.get_json()["ok"] is True

    res_down = client.post("/api/volume/down")
    assert res_down.status_code == 200
    assert res_down.get_json()["ok"] is True


def test_api_mute_unmute(client):
    res_mute = client.post("/api/mute")
    assert res_mute.status_code == 200
    assert res_mute.get_json()["muted"] is True

    res_unmute = client.post("/api/unmute")
    assert res_unmute.status_code == 200
    assert res_unmute.get_json()["muted"] is False


def test_api_brightness_set(client):
    res = client.post("/api/brightness", json={"level": 60})
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert data["brightness"] == 60


def test_api_voice_command(client):
    res = client.post("/api/voice/command", json={"text": "volume up"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert data["action"] == "volume_up"


def test_api_search(client, monkeypatch):
    # Mock search_and_respond to avoid external network calls during unit test
    def mock_search(query):
        return {
            "ok": True,
            "query": query,
            "response": f"Mock answer for {query}",
            "source": "test_mock",
            "time": "12:00:00",
        }

    monkeypatch.setattr(search_service, "search_and_respond", mock_search)
    res = client.post("/api/search", json={"query": "Test search query"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert "Mock answer" in data["result"]["response"]


def test_api_logs(client):
    res = client.get("/api/logs")
    assert res.status_code == 200
    data = res.get_json()
    assert data["ok"] is True
    assert isinstance(data["entries"], list)
