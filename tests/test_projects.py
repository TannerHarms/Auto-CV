"""Tests for master-vault project loading and CLI flows."""

import pytest
from pathlib import Path
from typer.testing import CliRunner

from auto_cv.cli import app
from auto_cv.parser.vault_reader import (
    load_vault,
    load_project,
    list_projects,
    _is_master_vault,
)


runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures — create a temporary master vault on disk
# ---------------------------------------------------------------------------

@pytest.fixture
def master_vault(tmp_path):
    """Create a minimal master vault with two projects."""
    master = tmp_path / "_master"
    master.mkdir()

    # Master _config.yml
    (master / "_config.yml").write_text(
        "name: Test Person\n"
        "title: Software Engineer\n"
        "contact:\n"
        "  email: test@example.com\n"
        "section_order:\n"
        "  - summary\n"
        "  - experience\n"
        "  - skills\n",
        encoding="utf-8",
    )

    # Master _style.yml
    (master / "_style.yml").write_text(
        "preset: classic\n",
        encoding="utf-8",
    )

    # Master sections
    sections = master / "sections"
    sections.mkdir()
    (sections / "01-summary.md").write_text(
        "---\ntype: summary\n---\n# Summary\n\nMaster summary text.\n",
        encoding="utf-8",
    )
    (sections / "02-experience.md").write_text(
        "---\ntype: experience\n---\n# Experience\n\n"
        "## Software Engineer\n**Acme Corp** | Remote | 2020-01 – present\n\n"
        "- Built things\n",
        encoding="utf-8",
    )
    (sections / "03-skills.md").write_text(
        "---\ntype: skills\n---\n# Skills\n\n### Languages\nPython, TypeScript\n",
        encoding="utf-8",
    )
    (sections / "04-education.md").write_text(
        "---\ntype: education\n---\n# Education\n\n"
        "## BS Computer Science\n**State University** | 2016 – 2020\n",
        encoding="utf-8",
    )

    # Master pages
    pages = master / "pages"
    pages.mkdir()
    (pages / "portfolio.md").write_text(
        "---\ntitle: Portfolio\n---\n# Portfolio\n\nMy projects.\n",
        encoding="utf-8",
    )

    # Project A — selects a subset with a local summary override
    proj_a = tmp_path / "projects" / "frontend-role"
    proj_a.mkdir(parents=True)
    (proj_a / "_project.yml").write_text(
        "include:\n"
        "  - 01-summary\n"
        "  - 02-experience\n"
        "  - 03-skills\n"
        "section_order:\n"
        "  - summary\n"
        "  - skills\n"
        "  - experience\n"
        "config:\n"
        "  title: Frontend Engineer\n",
        encoding="utf-8",
    )
    proj_a_sections = proj_a / "sections"
    proj_a_sections.mkdir()
    (proj_a_sections / "01-summary.md").write_text(
        "---\ntype: summary\n---\n# Summary\n\nFrontend-focused summary.\n",
        encoding="utf-8",
    )

    # Project B — includes everything (no include list)
    proj_b = tmp_path / "projects" / "all-sections"
    proj_b.mkdir(parents=True)
    (proj_b / "_project.yml").write_text(
        "# Uses all master sections\n",
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def flat_vault(tmp_path):
    """Create a minimal flat (legacy) vault."""
    vault = tmp_path / "flat_vault"
    vault.mkdir()
    (vault / "_config.yml").write_text(
        "name: Flat Person\ntitle: Dev\ncontact:\n  email: flat@ex.com\n",
        encoding="utf-8",
    )
    (vault / "_style.yml").write_text("preset: classic\n", encoding="utf-8")
    sections = vault / "sections"
    sections.mkdir()
    (sections / "01-summary.md").write_text(
        "---\ntype: summary\n---\n# Summary\n\nFlat vault summary.\n",
        encoding="utf-8",
    )
    return vault


@pytest.fixture
def header_md_vault(tmp_path):
    """Create a master vault using header.md instead of _config.yml."""
    master = tmp_path / "_master"
    master.mkdir()

    (master / "header.md").write_text(
        "---\n"
        "section_order:\n"
        "  - summary\n"
        "  - experience\n"
        "---\n"
        "# Header Person\n"
        "*Lead Engineer*\n"
        "\n"
        "hdr@example.com | +1-555-1234 | Portland, OR\n"
        "[LinkedIn](https://linkedin.com/in/hdr-person) | [GitHub](https://github.com/hdrp)\n",
        encoding="utf-8",
    )
    (master / "_style.yml").write_text("preset: classic\n", encoding="utf-8")
    sections = master / "sections"
    sections.mkdir()
    (sections / "01-summary.md").write_text(
        "---\ntype: summary\n---\n# Summary\n\nHeader vault summary.\n",
        encoding="utf-8",
    )
    (sections / "02-experience.md").write_text(
        "---\ntype: experience\n---\n# Experience\n\n"
        "## Dev\n**Co** | Remote | 2020-01 – present\n\n- Worked\n",
        encoding="utf-8",
    )

    # Project using header.md with title override
    proj = tmp_path / "projects" / "hdr-proj"
    proj.mkdir(parents=True)
    (proj / "header.md").write_text(
        "---\n"
        "include:\n"
        "  - 01-summary\n"
        "section_order:\n"
        "  - summary\n"
        "---\n"
        "*Backend Specialist*\n",
        encoding="utf-8",
    )

    return tmp_path


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def test_is_master_vault(master_vault, flat_vault):
    assert _is_master_vault(master_vault) is True
    assert _is_master_vault(flat_vault) is False


# ---------------------------------------------------------------------------
# list_projects
# ---------------------------------------------------------------------------

def test_list_projects(master_vault):
    names = list_projects(master_vault)
    assert "frontend-role" in names
    assert "all-sections" in names
    assert len(names) == 2


def test_list_projects_flat_vault(flat_vault):
    assert list_projects(flat_vault) == []


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------

def test_flat_vault_loads(flat_vault):
    resume, style = load_vault(flat_vault)
    assert resume.config.name == "Flat Person"
    assert len(resume.sections) == 1
    assert resume.sections[0].section_type.value == "summary"


def test_master_vault_without_project_loads_master(master_vault):
    """When no project is specified, load_vault loads _master/ directly."""
    resume, style = load_vault(master_vault)
    assert resume.config.name == "Test Person"
    assert len(resume.sections) == 4  # all master sections


# ---------------------------------------------------------------------------
# Project loading
# ---------------------------------------------------------------------------

def test_load_project_subset(master_vault):
    """Frontend-role project should only include 3 sections."""
    resume, style = load_vault(master_vault, project="frontend-role")
    assert len(resume.sections) == 3
    ids = {s.id for s in resume.sections}
    assert ids == {"summary", "experience", "skills"}


def test_load_project_config_override(master_vault):
    """Project config override should update resume title."""
    resume, _ = load_vault(master_vault, project="frontend-role")
    assert resume.config.title == "Frontend Engineer"


def test_load_project_section_order(master_vault):
    """Project section_order should be applied."""
    resume, _ = load_vault(master_vault, project="frontend-role")
    ordered = resume.ordered_sections()
    ids = [s.id for s in ordered]
    assert ids == ["summary", "skills", "experience"]


def test_load_project_local_override(master_vault):
    """Local section override should take priority over master."""
    resume, _ = load_vault(master_vault, project="frontend-role")
    summary = next(s for s in resume.sections if s.id == "summary")
    assert "Frontend-focused" in summary.raw_content


def test_load_project_all_sections(master_vault):
    """Project with no include list loads all master sections."""
    resume, _ = load_vault(master_vault, project="all-sections")
    assert len(resume.sections) == 4


def test_load_project_master_name_preserved(master_vault):
    """Master config name should carry through to project."""
    resume, _ = load_vault(master_vault, project="all-sections")
    assert resume.config.name == "Test Person"


def test_load_project_not_found(master_vault):
    with pytest.raises(FileNotFoundError, match="Project not found"):
        load_project(master_vault, "nonexistent")


def test_load_project_no_master(flat_vault):
    with pytest.raises(FileNotFoundError, match="Master vault not found"):
        load_project(flat_vault, "anything")


# ---------------------------------------------------------------------------
# header.md format
# ---------------------------------------------------------------------------

def test_header_md_loads_config(header_md_vault):
    """header.md should be parsed into ResumeConfig."""
    resume, _ = load_vault(header_md_vault)
    assert resume.config.name == "Header Person"
    assert resume.config.title == "Lead Engineer"
    assert resume.config.contact.email == "hdr@example.com"
    assert resume.config.contact.phone == "+1-555-1234"
    assert resume.config.contact.location == "Portland, OR"
    assert resume.config.contact.linkedin == "hdr-person"
    assert resume.config.contact.github == "hdrp"


def test_header_md_section_order(header_md_vault):
    resume, _ = load_vault(header_md_vault)
    assert resume.config.section_order == ["summary", "experience"]


def test_header_md_project_override(header_md_vault):
    """Project header.md should override title from master."""
    resume, _ = load_vault(header_md_vault, project="hdr-proj")
    assert resume.config.title == "Backend Specialist"
    assert resume.config.name == "Header Person"  # inherited
    assert len(resume.sections) == 1


# ---------------------------------------------------------------------------
# CLI integration
# ---------------------------------------------------------------------------


def test_cli_list_projects(master_vault):
    result = runner.invoke(app, ["list-projects", str(master_vault)])

    assert result.exit_code == 0
    assert "frontend-role" in result.stdout
    assert "all-sections" in result.stdout


def test_cli_build_project_html(master_vault, tmp_path):
    output_dir = tmp_path / "html"

    result = runner.invoke(
        app,
        [
            "build",
            str(master_vault),
            "-p",
            "frontend-role",
            "-f",
            "html",
            "-o",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "index.html").exists()
    assert not (output_dir / "html" / "index.html").exists()
    html = (output_dir / "index.html").read_text(encoding="utf-8")
    assert "Frontend-focused summary" in html
    assert "Frontend Engineer" in html


def test_cli_new_project(master_vault):
    result = runner.invoke(app, ["new-project", str(master_vault), "qa-role"])

    project_dir = master_vault / "projects" / "qa-role"
    assert result.exit_code == 0
    assert project_dir.exists()
    assert (project_dir / "header.md").exists()
