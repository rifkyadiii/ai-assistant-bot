"""Gemini LLM search and assistant service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from config.settings import GEMINI_API_KEY, GEMINI_MODEL
from src.core.logger import activity_logger


class SearchService:
    """Handles natural language queries and web searches powered by Google Gemini."""

    # Models to try in order of preference if primary fails
    FALLBACK_MODELS: list[str] = [
        "gemini-3.6-flash",
        "gemini-2.5-flash",
        "gemini-1.5-flash",
        "gemini-2.0-flash",
        "gemini-pro",
    ]

    def __init__(self) -> None:
        self._api_key: str = GEMINI_API_KEY
        self._configured_model: str = GEMINI_MODEL
        # If user left gemini-pro in settings or .env, prefer modern 3.6-flash first
        if self._configured_model in ("gemini-pro", "gemini-1.0-pro"):
            self._configured_model = "gemini-3.6-flash"

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

    def _llm_search(self, query: str) -> tuple[str, str]:
        """Query Gemini models with automatic fallback on model deprecation/errors."""
        prompt = (
            f"You are a helpful and concise voice assistant.\n"
            f"User request / search query: {query}\n\n"
            f"Provide a clear, engaging, human-like response with key facts, direct answers, and concise explanation. "
            f"Format key points clearly with clean bullet points if helpful. Keep the tone natural and conversational."
        )

        models_to_try = [self._configured_model] + [
            m for m in self.FALLBACK_MODELS if m != self._configured_model
        ]

        last_error = ""
        for model_name in models_to_try:
            try:
                response = self._client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                if response and response.text:
                    activity_logger.log(f"Gemini response generated using {model_name}", category="SEARCH")
                    return response.text.strip(), f"gemini ({model_name})"
            except Exception as exc:
                last_error = str(exc)
                continue

        # If all model attempts fail
        activity_logger.log(f"Gemini API error across all models: {last_error}", category="SEARCH", level="ERROR")
        return (
            f"Unable to complete LLM search: {last_error}.\n\n"
            f"Offline fallback: For questions regarding '{query}', verify your network connection "
            f"and check that your GEMINI_API_KEY in .env has valid quota.",
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
