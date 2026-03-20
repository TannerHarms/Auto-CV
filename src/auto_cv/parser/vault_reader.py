"""Vault reader — loads a markdown vault directory into Resume + StyleConfig."""

from __future__ import annotations

import re
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
    LanguageEntry,
    ReferenceEntry,
    Page,
    ProjectConfig,
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


def _is_master_vault(vault: Path) -> bool:
    """Return True if the vault uses the master/projects layout."""
    return (vault / "_master").is_dir()


def load_vault(
    vault_path: str | Path,
    project: str | None = None,
) -> tuple[Resume, StyleConfig]:
    """Load a resume vault from disk.

    If the vault contains a ``_master/`` directory and *project* is given,
    delegates to :func:`load_project`.  Otherwise falls back to loading
    the vault as a flat (legacy) layout.

    Returns ``(Resume, StyleConfig)`` tuple.
    """
    vault = Path(vault_path).resolve()
    if not vault.is_dir():
        raise FileNotFoundError(f"Vault directory not found: {vault}")

    if _is_master_vault(vault) and project:
        return load_project(vault, project)

    # Legacy flat vault — _config.yml + sections/ at vault root.
    # Also handles master-vault when no project is given: use _master/ as
    # the flat root (so `auto-cv build <vault>` still works).
    root = vault / "_master" if _is_master_vault(vault) else vault

    config = _load_config(root)
    style = _load_style(root)
    sections = _load_sections(root)
    pages = _load_pages(root)
    overrides = _detect_overrides(root)

    resume = Resume(
        config=config,
        sections=sections,
        pages=pages,
        overrides=overrides,
    )
    return resume, style


# ---------------------------------------------------------------------------
# Project-based loading
# ---------------------------------------------------------------------------

def list_projects(vault_path: str | Path) -> list[str]:
    """Return names of all projects in a master vault."""
    vault = Path(vault_path).resolve()
    projects_dir = vault / "projects"
    if not projects_dir.is_dir():
        return []
    return sorted(
        d.name for d in projects_dir.iterdir()
        if d.is_dir() and (
            (d / "header.md").exists() or (d / "_project.yml").exists()
        )
    )


def load_project(
    vault_path: str | Path,
    project_name: str,
) -> tuple[Resume, StyleConfig]:
    """Load a specific project resume from a master vault.

    Resolution logic:
    1. Load master ``_config.yml``, deep-merge with project config overrides.
    2. For each entry in the project's ``include`` list, look for a local
       override in ``projects/<name>/sections/`` first, then fall back to
       ``_master/sections/``.  Path segments like ``experience/acme-corp``
       resolve to ``_master/sections/experience/acme-corp.md``.
    3. Style comes from the project's ``_style.yml`` (falls back to master's).
    4. Pages come from the project's ``pages/`` (falls back to master's).
    """
    vault = Path(vault_path).resolve()
    master = vault / "_master"
    project_dir = vault / "projects" / project_name

    if not master.is_dir():
        raise FileNotFoundError(f"Master vault not found: {master}")
    if not project_dir.is_dir():
        raise FileNotFoundError(f"Project not found: {project_dir}")

    project_cfg = _load_project_config(project_dir)

    # --- Config: master + project overrides ---
    config = _load_config(master)
    if project_cfg.config:
        config = _merge_resume_config(config, project_cfg.config)

    # Apply project's section_order to config if specified
    if project_cfg.section_order:
        config.section_order = project_cfg.section_order

    # --- Sections: resolve include list ---
    if project_cfg.include:
        sections = _resolve_project_sections(
            master, project_dir, project_cfg.include
        )
    else:
        # No include list — use all master sections
        sections = _load_sections(master)

    # --- Style: project-local > master ---
    if (project_dir / "_style.yml").exists():
        style = _load_style(project_dir)
    else:
        style = _load_style(master)

    # --- Pages: project-local > master ---
    pages = _load_pages(project_dir)
    if not pages:
        pages = _load_pages(master)

    # --- Overrides: project-local > master ---
    overrides = _detect_overrides(project_dir)
    if not overrides.custom_css and not overrides.resume_sty:
        overrides = _detect_overrides(master)

    resume = Resume(
        config=config,
        sections=sections,
        pages=pages,
        overrides=overrides,
    )
    return resume, style


def _load_project_config(project_dir: Path) -> ProjectConfig:
    """Load project config from ``header.md`` or ``_project.yml``."""
    header_path = project_dir / "header.md"
    if header_path.exists():
        return _load_project_config_from_header(header_path)

    path = project_dir / "_project.yml"
    if not path.exists():
        return ProjectConfig()

    with open(path, "r", encoding="utf-8") as f:
        raw: dict = yaml.safe_load(f) or {}

    return ProjectConfig(
        include=raw.get("include", []),
        section_order=raw.get("section_order", []),
        config=raw.get("config", {}),
    )


def _merge_resume_config(base: ResumeConfig, overrides: dict) -> ResumeConfig:
    """Deep-merge override dict into an existing ResumeConfig."""
    base_dict = base.model_dump()
    for key, value in overrides.items():
        if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
            base_dict[key] = {**base_dict[key], **value}
        else:
            base_dict[key] = value
    return ResumeConfig.model_validate(base_dict)


def _resolve_project_sections(
    master: Path,
    project_dir: Path,
    include: list[str],
) -> list[Section]:
    """Resolve the include list to Section objects.

    For each include entry (e.g. ``"experience/acme-corp"``):
    1. Check ``project_dir/sections/<path>.md`` (local override).
    2. Fall back to ``master/sections/<path>.md``.
    3. If ``<path>`` matches a directory in master, load all ``.md`` files
       in that directory (e.g. ``"experience"`` loads all experience entries).
    """
    sections: list[Section] = []
    seen_ids: set[str] = set()

    for order_idx, include_path in enumerate(include):
        section = _resolve_one_include(master, project_dir, include_path, order_idx)
        if section:
            for s in section:
                if s.id not in seen_ids:
                    sections.append(s)
                    seen_ids.add(s.id)

    return sections


def _resolve_one_include(
    master: Path,
    project_dir: Path,
    include_path: str,
    order_idx: int,
) -> list[Section]:
    """Resolve a single include entry to one or more Section objects."""
    # Normalise separators
    include_path = include_path.replace("\\", "/")

    # 1. Check for local project override file
    local_file = project_dir / "sections" / f"{include_path}.md"
    if local_file.is_file():
        s = _parse_section_file(local_file)
        if s:
            s.order = order_idx
            return [s]

    # 2. Check for master section file
    master_file = master / "sections" / f"{include_path}.md"
    if master_file.is_file():
        s = _parse_section_file(master_file)
        if s:
            s.order = order_idx
            return [s]

    # 3. Check if include_path refers to a directory of sections
    master_dir = master / "sections" / include_path
    if master_dir.is_dir():
        results: list[Section] = []
        for md_file in sorted(master_dir.glob("*.md")):
            # Check for local override of this specific file
            relative = md_file.relative_to(master / "sections")
            local_override = project_dir / "sections" / relative.with_suffix(".md")
            if local_override.is_file():
                s = _parse_section_file(local_override)
            else:
                s = _parse_section_file(md_file)
            if s:
                s.order = order_idx
                results.append(s)
        return results

    return []


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _load_config(vault: Path) -> ResumeConfig:
    # Prefer header.md, fall back to _config.yml
    header_path = vault / "header.md"
    if header_path.exists():
        return _load_config_from_header(header_path)

    config_path = vault / "_config.yml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Missing header.md or _config.yml in vault: {vault}"
        )

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
# header.md parsing
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^[\+\d\(\)\-\s\.]{7,}$")
_MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _parse_contact_items(items: list[str]) -> dict[str, str]:
    """Classify pipe-separated contact fragments into ContactInfo fields."""
    contact: dict[str, str] = {}
    for item in items:
        item = item.strip()
        if not item:
            continue

        # Markdown link: [text](url)
        link = _MD_LINK_RE.match(item)
        if link:
            url = link.group(2)
            if "linkedin.com" in url:
                contact["linkedin"] = url.rstrip("/").split("/")[-1]
            elif "github.com" in url:
                contact["github"] = url.rstrip("/").split("/")[-1]
            else:
                contact["website"] = url
            continue

        # Bare email
        if _EMAIL_RE.match(item):
            contact["email"] = item
            continue

        # Phone number
        if _PHONE_RE.match(item):
            contact["phone"] = item
            continue

        # Bare URL
        if item.startswith("http://") or item.startswith("https://"):
            if "linkedin.com" in item:
                contact["linkedin"] = item.rstrip("/").split("/")[-1]
            elif "github.com" in item:
                contact["github"] = item.rstrip("/").split("/")[-1]
            else:
                contact["website"] = item
            continue

        # Default: location
        contact["location"] = item

    return contact


def _load_config_from_header(path: Path) -> ResumeConfig:
    """Parse a ``header.md`` file into a :class:`ResumeConfig`.

    Format::

        ---
        photo: headshot.jpg
        section_order: [summary, experience, ...]
        html_meta:
          title: "..."
        ---
        # Full Name
        *Job Title*

        email@example.com | +1-555-0000 | City, ST
        [LinkedIn](https://linkedin.com/in/handle) | [GitHub](https://github.com/handle)
    """
    post = frontmatter.load(str(path))
    fm: dict = dict(post.metadata)
    body: str = post.content.strip()

    section_order = fm.pop("section_order", fm.pop("sections", []))
    html_meta = fm.pop("html_meta", {})
    metadata = fm.pop("metadata", {})
    photo = fm.pop("photo", None)

    # Parse body for name, title, contact
    name = "Your Name"
    title = None
    contact_items: list[str] = []

    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        # H1 → name
        if stripped.startswith("# ") and not stripped.startswith("## "):
            name = stripped[2:].strip()
            continue
        # *italic* → title  (but not **bold**)
        if (
            stripped.startswith("*")
            and stripped.endswith("*")
            and not stripped.startswith("**")
        ):
            title = stripped.strip("*").strip()
            continue
        # H2 → title (alternative syntax)
        if stripped.startswith("## "):
            title = stripped[3:].strip()
            continue
        # Contact line — contains | or recognised tokens
        if "|" in stripped:
            contact_items.extend(i.strip() for i in stripped.split("|"))
        elif _EMAIL_RE.match(stripped) or _PHONE_RE.match(stripped):
            contact_items.append(stripped)
        elif _MD_LINK_RE.match(stripped):
            contact_items.append(stripped)
        elif stripped.startswith("http://") or stripped.startswith("https://"):
            contact_items.append(stripped)

    contact_data = _parse_contact_items(contact_items) if contact_items else {}

    return ResumeConfig(
        name=name,
        title=title,
        photo=photo,
        contact=ContactInfo(**contact_data),
        section_order=section_order,
        html_meta=html_meta,
        metadata=metadata,
    )


def _load_project_config_from_header(path: Path) -> ProjectConfig:
    """Parse a project ``header.md`` into a :class:`ProjectConfig`.

    Frontmatter carries ``include`` and ``section_order``.
    Body may override config fields (name, title, contact).
    """
    post = frontmatter.load(str(path))
    fm: dict = dict(post.metadata)
    body: str = post.content.strip()

    include = fm.pop("include", [])
    section_order = fm.pop("section_order", [])

    # Parse body for config overrides
    config_overrides: dict[str, Any] = {}
    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# ") and not stripped.startswith("## "):
            config_overrides["name"] = stripped[2:].strip()
        elif (
            stripped.startswith("*")
            and stripped.endswith("*")
            and not stripped.startswith("**")
        ):
            config_overrides["title"] = stripped.strip("*").strip()
        elif stripped.startswith("## "):
            config_overrides["title"] = stripped[3:].strip()
        elif "|" in stripped:
            items = [i.strip() for i in stripped.split("|")]
            config_overrides["contact"] = _parse_contact_items(items)

    return ProjectConfig(
        include=include,
        section_order=section_order,
        config=config_overrides,
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
                description=e.get("description"),
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
                description=e.get("description"),
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

    elif section.section_type == SectionType.SERVICE:
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

    elif section.section_type == SectionType.LANGUAGES:
        for e in entries_raw:
            section.language_entries.append(LanguageEntry(
                name=e.get("name", ""),
                proficiency=e.get("proficiency"),
            ))

    elif section.section_type == SectionType.INTERESTS:
        for e in entries_raw:
            section.skill_categories.append(SkillCategory(
                name=e.get("name", e.get("category", "")),
                skills=e.get("skills", []),
            ))

    elif section.section_type == SectionType.REFERENCES:
        for e in entries_raw:
            section.reference_entries.append(ReferenceEntry(
                name=e.get("name", ""),
                title=e.get("title"),
                organization=e.get("organization"),
                email=e.get("email"),
                phone=e.get("phone"),
                relationship=e.get("relationship"),
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
