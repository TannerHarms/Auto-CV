"""Vault reader — loads a markdown vault directory into Resume + StyleConfig."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import frontmatter
import yaml

from auto_cv.models.resume import (
    AwardEntry,
    CertificationEntry,
    ContactInfo,
    DateRange,
    EducationEntry,
    ExperienceEntry,
    Page,
    ProjectEntry,
    PublicationEntry,
    Resume,
    ResumeConfig,
    Section,
    SectionType,
    SkillCategory,
    VaultOverrides,
)
from auto_cv.models.style import StyleConfig
from auto_cv.parser.body_parser import parse_body, strip_body_title
from auto_cv.styles.presets import load_preset


def load_vault(vault_path: str | Path) -> tuple[Resume, StyleConfig]:
    """Load a complete resume vault from disk.

    Returns ``(Resume, StyleConfig)`` tuple.
    """
    vault = Path(vault_path).resolve()
    if not vault.is_dir():
        raise FileNotFoundError(f"Vault directory not found: {vault}")

    config = _load_config(vault)
    style = _load_style(vault)
    sections = _load_sections(vault)
    pages = _load_pages(vault)
    overrides = _detect_overrides(vault)

    resume = Resume(
        config=config,
        sections=sections,
        pages=pages,
        overrides=overrides,
    )
    return resume, style


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _load_config(vault: Path) -> ResumeConfig:
    config_path = vault / "_config.yml"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing _config.yml in vault: {vault}")

    with open(config_path, "r", encoding="utf-8") as f:
        raw: dict = yaml.safe_load(f) or {}

    contact_data = raw.pop("contact", {})
    section_order = raw.pop("section_order", raw.pop("sections", []))
    html_meta = raw.pop("html_meta", {})
    metadata = raw.pop("metadata", {})
    name = raw.pop("name", "Your Name")
    title = raw.pop("title", None)
    photo = raw.pop("photo", None)

    return ResumeConfig(
        name=name,
        title=title,
        photo=photo,
        contact=ContactInfo(**contact_data),
        section_order=section_order,
        html_meta=html_meta,
        metadata=metadata,
    )


# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------

def _load_style(vault: Path) -> StyleConfig:
    style_path = vault / "_style.yml"
    if not style_path.exists():
        return load_preset("classic", vault_path=vault)

    with open(style_path, "r", encoding="utf-8") as f:
        raw: dict = yaml.safe_load(f) or {}

    preset_name = raw.pop("preset", "classic")
    base = load_preset(preset_name, vault_path=vault)

    if raw:
        style = base.merge(raw)
    else:
        style = base

    # Resolve font_dir relative to vault if it's not absolute
    if style.latex.font_dir and not Path(style.latex.font_dir).is_absolute():
        style.latex.font_dir = str((vault / style.latex.font_dir).resolve())

    return style


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _load_sections(vault: Path) -> list[Section]:
    sections_dir = vault / "sections"
    if not sections_dir.is_dir():
        return []

    sections: list[Section] = []
    for md_file in sorted(sections_dir.glob("*.md")):
        section = _parse_section_file(md_file)
        if section:
            sections.append(section)
    return sections


def _parse_section_file(path: Path) -> Section | None:
    post = frontmatter.load(str(path))
    meta: dict[str, Any] = dict(post.metadata)
    content: str = post.content

    # Derive section id & order from filename (e.g. "02-experience.md")
    filename = path.stem
    parts = filename.split("-", 1)
    if len(parts) == 2 and parts[0].isdigit():
        order = int(parts[0])
        section_id = parts[1]
    else:
        order = meta.get("order", 99)
        section_id = filename

    # Resolve section type
    type_str = meta.get("type", section_id)
    try:
        section_type = SectionType(type_str.lower())
    except ValueError:
        section_type = SectionType.CUSTOM

    visible = meta.get("visible", True)

    # --- Entry source: YAML frontmatter vs. markdown body ---
    entries_raw: list[dict] = meta.get("entries", [])

    # Skills sections may use 'categories' instead of 'entries'
    if not entries_raw and "categories" in meta:
        entries_raw = meta.get("categories", [])

    # If no YAML entries, attempt to parse entries from the markdown body
    body_title: str | None = None
    if not entries_raw and content.strip():
        body_title, entries_raw = parse_body(section_type.value, content)

    # Title priority: frontmatter > body H1 > filename-derived
    title = meta.get(
        "title",
        body_title or section_id.replace("-", " ").replace("_", " ").title(),
    )

    # Strip the H1 heading from raw_content so renderers don't double it
    cleaned_content = strip_body_title(content) if content.strip() else content

    section = Section(
        id=section_id,
        title=title,
        section_type=section_type,
        order=order,
        visible=visible,
        display=meta.get("display", ""),
        raw_content=cleaned_content,
        entries=entries_raw,
    )

    _populate_typed_entries(section, entries_raw)
    return section


# ---------------------------------------------------------------------------
# Pages (HTML-only)
# ---------------------------------------------------------------------------

def _load_pages(vault: Path) -> list[Page]:
    pages_dir = vault / "pages"
    if not pages_dir.is_dir():
        return []

    pages: list[Page] = []
    for md_file in sorted(pages_dir.glob("*.md")):
        post = frontmatter.load(str(md_file))
        meta: dict[str, Any] = dict(post.metadata)

        filename = md_file.stem
        parts = filename.split("-", 1)
        if len(parts) == 2 and parts[0].isdigit():
            order = int(parts[0])
            page_id = parts[1]
        else:
            order = meta.get("order", 99)
            page_id = filename

        pages.append(Page(
            id=page_id,
            title=meta.get("title", page_id.replace("-", " ").replace("_", " ").title()),
            order=order,
            raw_content=post.content,
            metadata=meta,
        ))
    return pages


# ---------------------------------------------------------------------------
# Override detection
# ---------------------------------------------------------------------------

def _detect_overrides(vault: Path) -> VaultOverrides:
    overrides = VaultOverrides()

    sty = vault / "resume.sty"
    if sty.exists():
        overrides.resume_sty = True
        overrides.resume_sty_path = str(sty)

    css = vault / "custom.css"
    if css.exists():
        overrides.custom_css = True
        overrides.custom_css_path = str(css)

    js = vault / "custom.js"
    if js.exists():
        overrides.custom_js = True
        overrides.custom_js_path = str(js)

    return overrides


# ---------------------------------------------------------------------------
# Typed entry population
# ---------------------------------------------------------------------------

def _populate_typed_entries(section: Section, entries_raw: list[dict]) -> None:
    if not entries_raw:
        return

    if section.section_type == SectionType.EXPERIENCE:
        for e in entries_raw:
            section.experience_entries.append(ExperienceEntry(
                title=e.get("title", e.get("role", "")),
                organization=e.get("organization", e.get("company", "")),
                location=e.get("location"),
                dates=_parse_dates(e),
                highlights=e.get("highlights", []),
                description=e.get("description"),
                tags=e.get("tags", []),
            ))

    elif section.section_type == SectionType.EDUCATION:
        for e in entries_raw:
            section.education_entries.append(EducationEntry(
                degree=e.get("degree", ""),
                institution=e.get("institution", e.get("school", "")),
                location=e.get("location"),
                dates=_parse_dates(e),
                gpa=e.get("gpa"),
                highlights=e.get("highlights", []),
                coursework=e.get("coursework", []),
            ))

    elif section.section_type == SectionType.SKILLS:
        for e in entries_raw:
            section.skill_categories.append(SkillCategory(
                name=e.get("name", e.get("category", "")),
                skills=e.get("skills", []),
            ))

    elif section.section_type == SectionType.PROJECTS:
        for e in entries_raw:
            section.project_entries.append(ProjectEntry(
                name=e.get("name", ""),
                url=e.get("url"),
                dates=_parse_dates(e),
                description=e.get("description"),
                highlights=e.get("highlights", []),
                technologies=e.get("technologies", e.get("tech", [])),
            ))

    elif section.section_type == SectionType.CERTIFICATIONS:
        for e in entries_raw:
            section.certification_entries.append(CertificationEntry(
                name=e.get("name", ""),
                issuer=e.get("issuer"),
                date=e.get("date"),
                url=e.get("url"),
            ))

    elif section.section_type == SectionType.PUBLICATIONS:
        for e in entries_raw:
            section.publication_entries.append(PublicationEntry(
                title=e.get("title", ""),
                venue=e.get("venue"),
                date=e.get("date"),
                url=e.get("url"),
                authors=e.get("authors", []),
            ))

    elif section.section_type == SectionType.AWARDS:
        for e in entries_raw:
            section.award_entries.append(AwardEntry(
                title=e.get("title", ""),
                issuer=e.get("issuer"),
                date=e.get("date"),
                location=e.get("location"),
                description=e.get("description"),
                highlights=e.get("highlights", []),
            ))

    elif section.section_type == SectionType.VOLUNTEER:
        for e in entries_raw:
            section.experience_entries.append(ExperienceEntry(
                title=e.get("title", e.get("role", "")),
                organization=e.get("organization", e.get("company", "")),
                location=e.get("location"),
                dates=_parse_dates(e),
                highlights=e.get("highlights", []),
                description=e.get("description"),
                tags=e.get("tags", []),
            ))


def _parse_dates(entry: dict) -> DateRange | None:
    if "start" in entry:
        return DateRange(start=str(entry["start"]), end=_str_or_none(entry.get("end")))
    if "dates" in entry:
        d = entry["dates"]
        if isinstance(d, dict):
            return DateRange(start=str(d.get("start", "")), end=_str_or_none(d.get("end")))
        if isinstance(d, str):
            sep = " - " if " - " in d else "-"
            parts = d.split(sep, 1)
            if len(parts) == 2:
                return DateRange(start=parts[0].strip(), end=parts[1].strip() or None)
            return DateRange(start=d.strip())
    return None


def _str_or_none(val: Any) -> str | None:
    if val is None:
        return None
    return str(val)
