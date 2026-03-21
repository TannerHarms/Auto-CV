# Auto-CV Roadmap & Feature Planning

> **Version:** 1.0.0 (current)
> **Date:** 2026-03-20
> **Status:** Living document — update as phases progress.

---

## Architecture Summary

```
                  ┌──────────────────────────────────┐
                  │        User Interface             │
                  │  (CLI: Typer)  (Obsidian Plugin)  │
                  └──────────┬───────────────────────-┘
                             │
                  ┌──────────▼───────────────────────-┐
                  │     PARSER (vault_reader.py)       │
                  │  header.md → Resume + StyleConfig  │
                  │  _master ← project overrides       │
                  └──────────┬───────────────────────-┘
                             │
                  ┌──────────▼───────────────────────-┐
                  │     AGENTS (optional pipeline)     │
                  │  PolishAgent → TailorAgent →       │
                  │  LayoutAgent → (future agents)     │
                  │  Each returns Resume copy           │
                  └──────────┬───────────────────────-┘
                             │
                  ┌──────────▼───────────────────────-┐
                  │     RENDERERS (deterministic)      │
                  │  LaTeX / DOCX / HTML               │
                  └────────────────────────────────────┘
```

**Key invariant:** Agents modify the `Resume` model *before* rendering. Renderers
are pure functions of (Resume, StyleConfig) → output files. This separation must
be preserved across all phases.

**Agent interface contract:** `BaseAgent.process(resume, **kwargs) -> Resume`.
All agents that transform resumes extend this ABC. Agents that produce *other*
artifacts (cover letters, vault files) should not extend `BaseAgent` — they use
the shared LLM client utility directly (see Technical Notes).

---

## Phase 1 — Standalone Project Builds

**Priority:** Highest
**Scope:** Parser + CLI + Obsidian plugin
**Dependencies:** None — works on existing codebase

### Problem

Currently, building a project sub-vault requires referencing the parent master
vault:

```bash
auto-cv build my_vault -p platform-eng
```

This means the project directory can't be built in isolation. Users who want to
share or archive a single project can't just hand someone the project folder.

### Goal

Allow `auto-cv build projects/platform-eng` to work *without* the `-p` flag
by auto-detecting the master vault relationship.

### Design

#### 1a. Auto-detect master vault from project path

When `load_vault(path)` is called and `path` looks like it's inside a
`projects/<name>/` directory, walk up to find the parent vault:

```
projects/platform-eng/    ← user points here
  header.md               ← has `include:` key → signals it's a project
  sections/               ← local overrides
  _style.yml
../../_master/            ← resolved by walking up to grandparent
  header.md
  sections/
  _style.yml
```

**Detection heuristic** (in `vault_reader.py`):

```python
def _detect_project_context(vault_path: Path) -> tuple[Path, str] | None:
    """If vault_path is inside a projects/ dir, return (master_vault, project_name)."""
    if vault_path.parent.name == "projects":
        master_root = vault_path.parent.parent
        if (master_root / "_master").is_dir():
            return master_root, vault_path.name
    return None
```

**Changes required:**

| File | Change |
|------|--------|
| `src/auto_cv/parser/vault_reader.py` | Add `_detect_project_context()`. Update `load_vault()` to call it when `project=None` but path is inside `projects/`. |
| `src/auto_cv/cli.py` | No change needed — `load_vault()` handles it transparently. |
| `obsidian-plugin/src/utils.ts` | Update `buildResume()` to detect and pass project paths directly. |

#### 1b. Copy-to-standalone export (stretch goal)

Add a CLI command that copies a project into a fully self-contained flat vault:

```bash
auto-cv export my_vault -p platform-eng -o ~/Desktop/platform-eng-resume/
```

This resolves includes, merges master + project sections, and writes a flat
vault that needs no `_master/` reference.

**Changes required:**

| File | Change |
|------|--------|
| `src/auto_cv/cli.py` | New `export` command. |
| `src/auto_cv/parser/vault_reader.py` | New `export_flat_vault()` function. |

### Tasks

- [ ] Implement `_detect_project_context()` in vault_reader.py
- [ ] Update `load_vault()` to use auto-detection when `project` is None
- [ ] Add tests: build a project by pointing directly at its folder
- [ ] Update Obsidian plugin to support direct-project-folder builds
- [ ] (Stretch) Implement `export` CLI command
- [ ] Update README and docs/sections.md

### Acceptance Criteria

- `auto-cv build local_test_vault/projects/platform-eng` produces identical
  output to `auto-cv build local_test_vault -p platform-eng`
- Existing `-p` flag still works unchanged
- Obsidian plugin detects project folders and builds them correctly

---

## Phase 2 — Agentic Resume Generation

**Priority:** High
**Scope:** Agents + CLI + Obsidian plugin
**Dependencies:** Existing agent infrastructure (BaseAgent, PolishAgent, TailorAgent, LayoutAgent)

### Problem

The current agent pipeline (`--polish`, `--tailor-to`, `--suggest-layout`) works
post-parse: it takes a complete Resume model and tweaks it. There is no agent
that can *select from* a master vault's full content to build a targeted resume,
nor does any agent control formatting density (page count, compactness).

### Goal

A `GenerateAgent` that reads the full `_master` vault, optionally reads job
description text, and produces a project-ready Resume by selecting and optionally
tuning content — with user-controlled oversight levels.

### Design

#### 2a. Oversight Levels

Define an enum for how aggressively the agent may modify content:

```python
class AgentOversight(str, Enum):
    SELECT_ONLY = "select-only"      # Pick items/bullets, but change nothing
    LIGHT_TUNING = "light"           # Minor wording adjustments, keyword insertion
    HEAVY_TUNING = "heavy"           # Full rewrite of bullets, summary, etc.
```

**Rules per level:**

| Level | Section selection | Bullet selection | Text changes | Summary rewrite |
|-------|-------------------|------------------|--------------|-----------------|
| `select-only` | Yes | Yes | No | No |
| `light` | Yes | Yes | Minor keyword additions, verb substitution | Light targeting |
| `heavy` | Yes | Yes | Full rewrite for impact | Full rewrite |

**Invariant across all levels:** Factual data (company names, dates, degrees,
certifications, institutions) must **never** be altered. The LLM may only
modify bullet text, summary prose, and section/entry ordering.

#### 2b. Formatting Constraints

```python
@dataclass
class FormatConstraints:
    max_pages: int | None = None          # e.g., 1, 2
    density: Literal["compact", "normal", "open"] = "normal"
```

The agent translates these into concrete decisions:
- `max_pages=1` → limit total entries, shorten bullets, reduce sections
- `compact` → select fewer bullets per entry, tighter summary
- `open` → allow full content, more whitespace (maps to spacing overrides)

Density maps to style overrides that the agent sets on the Resume:

| Density | section_gap | entry_gap | line_height | bullet_list_topsep |
|---------|------------|-----------|-------------|-------------------|
| compact | 6pt | 4pt | 1.0 | -2mm |
| normal | (preset default) | | | |
| open | 14pt | 8pt | 1.3 | 0mm |

#### 2c. GenerateAgent Design

`GenerateAgent` extends `BaseAgent` (Resume → Resume) and **subsumes** the
existing `TailorAgent` and `LayoutAgent` for the `generate` workflow. It
performs selection, ordering, and optional text tuning in a single LLM call
rather than chaining separate agents. The existing `--polish`, `--tailor-to`,
and `--suggest-layout` flags on the `build` command remain as the lightweight
à la carte pipeline.

| Workflow | Agents used |
|----------|-------------|
| `build --polish --tailor-to` | TailorAgent → PolishAgent (unchanged) |
| `generate` | GenerateAgent (does selection + ordering + optional tuning) |

```python
class GenerateAgent(BaseAgent):
    """Selects and optionally tunes master vault content for a target role."""

    def process(self, resume: Resume, **kwargs) -> Resume:
        oversight: AgentOversight = kwargs.get("oversight", AgentOversight.SELECT_ONLY)
        job_description: str | None = kwargs.get("job_description")
        constraints: FormatConstraints = kwargs.get("constraints", FormatConstraints())

        # Step 1: Summarise full master vault content for LLM
        master_summary = self._summarise_master(resume)

        # Step 2: Build prompt based on oversight level
        prompt = self._build_prompt(master_summary, oversight, job_description, constraints)

        # Step 3: LLM returns selection + optional rewrites as JSON
        raw = self._chat(SYSTEM_PROMPT, prompt)
        plan = self._parse_response(raw)

        # Step 4: Apply plan to resume copy
        return self._apply(resume, plan, oversight)
```

**LLM response schema:**

```json
{
  "section_order": ["summary", "experience", "skills", "projects", "education"],
  "hidden_sections": ["publications", "awards"],
  "entry_selections": {
    "experience": ["Senior Platform Engineer@Acme Corp", "DevOps Lead@StartupCo"],
    "projects": ["Auto CV", "Infrastructure Monitor"]
  },
  "bullet_selections": {
    "Senior Platform Engineer@Acme Corp": [0, 1, 3],   // 0-based indices into that entry's highlights
    "DevOps Lead@StartupCo": [0, 2]
  },
  "rewrites": {
    "summary": "Rewritten summary text...",
    "Senior Platform Engineer@Acme Corp": ["Rewritten bullet 1", "Rewritten bullet 2"]
  }
}
```

For `select-only`, the `rewrites` key is empty. For `light`/`heavy`, it contains
modified text.

#### 2d. Job Description Import

Support importing one or more files containing job descriptions:

**CLI:**
```bash
# Single job description
auto-cv generate my_vault --job-file posting.txt --oversight light

# Multiple (agent considers all, produces one tailored resume)
auto-cv generate my_vault --job-file role1.txt --job-file role2.txt

# No job description — general-purpose generation
auto-cv generate my_vault --oversight select-only --max-pages 1
```

**Obsidian plugin:** New modal step for optional job description:
- Paste text directly into a text area
- Or select a .md/.txt file from the vault
- Or skip (agentic operations do not require imported text)

#### 2e. CLI Integration

New top-level command:

```python
@app.command()
def generate(
    vault: Path,
    format: list[OutputFormat] = [...],
    output: Path = Path("output"),
    project: str | None = None,        # Target project to create/update
    job_file: list[Path] | None = None, # One or more job description files
    oversight: AgentOversight = AgentOversight.SELECT_ONLY,
    max_pages: int | None = None,
    density: str = "normal",           # compact | normal | open
    model: str | None = None,
) -> None:
```

The `generate` command:
1. Loads the full `_master` vault (all sections, all entries)
2. Reads job description files (if any)
3. Runs `GenerateAgent.process()` with oversight and constraints
4. Optionally saves the selection as a new project `header.md`
5. Renders output

#### 2f. Obsidian Plugin Integration

Add a new wizard step (or modal variant) for agentic generation:

1. **Source** — Confirm master vault detected, show section count
2. **Job Description** (optional) — Paste or select file(s)
3. **Settings** — Oversight level dropdown, max pages, density
4. **Review** — Show what the agent selected before rendering (allow user to
   adjust selections)
5. **Build** — Render and show output

The review step is critical for user trust — they should see and approve what
the agent picked before committing to a build.

### Tasks

- [ ] Define `AgentOversight` enum and `FormatConstraints` dataclass in models
- [ ] Implement `GenerateAgent` in `src/auto_cv/agents/generate.py`
- [ ] Write system/user prompt templates for each oversight level
- [ ] Add `generate` command to CLI
- [ ] Add job-file reading and multi-file concatenation
- [ ] Write density-to-style-override mapping logic
- [ ] Add Obsidian plugin modal for agentic generation
- [ ] Add agent review/preview step to Obsidian plugin
- [ ] Write tests with mocked LLM responses
- [ ] Update README agents section

### Acceptance Criteria

- `auto-cv generate my_vault` with no flags produces a reasonable 1-page resume
  from the master vault using `select-only` oversight
- `auto-cv generate my_vault --job-file posting.txt --oversight light --max-pages 1`
  produces a 1-page resume tailored to the job with light text adjustments
- `select-only` never changes any text content — only selects/orders
- Factual data is never altered at any oversight level
- Obsidian plugin shows a review step before rendering
- Generated project can be saved and re-built later without the agent

---

## Phase 3 — Agentic Master Data Creation

**Priority:** Medium
**Scope:** New agent + CLI interactive mode + Obsidian plugin
**Dependencies:** Phase 2 agent infrastructure, BaseAgent

### Problem

New users face a cold-start problem: they need to populate an entire `_master`
vault with structured markdown before they can use auto-cv. This is tedious and
error-prone, especially for users unfamiliar with the section formats.

### Goal

A conversational agent that interviews the user and generates properly formatted
section files. Works in both CLI (interactive terminal) and Obsidian (chat-style
modal).

### Design

#### 3a. Interview Flow

For each section type, the agent follows a structured interview:

**Experience (per entry):**
```
→ What was your job title?
→ Company name?
→ Location? (City, State or Remote)
→ Start date? (e.g. 2021-01)
→ End date? (or "present")
→ Describe your role and key accomplishments. (freeform — agent will
    extract and format bullets)
→ Anything else you'd like to add for this role?
→ Add another position? (y/n)
```

**Education (per entry):**
```
→ Degree and field? (e.g. B.S. Computer Science)
→ Institution?
→ Location?
→ Dates?
→ GPA? (optional)
→ Any honors, relevant coursework, or highlights?
```

**Skills:**
```
→ List your technical skills — I'll help organise them into categories.
  (freeform — agent groups into categories)
```

**Summary:**
```
→ Tell me about yourself and what you're looking for.
  (Agent drafts a professional summary from freeform input)
→ Here's what I came up with — would you like to adjust anything?
```

Similar flows for: Projects, Certifications, Publications, Awards, Languages.

#### 3b. InterviewAgent Design

`InterviewAgent` does **not** extend `BaseAgent` — its interface is multi-turn
conversation, not `Resume → Resume`. It uses the shared `LLMClient` utility
(see Technical Notes) for LLM communication.

```python
class InterviewAgent:
    """Conversational agent that generates master vault sections from Q&A."""

    def __init__(self, *, model: str | None = None):
        self._llm = LLMClient(model=model)

    def interview_section(
        self,
        section_type: SectionType,
        answers: list[dict],        # Q&A pairs from the UI
    ) -> str:
        """Generate a formatted markdown section file from interview answers."""
        # Builds prompt with section format spec + user answers
        # Returns markdown content ready to write to file

    def suggest_next_question(
        self,
        section_type: SectionType,
        answers_so_far: list[dict],
    ) -> str:
        """Return the next question to ask based on what's been answered."""
```

The agent is **not** a single `.process()` call — it's a multi-turn conversation.
The UI (CLI or Obsidian) drives the loop:

```
while not done:
    question = agent.suggest_next_question(section_type, answers)
    answer = get_user_input(question)
    answers.append({"q": question, "a": answer})
    if answer signals "done" or "next section":
        markdown = agent.interview_section(section_type, answers)
        write_section_file(markdown)
        move to next section
```

#### 3c. CLI Interactive Mode

```bash
auto-cv interview my_vault
```

- Uses `rich.prompt.Prompt` for interactive terminal Q&A
- Shows progress: "Section 2/7: Experience"
- At the end, writes all section files and a `header.md`
- User can `Ctrl+C` at any time; already-written files are preserved

#### 3d. Obsidian Plugin Chat Modal

New modal with a chat-style interface:
- Agent messages appear as formatted bubbles
- User types answers in a text input
- Section files are written to the vault as they're completed
- Progress indicator shows which sections are done
- "Skip this section" button for optional sections

### Tasks

- [ ] Design question templates for each SectionType
- [ ] Implement `InterviewAgent` with `suggest_next_question()` and `interview_section()`
- [ ] Implement CLI `interview` command with Rich interactive prompts
- [ ] Implement Obsidian chat-style interview modal
- [ ] Handle partial completion (resume interview later)
- [ ] Write tests with mocked LLM for question generation and section formatting
- [ ] Add `--section` flag to interview a single section type

### Acceptance Criteria

- `auto-cv interview my_vault` walks user through all sections and produces
  a valid vault that builds without errors
- Obsidian chat modal produces identical vault output
- Generated markdown matches the project's format conventions exactly
- Users can skip optional sections
- Partial progress is preserved if interrupted

---

## Phase 4 — Agentic Cover Letter Composition

**Priority:** Medium-Low
**Scope:** New agent + new renderer + CLI + Obsidian plugin
**Dependencies:** Phase 2 (job description import, oversight framework)

### Problem

Cover letters are tightly coupled to resumes but currently out of scope. Users
need a separate tool or manual process to create matching cover letters.

### Goal

Generate formatted cover letters that are consistent with the resume's visual
theme and content, using the same preset/style system.

### Design

#### 4a. Cover Letter Model

```python
class CoverLetter(BaseModel):
    """Structured cover letter content."""
    recipient_name: str | None = None
    recipient_title: str | None = None
    company_name: str
    date: str                          # Auto-filled or user-specified
    greeting: str                      # "Dear Hiring Manager,"
    opening_paragraph: str             # Hook + why this role
    body_paragraphs: list[str]         # 1-3 paragraphs mapping experience to role
    closing_paragraph: str             # Call to action
    sign_off: str                      # "Sincerely,"
    # Inherits name, contact from Resume.config
```

#### 4b. CoverLetterAgent

`CoverLetterAgent` does **not** extend `BaseAgent` — it returns a `CoverLetter`,
not a `Resume`. It uses the shared `LLMClient` utility for LLM communication.

```python
class CoverLetterAgent:
    def __init__(self, *, model: str | None = None):
        self._llm = LLMClient(model=model)

    def compose(self, resume: Resume, **kwargs) -> CoverLetter:
        job_description: str = kwargs["job_description"]
        company_name: str = kwargs.get("company_name", "")
        tone: str = kwargs.get("tone", "professional")  # professional|warm|concise
        # Reads resume content to reference specific achievements
        # Generates cover letter that complements (not repeats) the resume
```

**Key rules for the LLM:**
- Reference specific achievements from the resume, don't just list them
- Complement the resume — add narrative depth, don't duplicate
- Match the tone to the role (enterprise = formal, startup = conversational)
- Always stay truthful to the person's actual experience

#### 4c. Rendering

Cover letters use the same preset system but with letter-specific templates:

| Format | Template |
|--------|----------|
| LaTeX | `templates/cover_letter.tex.j2` — uses same fonts, colors, header |
| DOCX | Same header style, business letter formatting |
| HTML | Same CSS theme, letter layout |

The letter header matches the resume header (name, contact info, styling) for
visual consistency.

#### 4d. CLI Integration

```bash
# Generate cover letter alongside resume
auto-cv cover-letter my_vault --job-file posting.txt --company "Acme Corp"

# Generate both resume and cover letter
auto-cv generate my_vault --job-file posting.txt --cover-letter --company "Acme Corp"
```

#### 4e. Obsidian Integration

Add a "Cover Letter" option to the build wizard:
- Toggle in the output step: "Also generate cover letter"
- Additional fields: company name, recipient (optional), tone
- Preview before rendering

### Tasks

- [ ] Define `CoverLetter` model in `src/auto_cv/models/`
- [ ] Implement `CoverLetterAgent` in `src/auto_cv/agents/`
- [ ] Create LaTeX cover letter template (Jinja2)
- [ ] Create DOCX cover letter renderer
- [ ] Create HTML cover letter template
- [ ] Add `cover-letter` CLI command
- [ ] Integrate into `generate` command with `--cover-letter` flag
- [ ] Add Obsidian plugin cover letter toggle and fields
- [ ] Write tests
- [ ] Ensure all 9 presets produce visually consistent letter + resume pairs

### Acceptance Criteria

- Cover letter uses the same visual theme (fonts, colors, header) as the resume
- Generated text references actual resume content, never invents achievements
- All 3 output formats (HTML, LaTeX, DOCX) produce professional letters
- Works with or without a job description file

---

## Phase 5 — User Feedback Integration

**Priority:** Low
**Scope:** Obsidian plugin + GitHub integration
**Dependencies:** GitHub repo (TannerHarms/Auto-CV already public)

### Problem

No built-in mechanism for users to report bugs, request features, or provide
general feedback without leaving the app.

### Goal

A lightweight feedback button in the Obsidian plugin that pre-populates a GitHub
issue with contextual information.

### Design

#### 5a. Feedback Button

Add a "Send Feedback" button to:
- The plugin settings tab
- The post-build success modal
- The ribbon menu (optional)

#### 5b. Issue Pre-Population

When clicked, opens the user's browser to a pre-filled GitHub issue URL:

```
https://github.com/TannerHarms/Auto-CV/issues/new?
  template=feedback.yml&
  title=[Feedback] &
  labels=feedback&
  body=...
```

**Auto-included context** (with user consent):
- Auto-CV version (from manifest.json)
- Obsidian version
- OS platform
- Preset used (if just built)
- Format(s) rendered
- **Never** include resume content, personal data, or API keys

#### 5c. Issue Templates

Create `.github/ISSUE_TEMPLATE/feedback.yml`:

```yaml
name: Feedback
description: Share feedback, report a bug, or request a feature.
labels: ["feedback"]
body:
  - type: dropdown
    id: type
    attributes:
      label: Feedback Type
      options:
        - Bug Report
        - Feature Request
        - General Feedback
    validations:
      required: true
  - type: textarea
    id: description
    attributes:
      label: Description
  - type: textarea
    id: context
    attributes:
      label: Environment (auto-filled)
```

#### 5d. Optional: In-App Rating

After a successful build, show a non-intrusive prompt:
```
"How was your experience? [Great] [Could be better] [Report Issue]"
```
- "Great" → optional redirect to leave a GitHub star
- "Could be better" → opens feedback issue
- "Report Issue" → opens bug report template
- Prompt only shows once per session, can be permanently dismissed

### Tasks

- [ ] Create `.github/ISSUE_TEMPLATE/feedback.yml`
- [ ] Create `.github/ISSUE_TEMPLATE/bug_report.yml`
- [ ] Add "Send Feedback" button to Obsidian plugin settings tab
- [ ] Add post-build feedback prompt (dismissible)
- [ ] Implement URL builder with auto-filled context
- [ ] Ensure no personal data is included in pre-filled content
- [ ] Test URL generation across platforms (Windows, macOS, Linux)

### Acceptance Criteria

- Feedback button opens browser to pre-filled GitHub issue
- No personal data (resume content, names, emails) is ever sent
- User can dismiss the feedback prompt permanently
- Works on all OSes Obsidian supports

---

## Phase Summary & Sequencing

```
Phase 1: Standalone Project Builds        ← Start here (small, high-value)
  │
  ▼
Phase 2: Agentic Resume Generation         ← Core differentiator
  │
  ├─── Phase 3: Agentic Master Data        ← Can start in parallel
  │    Creation                                with Phase 2 rendering work
  │
  ▼
Phase 4: Agentic Cover Letters             ← Builds on Phase 2 infra
  │
  ▼
Phase 5: User Feedback                     ← Low effort, do whenever
```

**Phases 2 and 3 share common infrastructure** (LLM prompt patterns, JSON
schema round-tripping, Obsidian modal patterns) so working on them in
overlapping windows is efficient.

**Phase 5 is independent** and can be shipped at any time — even before Phase 1
if early feedback collection is desired.

---

## Version Targeting

| Phase | Target Version | Estimated Scope |
|-------|---------------|-----------------|
| Phase 1 | 1.1.0 | ~2-3 days |
| Phase 2 | 1.2.0 | ~1-2 weeks |
| Phase 3 | 1.3.0 | ~1 week |
| Phase 4 | 1.4.0 | ~1 week |
| Phase 5 | Any (1.1.0+) | ~1 day |

---

## Technical Notes

### LLM Client Extraction

Phases 3 and 4 introduce agents that don't conform to the `BaseAgent` interface
(`Resume → Resume`). Before starting Phase 3, extract the LLM plumbing from
`BaseAgent` into a standalone utility:

```python
class LLMClient:
    """Shared LLM communication — used by all agents."""
    def __init__(self, *, model: str | None = None):
        self.model = model or os.environ.get("AUTO_CV_MODEL", "gpt-4o")
        self.api_key = os.environ.get("OPENAI_API_KEY", "")

    def chat(self, system: str, user: str, *, temperature: float = 0.3) -> str: ...
    def chat_multi(self, messages: list[dict], *, temperature: float = 0.3) -> str: ...
```

`BaseAgent` delegates to `LLMClient` internally. Non-BaseAgent classes
(`InterviewAgent`, `CoverLetterAgent`) instantiate `LLMClient` directly.
`chat_multi()` supports multi-turn conversations needed by `InterviewAgent`.

### LLM Provider Flexibility

The current `BaseAgent` is hardcoded to OpenAI. Before Phase 2 ships, consider:
- Adding `provider` field (openai, anthropic, local)
- Using `litellm` as an abstraction layer for multi-provider support
- Environment variable pattern: `AUTO_CV_PROVIDER=anthropic AUTO_CV_MODEL=claude-sonnet-4-20250514`

### Token Budget Management

Phase 2's `GenerateAgent` will send the entire master vault to the LLM. For
large vaults, this could exceed context windows. Strategies:
- Summarise entries before sending (like `TailorAgent._summarise_resume()`)
- Chunk by section type if needed
- Track token usage and warn if approaching limits

### Obsidian Plugin State Management

Phases 2-4 introduce multi-turn interactions in the plugin. Current modals are
single-shot. Consider:
- A shared state store (simple class with observable properties)
- Persisting agent session state in plugin settings for resume-later flows
- Using Obsidian's `ItemView` for more complex UIs instead of modal stacking

### Testing Strategy

All agents should be testable without making real LLM calls:
- Mock `_chat()` in BaseAgent to return fixture JSON
- Existing pattern in `test_agents.py` already does this
- Add integration tests that run against a live LLM (skipped in CI, runnable
  locally with `--run-live-agents` flag)
