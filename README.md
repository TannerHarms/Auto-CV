# Auto CV

Build polished resumes from an **Obsidian-style markdown vault**. One command produces three outputs:

| Format | Description |
| --- | --- |
| **LaTeX → PDF** | Structured LaTeX repo (`main.tex` + `resume.sty` + `sections/*.tex`), auto-compiled with `latexmk` |
| **DOCX** | Word document built from scratch via `python-docx` — open and edit in Word/Google Docs |
| **HTML** | Styled, multi-page website with six layout options, print stylesheet, and custom CSS/JS support |

## Preview

Nine built-in style presets — each produces matching output across all three formats:

| ![Software Engineer (Modern)](examples/previews/software-engineer.png) | ![Executive](examples/previews/executive.png) | ![Creative Designer](examples/previews/creative-designer.png) |
|:---:|:---:|:---:|
| **Modern** | **Executive** | **Creative** |
| ![Academic Researcher](examples/previews/academic-researcher.png) | ![New Graduate (Elegant)](examples/previews/new-graduate.png) | ![Data Scientist (Technical)](examples/previews/data-scientist.png) |
| **Academic (Awesome-CV)** | **Elegant** | **Technical** |

> See [examples/](examples/) for full example vaults you can build yourself.

## Quick Start

### As a Python CLI

```bash
# Install
pip install -e .

# Scaffold a new vault
auto-cv init my_cv

# Edit your sections in my_cv/sections/*.md, then build:
auto-cv build my_cv

# Outputs land in ./output/{latex,docx,html}/
```

### As an Obsidian Plugin

1. Install the **Auto CV** plugin from Obsidian Community Plugins
2. Install the Python backend: `pip install auto-cv`
3. Open a vault with `header.md` + `sections/` folder
4. Run **Auto CV: Build Resume** from the command palette

## Vault Structure

A vault is a directory with a header file + markdown section files:

```text
my_cv/
├── header.md             # Name, contact, section ordering (YAML frontmatter + markdown)
├── _style.yml            # Style preset + overrides (optional)
├── sections/
│   ├── 01-summary.md
│   ├── 02-experience.md
│   ├── 03-education.md
│   ├── 04-skills.md
│   └── 05-projects.md
├── pages/                # Extra HTML pages (portfolio, about, etc.)
│   └── portfolio.md
├── assets/               # Photos, images
│   └── headshot.jpg
├── custom.css            # Auto-included in HTML output (optional)
├── custom.js             # Auto-included in HTML output (optional)
└── resume.sty            # Overrides generated LaTeX style (optional)
```

### `header.md`

Your name, title, and contact information live in `header.md` — YAML frontmatter for metadata, markdown body for the header content:

```markdown
---
section_order:
  - summary
  - experience
  - education
  - skills
  - projects
html_meta:
  title: "Jane Doe — Resume"
  description: "Full-stack software engineer."
photo: headshot.jpg
---
# Jane Doe
*Software Engineer*

jane@example.com | +1-555-000-0000 | Austin, TX
[LinkedIn](https://linkedin.com/in/janedoe) | [GitHub](https://github.com/janedoe) | [janedoe.dev](https://janedoe.dev)
```

### Section Files

Each section is a markdown file with YAML frontmatter. The filename prefix (`01-`, `02-`, etc.) controls default ordering.

**Experience** (`sections/02-experience.md`):

```yaml
---
title: Experience
type: experience
order: 2
entries:
  - role: Senior Software Engineer
    company: Acme Corp
    location: San Francisco, CA
    start: "2021-01"
    end: present
    highlights:
      - Led migration of monolith to microservices, reducing deploy time by 60%
      - Mentored 3 junior engineers through structured code review programme
---
```

**Skills** (`sections/04-skills.md`):

```yaml
---
title: Skills
type: skills
order: 4
categories:
  - name: Languages
    skills: [Python, TypeScript, Go, SQL]
  - name: Frameworks
    skills: [FastAPI, React, Django]
---
```

**Supported section types**: `summary`, `experience`, `education`, `skills`, `projects`, `certifications`, `publications`, `awards`, `volunteer`, `languages`, `interests`, `references`, `custom`

> **📖 See [docs/sections.md](docs/sections.md) for the complete section authoring guide** — all field names, markdown formats, display variants, and examples.

## Style Customisation

### Presets

Nine built-in presets are included:

| Preset | Description |
| --- | --- |
| `classic` | Georgia serif, conservative navy palette, single-column |
| `modern` | Helvetica sans-serif, blue accents, sidebar HTML layout, icons |
| `minimal` | Near-black, maximum whitespace, quiet typography |
| `academic` | Traditional academic CV style |
| `awesome-cv` | Faithful reproduction of the Awesome-CV LaTeX class (Roboto + Source Sans Pro via XeLaTeX) |
| `creative` | Bold colours and layout for creative professionals |
| `elegant` | Refined serif typography with subtle accents |
| `executive` | Professional executive-level resume style |
| `technical` | Clean technical resume with monospace accents |

List available presets:

```bash
auto-cv list-presets
```

### `_style.yml`

Override any preset value:

```yaml
preset: modern

colors:
  primary: "#1B3A4B"
  accent: "#3D85C6"

fonts:
  heading: Helvetica
  body: "Source Sans Pro"
  size_base: "11pt"

spacing:
  page_margin: "0.75in"
  section_gap: "12pt"

latex:
  font_package: helvet
  use_icons: false

docx:
  page_width_inches: 8.5

html:
  layout: sidebar        # top-header | sidebar | cards
  include_photo: true
  include_nav: true
```

### Vault-Local Presets

Create your own preset YAML file and reference it:

```yaml
preset: ./presets/my_theme.yml
```

### Full Schema

Dump the complete `StyleConfig` JSON schema for reference:

```bash
auto-cv style-schema
```

## HTML Layouts

Three built-in layouts, selectable via `html.layout` in `_style.yml`:

- **`top-header`** (default) — Traditional single-column with name/contact at top
- **`sidebar`** — Two-column: photo/contact/skills in colored sidebar, main content on right
- **`cards`** — Grid of cards per section with hover effects, modern portfolio feel

All layouts include:

- CSS variables generated from your `StyleConfig` (no framework dependency)
- Responsive design (mobile collapse)
- Print stylesheet (`@media print`) — "Print to PDF" from browser looks professional
- Navigation bar for multi-page resumes
- `custom.css` / `custom.js` auto-injection

### Extra Pages

Add markdown files to `pages/` for additional HTML pages (portfolio, about, etc.):

```yaml
---
title: Portfolio
id: portfolio
order: 1
---
Your portfolio content in markdown...
```

These are rendered as separate HTML pages with navigation. Ignored by LaTeX/DOCX.

## CLI Reference

```text
auto-cv build <vault> [OPTIONS]
```

| Option | Description |
| --- | --- |
| `--format`, `-f` | Output formats: `latex`, `docx`, `html` (repeatable, default: all three) |
| `--output`, `-o` | Output directory (default: `./output`) |
| `--polish` | Use LLM to rewrite bullet points for impact |
| `--tailor-to <file>` | Tailor resume to a job description `.txt` file |
| `--suggest-layout` | Use LLM to optimise section ordering |
| `--model` | LLM model name (default: `gpt-4o` or `AUTO_CV_MODEL` env) |

```
auto-cv init <path>          # Scaffold a new vault with example content
auto-cv preview <vault>      # Quick HTML render + open in browser
auto-cv list-presets          # Show available style presets
auto-cv style-schema          # Print StyleConfig JSON schema
```

## LLM Agents (Optional)

Agents modify the resume model *before* rendering — the pipeline stays deterministic.

```bash
# Install the agents extra
pip install -e ".[agents]"

# Polish bullet points
auto-cv build my_cv --polish

# Tailor to a job description
auto-cv build my_cv --tailor-to job_posting.txt

# Suggest optimal section layout
auto-cv build my_cv --suggest-layout

# Combine them
auto-cv build my_cv --polish --tailor-to job_posting.txt --suggest-layout
```

**Requirements**: Set `OPENAI_API_KEY` environment variable. Optionally set `AUTO_CV_MODEL` to change the default model from `gpt-4o`.

### Agent Details

| Agent | What it does |
| --- | --- |
| **PolishAgent** | Rewrites experience & project bullet points — stronger action verbs, quantified results, concise phrasing |
| **TailorAgent** | Adjusts summary, reorders highlights, injects keywords to match a target job description |
| **LayoutAgent** | Suggests section ordering and hides irrelevant sections for a target role |

## LaTeX Override

Drop a `resume.sty` file in your vault root to fully replace the generated LaTeX style. This lets power users hand-craft their LaTeX style once and reuse it across builds.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/
```

## Project Structure

```text
src/auto_cv/
├── models/          # Pydantic data models (Resume, Section, StyleConfig)
├── parser/          # Vault reader (YAML/frontmatter → models)
├── renderers/       # LaTeX, DOCX, HTML renderers
├── styles/          # Preset loader + built-in YAML presets
├── agents/          # Optional LLM agents (polish, tailor, layout)
├── templates/       # Jinja2 templates (LaTeX + HTML layouts/partials)
├── cli.py           # Typer CLI
└── web/             # FastAPI web app (future)
```

## License

MIT
