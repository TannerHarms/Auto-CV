# Auto CV — Example Gallery

Eight complete example vaults showcasing different presets, layouts, and content types.
Each example is an artificial résumé/CV for a member of the **Fellowship of the Ring** — written as if they were applying for their role on the quest.
Every example is a self-contained vault you can build with `auto-cv build`.

---

## Available Presets (9 total)

| Preset | Style | Layout | Best For |
| --- | --- | --- | --- |
| `classic` | Serif, conservative slate/gray | top-header | Traditional industries |
| `modern` | Sans-serif, dark blue accents | sidebar | Tech & professional roles |
| `minimal` | Maximum whitespace, black/gray | top-header | Clean, understated profiles |
| `awesome-cv` | XeLaTeX class, bold headings | top-header | Academic CVs, research |
| `executive` | Navy + gold, serif Palatino | top-header | Senior leadership, C-suite |
| `creative` | Coral + teal, vibrant cards | cards | Design, marketing, creative |
| `academic` | Dense Times New Roman, dark red links | top-header | Professors, researchers |
| `technical` | Dark slate, green terminal accents | sidebar | Engineers, DevOps, SREs |
| `elegant` | Burgundy + warm cream, Palatino | top-header | Consulting, finance, law |

---

## Examples

### 1. Software Engineer — `modern` preset, sidebar layout

![Software Engineer Preview](previews/software-engineer.png)

**Profile:** Gimli son of Glóin, Senior Structural & Mining Engineer (Erebor)
**Preset:** `modern` with blue/cyan customisation
**Layout:** Sidebar with photo
**Sections:** Summary, Experience, Skills, Projects, Education, Certifications
**Build:**

```bash
auto-cv build examples/software-engineer -f html -f latex -f docx
```

---

### 2. Executive — `executive` preset, top-header layout

![Executive Preview](previews/executive.png)

**Profile:** Aragorn II Elessar, Chieftain of the Dúnedain & Heir of Isildur (Rivendell)
**Preset:** `executive` with gold border accents
**Layout:** Top-header, no photo — formal and authoritative
**Sections:** Summary, Experience, Education, Skills, Awards
**Build:**

```bash
auto-cv build examples/executive -f html -f latex -f docx
```

---

### 3. Creative Designer — `creative` preset, cards layout

![Creative Designer Preview](previews/creative-designer.png)

**Profile:** Legolas Greenleaf, Master Bowyer & Elven Artisan (Mirkwood)
**Preset:** `creative` with coral/teal/purple palette
**Layout:** Cards grid with photo — portfolio-style
**Sections:** Summary, Experience, Featured Work, Skills, Education, Certifications
**Build:**

```bash
auto-cv build examples/creative-designer -f html -f latex -f docx
```

---

### 4. Academic Researcher — `awesome-cv` preset

![Academic Researcher Preview](previews/academic-researcher.png)

**Profile:** Gandalf the Grey, Istari Scholar & Loremaster (The Shire / Middle-earth)
**Preset:** `awesome-cv` with emerald green accent
**Layout:** Top-header (awesome-cv XeLaTeX class for PDF)
**Sections:** Research Interests, Experience, Education, Publications, Skills, Awards, Projects, Certifications, Service, Languages
**Note:** PDF output requires XeLaTeX with Roboto & Source Sans Pro fonts
**Build:**

```bash
auto-cv build examples/academic-researcher -f html -f latex -f docx
```

---

### 5. New Graduate — `elegant` preset

![New Graduate Preview](previews/new-graduate.png)

**Profile:** Frodo Baggins, Aspiring Adventurer — Recent Graduate (Hobbiton, The Shire)
**Preset:** `elegant` with plum/purple customisation
**Layout:** Top-header, no photo — clean and polished
**Sections:** Summary, Education, Projects, Experience, Skills, Certifications
**Build:**

```bash
auto-cv build examples/new-graduate -f html -f latex -f docx
```

---

### 6. Data Scientist — `technical` preset, sidebar layout

![Data Scientist Preview](previews/data-scientist.png)

**Profile:** Samwise Gamgee, Agricultural Data Analyst & Provisions Specialist (Hobbiton, The Shire)
**Preset:** `technical` with blue-green palette
**Layout:** Sidebar with photo
**Sections:** Summary, Experience, Skills, Projects, Education, Publications, Certifications
**Build:**

```bash
auto-cv build examples/data-scientist -f html -f latex -f docx
```

---

### 7. Project Manager — `classic` preset, top-header layout

![Project Manager Preview](previews/project-manager.png)

**Profile:** Meriadoc "Merry" Brandybuck, Tactical Operations Coordinator & Esquire of Rohan (Buckland, The Shire)
**Preset:** `classic` with slate/blue tones
**Layout:** Top-header, no photo — traditional and authoritative
**Sections:** Summary, Experience, Education, Skills, Projects, Certifications
**Build:**

```bash
auto-cv build examples/project-manager -f html -f latex -f docx
```

---

### 8. Consultant — `minimal` preset, top-header layout

![Consultant Preview](previews/consultant.png)

**Profile:** Peregrin "Pippin" Took, Diplomatic Liaison & Guard of the Citadel (Tuckborough, The Shire)
**Preset:** `minimal` with clean black/gray palette
**Layout:** Top-header, no photo — understated and modern
**Sections:** Summary, Experience, Education, Skills, Projects, Certifications
**Build:**

```bash
auto-cv build examples/consultant -f html -f latex -f docx
```

---

## Customising Styles

Every `_style.yml` shows how to override preset defaults:

```yaml
# Select a base preset
preset: modern

# Override specific colours
colors:
  primary: "#1565C0"
  accent: "#00BCD4"

# Change fonts
fonts:
  heading: Helvetica
  body: "Segoe UI"

# Pick a layout
html:
  layout: sidebar
  include_photo: true
```

See `auto-cv style-schema` for the full list of configurable options.

## Building All Examples

```bash
# Build all examples at once
for dir in examples/*/; do
  auto-cv build "$dir" -f html -f latex -f docx -o "$dir/output"
done
```

## Regenerating Preview Images

```bash
python examples/generate_previews.py
```

Requires `playwright` (`pip install playwright && playwright install chromium`).
