"""Tests for data models (resume + style)."""

import pytest
from auto_cv.models.resume import (
    ContactInfo,
    DateRange,
    EducationEntry,
    ExperienceEntry,
    Page,
    Resume,
    ResumeConfig,
    Section,
    SectionType,
    SkillCategory,
    VaultOverrides,
)
from auto_cv.models.style import StyleConfig


# ---------------------------------------------------------------------------
# Section ordering
# ---------------------------------------------------------------------------


def _make_resume(section_order: list[str] | None = None) -> Resume:
    sections = [
        Section(id="skills", title="Skills", section_type=SectionType.SKILLS, order=3),
        Section(id="summary", title="Summary", section_type=SectionType.SUMMARY, order=1),
        Section(id="experience", title="Experience", section_type=SectionType.EXPERIENCE, order=2),
    ]
    config = ResumeConfig(
        name="Test",
        contact=ContactInfo(),
        section_order=section_order or [],
    )
    return Resume(config=config, sections=sections)


def test_ordered_sections_by_order_field():
    r = _make_resume()
    titles = [s.title for s in r.ordered_sections()]
    assert titles == ["Summary", "Experience", "Skills"]


def test_ordered_sections_respects_section_order():
    r = _make_resume(section_order=["skills", "summary", "experience"])
    titles = [s.title for s in r.ordered_sections()]
    assert titles == ["Skills", "Summary", "Experience"]


# ---------------------------------------------------------------------------
# Pages ordering
# ---------------------------------------------------------------------------


def test_ordered_pages():
    pages = [
        Page(title="B", id="b", order=2, raw_content="b"),
        Page(title="A", id="a", order=1, raw_content="a"),
    ]
    r = Resume(
        config=ResumeConfig(name="Test", contact=ContactInfo()),
        sections=[],
        pages=pages,
    )
    assert [p.id for p in r.ordered_pages()] == ["a", "b"]


# ---------------------------------------------------------------------------
# Style merging
# ---------------------------------------------------------------------------


def test_style_merge():
    base = StyleConfig()
    merged = base.merge({"colors": {"primary": "#FF0000"}, "fonts": {"heading": "Arial"}})
    assert merged.colors.primary == "#FF0000"
    assert merged.fonts.heading == "Arial"
    # Unchanged fields preserved
    assert merged.colors.secondary == base.colors.secondary


def test_style_css_variables():
    style = StyleConfig()
    css = style.to_css_variables()
    assert "--color-primary" in css
    assert "--font-heading" in css
    assert "--spacing-section-gap" in css


# ---------------------------------------------------------------------------
# Typed entries
# ---------------------------------------------------------------------------


def test_experience_entry_date_range():
    e = ExperienceEntry(title="Dev", organization="Co", dates=DateRange(start="2020-01", end="present"))
    assert e.dates.start == "2020-01"
    assert e.dates.end == "present"


def test_education_entry_optional_fields():
    e = EducationEntry(degree="BS", institution="Uni")
    assert e.gpa is None
    assert e.location is None


def test_vault_overrides_defaults():
    v = VaultOverrides()
    assert v.resume_sty is False
    assert v.custom_css is False
    assert v.custom_js is False
