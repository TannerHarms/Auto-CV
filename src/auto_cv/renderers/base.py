"""Abstract base for all renderers."""

from __future__ import annotations

import abc
from pathlib import Path

from auto_cv.models.resume import Resume
from auto_cv.models.style import StyleConfig


class BaseRenderer(abc.ABC):
    """All renderers implement this interface."""

    @abc.abstractmethod
    def render(self, resume: Resume, style: StyleConfig, output_dir: Path) -> Path:
        """Render the resume to *output_dir* and return the primary output path."""
        ...
