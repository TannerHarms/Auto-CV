# Plan: Auto_Resume — Markdown-to-Resume Builder

## TL;DR

Build a Python tool that reads an Obsidian-style markdown vault (one file per section, YAML frontmatter-first) and deterministically renders resumes to three outputs: a structured LaTeX repo that compiles to PDF, a .docx file, and an HTML digital resume. Styling is controlled via presets + YAML overrides. Optional LLM agents polish content, tailor to job descriptions, or suggest layout. Architecture is CLI-first but web-app-ready from day one.

---

## Architecture

```text
src/auto_resume/
├── __init__.py
├── models/              # Pydantic data models (no I/O)
│   ├── resume.py        # Resume, Section, typed entries
│   └── style.py         # StyleConfig, ColorScheme, FontScheme, etc.
├── parser/              # Vault → models
│   └── vault_reader.py  # Read _config.yml, _style.yml, sections/*.md
├── renderers/           # Models → output files (each is independent)
│   ├── base.py          # Abstract Renderer interface
│   ├── latex.py         # Generates LaTeX repo structure + compiles
│   ├── docx.py          # Generates .docx via python-docx
│   └── html.py          # Generates HTML site via Jinja2
├── styles/              # Preset definitions
│   ├── presets.py        # Registry of built-in presets
│   └── presets/          # YAML preset files (classic.yml, modern.yml, minimal.yml)
├── agents/              # Optional LLM integration
│   ├── base.py          # Agent interface
│   ├── polish.py        # Rewrite/improve bullet points
│   ├── tailor.py        # Tailor resume to a job description
│   └── layout.py        # Suggest section ordering / emphasis
├── templates/           # Jinja2 templates
│   ├── latex/           # .tex.j2 templates (per section type + main/sty)
│   └── html/            # HTML layout templates
│       ├── layouts/     # top-header/, sidebar/, cards/ — each a full template set
│       └── partials/    # Shared section partials (experience.html.j2, etc.)
├── cli.py               # Typer CLI (thin wrapper around core)
└── web/                 # FastAPI (future phase)
    ├── app.py
    └── routes/
```

### Vault (input) structure

```text
my_resume/
├── _config.yml          # Name, contact info, section ordering, metadata, html_meta
├── _style.yml           # Optional: preset name + overrides (commented template on init)
├── sections/
│   ├── 01-summary.md
│   ├── 02-experience.md
│   ├── 03-education.md
│   ├── 04-skills.md
│   └── 05-projects.md
├── pages/               # Optional: extra pages for HTML output only
│   ├── portfolio.md
│   └── about.md
├── presets/              # Optional: vault-local custom presets
│   └── my_corporate.yml
├── assets/
│   └── photo.jpg
├── custom.css           # Optional: auto-included in HTML output
├── custom.js            # Optional: auto-included in HTML output
└── resume.sty           # Optional: overrides generated LaTeX .sty entirely
```

### LaTeX output structure (per user request)

```text
output/latex/
├── main.tex             # \input{sections/*}, document setup
├── resume.sty           # Style file: colors, fonts, spacing, section commands
├── sections/
│   ├── summary.tex
│   ├── experience.tex
│   ├── education.tex
│   ├── skills.tex
│   └── projects.tex
└── (resume.pdf)         # Compiled via latexmk if available
```

---

## Steps

### Phase 1: Foundation (no dependencies between steps 1–3)

1. **Project scaffolding** — Create pyproject.toml, .gitignore, src layout, `__init__.py` files. Dependencies: pydantic, pyyaml, python-frontmatter, jinja2, python-docx, markdown, typer, rich.

2. **Data models** (`models/resume.py`, `models/style.py`)
   - `Resume` (top-level), `ResumeConfig` (name, contact, section order), `Section` (generic section with typed sub-lists), `ContactInfo`
   - Typed entry models: `ExperienceEntry`, `EducationEntry`, `SkillCategory`, `ProjectEntry`, `CertificationEntry` — each with `DateRange`
   - `SectionType` enum mapping known section types
   - `StyleConfig` with nested `ColorScheme`, `FontScheme`, `SpacingScheme`, plus output-specific options (`LatexOptions`, `DocxOptions`, `HtmlOptions`)
   - `StyleConfig.merge()` for deep-merging preset + user overrides

3. **Style presets** (`styles/presets.py`, `styles/presets/*.yml`)
   - Three built-in presets: `classic` (traditional serif), `modern` (clean sans-serif, color accents), `minimal` (maximum whitespace)
   - Each is a YAML file that maps 1:1 to StyleConfig
   - `load_preset(name) -> StyleConfig` function
   - Vault's `_style.yml` references a preset by name and overrides specific fields
   - **Vault-local presets**: `preset: ./presets/my_corporate.yml` loads from vault's `presets/` dir. Users can build, save, and share custom presets.
   - **Commented `_style.yml` on init**: `auto-resume init` generates a fully-commented `_style.yml` showing every key with descriptions + defaults — acts as live documentation
   - **`style-schema` CLI command**: `auto-resume style-schema` prints the full style schema with types, descriptions, and defaults

### Phase 2: Core Pipeline (sequential: 4 → 5–7 parallel)

1. **Vault parser** (`parser/vault_reader.py`)
   - `load_vault(path) -> (Resume, StyleConfig)`: main entry point
   - Reads `_config.yml` → `ResumeConfig` (including `html_meta` if present)
   - Reads `_style.yml` → loads preset (built-in or vault-local via `./presets/` path), merges overrides → `StyleConfig`
   - Reads `sections/*.md`: for each file, parse frontmatter (structured entries) and body (raw markdown). Filename prefix (`01-`, `02-`) determines order; frontmatter `type` key maps to `SectionType`.
   - Reads `pages/*.md` (if present): extra pages for HTML output. Same frontmatter parsing.
   - Detects vault-level override files: `resume.sty`, `custom.css`, `custom.js`
   - Populates typed entry lists on each `Section` based on its `SectionType`

2. **LaTeX renderer** (`renderers/latex.py`, `templates/latex/`) — *parallel with 6, 7*
   - `LatexRenderer.render(resume, style, output_dir)`
   - Generate `resume.sty` from style config (colors via xcolor, fonts, spacing, custom commands like `\cvsection`, `\cventry`)
   - **Vault .sty override**: if vault contains `resume.sty`, copy it into output instead of generating. Lets power users hand-craft their LaTeX style once and reuse it.
   - Generate `main.tex` with document class, `\usepackage{resume}`, `\input{sections/*}` in order
   - Generate per-section .tex files from Jinja2 templates (one template per SectionType + a fallback for CUSTOM)
   - Compile step: shell out to `latexmk -pdf main.tex` if available; log warning if not installed
   - Escape LaTeX special chars in all user data (& % $ # _ { } ~ ^ \)

3. **DOCX renderer** (`renderers/docx.py`) — *parallel with 5, 7*
   - `DocxRenderer.render(resume, style, output_dir)`
   - Use python-docx to build a .docx from scratch (no template dependency)
   - Map StyleConfig → Word styles (fonts, colors, spacing)
   - Section-by-section rendering: heading + entries using styled paragraphs/runs
   - Support for skill tables (tabular layout for skill categories)

4. **HTML renderer** (`renderers/html.py`, `templates/html/`) — *parallel with 5, 6*
   - `HtmlRenderer.render(resume, style, output_dir)`
   - **Layout templates**: Named layouts, not just a flag. Three built-in:
     - `top-header` — traditional single-column, name/contact at top (default)
     - `sidebar` — two-column: contact/skills/photo in a fixed sidebar, main content on right
     - `cards` — grid of cards per section, modern portfolio feel
   - Each layout is a Jinja2 template set (base + section partials). Users select via `html.layout: sidebar` in `_style.yml`.
   - **Inline CSS from StyleConfig** — No external framework dependency. Colors, fonts, spacing map directly to CSS variables.
   - **`custom.css` / `custom.js` auto-include** — If these files exist in the vault root, they are automatically linked in the HTML output. Full escape hatch for power users.
   - **`pages/` directory (HTML-only)** — Vault can contain `pages/*.md` for extra pages beyond resume sections (portfolio, about, blog-style posts). Each becomes a separate HTML page. Ignored by LaTeX/DOCX.
   - **Multi-page nav** — When `pages/` exist or `html.layout = "multi-page"`, a nav bar is generated with links between pages.
   - **Print stylesheet** — Every layout includes `@media print` rules: single-column collapse, hide nav, drop background colors, clean typography. "Print to PDF" from browser looks professional.
   - **Asset handling** — Images from `assets/` are copied to `output/html/assets/` and referenced with relative paths. Future: `--inline-assets` flag to base64-encode everything for single-file output.
   - **Photo & meta** — `ResumeConfig.photo` is rendered in the header/sidebar. `_config.yml` can include `html_meta` dict for `<title>`, `<meta description>`, Open Graph tags, favicon path — matters if hosted.
   - **Markdown body → HTML** — Section markdown content rendered via `markdown` library with extensions (tables, fenced code, etc.)

### Phase 3: Interface & Content

1. **CLI** (`cli.py`) — *depends on 4–7*
   - `auto-resume build <vault_path> --format latex,docx,html --output ./output`
   - `auto-resume init <path>` — scaffold a new vault with example content
   - `auto-resume preview` — quick HTML render + open in browser
   - `auto-resume list-presets` — show available style presets
   - Uses Typer for argument parsing, Rich for terminal output

2. **Example vault** — *parallel with 8*
   - Full example vault with realistic content (fictional person)
   - Demonstrates all section types, frontmatter patterns, and style overrides
   - Serves as documentation-by-example and test fixture

### Phase 4: Agents (optional module)

1. **Agent framework** (`agents/`) — *depends on 4*
    - `BaseAgent` abstract class with `process(resume, **kwargs) -> Resume` interface
    - `PolishAgent`: takes resume, rewrites bullet points for impact/conciseness
    - `TailorAgent`: takes resume + job description text, adjusts emphasis/keywords
    - `LayoutAgent`: suggests section ordering and visibility for a given target role
    - CLI flags: `--polish`, `--tailor-to <job_description.txt>`
    - All agents return a *modified copy* of the Resume model — deterministic pipeline then renders it
    - Provider-agnostic: support OpenAI API by default, configurable via env vars

### Phase 5: Testing & Documentation

1. **Tests** — `tests/`
    - Unit tests for models (serialization, merging, ordering)
    - Unit tests for parser (fixture vaults in `tests/fixtures/`)
    - Integration tests for each renderer (generate output, verify structure)
    - LaTeX test: verify .tex files are valid (parseable, no missing braces)
    - DOCX test: verify output is valid .docx (can be opened by python-docx)
    - HTML test: verify output contains expected sections/content

2. **README & docs**
    - Project overview, installation, quickstart
    - Vault format documentation (frontmatter schemas per section type)
    - Style customization guide
    - CLI reference

---

## Relevant Files

- `pyproject.toml` — Project config, dependencies, entry point
- `src/auto_resume/models/resume.py` — Core data models (Resume, Section, typed entries)
- `src/auto_resume/models/style.py` — Style models (StyleConfig, ColorScheme, etc.)
- `src/auto_resume/parser/vault_reader.py` — Vault loading + frontmatter parsing (incl. pages/, override detection)
- `src/auto_resume/renderers/base.py` — Abstract Renderer interface
- `src/auto_resume/renderers/latex.py` — LaTeX repo generation + .sty override support + compilation
- `src/auto_resume/renderers/docx.py` — DOCX generation
- `src/auto_resume/renderers/html.py` — HTML site generation (layout selection, multi-page, assets, custom CSS/JS)
- `src/auto_resume/styles/presets.py` — Preset loader + registry (built-in + vault-local)
- `src/auto_resume/styles/presets/classic.yml` — Classic preset
- `src/auto_resume/styles/presets/modern.yml` — Modern preset
- `src/auto_resume/styles/presets/minimal.yml` — Minimal preset
- `src/auto_resume/templates/latex/` — Jinja2 LaTeX templates (main, sty, per-section-type)
- `src/auto_resume/templates/html/layouts/` — HTML layout template sets (top-header, sidebar, cards)
- `src/auto_resume/templates/html/partials/` — Shared HTML section partials
- `src/auto_resume/agents/` — Optional LLM agent modules
- `src/auto_resume/cli.py` — Typer CLI
- `example_vault/` — Example resume vault (incl. pages/, presets/, assets/)

## Verification

1. `auto-resume init test_vault` creates a valid vault with all expected files including commented `_style.yml`
2. `auto-resume build example_vault --format latex` produces `output/latex/` with `main.tex`, `resume.sty`, `sections/*.tex`; running `latexmk -pdf main.tex` inside that dir compiles cleanly
3. `auto-resume build example_vault --format docx` produces a valid .docx that opens in Word/LibreOffice
4. `auto-resume build example_vault --format html` produces HTML with all sections, correct layout, print-friendly `@media print`
5. Changing `preset: modern` in `_style.yml` visibly changes output styling across all formats
6. Changing `html.layout: sidebar` renders a two-column layout; `cards` renders a grid
7. Dropping a `resume.sty` in the vault root overrides the generated style in LaTeX output
8. Adding a `custom.css` to the vault root applies custom styles in HTML output
9. Creating `pages/portfolio.md` adds a linked portfolio page in HTML output (ignored by LaTeX/DOCX)
10. `auto-resume style-schema` prints all available style keys with defaults
11. `pytest tests/` passes with all unit + integration tests green

## Decisions

- **Frontmatter-first**: Structured data lives in YAML frontmatter. Markdown body is supplemental (e.g., a paragraph summary or custom HTML). This keeps parsing deterministic.
- **LaTeX structure**: Output is a full repo (main.tex + resume.sty + sections/*.tex), not a monolithic .tex file. Users can hand-edit individual pieces or override .sty entirely.
- **Deterministic by default**: Zero LLM calls in the standard build pipeline. Agents are opt-in via CLI flags and never mutate files on disk — they return modified Resume models.
- **Web-ready architecture**: Core logic (models, parser, renderers) has no CLI/web dependencies. CLI and web are thin wrappers calling the same functions.
- **HTML is a website, not a document**: The HTML renderer supports layouts, multi-page, custom CSS/JS, assets, and meta tags — treating it as a deployable personal site.
- **Style system is layered**: built-in presets → vault-local presets → `_style.yml` overrides → per-output override files (`resume.sty`, `custom.css`). Each layer gives more control.

## Further Considerations

1. **Obsidian wikilink support** — Should `[[links]]` between section files be resolved (e.g., experience referencing a project)? Recommendation: Not in v1; treat each section as standalone.
2. **LaTeX toolchain dependency** — Should we bundle or recommend a specific LaTeX distribution? Recommendation: Document that TeX Live / MiKTeX is required; detect via `which latexmk` and give a clear error if missing.
3. **Asset handling for HTML** — Resolved: copy to `output/html/assets/` and reference relatively. Future: `--inline-assets` flag for single-file output.
