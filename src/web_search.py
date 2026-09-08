"""Backward-compatible wrapper for WebSearcher -> SearchService."""

from src.services.search_service import SearchService as WebSearcher, search_service

__all__ = ["WebSearcher", "search_service"]
