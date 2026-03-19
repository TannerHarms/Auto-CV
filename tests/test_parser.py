"""Tests for vault parser."""

import pytest
from pathlib import Path

from auto_cv.parser.vault_reader import load_vault


EXAMPLE_VAULT = Path(__file__).resolve().parent.parent / "example_vault"


@pytest.fixture
def vault_data():
    """Load the example vault once per test session."""
    return load_vault(EXAMPLE_VAULT)


def test_load_vault_returns_tuple(vault_data):
    resume, style = vault_data
    assert resume is not None
    assert style is not None


def test_config_name(vault_data):
    resume, _ = vault_data
    assert resume.config.name == "Jordan Rivera"


def test_config_contact(vault_data):
    resume, _ = vault_data
    assert resume.config.contact.email == "jordan.rivera@example.com"
    assert resume.config.contact.github == "jrivera-dev"


def test_section_count(vault_data):
    resume, _ = vault_data
    assert len(resume.sections) == 6


def test_section_types(vault_data):
    resume, _ = vault_data
    types = {s.section_type.value for s in resume.sections}
    assert "experience" in types
    assert "education" in types
    assert "skills" in types
    assert "projects" in types
    assert "certifications" in types
    assert "summary" in types


def test_experience_entries(vault_data):
    resume, _ = vault_data
    exp = next(s for s in resume.sections if s.section_type.value == "experience")
    assert len(exp.experience_entries) == 4
    assert exp.experience_entries[0].title == "Staff Software Engineer"


def test_education_entries(vault_data):
    resume, _ = vault_data
    edu = next(s for s in resume.sections if s.section_type.value == "education")
    assert len(edu.education_entries) == 2


def test_skills_categories(vault_data):
    resume, _ = vault_data
    skills = next(s for s in resume.sections if s.section_type.value == "skills")
    assert len(skills.skill_categories) == 5
    names = [c.name for c in skills.skill_categories]
    assert "Languages" in names


def test_projects_entries(vault_data):
    resume, _ = vault_data
    proj = next(s for s in resume.sections if s.section_type.value == "projects")
    assert len(proj.project_entries) == 3


def test_pages_loaded(vault_data):
    resume, _ = vault_data
    assert len(resume.pages) == 1
    assert resume.pages[0].title == "Portfolio"


def test_style_overrides(vault_data):
    _, style = vault_data
    # The example vault has _style.yml with color overrides
    assert style.colors.primary == "#1B3A4B"


def test_custom_css_detected(vault_data):
    resume, _ = vault_data
    assert resume.overrides.custom_css is True


def test_missing_vault_raises():
    with pytest.raises(FileNotFoundError):
        load_vault("/nonexistent/vault/path")
