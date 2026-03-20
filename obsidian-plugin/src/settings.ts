/**
 * Plugin settings and settings tab.
 */

import { App, Plugin, PluginSettingTab, Setting } from 'obsidian';
import { detectPythonExecutable } from './utils';
import { applyDetectedPythonPath, toggleFormatSelection } from './settings-helpers';

interface AutoResumePluginLike extends Plugin {
  settings: AutoResumeSettings;
  saveSettings(): Promise<void>;
}

export interface AutoResumeSettings {
  pythonExecutable: string;
  defaultOutputFolder: string;
  defaultFormats: string[];
}

export const DEFAULT_SETTINGS: AutoResumeSettings = {
  pythonExecutable: '',
  defaultOutputFolder: 'output',
  defaultFormats: ['html', 'docx'],
};

export class AutoResumeSettingTab extends PluginSettingTab {
  plugin: AutoResumePluginLike;

  constructor(app: App, plugin: AutoResumePluginLike) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;

    containerEl.empty();

    containerEl.createEl('h2', { text: 'Auto CV Settings' });

    // Python executable path
    const pythonSetting = new Setting(containerEl)
      .setName('Python Executable')
      .setDesc('Path to the Python executable (leave blank to auto-detect)')
      .addText((text) =>
        text
          .setPlaceholder('python3')
          .setValue(this.plugin.settings.pythonExecutable)
          .onChange(async (value) => {
            this.plugin.settings.pythonExecutable = value;
            await this.plugin.saveSettings();
          })
      );

    pythonSetting.addButton((button) =>
      button
        .setButtonText('Auto-Detect')
        .onClick(async () => {
          try {
            const adapterWithBasePath = this.app.vault.adapter as unknown as { basePath?: string };
            const vaultRoot = adapterWithBasePath.basePath || process.cwd();
            const pythonPath = await detectPythonExecutable(undefined, [
              `${vaultRoot}\\.venv\\Scripts\\python.exe`,
              `${vaultRoot}\\..\\.venv\\Scripts\\python.exe`,
              `${vaultRoot}/.venv/bin/python`,
              `${vaultRoot}/../.venv/bin/python`,
            ]);
            this.plugin.settings.pythonExecutable = pythonPath;
            await this.plugin.saveSettings();
            applyDetectedPythonPath(containerEl, pythonPath);
          } catch (e) {
            alert(`Failed to detect Python: ${(e as Error).message}`);
          }
        })
    );

    // Default output folder
    new Setting(containerEl)
      .setName('Default Output Folder')
      .setDesc('Default folder for resume output (relative to vault root)')
      .addText((text) =>
        text
          .setPlaceholder('output')
          .setValue(this.plugin.settings.defaultOutputFolder)
          .onChange(async (value) => {
            this.plugin.settings.defaultOutputFolder = value || 'output';
            await this.plugin.saveSettings();
          })
      );

    // Default formats
    containerEl.createEl('h3', { text: 'Default Output Formats' });
    const formatsDesc = containerEl.createEl('p');
    formatsDesc.setText('Select which formats to generate by default');

    const formats = ['html', 'docx', 'latex'];
    for (const fmt of formats) {
      const label = fmt === 'latex' ? 'LaTeX/PDF' : fmt.toUpperCase();
      new Setting(containerEl)
        .setName(label)
        .addToggle((toggle) =>
          toggle
            .setValue(this.plugin.settings.defaultFormats.includes(fmt))
            .onChange(async (value) => {
              this.plugin.settings.defaultFormats = toggleFormatSelection(
                this.plugin.settings.defaultFormats,
                fmt,
                value
              );
              await this.plugin.saveSettings();
            })
        );
    }
  }
}
