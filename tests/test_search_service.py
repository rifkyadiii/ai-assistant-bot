"""Tests for SearchService."""

import pytest
from src.services.search_service import SearchService


@pytest.fixture
def search_service_instance():
    svc = SearchService()
    svc.clear_history()
    return svc


def test_empty_query(search_service_instance):
    res = search_service_instance.search_and_respond("   ")
    assert res["ok"] is False


def test_fallback_search(search_service_instance):
    fallback_text = search_service_instance._fallback_search("test topic")
    assert "test topic" in fallback_text
    assert "https://www.google.com/search?q=test+topic" in fallback_text


def test_history_tracking(search_service_instance, monkeypatch):
    monkeypatch.setattr(
        search_service_instance, "_llm_search", lambda q: (f"Mock answer for {q}", "mock")
    )
    search_service_instance.search_and_respond("History test query 1")
    history = search_service_instance.get_history()
    assert len(history) >= 1
    assert history[0]["query"] == "History test query 1"
