"""Parse structured resume entries from natural markdown body content.

Supports a human-friendly authoring format where entries are written as
markdown headings, bold metadata lines, and bullet lists rather than
YAML frontmatter arrays.

Expected patterns per section type
-----------------------------------

**Experience / Education:**
    ## Entry Title
    **Organization** | Location | 2022-03 – present

    - Highlight one
    - Highlight two

**Skills:**
    ### Category Name
    Python, TypeScript, Go, SQL

    (or bullet list)

**Projects:**
    ## [Project Name](https://url)
    Description paragraph.

    **Technologies:** Python, Jinja2, Pydantic

    - Optional highlight

**Certifications / Awards / Publications:**
    ## Entry Name
    **Issuer** | 2023-05
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_body(section_type: str, content: str) -> tuple[str | None, list[dict]]:
    """Parse markdown body into an optional title and a list of entry dicts.

    Returns ``(title_from_body, entries)``.  *title_from_body* is extracted
    from a leading ``# Heading`` if present; the heading is stripped before
    entry parsing.
    """
    content = content.strip()
    if not content:
        return None, []

    title, body = _strip_h1(content)

    parser = _PARSERS.get(section_type)
    if parser is None:
        return title, []

    entries = parser(body)
    return title, entries


def strip_body_title(content: str) -> str:
    """Return *content* with any leading ``# Heading`` removed.

    Useful for keeping ``raw_content`` free of the section title that
    templates already render separately.
    """
    _, body = _strip_h1(content.strip())
    return body


# ---------------------------------------------------------------------------
# Heading / structural helpers
# ---------------------------------------------------------------------------

def _strip_h1(content: str) -> tuple[str | None, str]:
    """Extract a leading H1 heading and return (title, remaining_content)."""
    lines = content.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(r"^#\s+(.+)$", stripped)
        if m:
            title = m.group(1).strip()
            rest = "\n".join(lines[i + 1:]).strip()
            return title, rest
        # First non-empty line is not an H1 → no title in body
        break
    return None, content


def _split_by_heading(content: str, level: int = 2) -> list[tuple[str, str]]:
    """Split *content* by headings of *level*.

    Returns ``[(heading_text, body_text), ...]``.
    Content before the first heading is discarded.
    """
    prefix = "#" * level
    pattern = re.compile(rf"^{prefix}\s+(.+)$", re.MULTILINE)

    positions: list[tuple[int, str]] = []
    for m in pattern.finditer(content):
        positions.append((m.end(), m.group(1).strip()))

    if not positions:
        return []

    entries: list[tuple[str, str]] = []
    for idx, (end_pos, heading) in enumerate(positions):
        if idx + 1 < len(positions):
            body = content[end_pos : positions[idx + 1][0] - len(prefix) - len(positions[idx + 1][1]) - 2]
        else:
            body = content[end_pos:]
        entries.append((heading, body.strip()))
    return entries


def _split_by_heading_simple(content: str, level: int = 2) -> list[tuple[str, str]]:
    """Simpler heading splitter using line iteration."""
    prefix = "#" * level + " "
    entries: list[tuple[str, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in content.split("\n"):
        if line.strip().startswith(prefix) or (
            line.startswith(prefix)
        ):
            # Check it's exactly the right level
            stripped = line.strip()
            if stripped.startswith(prefix) and not stripped.startswith("#" * (level + 1)):
                if current_heading is not None:
                    entries.append((current_heading, "\n".join(current_lines).strip()))
                current_heading = stripped[len(prefix):].strip()
                current_lines = []
                continue
        current_lines.append(line)

    if current_heading is not None:
        entries.append((current_heading, "\n".join(current_lines).strip()))

    return entries


# ---------------------------------------------------------------------------
# Heading number stripping
# ---------------------------------------------------------------------------

_HEADING_NUMBER_RE = re.compile(r"^\d+\.\s+")


def _strip_heading_number(heading: str) -> str:
    """Remove optional leading ``1. `` numbering from a heading."""
    return _HEADING_NUMBER_RE.sub("", heading)


# ---------------------------------------------------------------------------
# Metadata line parsing
# ---------------------------------------------------------------------------

_DATE_YEAR_RE = re.compile(r"\d{4}")


def _looks_like_date(text: str) -> bool:
    """Heuristic: does *text* look like a date or date range?"""
    t = text.strip().lower()
    if t in ("present", "current", "now"):
        return True
    if _DATE_YEAR_RE.search(t):
        return True
    return False


def _parse_kv_lines(lines: list[str]) -> tuple[dict[str, str], int]:
    """Parse consecutive ``**Key:** Value`` lines from the start of *lines*.

    Returns ``(kv_dict, body_start_index)`` where *kv_dict* maps
    lower-cased key names to their string values and *body_start_index*
    is the index of the first line that is not a KV metadata line
    (skipping blank lines between KV lines).
    """
    kv: dict[str, str] = {}
    last_kv_idx = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(r"\*\*(.+?):\*\*\s*(.+)", stripped)
        if m:
            key = m.group(1).strip().lower()
            value = m.group(2).strip()
            kv[key] = value
            last_kv_idx = i
        else:
            # Once we hit a non-blank, non-KV line, stop
            if last_kv_idx >= 0 or not stripped.startswith("**"):
                break
            # First ** line that doesn't match KV format — stop
            break

    body_start = last_kv_idx + 1 if last_kv_idx >= 0 else 0
    return kv, body_start


def _is_kv_format(lines: list[str]) -> bool:
    """Check if the first ``**`` line uses ``**Key:** Value`` format."""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("**"):
            return bool(re.match(r"\*\*(.+?):\*\*", stripped))
        break
    return False


def _parse_metadata_line(line: str) -> dict[str, str | None]:
    """Parse ``**Bold** | Location | dates`` into component parts.

    Returns ``{"organization": ..., "location": ..., "date_str": ...}``.
    """
    result: dict[str, str | None] = {
        "organization": None,
        "location": None,
        "date_str": None,
    }
    stripped = line.strip()
    bold = re.match(r"\*\*(.+?)\*\*(.*)", stripped)
    if not bold:
        return result

    result["organization"] = bold.group(1).strip()
    remainder = bold.group(2).strip().lstrip("|").strip()

    if not remainder:
        return result

    parts = [p.strip() for p in remainder.split("|") if p.strip()]

    date_parts: list[str] = []
    location_parts: list[str] = []
    for part in parts:
        if _looks_like_date(part):
            date_parts.append(part)
        else:
            location_parts.append(part)

    if location_parts:
        result["location"] = location_parts[0]
    if date_parts:
        result["date_str"] = date_parts[0]

    return result


def _parse_date_str(date_str: str) -> dict[str, str]:
    """Convert ``"2022-03 – present"`` into ``{"start": ..., "end": ...}``."""
    if not date_str:
        return {}

    for sep in (" – ", " — ", " - ", "–", "—", " to "):
        if sep in date_str:
            parts = date_str.split(sep, 1)
            start = parts[0].strip()
            end = parts[1].strip()
            if end.lower() in ("present", "current", "now", ""):
                return {"start": start, "end": "present"}
            return {"start": start, "end": end}

    return {"start": date_str.strip()}


# ---------------------------------------------------------------------------
# Bullet / link extraction
# ---------------------------------------------------------------------------

def _extract_bullets(lines: list[str]) -> list[str]:
    """Collect ``- `` or ``* `` bullet items (with continuation lines)."""
    bullets: list[str] = []
    current: str | None = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- ") or stripped.startswith("* "):
            if current is not None:
                bullets.append(current)
            current = stripped[2:].strip()
        elif current is not None and stripped and (
            line.startswith("  ") or line.startswith("\t")
        ):
            current += " " + stripped
        else:
            if current is not None:
                bullets.append(current)
                current = None

    if current is not None:
        bullets.append(current)
    return bullets


def _extract_heading_link(heading: str) -> tuple[str, str | None]:
    """Extract name and URL from ``[Name](url)`` or plain text."""
    m = re.match(r"\[(.+?)\]\((.+?)\)", heading)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return heading.strip(), None


# ---------------------------------------------------------------------------
# Section-specific parsers
# ---------------------------------------------------------------------------

def _parse_experience_body(content: str) -> list[dict]:
    entries: list[dict[str, Any]] = []
    for heading, body in _split_by_heading_simple(content, 2):
        entry: dict[str, Any] = {"title": _strip_heading_number(heading)}
        lines = body.split("\n")

        if _is_kv_format(lines):
            kv, body_start = _parse_kv_lines(lines)
            org = kv.get("company") or kv.get("organization") or kv.get("employer")
            if org:
                entry["organization"] = org
            loc = kv.get("location")
            if loc:
                entry["location"] = loc
            dates = kv.get("dates") or kv.get("date")
            if dates:
                entry.update(_parse_date_str(dates))
        else:
            # Fallback: single-line pipe-delimited metadata
            body_start = 0
            for i, line in enumerate(lines):
                if line.strip():
                    if line.strip().startswith("**"):
                        meta = _parse_metadata_line(line)
                        if meta["organization"]:
                            entry["organization"] = meta["organization"]
                        if meta["location"]:
                            entry["location"] = meta["location"]
                        if meta["date_str"]:
                            entry.update(_parse_date_str(meta["date_str"]))
                        body_start = i + 1
                    break

        remaining = lines[body_start:]

        # Highlights (bullet points)
        bullets = _extract_bullets(remaining)
        if bullets:
            entry["highlights"] = bullets

        # Description: paragraph text before the first bullet
        desc_lines: list[str] = []
        for line in remaining:
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                break
            if stripped and not stripped.startswith("**"):
                desc_lines.append(stripped)
        if desc_lines:
            entry["description"] = " ".join(desc_lines)

        entries.append(entry)
    return entries


def _parse_education_body(content: str) -> list[dict]:
    entries: list[dict[str, Any]] = []
    for heading, body in _split_by_heading_simple(content, 2):
        entry: dict[str, Any] = {"degree": _strip_heading_number(heading)}
        lines = body.split("\n")

        if _is_kv_format(lines):
            kv, body_start = _parse_kv_lines(lines)
            inst = kv.get("institution") or kv.get("school") or kv.get("university")
            if inst:
                entry["institution"] = inst
            loc = kv.get("location")
            if loc:
                entry["location"] = loc
            dates = kv.get("dates") or kv.get("date")
            if dates:
                entry.update(_parse_date_str(dates))
            gpa = kv.get("gpa")
            if gpa:
                entry["gpa"] = gpa
        else:
            body_start = 0
            for i, line in enumerate(lines):
                if line.strip():
                    if line.strip().startswith("**"):
                        meta = _parse_metadata_line(line)
                        if meta["organization"]:
                            entry["institution"] = meta["organization"]
                        if meta["location"]:
                            entry["location"] = meta["location"]
                        if meta["date_str"]:
                            entry.update(_parse_date_str(meta["date_str"]))
                        body_start = i + 1
                    break

        remaining = lines[body_start:]

        bullets = _extract_bullets(remaining)
        if bullets:
            entry["highlights"] = bullets

        # Special field lines: GPA, Honors, Coursework
        for line in remaining:
            stripped = line.strip()
            gpa_m = re.match(r"(?:GPA|gpa)[:\s]+(.+)", stripped, re.IGNORECASE)
            if gpa_m:
                entry["gpa"] = gpa_m.group(1).strip()
            honors_m = re.match(r"Honors?[:\s]+(.+)", stripped, re.IGNORECASE)
            if honors_m:
                entry["honors"] = honors_m.group(1).strip()

        entries.append(entry)
    return entries


def _parse_skills_body(content: str) -> list[dict]:
    """Parse ``### Category`` or ``## Category`` headings, or ``**Category:** list`` lines."""
    categories: list[dict[str, Any]] = []

    # Try ### headings first, then ## headings
    for level in (3, 2):
        entries = _split_by_heading_simple(content, level)
        if entries:
            for name, body in entries:
                skills = _extract_skill_list(body)
                if skills:
                    categories.append({"name": name, "skills": skills})
            return categories

    # Fallback: **Bold:** comma-list lines
    for line in content.split("\n"):
        stripped = line.strip()
        m = re.match(r"\*\*(.+?)\*\*[:\s]*(.+)", stripped)
        if m:
            name = m.group(1).strip().rstrip(":")
            skills = [s.strip() for s in m.group(2).split(",") if s.strip()]
            if skills:
                categories.append({"name": name, "skills": skills})

    return categories


def _extract_skill_list(body: str) -> list[str]:
    """Skills from bullet points or comma-separated text."""
    lines = body.strip().split("\n")

    bullets = [
        l.strip()[2:].strip()
        for l in lines
        if l.strip().startswith("- ") or l.strip().startswith("* ")
    ]
    if bullets:
        return bullets

    text = " ".join(l.strip() for l in lines if l.strip())
    return [s.strip() for s in text.split(",") if s.strip()]


def _parse_projects_body(content: str) -> list[dict]:
    entries: list[dict[str, Any]] = []
    for heading, body in _split_by_heading_simple(content, 2):
        name, url = _extract_heading_link(heading)
        entry: dict[str, Any] = {"name": _strip_heading_number(name)}
        if url:
            entry["url"] = url

        lines = body.split("\n")

        # Check for URL on its own line (if not in heading)
        if not url:
            for line in lines:
                stripped = line.strip()
                url_m = re.match(r"https?://\S+", stripped)
                if url_m:
                    entry["url"] = url_m.group(0)
                    break

        # Technologies line
        for line in lines:
            stripped = line.strip()
            tech_m = re.match(
                r"(?:\*\*)?(?:Technologies?|Tech|Stack)[:\s]*(?:\*\*)?[:\s]*(.+)",
                stripped,
                re.IGNORECASE,
            )
            if tech_m:
                raw = tech_m.group(1).strip()
                entry["technologies"] = [t.strip() for t in raw.split(",") if t.strip()]

        # Metadata line (dates, org)
        for i, line in enumerate(lines):
            if line.strip() and line.strip().startswith("**"):
                # Skip if it's a Technologies line
                if re.match(r"\*\*(?:Technologies?|Tech|Stack)", line.strip(), re.IGNORECASE):
                    continue
                meta = _parse_metadata_line(line)
                if meta["date_str"]:
                    entry.update(_parse_date_str(meta["date_str"]))
                break

        bullets = _extract_bullets(lines)
        if bullets:
            entry["highlights"] = bullets

        # Description: paragraphs that aren't bullets, tech lines, or URLs
        desc_lines: list[str] = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- ") or stripped.startswith("* "):
                continue
            if stripped.startswith("**"):
                continue
            if re.match(r"https?://", stripped):
                continue
            if re.match(
                r"(?:Technologies?|Tech|Stack)[:\s]", stripped, re.IGNORECASE
            ):
                continue
            desc_lines.append(stripped)
        if desc_lines:
            entry["description"] = " ".join(desc_lines)

        entries.append(entry)
    return entries


def _parse_certifications_body(content: str) -> list[dict]:
    entries: list[dict[str, Any]] = []
    for heading, body in _split_by_heading_simple(content, 2):
        name, url = _extract_heading_link(heading)
        entry: dict[str, Any] = {"name": _strip_heading_number(name)}
        if url:
            entry["url"] = url

        lines = body.split("\n")

        if _is_kv_format(lines):
            kv, _ = _parse_kv_lines(lines)
            issuer = kv.get("issuer") or kv.get("organization")
            if issuer:
                entry["issuer"] = issuer
            date = kv.get("date") or kv.get("year")
            if date:
                entry["date"] = date
        else:
            for i, line in enumerate(lines):
                if line.strip() and line.strip().startswith("**"):
                    meta = _parse_metadata_line(line)
                    if meta["organization"]:
                        entry["issuer"] = meta["organization"]
                    if meta["date_str"]:
                        entry["date"] = meta["date_str"]
                    break

        # URL in body
        if not url:
            for line in lines:
                stripped = line.strip()
                url_m = re.match(r"https?://\S+", stripped)
                if url_m:
                    entry["url"] = url_m.group(0)
                    break
                link_m = re.search(r"\[.+?\]\((.+?)\)", stripped)
                if link_m:
                    entry["url"] = link_m.group(1)
                    break

        entries.append(entry)
    return entries


def _parse_publications_body(content: str) -> list[dict]:
    entries: list[dict[str, Any]] = []
    for heading, body in _split_by_heading_simple(content, 2):
        name, url = _extract_heading_link(heading)
        entry: dict[str, Any] = {"title": _strip_heading_number(name)}
        if url:
            entry["url"] = url

        lines = body.split("\n")

        if _is_kv_format(lines):
            kv, _ = _parse_kv_lines(lines)
            venue = kv.get("venue") or kv.get("journal") or kv.get("conference")
            if venue:
                entry["venue"] = venue
            date = kv.get("date") or kv.get("year")
            if date:
                entry["date"] = date
            authors_str = kv.get("authors") or kv.get("author") or kv.get("by")
            if authors_str:
                entry["authors"] = [a.strip() for a in authors_str.split(",")]
        else:
            for i, line in enumerate(lines):
                if line.strip() and line.strip().startswith("**"):
                    meta = _parse_metadata_line(line)
                    if meta["organization"]:
                        entry["venue"] = meta["organization"]
                    if meta["date_str"]:
                        entry["date"] = meta["date_str"]
                    break

            for line in lines:
                stripped = line.strip()
                m = re.match(r"(?:Authors?|By)[:\s]+(.+)", stripped, re.IGNORECASE)
                if m:
                    entry["authors"] = [a.strip() for a in m.group(1).split(",")]

        entries.append(entry)
    return entries


def _parse_awards_body(content: str) -> list[dict]:
    entries: list[dict[str, Any]] = []
    for heading, body in _split_by_heading_simple(content, 2):
        entry: dict[str, Any] = {"title": _strip_heading_number(heading)}
        lines = body.split("\n")

        if _is_kv_format(lines):
            kv, body_start = _parse_kv_lines(lines)
            issuer = kv.get("issuer") or kv.get("organization") or kv.get("awarded by")
            if issuer:
                entry["issuer"] = issuer
            date = kv.get("date") or kv.get("year")
            if date:
                entry["date"] = date
            location = kv.get("location")
            if location:
                entry["location"] = location
            remaining = lines[body_start:]
        else:
            remaining = lines
            for i, line in enumerate(lines):
                if line.strip() and line.strip().startswith("**"):
                    meta = _parse_metadata_line(line)
                    if meta["organization"]:
                        entry["issuer"] = meta["organization"]
                    if meta["date_str"]:
                        entry["date"] = meta["date_str"]
                    if meta.get("location"):
                        entry["location"] = meta["location"]
                    break

        desc_lines: list[str] = []
        highlights: list[str] = []
        for line in remaining:
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                highlights.append(stripped[2:])
            elif stripped and not stripped.startswith("**"):
                desc_lines.append(stripped)
        if desc_lines:
            entry["description"] = " ".join(desc_lines)
        if highlights:
            entry["highlights"] = highlights

        entries.append(entry)
    return entries


def _parse_languages_body(content: str) -> list[dict]:
    """Parse ``## Language`` headings with ``**Proficiency:** value``."""
    entries: list[dict[str, Any]] = []
    for heading, body in _split_by_heading_simple(content, 2):
        entry: dict[str, Any] = {"name": _strip_heading_number(heading)}
        lines = body.split("\n")

        kv, _ = _parse_kv_lines(lines)
        if kv.get("proficiency"):
            entry["proficiency"] = kv["proficiency"]
        elif kv.get("level"):
            entry["proficiency"] = kv["level"]

        entries.append(entry)
    return entries


def _parse_references_body(content: str) -> list[dict]:
    """Parse ``## Name`` headings with title, organization, contact info."""
    entries: list[dict[str, Any]] = []
    for heading, body in _split_by_heading_simple(content, 2):
        entry: dict[str, Any] = {"name": _strip_heading_number(heading)}
        lines = body.split("\n")

        kv, _ = _parse_kv_lines(lines)
        if kv.get("title") or kv.get("position") or kv.get("role"):
            entry["title"] = kv.get("title") or kv.get("position") or kv.get("role")
        if kv.get("organization") or kv.get("company") or kv.get("institution"):
            entry["organization"] = kv.get("organization") or kv.get("company") or kv.get("institution")
        if kv.get("email"):
            entry["email"] = kv["email"]
        if kv.get("phone"):
            entry["phone"] = kv["phone"]
        if kv.get("relationship") or kv.get("relation"):
            entry["relationship"] = kv.get("relationship") or kv.get("relation")

        entries.append(entry)
    return entries


# ---------------------------------------------------------------------------
# Parser dispatch table
# ---------------------------------------------------------------------------

_PARSERS: dict[str, Any] = {
    "experience": _parse_experience_body,
    "education": _parse_education_body,
    "skills": _parse_skills_body,
    "projects": _parse_projects_body,
    "certifications": _parse_certifications_body,
    "publications": _parse_publications_body,
    "awards": _parse_awards_body,
    "volunteer": _parse_experience_body,
    "languages": _parse_languages_body,
    "service": _parse_experience_body,
    "interests": _parse_skills_body,  # reuse skill-list parsing for interests
    "references": _parse_references_body,
}
