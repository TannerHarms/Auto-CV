"""Abstract base for all renderers."""

from __future__ import annotations

import abc
from pathlib import Path

from auto_cv.models.resume import Resume
from auto_cv.models.style import StyleConfig


class BaseRenderer(abc.ABC):
    """All renderers implement this interface."""

    @staticmethod
    def prepare_output_dir(output_dir: Path, format_name: str) -> Path:
        """Return the directory a renderer should write into.

        Callers may pass either a shared root output directory such as
        ``output/`` or a format-specific path such as ``output/html``. This
        normalizes both cases so renderers do not create nested paths like
        ``output/html/html``.
        """
        if output_dir.name.lower() == format_name.lower():
            return output_dir
        return output_dir / format_name

    @abc.abstractmethod
    def render(self, resume: Resume, style: StyleConfig, output_dir: Path) -> Path:
        """Render the resume to *output_dir* and return the primary output path."""
        ...
