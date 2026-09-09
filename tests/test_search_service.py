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


def test_fallback_models_omit_deprecated_aliases():
    assert "gemini-pro" not in SearchService.FALLBACK_MODELS
    assert "gemini-1.0-pro" not in SearchService.FALLBACK_MODELS
    assert all(m in SearchService.SUPPORTED_MODELS for m in SearchService.FALLBACK_MODELS)


def test_deprecated_model_is_remapped(monkeypatch):
    import importlib

    mod = importlib.import_module("src.services.search_service")
    monkeypatch.setattr(mod, "GEMINI_MODEL", "gemini-pro")
    svc = mod.SearchService()
    assert svc._configured_model == mod.SearchService.SUPPORTED_MODELS[0]


def test_unknown_future_model_is_preserved(monkeypatch):
    import importlib

    mod = importlib.import_module("src.services.search_service")
    monkeypatch.setattr(mod, "GEMINI_MODEL", "gemini-4.0-flash")
    svc = mod.SearchService()
    assert svc._configured_model == "gemini-4.0-flash"


def test_classify_error_model_not_found(search_service_instance):
    msg = search_service_instance._classify_error(
        Exception("404 NOT_FOUND models/gemini-pro, API version v1beta")
    )
    assert "GEMINI_MODEL" in msg
    assert "not available" in msg.lower()


def test_classify_error_auth(search_service_instance):
    class FakeError(Exception):
        code = 403

    msg = search_service_instance._classify_error(FakeError("PERMISSION_DENIED"))
    assert "denied" in msg.lower() or "ai studio" in msg.lower()


def test_classify_error_quota(search_service_instance):
    class FakeError(Exception):
        code = 429

    msg = search_service_instance._classify_error(FakeError("RESOURCE_EXHAUSTED"))
    assert "quota" in msg.lower()


def test_llm_search_all_models_fail_reports_precise_reason(search_service_instance):
    import importlib

    mod = importlib.import_module("src.services.search_service")

    class FakeModels:
        def generate_content(self, **kwargs):
            raise Exception("404 NOT_FOUND models/gemini-2.5-flash, API version v1beta")

    class FakeClient:
        models = FakeModels()

    search_service_instance._client = FakeClient()
    text, source = search_service_instance._llm_search("test query")
    assert source == "error"
    assert "Offline fallback" not in text
    assert "GEMINI_MODEL" in text
