/**
 * UI Modals for the Auto CV plugin.
 */

import { App, Modal, Setting, DropdownComponent } from 'obsidian';

export interface BuildOptions {
  formats: string[];
  outputPath: string;
}

export class BuildModal extends Modal {
  result: BuildOptions | null = null;
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

    contentEl.createEl('h2', { text: 'Build Resume' });

    // Output formats
    contentEl.createEl('h3', { text: 'Output Formats' });
    const formatsDiv = contentEl.createDiv();

    const formats = ['html', 'docx', 'latex'];
    for (const fmt of formats) {
      const label = contentEl.createEl('label', { cls: 'checkbox-label' });
      const input = label.createEl('input', { type: 'checkbox' }) as HTMLInputElement;
      input.checked = selectedFormats.includes(fmt);
      input.onchange = () => {
        if (input.checked && !selectedFormats.includes(fmt)) {
          selectedFormats.push(fmt);
        } else if (!input.checked) {
          selectedFormats = selectedFormats.filter(f => f !== fmt);
        }
      };
      label.createSpan({ text: fmt.toUpperCase() });
    }

    // Output path
    contentEl.createEl('h3', { text: 'Output Directory' });
    new Setting(contentEl)
      .addText((text) =>
        text
          .setPlaceholder('output')
          .setValue(selectedOutputPath)
          .onChange((value) => {
            selectedOutputPath = value || 'output';
          })
      );

    // Buttons
    const buttonDiv = contentEl.createDiv({ cls: 'modal-button-container' });
    buttonDiv.createEl('button', { text: 'Cancel' }).onclick = () => this.close();
    buttonDiv.createEl('button', { text: 'Build', cls: 'mod-cta' }).onclick = () => {
      if (selectedFormats.length === 0) {
        alert('Please select at least one format');
        return;
      }
      this.onSubmit({
        formats: selectedFormats,
        outputPath: selectedOutputPath,
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

  constructor(app: App, message: string) {
    super(app);
    this.message = message;
  }

  onOpen() {
    const { contentEl } = this;
    contentEl.createEl('h2', { text: 'Building Resume' });
    contentEl.createEl('p', { text: this.message });
    contentEl.createEl('div', { cls: 'progress-spinner' });
  }

  onClose() {
    const { contentEl } = this;
    contentEl.empty();
  }
}
