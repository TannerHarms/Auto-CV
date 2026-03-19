"""CLI entry point — thin wrapper around core library using Typer + Rich."""

from __future__ import annotations

import webbrowser
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

app = typer.Typer(
    name="auto-resume",
    help="Build polished resumes from Obsidian-style markdown vaults.",
    add_completion=False,
)
console = Console()


class OutputFormat(str, Enum):
    latex = "latex"
    docx = "docx"
    html = "html"


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

@app.command()
def build(
    vault: Annotated[Path, typer.Argument(help="Path to the resume vault directory.")],
    format: Annotated[
        list[OutputFormat],
        typer.Option("--format", "-f", help="Output formats to generate."),
    ] = [OutputFormat.latex, OutputFormat.docx, OutputFormat.html],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output directory."),
    ] = Path("output"),
    polish: Annotated[
        bool,
        typer.Option("--polish", help="Use LLM to polish bullet points."),
    ] = False,
    tailor_to: Annotated[
        Optional[Path],
        typer.Option("--tailor-to", help="Path to a job description .txt file to tailor towards."),
    ] = None,
    suggest_layout: Annotated[
        bool,
        typer.Option("--suggest-layout", help="Use LLM to optimise section order."),
    ] = False,
    model: Annotated[
        Optional[str],
        typer.Option("--model", help="LLM model name (default: gpt-4o or AUTO_CV_MODEL env)."),
    ] = None,
) -> None:
    """Parse a vault and render resumes in the requested formats."""
from auto_cv.parser.vault_reader import load_vault

    vault = vault.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    with console.status("[bold green]Loading vault…"):
        resume, style = load_vault(vault)

    # --- Agent pipeline (optional) ---
    if polish:
        from auto_cv.agents.polish import PolishAgent

        with console.status("[bold yellow]Polishing bullet points…"):
            resume = PolishAgent(model=model).process(resume)
        rprint("[green]✓[/green] Bullets polished")

    if tailor_to:
        from auto_cv.agents.tailor import TailorAgent

        jd_text = tailor_to.resolve().read_text(encoding="utf-8")
        with console.status("[bold yellow]Tailoring to job description…"):
            resume = TailorAgent(model=model).process(resume, job_description=jd_text)
        rprint(f"[green]✓[/green] Tailored to {tailor_to.name}")

    if suggest_layout:
        from auto_cv.agents.layout import LayoutAgent

        with console.status("[bold yellow]Optimising layout…"):
            resume = LayoutAgent(model=model).process(resume)
        rprint("[green]✓[/green] Layout optimised")

    # --- Render ---
    for fmt in format:
        renderer = _get_renderer(fmt)
        with console.status(f"[bold cyan]Rendering {fmt.value}…"):
            result = renderer.render(resume, style, output)
        rprint(f"[green]✓[/green] {fmt.value} → {result}")

    rprint("[bold green]Done![/bold green]")


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------

_INIT_CONFIG = """\
name: Your Name
title: Software Engineer
# photo: headshot.jpg

contact:
  email: you@example.com
  phone: "+1-555-000-0000"
  location: City, State
  linkedin: yourprofile
  github: yourhandle
  website: https://yoursite.dev

# Order controls how sections appear in the output.
section_order:
  - summary
  - experience
  - education
  - skills
  - projects

# HTML-only metadata (optional)
# html_meta:
#   title: "Your Name — Resume"
#   description: "Experienced software engineer."
"""

_INIT_STYLE = """\
# Style preset — choose from: classic, modern, minimal
# Or point to a vault-local preset: ./presets/my_theme.yml
preset: classic

# Override any preset value below (uncomment to customise):
# colors:
#   primary: "#2C3E50"
#   accent: "#3498DB"
# fonts:
#   heading: Helvetica
#   body: Georgia
#   size_base: "11pt"
# spacing:
#   page_margin: "0.75in"
#   section_gap: "12pt"

# Per-format options:
# latex:
#   font_package: helvet
#   use_icons: false
# docx:
#   page_width_inches: 8.5
# html:
#   layout: top-header   # top-header | sidebar | cards
#   include_photo: false
"""

_INIT_SUMMARY = """\
---
type: summary
---
# Summary

Results-driven software engineer with 5+ years of experience building scalable
web applications. Passionate about clean code, automation, and developer tooling.
"""

_INIT_EXPERIENCE = """\
---
type: experience
---
# Experience

## Senior Software Engineer
**Acme Corp** | San Francisco, CA | 2021-01 – present

- Led migration of monolith to microservices, reducing deploy time by 60%
- Mentored 3 junior engineers through structured code review programme

## Software Engineer
**StartupCo** | Remote | 2018-06 – 2020-12

- Built real-time dashboard consumed by 200+ internal users
- Introduced CI/CD pipeline that cut release cycle from 2 weeks to 1 day
"""

_INIT_EDUCATION = """\
---
type: education
---
# Education

## B.S. Computer Science
**State University** | Anytown, USA | 2014 – 2018
Honors: cum laude
"""

_INIT_SKILLS = """\
---
type: skills
---
# Skills

### Languages
Python, TypeScript, Go, SQL

### Frameworks
FastAPI, React, Django

### Tools
Docker, Kubernetes, Git, GitHub Actions
"""

_INIT_PROJECTS = """\
---
type: projects
---
# Projects

## [Auto Resume](https://github.com/you/auto-resume)
Markdown-to-resume builder with LaTeX, DOCX, and HTML output.

**Technologies:** Python, Jinja2, Pydantic
"""


@app.command()
def init(
    path: Annotated[Path, typer.Argument(help="Directory to create the new vault in.")],
) -> None:
    """Scaffold a new resume vault with example content."""
    path = path.resolve()
    if path.exists() and any(path.iterdir()):
        rprint(f"[red]Error:[/red] {path} already exists and is not empty.")
        raise typer.Exit(code=1)

    # Directories
    path.mkdir(parents=True, exist_ok=True)
    (path / "sections").mkdir()
    (path / "pages").mkdir()
    (path / "assets").mkdir()

    # Files
    (path / "_config.yml").write_text(_INIT_CONFIG, encoding="utf-8")
    (path / "_style.yml").write_text(_INIT_STYLE, encoding="utf-8")
    (path / "sections" / "01-summary.md").write_text(_INIT_SUMMARY, encoding="utf-8")
    (path / "sections" / "02-experience.md").write_text(_INIT_EXPERIENCE, encoding="utf-8")
    (path / "sections" / "03-education.md").write_text(_INIT_EDUCATION, encoding="utf-8")
    (path / "sections" / "04-skills.md").write_text(_INIT_SKILLS, encoding="utf-8")
    (path / "sections" / "05-projects.md").write_text(_INIT_PROJECTS, encoding="utf-8")

    rprint(f"[green]✓[/green] Vault created at [bold]{path}[/bold]")
    rprint("  Edit the files, then run: [bold]auto-cv build " + str(path) + "[/bold]")


# ---------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------

@app.command()
def preview(
    vault: Annotated[Path, typer.Argument(help="Path to the resume vault directory.")],
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Output directory."),
    ] = Path("output"),
) -> None:
    """Quick-render HTML and open in the default browser."""
    from auto_cv.parser.vault_reader import load_vault
    from auto_cv.renderers.html import HtmlRenderer

    vault = vault.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    with console.status("[bold green]Loading vault…"):
        resume, style = load_vault(vault)

    renderer = HtmlRenderer()
    with console.status("[bold cyan]Rendering HTML…"):
        result = renderer.render(resume, style, output)

    index = result if result.is_file() else result / "index.html"
    rprint(f"[green]✓[/green] HTML → {result}")
    webbrowser.open(index.as_uri())


# ---------------------------------------------------------------------------
# list-presets
# ---------------------------------------------------------------------------

@app.command("list-presets")
def list_presets_cmd() -> None:
    """Show available style presets."""
    from auto_cv.styles.presets import list_presets

    table = Table(title="Available Style Presets")
    table.add_column("Name", style="bold cyan")
    table.add_column("File")

    presets_dir = Path(__file__).parent / "styles" / "presets"
    for name in list_presets():
        table.add_row(name, str(presets_dir / f"{name}.yml"))

    console.print(table)


# ---------------------------------------------------------------------------
# style-schema
# ---------------------------------------------------------------------------

@app.command("style-schema")
def style_schema() -> None:
    """Print the full JSON schema for StyleConfig (useful for reference)."""
    from auto_cv.models.style import StyleConfig

    import json

    schema = StyleConfig.model_json_schema()
    rprint(json.dumps(schema, indent=2))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _get_renderer(fmt: OutputFormat):
    """Return the appropriate renderer for the given format."""
    if fmt == OutputFormat.latex:
        from auto_cv.renderers.latex import LatexRenderer

        return LatexRenderer()
    elif fmt == OutputFormat.docx:
        from auto_cv.renderers.docx import DocxRenderer

        return DocxRenderer()
    else:
        from auto_cv.renderers.html import HtmlRenderer

        return HtmlRenderer()
