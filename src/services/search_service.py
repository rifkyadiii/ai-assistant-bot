"""Gemini LLM search and assistant service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from src.core.logger import activity_logger


class SearchService:
    """Handles natural language queries and web searches powered by Google Gemini."""

    # Currently supported models, in preference order for fallback
    SUPPORTED_MODELS: tuple[str, ...] = (
        "gemini-3.6-flash",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    )

    # Retired aliases that are no longer served by the API
    DEPRECATED_MODELS: tuple[str, ...] = ("gemini-pro", "gemini-1.0-pro")

    # Models to try in order of preference if primary fails
    FALLBACK_MODELS: list[str] = list(SUPPORTED_MODELS)

    def __init__(self) -> None:
        self._api_key: str = GEMINI_API_KEY
        self._configured_model: str = GEMINI_MODEL
        # Retired aliases no longer served by the API — prefer a supported model
        if self._configured_model in self.DEPRECATED_MODELS:
            self._configured_model = self.SUPPORTED_MODELS[0]

        self._client: Optional[Any] = None
        self._history: list[dict[str, Any]] = []

        if self._api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
                activity_logger.log(f"Gemini client initialized with model '{self._configured_model}'", category="SEARCH")
            except Exception as exc:
                activity_logger.log(f"Failed to initialize Gemini client: {exc}", category="SEARCH", level="WARNING")
        else:
            activity_logger.log("Gemini API key not configured; fallback search active", category="SEARCH", level="WARNING")

    @property
    def is_configured(self) -> bool:
        """Return whether the Gemini client is initialized."""
        return self._client is not None

    def search_and_respond(self, query: str) -> dict[str, Any]:
        """Search or answer query using Gemini or fallback."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return {
                "ok": False,
                "query": "",
                "response": "Please enter a search query or question.",
                "source": "validation",
                "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            }

        activity_logger.log(f"Search request: '{cleaned_query}'", category="SEARCH")

        if self._client:
            response_text, source = self._llm_search(cleaned_query)
        else:
            response_text = self._fallback_search(cleaned_query)
            source = "fallback"

        result = {
            "ok": True,
            "query": cleaned_query,
            "response": response_text,
            "source": source,
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        }

        self._history.append(result)
        if len(self._history) > 30:
            self._history.pop(0)

        return result

    @staticmethod
    def _classify_error(exc: Exception) -> str:
        """Return a human-readable, accurate explanation for a Gemini API error."""
        raw = str(exc)
        lowered = raw.lower()
        code = getattr(exc, "code", None)
        if code in (400, 404) or "not found" in lowered or "models/" in lowered:
            return (
                "The selected Gemini model is not available for this API key. "
                "Set GEMINI_MODEL in .env to a supported model (e.g. gemini-2.5-flash)."
            )
        if code in (401,) or ("invalid" in lowered and "key" in lowered):
            return "Your GEMINI_API_KEY appears to be invalid. Check the key in your .env file."
        if code in (403,) or "permission denied" in lowered:
            return "Access to the Gemini API was denied. Enable the Gemini API for your key in Google AI Studio."
        if code in (429,) or "resource exhausted" in lowered or "quota" in lowered:
            return "Gemini API quota exhausted. Check your usage limits or billing."
        if code in (500, 503) or "internal" in lowered or "unavailable" in lowered:
            return "The Gemini API is temporarily unavailable. Try again shortly."
        return raw[:300]

    def _llm_search(self, query: str) -> tuple[str, str]:
        """Query Gemini models with automatic fallback on model deprecation/errors."""
        client = self._client
        if client is None:
            activity_logger.log("Gemini client not configured; cannot run LLM search", category="SEARCH", level="WARNING")
            return "The Gemini client is not configured. Set GEMINI_API_KEY in .env to enable AI search.", "error"

        prompt = (
            f"You are a helpful and concise voice assistant.\n"
            f"User request / search query: {query}\n\n"
            f"Provide a clear, engaging, human-like response with key facts, direct answers, and concise explanation. "
            f"Format key points clearly with clean bullet points if helpful. Keep the tone natural and conversational."
        )

        models_to_try = [self._configured_model] + [
            m for m in self.FALLBACK_MODELS if m != self._configured_model
        ]

        last_exc: Exception | None = None
        errors_by_model: list[str] = []
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    activity_logger.log(f"Gemini response generated using {model_name}", category="SEARCH")
                    return response.text.strip(), f"gemini ({model_name})"
            except Exception as exc:
                last_exc = exc
                errors_by_model.append(f"{model_name}: {exc}")
                continue

        # If all model attempts fail, report a precise reason instead of a generic offline message
        reason = self._classify_error(last_exc) if last_exc else "unknown API error"
        activity_logger.log(
            f"Gemini API error across all models. Tried: {', '.join(errors_by_model)}",
            category="SEARCH", level="ERROR",
        )
        return (
            f"Unable to complete LLM search: {reason}.\n\n"
            f"Verify that GEMINI_API_KEY and GEMINI_MODEL in your .env are valid, then try again.",
            "error",
        )

    def _fallback_search(self, query: str) -> str:
        """Informative response when GEMINI_API_KEY is not set."""
        return (
            f"Here is what I found for '{query}':\n\n"
            f"• Note: The Gemini LLM API is not currently configured with an API key.\n"
            f"• To enable AI-powered natural language answers and web search grounding, "
            f"obtain an API key at https://aistudio.google.com and set `GEMINI_API_KEY=your_key` in your `.env` file.\n\n"
            f"• Quick web search shortcut: https://www.google.com/search?q={query.replace(' ', '+')}"
        )

    def get_history(self) -> list[dict[str, Any]]:
        """Return recent searches."""
        return list(reversed(self._history))

    def clear_history(self) -> None:
        """Clear search history."""
        self._history.clear()


# Global singleton instance
search_service = SearchService()
