"""LLM provider abstraction.

Defines a minimal interface (`chat`) that all concrete providers must implement.
The factory in `factory.py` picks the right provider based on saved config.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Message:
    role: str
    content: str


class LLMError(Exception):
    """Raised when an LLM call fails for any reason (network, auth, parse)."""


class LLMProvider(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    def chat(self, system: str, user: str, *, temperature: float = 0.7, max_tokens: int = 2048) -> str:
        """Send messages and return the assistant's text response.

        Raises:
            LLMError: on any failure.
        """
