"""Abstract base for all LLM agents.

Agents receive a Resume model and return a *modified copy*.
The deterministic pipeline then renders the modified resume.
"""

from __future__ import annotations

import abc
import os
from typing import Any

from auto_cv.models.resume import Resume


class BaseAgent(abc.ABC):
    """All agents implement this interface."""

    def __init__(self, *, model: str | None = None, **kwargs: Any) -> None:
        self.model = model or os.environ.get("AUTO_RESUME_MODEL", "gpt-4o")
        self.api_key = os.environ.get("OPENAI_API_KEY", "")

    @abc.abstractmethod
    def process(self, resume: Resume, **kwargs: Any) -> Resume:
        """Return a modified *copy* of the resume. Must not mutate the original."""
        ...

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _get_client(self):
        """Lazy-import and return an OpenAI client."""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "The 'openai' package is required for agents. "
                "Install it with: pip install auto-resume[agents]"
            )
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Set it before using agents."
            )
        return OpenAI(api_key=self.api_key)

    def _chat(self, system: str, user: str, *, temperature: float = 0.3) -> str:
        """Send a chat completion request and return the assistant message."""
        client = self._get_client()
        response = client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""
