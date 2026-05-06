"""
Data classes for LLM responses used across Revati's module
(News Sentiment, Chatbot, History).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LLMResponse:
    """Structured result returned by LLMService.generate_response()."""

    model_used: str          # "gemini" | "llama" | "mistral" | "none"
    provider: str            # "google" | "ollama" | "none"
    response: str            # raw text from the model
    fallback_used: bool      # True when a non-preferred provider was used
    error: Optional[str] = None   # set when all providers failed


@dataclass
class ParsedThemesResponse:
    """Parsed output of the news-themes LLM prompt."""

    themes: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class ParsedChatResponse:
    """Parsed output of a chat LLM prompt."""

    answer: str = ""
    bullets: list[str] = field(default_factory=list)
