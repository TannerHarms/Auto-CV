"""LayoutAgent — suggests section ordering and visibility for a target role."""

from __future__ import annotations

import json
from typing import Any

from auto_cv.agents.base import BaseAgent
from auto_cv.models.resume import Resume, SectionType

_SYSTEM = """\
You are an expert resume layout consultant. Given the sections of a resume and
an optional target role, you suggest the optimal section ordering and visibility
to make the strongest impression.

Rules:
- Return a JSON object with two keys:
  "section_order": list of section IDs in recommended order.
  "hidden": list of section IDs that should be hidden (set visible=false).
- Only hide sections that are clearly irrelevant to the target role.
  If no target role is given, do not hide anything.
- Put the most impactful sections first (e.g. summary, then the section
  most relevant to the role, then supporting sections).
- Return ONLY valid JSON — no markdown fences, no commentary.
"""

_USER_TEMPLATE = """\
## Sections
{sections_json}

## Target Role
{target_role}

Return the recommended section_order and hidden list.
"""


class LayoutAgent(BaseAgent):
    """Suggests section ordering and visibility."""

    def process(self, resume: Resume, **kwargs: Any) -> Resume:
        target_role: str = kwargs.get("target_role", resume.config.title or "general")

        sections_info = [
            {
                "id": s.id,
                "title": s.title,
                "type": s.section_type.value,
                "entry_count": (
                    len(s.experience_entries) or len(s.education_entries)
                    or len(s.skill_categories) or len(s.project_entries)
                    or len(s.certification_entries) or (1 if s.raw_content.strip() else 0)
                ),
            }
            for s in resume.sections
        ]

        prompt = _USER_TEMPLATE.format(
            sections_json=json.dumps(sections_info, indent=2),
            target_role=target_role,
        )
        raw = self._chat(_SYSTEM, prompt, temperature=0.2)
        layout = self._parse_response(raw)
        return self._apply(resume, layout)

    @staticmethod
    def _parse_response(raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
        return json.loads(text)

    @staticmethod
    def _apply(resume: Resume, layout: dict) -> Resume:
        new = resume.model_copy(deep=True)

        section_order = layout.get("section_order")
        if section_order and isinstance(section_order, list):
            new.config.section_order = section_order

        hidden = set(layout.get("hidden", []))
        if hidden:
            for section in new.sections:
                if section.id in hidden:
                    section.visible = False

        return new
