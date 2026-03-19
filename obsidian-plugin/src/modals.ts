/**
 * UI Modals for the Auto CV plugin.
 */

import { App, Modal, Setting, Notice } from 'obsidian';

export interface BuildOptions {
  formats: string[];
  outputPath: string;
  preset: string;
}

export class BuildModal extends Modal {
  result: BuildOptions | null = null;
  defaultFormats: string[];
  defaultOutputPath: string;
  defaultPreset: string;
  onSubmit: (options: BuildOptions) => void;

  constructor(
    app: App,
    defaultFormats: string[],
    defaultOutputPath: string,
    defaultPreset: string,
    onSubmit: (options: BuildOptions) => void
  ) {
    super(app);
    this.defaultFormats = defaultFormats;
    this.defaultOutputPath = defaultOutputPath;
    this.defaultPreset = defaultPreset;
    this.onSubmit = onSubmit;
  }

  onOpen() {
    const { contentEl } = this;
    let selectedFormats = [...this.defaultFormats];
    let selectedOutputPath = this.defaultOutputPath;
    let selectedPreset = this.defaultPreset;

    contentEl.createEl('h2', { text: 'Build Resume/CV' });

    // Output formats
    contentEl.createEl('h3', { text: 'Output Formats' });
    const formatsContainer = contentEl.createDiv({ cls: 'format-checkboxes' });

    const formats = ['html', 'docx', 'latex'];
    for (const fmt of formats) {
      const label = formatsContainer.createEl('label', { cls: 'checkbox-label' });
      const input = label.createEl('input', { type: 'checkbox' }) as HTMLInputElement;
      input.checked = selectedFormats.includes(fmt);
      input.dataset.format = fmt;
      input.onchange = () => {
        if (input.checked && !selectedFormats.includes(fmt)) {
          selectedFormats.push(fmt);
        } else if (!input.checked) {
          selectedFormats = selectedFormats.filter(f => f !== fmt);
        }
      };
      const labelText = fmt === 'latex' ? 'LaTeX/PDF' : fmt.toUpperCase();
      label.createSpan({ text: labelText });
    }

    if (selectedFormats.length === 0) {
      formatsContainer.createEl('p', {
        text: '⚠️ Select at least one format',
        cls: 'warning-text',
      });
    }

    // Preset selector
    contentEl.createEl('h3', { text: 'Resume Style' });
    new Setting(contentEl)
      .setName('Preset')
      .setDesc('Choose a resume template style')
      .addDropdown((dropdown) =>
        dropdown
          .addOption('default', 'Default')
          .addOption('awesome-cv', 'Awesome CV')
          .addOption('classic', 'Classic')
          .setValue(selectedPreset)
          .onChange((value) => {
            selectedPreset = value;
          })
      );

    // Output path
    contentEl.createEl('h3', { text: 'Output Directory' });
    new Setting(contentEl)
      .setName('Path')
      .setDesc('Relative to vault root')
      .addText((text) =>
        text
          .setPlaceholder('output')
          .setValue(selectedOutputPath)
          .onChange((value) => {
            selectedOutputPath = value || 'output';
          })
      );

    // Info text
    const infoDiv = contentEl.createDiv({ cls: 'modal-info' });
    infoDiv.createEl('p', {
      text: '💡 Tip: Configure your vault with _config.yml and sections/ folder. Check the documentation for details.',
      cls: 'info-text',
    });

    // Buttons
    const buttonDiv = contentEl.createDiv({ cls: 'modal-button-container' });
    buttonDiv.createEl('button', { text: 'Cancel', cls: 'mod-default' }).onclick = () => this.close();

    const buildBtn = buttonDiv.createEl('button', { text: 'Build', cls: 'mod-cta' });
    buildBtn.onclick = () => {
      if (selectedFormats.length === 0) {
        new Notice('⚠️ Please select at least one output format', 5000);
        return;
      }
      this.onSubmit({
        formats: selectedFormats,
        outputPath: selectedOutputPath,
        preset: selectedPreset,
      });
      this.close();
    };
  }

  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
}

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
    if (this.statusEl) {
      this.statusEl.textContent = message;
    }
  }

  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
}
