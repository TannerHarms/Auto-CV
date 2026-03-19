"""Tests for agent modules — deterministic logic only (no LLM calls)."""

import pytest

from auto_cv.models.resume import (
    ContactInfo,
    DateRange,
    ExperienceEntry,
    Page,
    ProjectEntry,
    Resume,
    ResumeConfig,
    Section,
    SectionType,
    SkillCategory,
)
from auto_cv.agents.polish import PolishAgent
from auto_cv.agents.tailor import TailorAgent
from auto_cv.agents.layout import LayoutAgent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_resume() -> Resume:
    return Resume(
        config=ResumeConfig(
            name="Test User",
            title="Software Engineer",
            contact=ContactInfo(email="test@example.com"),
            section_order=["summary", "experience", "skills", "projects"],
        ),
        sections=[
            Section(
                id="summary",
                title="Summary",
                section_type=SectionType.SUMMARY,
                order=1,
                raw_content="Experienced engineer with 5 years of experience.",
            ),
            Section(
                id="experience",
                title="Experience",
                section_type=SectionType.EXPERIENCE,
                order=2,
                experience_entries=[
                    ExperienceEntry(
                        title="Senior Dev",
                        organization="BigCorp",
                        dates=DateRange(start="2020", end="present"),
                        highlights=["Built an API", "Led a team of 3"],
                    ),
                    ExperienceEntry(
                        title="Dev",
                        organization="SmallCo",
                        dates=DateRange(start="2018", end="2020"),
                        highlights=["Wrote tests", "Deployed to AWS"],
                    ),
                ],
            ),
            Section(
                id="skills",
                title="Skills",
                section_type=SectionType.SKILLS,
                order=3,
                skill_categories=[
                    SkillCategory(name="Languages", skills=["Python", "Go"]),
                    SkillCategory(name="Tools", skills=["Docker", "Git"]),
                ],
            ),
            Section(
                id="projects",
                title="Projects",
                section_type=SectionType.PROJECTS,
                order=4,
                project_entries=[
                    ProjectEntry(
                        name="CoolApp",
                        highlights=["Open-sourced on GitHub", "500 stars"],
                        technologies=["Python", "React"],
                    ),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# PolishAgent — extract & apply logic
# ---------------------------------------------------------------------------


class TestPolishAgent:
    def test_extract_bullets(self, sample_resume):
        bullets = PolishAgent._extract_bullets(sample_resume)
        assert "Experience::Senior Dev@BigCorp" in bullets
        assert "Experience::Dev@SmallCo" in bullets
        assert "Projects::CoolApp" in bullets
        assert len(bullets["Experience::Senior Dev@BigCorp"]) == 2

    def test_apply_preserves_structure(self, sample_resume):
        polished = {
            "Experience::Senior Dev@BigCorp": ["Architected REST API", "Managed team of 3"],
            "Experience::Dev@SmallCo": ["Implemented test suite", "Automated AWS deploys"],
            "Projects::CoolApp": ["Open-sourced project on GitHub"],
        }
        result = PolishAgent._apply(sample_resume, polished)
        # Original not mutated
        exp = next(s for s in sample_resume.sections if s.id == "experience")
        assert exp.experience_entries[0].highlights[0] == "Built an API"

        # New resume has polished bullets
        new_exp = next(s for s in result.sections if s.id == "experience")
        assert new_exp.experience_entries[0].highlights[0] == "Architected REST API"
        assert new_exp.experience_entries[1].highlights[1] == "Automated AWS deploys"

    def test_apply_truncates_to_original_count(self, sample_resume):
        polished = {
            "Experience::Senior Dev@BigCorp": ["A", "B", "C", "D"],  # original has 2
        }
        result = PolishAgent._apply(sample_resume, polished)
        new_exp = next(s for s in result.sections if s.id == "experience")
        assert len(new_exp.experience_entries[0].highlights) == 2

    def test_parse_response_strips_fences(self):
        raw = '```json\n{"key": ["val"]}\n```'
        parsed = PolishAgent._parse_response(raw)
        assert parsed == {"key": ["val"]}

    def test_parse_response_plain_json(self):
        raw = '{"key": ["val"]}'
        parsed = PolishAgent._parse_response(raw)
        assert parsed == {"key": ["val"]}


# ---------------------------------------------------------------------------
# TailorAgent — summarise & apply logic
# ---------------------------------------------------------------------------


class TestTailorAgent:
    def test_summarise_resume(self, sample_resume):
        summary = TailorAgent._summarise_resume(sample_resume)
        assert summary["name"] == "Test User"
        assert len(summary["sections"]) == 4
        types = {s["type"] for s in summary["sections"]}
        assert "experience" in types
        assert "skills" in types

    def test_apply_summary_rewrite(self, sample_resume):
        tailored = {
            "summary": "Rewritten summary for a DevOps role.",
            "section_order": None,
            "experience_highlights": {},
            "project_highlights": {},
        }
        result = TailorAgent._apply(sample_resume, tailored)
        new_sum = next(s for s in result.sections if s.id == "summary")
        assert new_sum.raw_content == "Rewritten summary for a DevOps role."
        # Original unchanged
        old_sum = next(s for s in sample_resume.sections if s.id == "summary")
        assert old_sum.raw_content == "Experienced engineer with 5 years of experience."

    def test_apply_section_order(self, sample_resume):
        tailored = {
            "summary": None,
            "section_order": ["skills", "experience", "summary", "projects"],
            "experience_highlights": {},
            "project_highlights": {},
        }
        result = TailorAgent._apply(sample_resume, tailored)
        assert result.config.section_order == ["skills", "experience", "summary", "projects"]

    def test_apply_experience_highlights(self, sample_resume):
        tailored = {
            "summary": None,
            "section_order": None,
            "experience_highlights": {
                "Senior Dev@BigCorp": ["Designed scalable API", "Led cross-functional team"],
            },
            "project_highlights": {},
        }
        result = TailorAgent._apply(sample_resume, tailored)
        new_exp = next(s for s in result.sections if s.id == "experience")
        assert new_exp.experience_entries[0].highlights[0] == "Designed scalable API"

    def test_requires_job_description(self, sample_resume):
        agent = TailorAgent.__new__(TailorAgent)
        with pytest.raises(ValueError, match="job_description"):
            agent.process(sample_resume)


# ---------------------------------------------------------------------------
# LayoutAgent — apply logic
# ---------------------------------------------------------------------------


class TestLayoutAgent:
    def test_apply_reorders_sections(self, sample_resume):
        layout = {
            "section_order": ["projects", "experience", "skills", "summary"],
            "hidden": [],
        }
        result = LayoutAgent._apply(sample_resume, layout)
        assert result.config.section_order[0] == "projects"

    def test_apply_hides_sections(self, sample_resume):
        layout = {
            "section_order": ["summary", "experience", "skills"],
            "hidden": ["projects"],
        }
        result = LayoutAgent._apply(sample_resume, layout)
        proj = next(s for s in result.sections if s.id == "projects")
        assert proj.visible is False
        # Original unchanged
        orig_proj = next(s for s in sample_resume.sections if s.id == "projects")
        assert orig_proj.visible is True

    def test_apply_empty_hidden(self, sample_resume):
        layout = {"section_order": ["summary"], "hidden": []}
        result = LayoutAgent._apply(sample_resume, layout)
        assert all(s.visible for s in result.sections)


# ---------------------------------------------------------------------------
# BaseAgent — import validation
# ---------------------------------------------------------------------------


class TestBaseAgent:
    def test_missing_openai_raises(self):
        """_get_client should raise if openai is not available or no key."""
        from auto_cv.agents.base import BaseAgent

        class DummyAgent(BaseAgent):
            def process(self, resume, **kwargs):
                return resume

        agent = DummyAgent()
        agent.api_key = ""
        with pytest.raises((ValueError, ImportError)):
            agent._get_client()
