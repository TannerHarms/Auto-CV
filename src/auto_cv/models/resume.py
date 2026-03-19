"""Data models for resume content and structure."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SectionType(str, Enum):
    """Known section types with semantic meaning for renderers."""
    SUMMARY = "summary"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    SKILLS = "skills"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    PUBLICATIONS = "publications"
    AWARDS = "awards"
    VOLUNTEER = "volunteer"
    LANGUAGES = "languages"
    INTERESTS = "interests"
    REFERENCES = "references"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Shared value types
# ---------------------------------------------------------------------------

class DateRange(BaseModel):
    """A flexible date range for experience/education entries."""
    start: str  # Flexible: "Jan 2020", "2020", "2020-01", etc.
    end: str | None = None  # None ⇒ "Present"

    @property
    def display(self) -> str:
        return f"{self.start} – {self.end or 'Present'}"


class ContactInfo(BaseModel):
    """Contact information for the resume header."""
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    website: str | None = None
    extra: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Typed entry models
# ---------------------------------------------------------------------------

class ExperienceEntry(BaseModel):
    title: str
    organization: str
    location: str | None = None
    dates: DateRange | None = None
    highlights: list[str] = Field(default_factory=list)
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    degree: str
    institution: str
    location: str | None = None
    dates: DateRange | None = None
    gpa: str | None = None
    highlights: list[str] = Field(default_factory=list)
    coursework: list[str] = Field(default_factory=list)


class SkillCategory(BaseModel):
    name: str
    skills: list[str]


class ProjectEntry(BaseModel):
    name: str
    url: str | None = None
    dates: DateRange | None = None
    description: str | None = None
    highlights: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class CertificationEntry(BaseModel):
    name: str
    issuer: str | None = None
    date: str | None = None
    url: str | None = None


class PublicationEntry(BaseModel):
    title: str
    venue: str | None = None
    date: str | None = None
    url: str | None = None
    authors: list[str] = Field(default_factory=list)


class AwardEntry(BaseModel):
    title: str
    issuer: str | None = None
    date: str | None = None
    location: str | None = None
    description: str | None = None
    highlights: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Section
# ---------------------------------------------------------------------------

class Section(BaseModel):
    """A single resume section parsed from a markdown file."""
    id: str  # Derived from filename, e.g. "experience"
    title: str  # Display title, e.g. "Work Experience"
    section_type: SectionType = SectionType.CUSTOM
    order: int = 99
    visible: bool = True
    display: str = ""  # Display variant, e.g. "compact" or "expressive"

    # Raw YAML entry dicts (kept for renderers that want raw access)
    entries: list[dict[str, Any]] = Field(default_factory=list)

    # Raw markdown body (supplemental content / custom sections)
    raw_content: str = ""

    # Typed entry lists — populated by parser based on section_type
    experience_entries: list[ExperienceEntry] = Field(default_factory=list)
    education_entries: list[EducationEntry] = Field(default_factory=list)
    skill_categories: list[SkillCategory] = Field(default_factory=list)
    project_entries: list[ProjectEntry] = Field(default_factory=list)
    certification_entries: list[CertificationEntry] = Field(default_factory=list)
    publication_entries: list[PublicationEntry] = Field(default_factory=list)
    award_entries: list[AwardEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Page (HTML-only extra pages)
# ---------------------------------------------------------------------------

class Page(BaseModel):
    """An extra page for multi-page HTML output."""
    id: str
    title: str
    order: int = 99
    raw_content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Resume config & top-level model
# ---------------------------------------------------------------------------

class ResumeConfig(BaseModel):
    """Global resume configuration from _config.yml."""
    name: str
    title: str | None = None
    photo: str | None = None  # Path relative to vault
    contact: ContactInfo = Field(default_factory=ContactInfo)
    section_order: list[str] = Field(default_factory=list)
    html_meta: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VaultOverrides(BaseModel):
    """Tracks which optional override files exist in the vault."""
    resume_sty: bool = False
    resume_sty_path: str | None = None
    custom_css: bool = False
    custom_css_path: str | None = None
    custom_js: bool = False
    custom_js_path: str | None = None


class Resume(BaseModel):
    """The complete resume data model — output of the vault parser."""
    config: ResumeConfig
    sections: list[Section] = Field(default_factory=list)
    pages: list[Page] = Field(default_factory=list)
    overrides: VaultOverrides = Field(default_factory=VaultOverrides)

    def ordered_sections(self) -> list[Section]:
        """Return visible sections, respecting config section_order then order field."""
        visible = [s for s in self.sections if s.visible]
        if self.config.section_order:
            order_map = {sid: i for i, sid in enumerate(self.config.section_order)}
            return sorted(visible, key=lambda s: order_map.get(s.id, s.order + 1000))
        return sorted(visible, key=lambda s: s.order)

    def ordered_pages(self) -> list[Page]:
        return sorted(self.pages, key=lambda p: p.order)
