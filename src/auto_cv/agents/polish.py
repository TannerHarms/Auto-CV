"""PolishAgent — rewrites bullet points for impact and conciseness."""

from __future__ import annotations

import json
from typing import Any

from auto_cv.agents.base import BaseAgent
from auto_cv.models.resume import Resume, Section, SectionType

_SYSTEM = """\
You are an expert resume writer. Your job is to rewrite resume bullet points
to be more impactful, concise, and results-oriented.

Rules:
- Start every bullet with a strong action verb.
- Quantify results wherever plausible (use the numbers already present, or add
  approximate metrics only when clearly implied by context).
- Keep each bullet to one line (≤ 120 characters when possible).
- Preserve the original meaning — do NOT invent facts.
- Do NOT add new bullets or remove existing ones.
- Return ONLY valid JSON — no markdown fences, no commentary.
"""

_USER_TEMPLATE = """\
Below are resume bullet points grouped by section. Rewrite each bullet according
to the rules. Return a JSON object mapping each section title to a list of
rewritten bullets, preserving the original order.

{sections_json}
"""


class PolishAgent(BaseAgent):
    """Rewrites experience/project bullet points for impact."""

    def process(self, resume: Resume, **kwargs: Any) -> Resume:
        sections_to_polish = self._extract_bullets(resume)
        if not sections_to_polish:
            return resume

        prompt = _USER_TEMPLATE.format(sections_json=json.dumps(sections_to_polish, indent=2))
        raw = self._chat(_SYSTEM, prompt, temperature=0.3)
        polished = self._parse_response(raw)

        return self._apply(resume, polished)

    # ------------------------------------------------------------------

    @staticmethod
    def _extract_bullets(resume: Resume) -> dict[str, list[str]]:
        """Collect highlights from experience and project sections."""
        result: dict[str, list[str]] = {}
        for section in resume.sections:
            if section.section_type == SectionType.EXPERIENCE:
                for entry in section.experience_entries:
                    if entry.highlights:
                        key = f"{section.title}::{entry.title}@{entry.organization}"
                        result[key] = list(entry.highlights)
            elif section.section_type == SectionType.PROJECTS:
                for entry in section.project_entries:
                    if entry.highlights:
                        key = f"{section.title}::{entry.name}"
                        result[key] = list(entry.highlights)
        return result

    @staticmethod
    def _parse_response(raw: str) -> dict[str, list[str]]:
        """Parse the LLM JSON response, tolerating markdown fences."""
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
        return json.loads(text)

    @staticmethod
    def _apply(resume: Resume, polished: dict[str, list[str]]) -> Resume:
        """Apply polished bullets back onto a deep copy of the resume."""
        new = resume.model_copy(deep=True)
        for section in new.sections:
            if section.section_type == SectionType.EXPERIENCE:
                for entry in section.experience_entries:
                    key = f"{section.title}::{entry.title}@{entry.organization}"
                    if key in polished:
                        bullets = polished[key]
                        entry.highlights = bullets[: len(entry.highlights)]
            elif section.section_type == SectionType.PROJECTS:
                for entry in section.project_entries:
                    key = f"{section.title}::{entry.name}"
                    if key in polished:
                        bullets = polished[key]
                        entry.highlights = bullets[: len(entry.highlights)]
        return new
