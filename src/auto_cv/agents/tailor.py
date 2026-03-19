"""TailorAgent — adjusts resume emphasis and keywords to match a job description."""

from __future__ import annotations

import json
from typing import Any

from auto_cv.agents.base import BaseAgent
from auto_cv.models.resume import Resume, Section, SectionType

_SYSTEM = """\
You are an expert resume consultant. Given a resume and a target job description,
your job is to tailor the resume so it better matches the role.

What you may do:
- Rewrite bullet points to emphasise relevant skills & achievements.
- Reorder highlights within an entry (most relevant first).
- Add keywords from the job description where they naturally fit.
- Adjust the professional summary to target the role.
- Mark sections as less visible by setting visible=false if they are irrelevant.

What you must NOT do:
- Invent experience, degrees, certifications, or skills the candidate doesn't have.
- Remove entries entirely (only reorder or toggle visibility).
- Change company names, dates, degree names, or other factual data.

Return ONLY valid JSON matching the schema described in the user message.
No markdown fences, no commentary.
"""

_USER_TEMPLATE = """\
## Job Description
{job_description}

## Current Resume (JSON)
{resume_json}

## Instructions
Return a JSON object with:
- "summary": rewritten summary text (string) targeting this role, or null to keep as-is.
- "section_order": suggested list of section IDs in priority order for this role.
- "experience_highlights": object mapping "title@organization" to rewritten highlights list.
- "project_highlights": object mapping project name to rewritten highlights list.
- "skill_emphasis": list of skill category names to keep (others can be deprioritised but not removed).

Preserve original bullet count per entry. Only change wording, not facts.
"""


class TailorAgent(BaseAgent):
    """Tailors a resume to a specific job description."""

    def process(self, resume: Resume, **kwargs: Any) -> Resume:
        job_description: str = kwargs.get("job_description", "")
        if not job_description:
            raise ValueError("TailorAgent requires a 'job_description' keyword argument.")

        resume_summary = self._summarise_resume(resume)
        prompt = _USER_TEMPLATE.format(
            job_description=job_description,
            resume_json=json.dumps(resume_summary, indent=2),
        )
        raw = self._chat(_SYSTEM, prompt, temperature=0.4)
        tailored = self._parse_response(raw)
        return self._apply(resume, tailored)

    # ------------------------------------------------------------------

    @staticmethod
    def _summarise_resume(resume: Resume) -> dict:
        """Build a concise JSON representation for the LLM context."""
        sections = []
        for s in resume.ordered_sections():
            sec: dict[str, Any] = {"id": s.id, "title": s.title, "type": s.section_type.value}
            if s.section_type == SectionType.SUMMARY:
                sec["text"] = s.raw_content.strip()
            elif s.section_type == SectionType.EXPERIENCE:
                sec["entries"] = [
                    {
                        "title": e.title,
                        "organization": e.organization,
                        "highlights": e.highlights,
                    }
                    for e in s.experience_entries
                ]
            elif s.section_type == SectionType.PROJECTS:
                sec["entries"] = [
                    {"name": e.name, "highlights": e.highlights, "technologies": e.technologies}
                    for e in s.project_entries
                ]
            elif s.section_type == SectionType.SKILLS:
                sec["categories"] = [
                    {"name": c.name, "skills": c.skills} for c in s.skill_categories
                ]
            elif s.section_type == SectionType.EDUCATION:
                sec["entries"] = [
                    {"degree": e.degree, "institution": e.institution}
                    for e in s.education_entries
                ]
            sections.append(sec)
        return {"name": resume.config.name, "sections": sections}

    @staticmethod
    def _parse_response(raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
        return json.loads(text)

    @staticmethod
    def _apply(resume: Resume, tailored: dict) -> Resume:
        new = resume.model_copy(deep=True)

        # Apply rewritten summary
        summary_text = tailored.get("summary")
        if summary_text:
            for section in new.sections:
                if section.section_type == SectionType.SUMMARY:
                    section.raw_content = summary_text
                    break

        # Apply suggested section order
        section_order = tailored.get("section_order")
        if section_order and isinstance(section_order, list):
            new.config.section_order = section_order

        # Apply experience rewrites
        exp_highlights = tailored.get("experience_highlights", {})
        for section in new.sections:
            if section.section_type == SectionType.EXPERIENCE:
                for entry in section.experience_entries:
                    key = f"{entry.title}@{entry.organization}"
                    if key in exp_highlights:
                        bullets = exp_highlights[key]
                        entry.highlights = bullets[: len(entry.highlights)]

        # Apply project rewrites
        proj_highlights = tailored.get("project_highlights", {})
        for section in new.sections:
            if section.section_type == SectionType.PROJECTS:
                for entry in section.project_entries:
                    if entry.name in proj_highlights:
                        bullets = proj_highlights[entry.name]
                        entry.highlights = bullets[: len(entry.highlights)]

        return new
