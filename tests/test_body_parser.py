"""Tests for the markdown body parser."""

import pytest

from auto_cv.parser.body_parser import parse_body, strip_body_title


# ---------------------------------------------------------------------------
# strip_body_title
# ---------------------------------------------------------------------------


class TestStripBodyTitle:
    def test_strips_h1(self):
        content = "# Experience\n\nSome body text here"
        assert strip_body_title(content) == "Some body text here"

    def test_no_h1_returns_content(self):
        content = "Some body text with no heading"
        assert strip_body_title(content) == "Some body text with no heading"

    def test_empty_content(self):
        assert strip_body_title("") == ""

    def test_only_h1(self):
        assert strip_body_title("# Title") == ""

    def test_h2_not_stripped(self):
        content = "## Not a top heading\n\nBody"
        assert strip_body_title(content) == content.strip()


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------


class TestExperienceBody:
    CONTENT = """\
# Experience

## Staff Software Engineer
**CloudScale Inc.** | Austin, TX | 2022-03 – present

- Architected event-driven platform
- Led a team of 8 engineers

## Software Engineer
**WebWorks Agency** | Portland, OR | 2017-06 – 2019-07

- Developed full-stack features
"""

    def test_returns_title(self):
        title, entries = parse_body("experience", self.CONTENT)
        assert title == "Experience"

    def test_entry_count(self):
        _, entries = parse_body("experience", self.CONTENT)
        assert len(entries) == 2

    def test_first_entry_title(self):
        _, entries = parse_body("experience", self.CONTENT)
        assert entries[0]["title"] == "Staff Software Engineer"

    def test_first_entry_org(self):
        _, entries = parse_body("experience", self.CONTENT)
        assert entries[0]["organization"] == "CloudScale Inc."

    def test_first_entry_location(self):
        _, entries = parse_body("experience", self.CONTENT)
        assert entries[0]["location"] == "Austin, TX"

    def test_first_entry_dates(self):
        _, entries = parse_body("experience", self.CONTENT)
        assert entries[0]["start"] == "2022-03"
        assert entries[0]["end"] == "present"

    def test_highlights(self):
        _, entries = parse_body("experience", self.CONTENT)
        assert len(entries[0]["highlights"]) == 2
        assert "event-driven" in entries[0]["highlights"][0]

    def test_second_entry_dates(self):
        _, entries = parse_body("experience", self.CONTENT)
        assert entries[1]["start"] == "2017-06"
        assert entries[1]["end"] == "2019-07"

    def test_description_paragraph(self):
        content = """\
## Lead Engineer
**Acme Corp** | Remote | 2023 – present

Overseeing the platform team.

- Shipped v2.0 launch
"""
        _, entries = parse_body("experience", content)
        assert entries[0].get("description") == "Overseeing the platform team."


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------


class TestEducationBody:
    CONTENT = """\
## M.S. Computer Science
**University of Texas at Austin** | Austin, TX | 2014 – 2016
GPA: 3.9

- Thesis: Scalable Stream Processing

## B.S. Computer Science
**Oregon State University** | Corvallis, OR | 2010 – 2014
GPA: 3.7
Honors: magna cum laude
"""

    def test_entry_count(self):
        _, entries = parse_body("education", self.CONTENT)
        assert len(entries) == 2

    def test_degree(self):
        _, entries = parse_body("education", self.CONTENT)
        assert entries[0]["degree"] == "M.S. Computer Science"

    def test_institution(self):
        _, entries = parse_body("education", self.CONTENT)
        assert entries[0]["institution"] == "University of Texas at Austin"

    def test_gpa(self):
        _, entries = parse_body("education", self.CONTENT)
        assert entries[0]["gpa"] == "3.9"

    def test_honors(self):
        _, entries = parse_body("education", self.CONTENT)
        assert entries[1].get("honors") == "magna cum laude"

    def test_highlights(self):
        _, entries = parse_body("education", self.CONTENT)
        assert len(entries[0]["highlights"]) == 1


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


class TestSkillsBody:
    CONTENT = """\
# Technical Skills

### Languages
Python, TypeScript, Go, SQL

### Frameworks
FastAPI, React, Django

### Tools
Docker, Kubernetes, Git
"""

    def test_title(self):
        title, _ = parse_body("skills", self.CONTENT)
        assert title == "Technical Skills"

    def test_category_count(self):
        _, entries = parse_body("skills", self.CONTENT)
        assert len(entries) == 3

    def test_category_name(self):
        _, entries = parse_body("skills", self.CONTENT)
        assert entries[0]["name"] == "Languages"

    def test_skills_parsed(self):
        _, entries = parse_body("skills", self.CONTENT)
        assert "Python" in entries[0]["skills"]
        assert len(entries[0]["skills"]) == 4

    def test_bullet_list_skills(self):
        content = """\
### Languages
- Python
- TypeScript
- Go
"""
        _, entries = parse_body("skills", content)
        assert entries[0]["skills"] == ["Python", "TypeScript", "Go"]

    def test_bold_fallback_format(self):
        content = """\
**Languages:** Python, TypeScript, Go
**Tools:** Docker, Kubernetes
"""
        _, entries = parse_body("skills", content)
        assert len(entries) == 2
        assert entries[0]["name"] == "Languages"


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class TestProjectsBody:
    CONTENT = """\
## [Auto CV](https://github.com/TannerHarms/Auto-CV)
Markdown-to-CV/resume builder with PDF, DOCX, and HTML output.

**Technologies:** Python, Pydantic, Jinja2

## DevDocs Aggregator
CLI tool that aggregates API documentation.

**Technologies:** Python, SQLite, Click
"""

    def test_entry_count(self):
        _, entries = parse_body("projects", self.CONTENT)
        assert len(entries) == 2

    def test_name_from_link(self):
        _, entries = parse_body("projects", self.CONTENT)
        assert entries[0]["name"] == "Auto CV"

    def test_url_from_link(self):
        _, entries = parse_body("projects", self.CONTENT)
        assert entries[0]["url"] == "https://github.com/TannerHarms/Auto-CV"

    def test_description(self):
        _, entries = parse_body("projects", self.CONTENT)
        assert "Markdown-to-CV" in entries[0]["description"]

    def test_technologies(self):
        _, entries = parse_body("projects", self.CONTENT)
        assert "Python" in entries[0]["technologies"]
        assert len(entries[0]["technologies"]) == 3

    def test_no_url_entry(self):
        _, entries = parse_body("projects", self.CONTENT)
        assert entries[1]["name"] == "DevDocs Aggregator"
        assert "url" not in entries[1]


# ---------------------------------------------------------------------------
# Certifications
# ---------------------------------------------------------------------------


class TestCertificationsBody:
    CONTENT = """\
## AWS Solutions Architect – Professional
**Amazon Web Services** | 2023-05
https://aws.amazon.com/certification/

## Certified Kubernetes Administrator (CKA)
**Cloud Native Computing Foundation** | 2022-11
"""

    def test_entry_count(self):
        _, entries = parse_body("certifications", self.CONTENT)
        assert len(entries) == 2

    def test_name(self):
        _, entries = parse_body("certifications", self.CONTENT)
        assert "AWS Solutions Architect" in entries[0]["name"]

    def test_issuer(self):
        _, entries = parse_body("certifications", self.CONTENT)
        assert entries[0]["issuer"] == "Amazon Web Services"

    def test_date(self):
        _, entries = parse_body("certifications", self.CONTENT)
        assert entries[0]["date"] == "2023-05"

    def test_url(self):
        _, entries = parse_body("certifications", self.CONTENT)
        assert entries[0]["url"] == "https://aws.amazon.com/certification/"


# ---------------------------------------------------------------------------
# Summary (no entries — title only)
# ---------------------------------------------------------------------------


class TestSummaryBody:
    def test_summary_returns_no_entries(self):
        _, entries = parse_body("summary", "# Summary\n\nSome text here")
        assert entries == []

    def test_summary_extracts_title(self):
        title, _ = parse_body("summary", "# Professional Summary\n\nText")
        assert title == "Professional Summary"


# ---------------------------------------------------------------------------
# Custom / unknown type
# ---------------------------------------------------------------------------


class TestCustomBody:
    def test_unknown_type_returns_empty(self):
        _, entries = parse_body("custom", "## Heading\nBody text")
        assert entries == []


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_content(self):
        title, entries = parse_body("experience", "")
        assert title is None
        assert entries == []

    def test_no_h1_heading(self):
        content = """\
## Software Engineer
**Acme** | Remote | 2020 – present

- Did stuff
"""
        title, entries = parse_body("experience", content)
        assert title is None
        assert len(entries) == 1

    def test_yaml_entries_still_work(self):
        """Verify that parse_body is only called when no YAML entries exist;
        this test just documents the body parser behavior with an empty string."""
        title, entries = parse_body("experience", "   \n   ")
        assert entries == []
