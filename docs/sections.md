# Section Authoring Guide

Every resume section lives in its own markdown file under `sections/`. The filename prefix (`01-`, `02-`, etc.) controls the default display order.

## Frontmatter

Each section file starts with YAML frontmatter:

```yaml
---
type: experience        # Section type (see table below)
order: 2                # Display order (overrides filename prefix)
title: Work Experience  # Custom section title (optional)
visible: true           # Set to false to hide a section
display: ""             # Display variant (see Awards section)
---
```

- **`type`** is required. It tells the parser which format to expect.
- **`title`** is optional — if omitted, the first `# Heading` in the body is used, then the filename.
- **`display`** is optional — currently only `awards` supports variants (`compact`, `expressive`).

## Supported Section Types

| Type              | Entry Model         | Description                                          |
|-------------------|---------------------|------------------------------------------------------|
| `summary`         | *(raw text)*        | Free-form professional summary / objective           |
| `experience`      | `ExperienceEntry`   | Work experience with role, company, dates, bullets   |
| `education`       | `EducationEntry`    | Degrees with institution, GPA, coursework, bullets   |
| `skills`          | `SkillCategory`     | Categorised skill lists                              |
| `projects`        | `ProjectEntry`      | Personal/professional projects with tech stack       |
| `certifications`  | `CertificationEntry`| Professional certifications with issuer and date     |
| `publications`    | `PublicationEntry`  | Papers, articles with venue, authors, DOI            |
| `awards`          | `AwardEntry`        | Honours, awards, fellowships, societies              |
| `volunteer`       | `ExperienceEntry`   | Volunteer work — same format as experience           |
| `service`         | `ExperienceEntry`   | Academic/professional service — same as experience   |
| `languages`       | `LanguageEntry`     | Language proficiency entries                          |
| `interests`       | `SkillCategory`     | Interests grouped by category — same as skills       |
| `references`      | `ReferenceEntry`    | Professional references with contact info            |
| `custom`          | *(raw text)*        | Any content not matching a known type                |

---

## Markdown Formats

Each structured section type supports **two** authoring formats. You can mix and match across sections but should use one format consistently within a section.

### Format A — Key-Value Lines

Structured fields are written as `**Key:** Value` lines below each `## Heading`:

```markdown
## Senior Software Engineer
**Company:** Acme Corp
**Location:** San Francisco, CA
**Dates:** 2021-01 – present

- Led migration of monolith to microservices
- Mentored 3 junior engineers
```

### Format B — Pipe-Delimited Metadata

A compact single-line format using `**Bold** | Field | Field`:

```markdown
## Senior Software Engineer
**Acme Corp** | San Francisco, CA | 2021-01 – present

- Led migration of monolith to microservices
- Mentored 3 junior engineers
```

The parser automatically classifies pipe-separated fields as organisation, location, or date based on content heuristics (dates contain years or "present").

---

## Section Type Details

### Summary

Free-form text. No entry parsing — the markdown body renders directly.

```markdown
---
type: summary
---

# Professional Summary

Experienced software engineer with 10+ years building distributed systems.
Passionate about developer experience and open-source tooling.
```

---

### Experience

**Fields:** `title` (from heading), `organization`, `location`, `dates`, `highlights`, `description`, `tags`

**Key-Value format:**

```markdown
---
type: experience
---

# Work Experience

## Senior Software Engineer
**Company:** Acme Corp
**Location:** San Francisco, CA
**Dates:** 2021-01 – present

- Led migration of monolith to microservices, reducing deploy time by 60%
- Mentored 3 junior engineers through structured code review programme

## Backend Developer
**Company:** StartupCo
**Location:** Austin, TX
**Dates:** 2018-06 – 2021-01

- Built real-time data pipeline processing 1M events/day
- Designed REST API serving 50+ frontend clients
```

**Pipe-delimited format:**

```markdown
## Senior Software Engineer
**Acme Corp** | San Francisco, CA | 2021-01 – present

- Led migration of monolith to microservices
```

**Recognised keys:** `company`, `organization`, `employer`, `location`, `dates`, `date`

---

### Education

**Fields:** `degree` (from heading), `institution`, `location`, `dates`, `gpa`, `highlights`, `coursework`

**Key-Value format:**

```markdown
---
type: education
---

# Education

## Ph.D. Computer Science
**Institution:** Stanford University
**Location:** Stanford, CA
**Dates:** 2017 – 2022

- Thesis: "Scalable Graph Neural Networks"
- Stanford Graduate Fellowship

## B.S. Mathematics
**Institution:** MIT
**Location:** Cambridge, MA
**Dates:** 2013 – 2017
**GPA:** 3.95

- Summa Cum Laude
- Dean's List all semesters
```

**Pipe-delimited format:**

```markdown
## B.S. Mathematics
**MIT** | Cambridge, MA | 2013 – 2017

GPA: 3.95
- Summa Cum Laude
```

**Recognised keys:** `institution`, `school`, `university`, `location`, `dates`, `date`, `gpa`

**Special:** Lines matching `GPA: ...` are extracted as the GPA field even without the `**Key:**` prefix.

---

### Skills

**Fields:** `name` (category name), `skills` (list of skills)

Skills use `### Heading` sub-sections (level 3) to define categories.

**Sub-heading format:**

```markdown
---
type: skills
---

# Technical Skills

### Programming Languages
Python, TypeScript, Go, SQL

### Cloud & DevOps
- AWS (EC2, Lambda, S3)
- Docker, Kubernetes
- Terraform

### Databases
PostgreSQL, Redis, MongoDB
```

Under each `###` heading, skills are parsed from either comma-separated text or bullet lists.

**Bold-key fallback format:**

```markdown
**Programming Languages:** Python, TypeScript, Go, SQL
**Cloud & DevOps:** AWS, Docker, Kubernetes, Terraform
```

---

### Projects

**Fields:** `name` (from heading), `url`, `dates`, `description`, `highlights`, `technologies`

**Key-Value format:**

```markdown
---
type: projects
---

# Projects

## [Auto CV](https://github.com/TannerHarms/Auto-CV)
**Technologies:** Python, Jinja2, Pydantic
**Dates:** 2024

A markdown-to-resume generator supporting multiple output formats.

- Supports LaTeX, DOCX, and HTML output
- 9 built-in style presets
```

**Pipe-delimited format:**

```markdown
## Auto CV
**Python, Jinja2** | 2024

https://github.com/TannerHarms/Auto-CV

- Supports multiple output formats
```

**Recognised keys:** `technologies`, `tech`, `stack`, `tools`, `dates`, `date`, `url`, `link`

**Special:**

- Heading can be a link: `## [Name](url)` to extract the URL
- Standalone URL lines (`https://...`) are captured as the project URL
- Non-bullet, non-metadata paragraph text becomes the `description`

---

### Certifications

**Fields:** `name` (from heading), `issuer`, `date`, `url`

**Key-Value format:**

```markdown
---
type: certifications
---

# Certifications

## [AWS Solutions Architect – Associate](https://verify.link)
**Issuer:** Amazon Web Services
**Date:** 2023-05

## Certified Kubernetes Administrator
**Issuer:** CNCF
**Date:** 2022-11
```

**Pipe-delimited format:**

```markdown
## AWS Solutions Architect
**Amazon Web Services** | 2023-05
```

**Recognised keys:** `issuer`, `organization`, `date`, `year`

**Special:** Heading can be a link `[Name](url)` to extract the credential URL.

---

### Publications

**Fields:** `title` (from heading), `venue`, `date`, `url`, `authors`

**Key-Value format:**

```markdown
---
type: publications
---

# Publications

## [Scalable Graph Neural Networks](https://doi.org/10.1234)
**Venue:** NeurIPS 2023
**Authors:** Smith, J., Doe, A., Johnson, B.
**Date:** 2023

## Efficient Transformer Architectures
**Venue:** ICML 2022
**Authors:** Doe, A., Smith, J.
**Date:** 2022
```

**Pipe-delimited format:**

```markdown
## Paper Title
**NeurIPS 2023** | 2023

Authors: Smith, J., Doe, A.
```

**Recognised keys:** `venue`, `journal`, `conference`, `date`, `year`, `authors`, `author`, `by`

**Special:**

- Heading can be a link `[Title](url)` to extract the DOI/URL
- Freeform `Authors:` lines (without bold prefix) are also parsed

---

### Awards

**Fields:** `title` (from heading), `issuer`, `date`, `location`, `description`, `highlights`

**Key-Value format:**

```markdown
---
type: awards
---

# Honours & Awards

## NSF Postdoctoral Research Fellowship
**Issuer:** National Science Foundation
**Date:** 2022

## Best Paper Award
**Issuer:** IEEE
**Date:** 2023
**Location:** New York, NY

Recognised for outstanding contribution to the field.

- 500+ citations in first year
- Invited keynote at follow-up symposium
```

**Pipe-delimited format:**

```markdown
## NSF Postdoctoral Fellowship
**National Science Foundation** | 2022
```

**Recognised keys:** `issuer`, `organization`, `awarded by`, `date`, `year`, `location`

#### Display Variants

Awards support three display modes, set in the frontmatter:

```yaml
---
type: awards
display: compact    # or "expressive" or "" (default)
---
```

| Variant | Appearance |
| :-- | :-- |
| *(default)* | Honour-style: date on the left, title + issuer on the right |
| `compact` | One line per award: title (+ issuer) on left, date on right |
| `expressive` | Full entry layout like experience: title, issuer, date, location, bullet points |

**Compact** is ideal for professional affiliations, society memberships, or long award lists.
**Expressive** is ideal for major honours where you want to elaborate with descriptions and bullet points.

---

### Custom / Fallback Types

Section type `custom` renders the raw markdown body directly. Use standard markdown formatting:

```markdown
---
type: custom
title: Additional Information
---

Available for relocation. Open to remote work.
```

---

### Volunteer / Service

Volunteer and service sections use the **same format as experience** entries:

```markdown
---
type: volunteer
---

# Volunteer Work

## Code Mentor — Girls Who Code
**2020 – present**

Weekly mentoring sessions teaching Python fundamentals to high school students.

## Trail Maintenance — Appalachian Trail Conservancy
**2018 – 2019**

Organised monthly trail maintenance days with 20+ volunteers.
```

**Recognised keys:** Same as experience — `company`, `organization`, `location`, `dates`, `date`

---

### Languages

**Fields:** `name` (from heading), `proficiency`

```markdown
---
type: languages
---

# Languages

## English
**Proficiency:** Native

## Spanish
**Proficiency:** Professional working proficiency

## Mandarin
**Proficiency:** Elementary
```

**Recognised keys:** `proficiency`, `level`

---

### Interests

Interests use the **same format as skills** — `### Category` sub-headings with comma-separated or bulleted lists:

```markdown
---
type: interests
---

# Interests

### Sports
Rock climbing, Trail running, Swimming

### Creative
Photography, Woodworking
```

---

### References

**Fields:** `name` (from heading), `title`, `organization`, `email`, `phone`, `relationship`

```markdown
---
type: references
---

# References

## Dr. Jane Smith
**Title:** Professor of Computer Science
**Organization:** MIT
**Email:** jsmith@mit.edu
**Phone:** (555) 123-4567
**Relationship:** Ph.D. Advisor

## John Doe
**Title:** Engineering Manager
**Organization:** Acme Corp
**Email:** jdoe@acme.com
**Relationship:** Former Manager
```

**Recognised keys:** `title`, `position`, `role`, `organization`, `company`, `institution`, `email`, `phone`, `relationship`, `relation`

---

## YAML Frontmatter Entries (Alternative)

Instead of writing markdown body content, you can define entries directly in YAML frontmatter. This is useful for programmatic generation:

```yaml
---
type: experience
entries:
  - role: Senior Software Engineer
    company: Acme Corp
    location: San Francisco, CA
    start: "2021-01"
    end: present
    highlights:
      - Led migration of monolith to microservices
      - Mentored 3 junior engineers
---
```

```yaml
---
type: skills
categories:
  - name: Languages
    skills: [Python, TypeScript, Go]
  - name: Frameworks
    skills: [FastAPI, React, Django]
---
```

If both YAML entries and markdown body content exist, the YAML entries take priority.

---

## Tips

- **Ordering:** Use the filename prefix (`01-`, `02-`) for default order, or set `order:` in frontmatter.
- **Hiding sections:** Set `visible: false` in frontmatter to exclude a section from all outputs.
- **Section titles:** The `# H1 Heading` in the body is used as the section title. Override with `title:` in frontmatter.
- **Markdown in bullets:** Bullet points support inline markdown — `**bold**`, `*italic*`, `[links](url)`, `` `code` `` — which renders correctly in LaTeX, DOCX, and HTML.
- **Multiple formats:** You can use key-value format for some sections and pipe-delimited for others within the same vault.
