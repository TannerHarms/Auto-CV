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
    name="auto-cv",
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
    project: Annotated[
        Optional[str],
        typer.Option("--project", "-p", help="Project name (for master vaults with projects/)."),
    ] = None,
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
        resume, style = load_vault(vault, project=project)

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

_INIT_HEADER = """\
---
section_order:
  - summary
  - experience
  - education
  - skills
  - projects
# photo: headshot.jpg
# html_meta:
#   title: "Your Name — Resume"
#   description: "Experienced software engineer."
---
# Your Name
*Software Engineer*

you@example.com | +1-555-000-0000 | City, State
[LinkedIn](https://linkedin.com/in/yourprofile) | [GitHub](https://github.com/yourhandle) | [yoursite.dev](https://yoursite.dev)
"""

def _generate_full_style_yaml(preset: str = "classic") -> str:
    """Generate a _style.yml with all configurable values populated from a preset."""
    from auto_cv.models.style import StyleConfig
    from auto_cv.styles.presets import load_preset

    try:
        style = load_preset(preset)
    except Exception:
        style = StyleConfig(preset=preset)

    data = style.model_dump()

    import yaml
    # Force all strings through quotes for consistency
    yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    lines = [
        "# Auto-CV Style Configuration",
        "# All values below are configurable. Edit any value and rebuild.",
        f"# Preset: {preset}",
        "#",
        "# Available presets: classic, modern, minimal, academic, awesome-cv,",
        "#   creative, elegant, executive, technical",
        "",
    ]
    lines.append(yaml_str)
    return "\n".join(lines)

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

## [Auto CV](https://github.com/TannerHarms/Auto-CV)
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
    (path / "header.md").write_text(_INIT_HEADER, encoding="utf-8")
    (path / "_style.yml").write_text(_generate_full_style_yaml("classic"), encoding="utf-8")
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
# list-projects
# ---------------------------------------------------------------------------

@app.command("list-projects")
def list_projects_cmd(
    vault: Annotated[Path, typer.Argument(help="Path to the resume vault directory.")],
) -> None:
    """List all resume projects in a master vault."""
    from auto_cv.parser.vault_reader import list_projects

    vault = vault.resolve()
    names = list_projects(vault)
    if not names:
        rprint(f"[yellow]No projects found in {vault}/projects/[/yellow]")
        rprint("Create one with: [bold]auto-cv new-project <vault> <name>[/bold]")
        return

    table = Table(title="Resume Projects")
    table.add_column("Project", style="bold cyan")
    table.add_column("Path")
    for name in names:
        table.add_row(name, str(vault / "projects" / name))
    console.print(table)


# ---------------------------------------------------------------------------
# new-project
# ---------------------------------------------------------------------------

_PROJECT_TEMPLATE = """\
# Sections to include from _master/sections/ (order matters).
# Use paths relative to _master/sections/, e.g. "experience/acme-corp".
# Use a directory name like "experience" to include all files in it.
include:
  - summary
  - experience
  - education
  - skills
  - projects

# Display order — maps to section type names.
# If omitted, uses the order from 'include' above.
section_order:
  - summary
  - experience
  - skills
  - projects
  - education

# Override any _master/_config.yml fields.
# config:
#   title: "Specific Role Title"
"""

_PROJECT_HEADER_TEMPLATE = """\
---
include:
  - summary
  - experience
  - education
  - skills
  - projects
section_order:
  - summary
  - experience
  - skills
  - projects
  - education
---
# To override the master title, uncomment below:
# *Specific Role Title*
"""


@app.command("new-project")
def new_project_cmd(
    vault: Annotated[Path, typer.Argument(help="Path to the resume vault directory.")],
    name: Annotated[str, typer.Argument(help="Name for the new project.")],
) -> None:
    """Create a new resume project in a master vault."""
    vault = vault.resolve()
    master = vault / "_master"
    if not master.is_dir():
        rprint("[red]Error:[/red] No _master/ directory found. "
               "Initialise a master vault first or add a _master/ folder.")
        raise typer.Exit(code=1)

    project_dir = vault / "projects" / name
    if project_dir.exists():
        rprint(f"[red]Error:[/red] Project {name!r} already exists at {project_dir}")
        raise typer.Exit(code=1)

    project_dir.mkdir(parents=True)
    (project_dir / "sections").mkdir()
    (project_dir / "output").mkdir()
    (project_dir / "header.md").write_text(_PROJECT_HEADER_TEMPLATE, encoding="utf-8")

    # Generate _style.yml with full defaults so users can customise per-project
    master_style_path = vault / "_master" / "_style.yml"
    if master_style_path.exists():
        import yaml
        raw = yaml.safe_load(master_style_path.read_text(encoding="utf-8")) or {}
        preset_name = raw.get("preset", "classic")
    else:
        root_style_path = vault / "_style.yml"
        if root_style_path.exists():
            import yaml
            raw = yaml.safe_load(root_style_path.read_text(encoding="utf-8")) or {}
            preset_name = raw.get("preset", "classic")
        else:
            preset_name = "classic"
    (project_dir / "_style.yml").write_text(
        _generate_full_style_yaml(preset_name), encoding="utf-8"
    )

    rprint(f"[green]✓[/green] Project created at [bold]{project_dir}[/bold]")
    rprint(f"  Edit [bold]{project_dir / 'header.md'}[/bold] to select sections.")
    rprint(f"  Build with: [bold]auto-cv build {vault} -p {name}[/bold]")


# ---------------------------------------------------------------------------
# list-presets
# ---------------------------------------------------------------------------

@app.command("list-presets")
def list_presets_cmd(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output full preset data as JSON."),
    ] = False,
) -> None:
    """Show available style presets."""
    from auto_cv.styles.presets import list_presets, load_preset

    if json_output:
        import json

        presets = {}
        for name in list_presets():
            cfg = load_preset(name)
            presets[name] = cfg.model_dump()
        # Use print() to avoid Rich formatting
        print(json.dumps(presets))
        return

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
