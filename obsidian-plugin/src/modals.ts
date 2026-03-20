/**
 * UI Modals for the Auto CV plugin.
 */

import { App, Modal, Setting, Notice } from 'obsidian';
import { SectionInfo, ProjectData } from './utils';

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

export interface BuildOptions {
  formats: string[];
  outputPath: string;
  project?: string;
}

// ---------------------------------------------------------------------------
// Simple Build Modal (flat vaults)
// ---------------------------------------------------------------------------

export class BuildModal extends Modal {
  defaultFormats: string[];
  defaultOutputPath: string;
  onSubmit: (options: BuildOptions) => void;

  constructor(
    app: App,
    defaultFormats: string[],
    defaultOutputPath: string,
    onSubmit: (options: BuildOptions) => void
  ) {
    super(app);
    this.defaultFormats = defaultFormats;
    this.defaultOutputPath = defaultOutputPath;
    this.onSubmit = onSubmit;
  }

  onOpen() {
    const { contentEl } = this;
    let selectedFormats = [...this.defaultFormats];
    let selectedOutputPath = this.defaultOutputPath;

    contentEl.createEl('h2', { text: 'Build Resume/CV' });

    contentEl.createEl('h3', { text: 'Output Formats' });
    const formatsContainer = contentEl.createDiv({ cls: 'format-checkboxes' });
    for (const fmt of ['html', 'docx', 'latex']) {
      const label = formatsContainer.createEl('label', { cls: 'checkbox-label' });
      const input = label.createEl('input', { type: 'checkbox' }) as HTMLInputElement;
      input.checked = selectedFormats.includes(fmt);
      input.onchange = () => {
        if (input.checked && !selectedFormats.includes(fmt)) selectedFormats.push(fmt);
        else if (!input.checked) selectedFormats = selectedFormats.filter(f => f !== fmt);
      };
      label.createSpan({ text: fmt === 'latex' ? 'LaTeX/PDF' : fmt.toUpperCase() });
    }

    contentEl.createEl('h3', { text: 'Output Directory' });
    new Setting(contentEl)
      .setName('Path')
      .setDesc('Relative to vault root')
      .addText(t => t.setPlaceholder('output').setValue(selectedOutputPath)
        .onChange(v => { selectedOutputPath = v || 'output'; }));

    const buttonDiv = contentEl.createDiv({ cls: 'modal-button-container' });
    buttonDiv.createEl('button', { text: 'Cancel', cls: 'mod-default' }).onclick = () => this.close();
    buttonDiv.createEl('button', { text: 'Build', cls: 'mod-cta' }).onclick = () => {
      if (selectedFormats.length === 0) { new Notice('⚠️ Select at least one format', 5000); return; }
      this.onSubmit({ formats: selectedFormats, outputPath: selectedOutputPath });
      this.close();
    };
  }

  onClose() { this.contentEl.empty(); }
}

// ---------------------------------------------------------------------------
// Progress Modal
// ---------------------------------------------------------------------------

export class ProgressModal extends Modal {
  message: string;
  statusEl: HTMLElement | null = null;

  constructor(app: App, message: string) {
    super(app);
    this.message = message;
    this.modalEl.addClass('auto-cv-progress-modal');
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.createEl('h2', { text: '⏳ Building Resume/CV' });
    this.statusEl = contentEl.createEl('p', { text: this.message, cls: 'progress-message' });
    contentEl.createDiv({ cls: 'progress-spinner' });
  }

  updateMessage(message: string) {
    if (this.statusEl) this.statusEl.textContent = message;
  }

  onClose() { this.contentEl.empty(); }
}

// ---------------------------------------------------------------------------
// Wizard types
// ---------------------------------------------------------------------------

export interface WizardConfig {
  projects: string[];
  projectConfigs: Record<string, ProjectData>;
  sections: SectionInfo[];
  presets: Record<string, WizardPreset>;
  defaultFormats: string[];
  defaultOutputPath: string;
}

export interface WizardPreset {
  colors?: Record<string, string>;
  fonts?: Record<string, string>;
  spacing?: Record<string, string>;
  html?: {
    layout?: string;
  };
}

export interface WizardResult {
  projectName: string;
  isNewProject: boolean;
  include: string[];
  sectionOrder: string[];
  titleOverride: string;
  presetName: string;
  styleOverrides: {
    colors: Record<string, string>;
    fonts: Record<string, string>;
    spacing: Record<string, string>;
    htmlLayout: string;
  };
  formats: string[];
  outputPath: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PRESET_DESCRIPTIONS: Record<string, string> = {
  'academic':   'Dense, scholarly — for researchers & academics',
  'awesome-cv': 'Bold orange headers — inspired by Awesome-CV',
  'classic':    'Traditional serif — timeless & conservative',
  'creative':   'Vibrant card layout — for designers & creatives',
  'elegant':    'Refined serif — consulting & finance',
  'executive':  'Generous spacing — senior leadership',
  'minimal':    'Clean & understated — whitespace-focused',
  'modern':     'Contemporary sans-serif — clean sidebar layout',
  'technical':  'Monospace-friendly — ideal for DevOps / SWE',
};

const STEP_LABELS = ['Project', 'Sections', 'Style', 'Output'];

const COMMON_FONTS = [
  'Arial', 'Calibri', 'Cambria', 'Consolas', 'Courier New',
  'EB Garamond', 'Fira Code', 'Fira Sans', 'Garamond',
  'Georgia', 'Helvetica', 'IBM Plex Sans', 'IBM Plex Serif',
  'Inter', 'Lato', 'Libre Baskerville', 'Merriweather',
  'Montserrat', 'Noto Sans', 'Noto Serif', 'Open Sans',
  'Oswald', 'Palatino Linotype', 'Playfair Display', 'Poppins',
  'PT Sans', 'PT Serif', 'Raleway', 'Roboto', 'Roboto Slab',
  'Segoe UI', 'Source Code Pro', 'Source Sans Pro', 'Source Serif Pro',
  'Tahoma', 'Times New Roman', 'Trebuchet MS', 'Ubuntu',
  'Verdana', 'Work Sans',
];

/** Style each <option> and the <select> itself with its font-family. */
function applyFontPreview(selectEl: HTMLSelectElement): void {
  for (let i = 0; i < selectEl.options.length; i++) {
    selectEl.options[i].style.fontFamily = selectEl.options[i].value;
  }
  selectEl.style.fontFamily = selectEl.value;
}

const HTML_LAYOUTS = [
  { value: 'top-header', label: 'Top Header' },
  { value: 'sidebar',    label: 'Sidebar' },
  { value: 'cards',      label: 'Cards' },
  { value: 'latex-mirror', label: 'LaTeX Mirror' },
  { value: 'awesome-cv', label: 'Awesome-CV' },
];

// ---------------------------------------------------------------------------
// Build Wizard (master vaults)
// ---------------------------------------------------------------------------

export class BuildWizard extends Modal {
  private config: WizardConfig;
  private onResult: (result: WizardResult) => void;

  // Step tracking
  private step = 1;
  private totalSteps = STEP_LABELS.length;

  // Step 1: Project
  private projectMode: 'existing' | 'new' = 'new';
  private existingProject = '';
  private newProjectName = '';

  // Step 2: Sections
  private selectedSections: Set<string>;
  private sectionOrder: string[];

  // Step 3: Style
  private presetName = 'classic';
  private colorOverrides: Record<string, string> = {};
  private fontOverrides: Record<string, string> = {};
  private spacingOverrides: Record<string, string> = {};
  private htmlLayout = '';
  private titleOverride = '';

  // Step 4: Output
  private selectedFormats: string[];
  private outputPath: string;

  constructor(app: App, config: WizardConfig, onResult: (r: WizardResult) => void) {
    super(app);
    this.config = config;
    this.onResult = onResult;
    this.modalEl.addClass('auto-cv-wizard');

    // Defaults
    this.selectedSections = new Set(config.sections.map(s => s.filename));
    this.sectionOrder = config.sections.map(s => s.filename);
    this.selectedFormats = [...config.defaultFormats];
    this.outputPath = config.defaultOutputPath;

    if (config.projects.length > 0) {
      this.projectMode = 'existing';
      this.existingProject = config.projects[0];
      this.loadFromExistingProject(this.existingProject);
    }
  }

  onOpen() { this.renderStep(); }
  onClose() { this.contentEl.empty(); }

  // -------------------------------------------------------------------------
  // Project data loading
  // -------------------------------------------------------------------------

  private loadFromExistingProject(name: string) {
    const data = this.config.projectConfigs[name];
    if (!data) return;

    if (data.include.length > 0) {
      this.selectedSections = new Set(data.include);
      this.sectionOrder = data.include.filter(s =>
        this.config.sections.some(sec => sec.filename === s));
      // Append any unselected sections at end for ordering
      for (const sec of this.config.sections) {
        if (!this.sectionOrder.includes(sec.filename)) {
          this.sectionOrder.push(sec.filename);
        }
      }
    }
    if (data.section_order.length > 0) {
      // section_order uses type names; we keep it as-is for output
    }
    if (data.config.title) this.titleOverride = data.config.title;

    // Style
    if (data.style.preset) this.presetName = data.style.preset;
    if (Object.keys(data.style.colors).length > 0) this.colorOverrides = { ...data.style.colors };
    if (Object.keys(data.style.fonts).length > 0) this.fontOverrides = { ...data.style.fonts };
    if (Object.keys(data.style.spacing).length > 0) this.spacingOverrides = { ...data.style.spacing };
    if (data.style.htmlLayout) this.htmlLayout = data.style.htmlLayout;
  }

  // -------------------------------------------------------------------------
  // Render dispatcher
  // -------------------------------------------------------------------------

  private renderStep() {
    const { contentEl } = this;
    contentEl.empty();

    contentEl.createEl('h2', { text: 'Build Resume/CV' });
    this.renderStepIndicator(contentEl);

    const body = contentEl.createDiv({ cls: 'wizard-body' });
    switch (this.step) {
      case 1: this.renderProjectStep(body); break;
      case 2: this.renderSectionsStep(body); break;
      case 3: this.renderStyleStep(body); break;
      case 4: this.renderOutputStep(body); break;
    }

    this.renderNavigation(contentEl);
  }

  // -------------------------------------------------------------------------
  // Step indicator
  // -------------------------------------------------------------------------

  private renderStepIndicator(container: HTMLElement) {
    const bar = container.createDiv({ cls: 'wizard-step-bar' });
    for (let i = 0; i < this.totalSteps; i++) {
      const stepNum = i + 1;
      const dot = bar.createDiv({
        cls: `wizard-step-dot${stepNum === this.step ? ' active' : ''}${stepNum < this.step ? ' completed' : ''}`,
      });
      dot.createSpan({ cls: 'wizard-step-num', text: String(stepNum) });
      dot.createSpan({ cls: 'wizard-step-label', text: STEP_LABELS[i] });
    }
  }

  // -------------------------------------------------------------------------
  // Step 1: Project
  // -------------------------------------------------------------------------

  private renderProjectStep(container: HTMLElement) {
    container.createEl('h3', { text: 'Choose Project' });

    // Existing projects
    if (this.config.projects.length > 0) {
      const existingLabel = container.createEl('label', { cls: 'wizard-radio-label' });
      const existingRadio = existingLabel.createEl('input', { type: 'radio' }) as HTMLInputElement;
      existingRadio.name = 'project-mode';
      existingRadio.checked = this.projectMode === 'existing';
      existingLabel.createSpan({ text: ' Existing project' });

      const existingDropdownDiv = container.createDiv({ cls: 'wizard-indent' });
      const select = existingDropdownDiv.createEl('select', { cls: 'wizard-select' });
      for (const p of this.config.projects) {
        const opt = select.createEl('option', { text: p, value: p });
        if (p === this.existingProject) opt.selected = true;
      }
      select.onchange = () => {
        this.existingProject = select.value;
        this.loadFromExistingProject(select.value);
      };

      // New project radio
      const newLabel = container.createEl('label', { cls: 'wizard-radio-label' });
      const newRadio = newLabel.createEl('input', { type: 'radio' }) as HTMLInputElement;
      newRadio.name = 'project-mode';
      newRadio.checked = this.projectMode === 'new';
      newLabel.createSpan({ text: ' Create new project' });

      const newNameDiv = container.createDiv({ cls: 'wizard-indent' });
      const nameInput = newNameDiv.createEl('input', {
        type: 'text',
        cls: 'wizard-text-input',
        placeholder: 'project-name',
        value: this.newProjectName,
      }) as HTMLInputElement;
      nameInput.oninput = () => { this.newProjectName = nameInput.value.trim(); };

      // Toggle visibility
      const updateMode = () => {
        const isExisting = existingRadio.checked;
        this.projectMode = isExisting ? 'existing' : 'new';
        existingDropdownDiv.style.display = isExisting ? 'block' : 'none';
        newNameDiv.style.display = isExisting ? 'none' : 'block';
        if (isExisting && this.existingProject) {
          this.loadFromExistingProject(this.existingProject);
        } else {
          // Reset to all sections for new project
          this.selectedSections = new Set(this.config.sections.map(s => s.filename));
          this.sectionOrder = this.config.sections.map(s => s.filename);
          this.presetName = 'classic';
          this.colorOverrides = {};
          this.fontOverrides = {};
          this.spacingOverrides = {};
          this.htmlLayout = '';
          this.titleOverride = '';
        }
      };
      existingRadio.onchange = updateMode;
      newRadio.onchange = updateMode;
      updateMode();
    } else {
      // No existing projects — just show name input
      container.createEl('p', { text: 'Create your first project:', cls: 'wizard-hint' });
      const nameInput = container.createEl('input', {
        type: 'text',
        cls: 'wizard-text-input',
        placeholder: 'project-name',
        value: this.newProjectName,
      }) as HTMLInputElement;
      nameInput.oninput = () => { this.newProjectName = nameInput.value.trim(); };
      this.projectMode = 'new';
    }
  }

  // -------------------------------------------------------------------------
  // Step 2: Sections
  // -------------------------------------------------------------------------

  private renderSectionsStep(container: HTMLElement) {
    container.createEl('h3', { text: 'Select Sections to Include' });
    container.createEl('p', {
      text: 'Check the sections to include and drag to reorder.',
      cls: 'wizard-hint',
    });

    const listEl = container.createDiv({ cls: 'wizard-section-list' });

    // Render in sectionOrder, with all sections included
    const orderedSections = [...this.sectionOrder];
    // Add any sections not in the order yet
    for (const s of this.config.sections) {
      if (!orderedSections.includes(s.filename)) orderedSections.push(s.filename);
    }

    for (const filename of orderedSections) {
      const info = this.config.sections.find(s => s.filename === filename);
      if (!info) continue;

      const row = listEl.createDiv({ cls: 'wizard-section-row' });
      row.setAttribute('draggable', 'true');
      row.dataset.filename = filename;

      // Drag handle
      row.createSpan({ cls: 'wizard-drag-handle', text: '⠿' });

      const cb = row.createEl('input', { type: 'checkbox' }) as HTMLInputElement;
      cb.checked = this.selectedSections.has(filename);
      cb.onchange = () => {
        if (cb.checked) this.selectedSections.add(filename);
        else this.selectedSections.delete(filename);
      };

      row.createSpan({ cls: 'wizard-section-name', text: info.label });
      row.createSpan({ cls: 'wizard-section-file', text: filename });

      // Drag events for reordering
      row.ondragstart = (e) => {
        e.dataTransfer?.setData('text/plain', filename);
        row.addClass('dragging');
      };
      row.ondragend = () => row.removeClass('dragging');
      row.ondragover = (e) => { e.preventDefault(); row.addClass('drag-over'); };
      row.ondragleave = () => row.removeClass('drag-over');
      row.ondrop = (e) => {
        e.preventDefault();
        row.removeClass('drag-over');
        const draggedFilename = e.dataTransfer?.getData('text/plain');
        if (draggedFilename && draggedFilename !== filename) {
          this.reorderSection(draggedFilename, filename);
          this.renderStep();
        }
      };
    }
  }

  private reorderSection(from: string, before: string) {
    const arr = this.sectionOrder.filter(s => s !== from);
    const idx = arr.indexOf(before);
    if (idx >= 0) arr.splice(idx, 0, from);
    else arr.push(from);
    this.sectionOrder = arr;
  }

  // -------------------------------------------------------------------------
  // Step 3: Style
  // -------------------------------------------------------------------------

  private renderStyleStep(container: HTMLElement) {
    // Title override
    new Setting(container)
      .setName('Job Title')
      .setDesc('Override the title for this project')
      .addText(t => t.setPlaceholder('e.g. Senior Software Engineer')
        .setValue(this.titleOverride)
        .onChange(v => { this.titleOverride = v; }));

    // Preset selection
    container.createEl('h3', { text: 'Style Preset' });
    const presetGrid = container.createDiv({ cls: 'wizard-preset-grid' });
    const presetNames = Object.keys(this.config.presets);

    for (const name of presetNames) {
      const preset = this.config.presets[name];
      const card = presetGrid.createDiv({
        cls: `wizard-preset-card${name === this.presetName ? ' selected' : ''}`,
      });
      card.dataset.preset = name;

      // Color swatches
      const swatches = card.createDiv({ cls: 'wizard-preset-swatches' });
      const primary = preset?.colors?.primary || '#333';
      const accent = preset?.colors?.accent || '#333';
      swatches.createSpan({ cls: 'wizard-swatch' }).style.backgroundColor = primary;
      swatches.createSpan({ cls: 'wizard-swatch' }).style.backgroundColor = accent;

      // Name and description
      const textDiv = card.createDiv({ cls: 'wizard-preset-text' });
      textDiv.createEl('strong', { text: name });
      textDiv.createEl('small', { text: PRESET_DESCRIPTIONS[name] || '' });

      card.onclick = () => {
        this.presetName = name;
        // Reset overrides when preset changes
        this.colorOverrides = {};
        this.fontOverrides = {};
        this.spacingOverrides = {};
        this.htmlLayout = '';
        // Re-render to update selection + customization fields
        this.renderStep();
      };
    }

    // Customization section
    container.createEl('h3', { text: 'Customize' });
    const customDiv = container.createDiv({ cls: 'wizard-customize' });
    const preset = this.config.presets[this.presetName] || {};

    // Colors
    this.renderColorRow(customDiv, 'Primary', 'primary', preset?.colors?.primary || '#2C3E50');
    this.renderColorRow(customDiv, 'Accent', 'accent', preset?.colors?.accent || '#3498DB');

    // Fonts
    const headingFont = this.fontOverrides.heading || preset?.fonts?.heading || 'Helvetica';
    const bodyFont = this.fontOverrides.body || preset?.fonts?.body || 'Georgia';

    new Setting(customDiv)
      .setName('Heading Font')
      .addDropdown(d => {
        for (const f of COMMON_FONTS) d.addOption(f, f);
        d.setValue(headingFont);
        applyFontPreview(d.selectEl);
        d.onChange(v => { this.fontOverrides.heading = v; d.selectEl.style.fontFamily = v; });
      });

    new Setting(customDiv)
      .setName('Body Font')
      .addDropdown(d => {
        for (const f of COMMON_FONTS) d.addOption(f, f);
        d.setValue(bodyFont);
        applyFontPreview(d.selectEl);
        d.onChange(v => { this.fontOverrides.body = v; d.selectEl.style.fontFamily = v; });
      });

    // Spacing
    const margin = this.spacingOverrides.page_margin || preset?.spacing?.page_margin || '0.75in';
    const sectionGap = this.spacingOverrides.section_gap || preset?.spacing?.section_gap || '12pt';

    new Setting(customDiv)
      .setName('Page Margin')
      .addText(t => t.setValue(margin).setPlaceholder('0.75in')
        .onChange(v => { if (v) this.spacingOverrides.page_margin = v; }));

    new Setting(customDiv)
      .setName('Section Gap')
      .addText(t => t.setValue(sectionGap).setPlaceholder('12pt')
        .onChange(v => { if (v) this.spacingOverrides.section_gap = v; }));

    // HTML Layout
    const currentLayout = this.htmlLayout || preset?.html?.layout || 'top-header';
    new Setting(customDiv)
      .setName('HTML Layout')
      .addDropdown(d => {
        for (const l of HTML_LAYOUTS) d.addOption(l.value, l.label);
        d.setValue(currentLayout);
        d.onChange(v => { this.htmlLayout = v; });
      });
  }

  private renderColorRow(container: HTMLElement, label: string, key: string, defaultVal: string) {
    const currentVal = this.colorOverrides[key] || defaultVal;

    const row = container.createDiv({ cls: 'wizard-color-row' });
    row.createSpan({ text: label, cls: 'wizard-color-label' });

    const colorInput = row.createEl('input', { type: 'color' }) as HTMLInputElement;
    colorInput.value = currentVal;
    colorInput.className = 'wizard-color-picker';

    const textInput = row.createEl('input', {
      type: 'text',
      cls: 'wizard-color-text',
      value: currentVal,
    }) as HTMLInputElement;

    colorInput.oninput = () => {
      textInput.value = colorInput.value;
      this.colorOverrides[key] = colorInput.value;
    };
    textInput.oninput = () => {
      if (/^#[0-9a-fA-F]{6}$/.test(textInput.value)) {
        colorInput.value = textInput.value;
        this.colorOverrides[key] = textInput.value;
      }
    };
  }

  // -------------------------------------------------------------------------
  // Step 4: Output
  // -------------------------------------------------------------------------

  private renderOutputStep(container: HTMLElement) {
    container.createEl('h3', { text: 'Output Settings' });

    // Format checkboxes
    const formatsDiv = container.createDiv({ cls: 'format-checkboxes' });
    for (const fmt of ['html', 'docx', 'latex']) {
      const label = formatsDiv.createEl('label', { cls: 'checkbox-label' });
      const input = label.createEl('input', { type: 'checkbox' }) as HTMLInputElement;
      input.checked = this.selectedFormats.includes(fmt);
      input.onchange = () => {
        if (input.checked && !this.selectedFormats.includes(fmt)) this.selectedFormats.push(fmt);
        else if (!input.checked) this.selectedFormats = this.selectedFormats.filter(f => f !== fmt);
      };
      label.createSpan({ text: fmt === 'latex' ? 'LaTeX/PDF' : fmt.toUpperCase() });
    }

    // Output path
    new Setting(container)
      .setName('Output Directory')
      .setDesc('Relative to vault root (auto-resolves for projects)')
      .addText(t => t.setPlaceholder('output').setValue(this.outputPath)
        .onChange(v => { this.outputPath = v || 'output'; }));

    // Summary
    const summary = container.createDiv({ cls: 'wizard-summary' });
    summary.createEl('h4', { text: 'Summary' });
    const projectName = this.projectMode === 'existing' ? this.existingProject : this.newProjectName;
    const selectedCount = this.selectedSections.size;

    const dl = summary.createEl('dl', { cls: 'wizard-summary-list' });
    dl.createEl('dt', { text: 'Project' });
    dl.createEl('dd', { text: `${projectName}${this.projectMode === 'new' ? ' (new)' : ''}` });
    dl.createEl('dt', { text: 'Sections' });
    dl.createEl('dd', { text: `${selectedCount} selected` });
    dl.createEl('dt', { text: 'Style' });
    dl.createEl('dd', { text: this.presetName });
    if (this.titleOverride) {
      dl.createEl('dt', { text: 'Title' });
      dl.createEl('dd', { text: this.titleOverride });
    }
  }

  // -------------------------------------------------------------------------
  // Navigation
  // -------------------------------------------------------------------------

  private renderNavigation(container: HTMLElement) {
    const nav = container.createDiv({ cls: 'modal-button-container' });

    nav.createEl('button', { text: 'Cancel', cls: 'mod-default' }).onclick = () => this.close();

    if (this.step > 1) {
      nav.createEl('button', { text: '← Back', cls: 'mod-default' }).onclick = () => {
        this.step--;
        this.renderStep();
      };
    }

    if (this.step < this.totalSteps) {
      nav.createEl('button', { text: 'Next →', cls: 'mod-cta' }).onclick = () => {
        if (!this.validateStep()) return;
        this.step++;
        this.renderStep();
      };
    } else {
      nav.createEl('button', { text: '🔨 Build', cls: 'mod-cta' }).onclick = () => {
        if (!this.validateStep()) return;
        this.submit();
      };
    }

    // Quick-build shortcut for existing projects
    if (this.step === 1 && this.projectMode === 'existing' && this.existingProject) {
      nav.createEl('button', { text: '⚡ Quick Build', cls: 'mod-cta' }).onclick = () => {
        this.loadFromExistingProject(this.existingProject);
        this.submit();
      };
    }
  }

  private validateStep(): boolean {
    switch (this.step) {
      case 1: {
        if (this.projectMode === 'new') {
          if (!this.newProjectName) {
            new Notice('⚠️ Enter a project name', 5000);
            return false;
          }
          if (!/^[a-zA-Z0-9_-]+$/.test(this.newProjectName)) {
            new Notice('⚠️ Project name can only contain letters, numbers, hyphens and underscores', 5000);
            return false;
          }
          if (this.config.projects.includes(this.newProjectName)) {
            new Notice('⚠️ A project with that name already exists', 5000);
            return false;
          }
        }
        return true;
      }
      case 2:
        if (this.selectedSections.size === 0) {
          new Notice('⚠️ Select at least one section', 5000);
          return false;
        }
        return true;
      case 3:
        return true;
      case 4:
        if (this.selectedFormats.length === 0) {
          new Notice('⚠️ Select at least one output format', 5000);
          return false;
        }
        return true;
    }
    return true;
  }

  private submit() {
    const projectName = this.projectMode === 'existing'
      ? this.existingProject
      : this.newProjectName;

    // Build include list from sectionOrder, filtered to selected
    const include = this.sectionOrder.filter(s => this.selectedSections.has(s));

    // Derive section_order (type names) from the include list
    const sectionOrder = include.map(filename =>
      filename.replace(/^\d+-/, ''));

    // Build style overrides — only include changed values
    const preset = this.config.presets[this.presetName] || {};
    const colors: Record<string, string> = {};
    for (const [k, v] of Object.entries(this.colorOverrides)) {
      if (v !== preset?.colors?.[k]) colors[k] = v;
    }
    const fonts: Record<string, string> = {};
    for (const [k, v] of Object.entries(this.fontOverrides)) {
      if (v !== preset?.fonts?.[k]) fonts[k] = v;
    }
    const spacing: Record<string, string> = {};
    for (const [k, v] of Object.entries(this.spacingOverrides)) {
      if (v !== preset?.spacing?.[k]) spacing[k] = v;
    }
    const htmlLayout = (this.htmlLayout && this.htmlLayout !== preset?.html?.layout)
      ? this.htmlLayout : '';

    this.onResult({
      projectName,
      isNewProject: this.projectMode === 'new',
      include,
      sectionOrder,
      titleOverride: this.titleOverride,
      presetName: this.presetName,
      styleOverrides: { colors, fonts, spacing, htmlLayout },
      formats: this.selectedFormats,
      outputPath: this.outputPath,
    });
    this.close();
  }
}
