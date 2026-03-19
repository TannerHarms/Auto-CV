/**
 * Plugin settings and settings tab.
 */

import { App, PluginSettingTab, Setting } from 'obsidian';
import AutoResumePlugin from './main';
import { detectPythonExecutable } from './utils';

export interface AutoResumeSettings {
  pythonExecutable: string;
  defaultPreset: string;
  defaultOutputFolder: string;
  defaultFormats: string[];
}

export const DEFAULT_SETTINGS: AutoResumeSettings = {
  pythonExecutable: '',
  defaultPreset: 'default',
  defaultOutputFolder: 'output',
  defaultFormats: ['html', 'docx'],
};

export class AutoResumeSettingTab extends PluginSettingTab {
  plugin: AutoResumePlugin;

  constructor(app: App, plugin: AutoResumePlugin) {
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
            const pythonPath = await detectPythonExecutable();
            this.plugin.settings.pythonExecutable = pythonPath;
            await this.plugin.saveSettings();
            // Update the text input
            containerEl.querySelector('input[placeholder="python3"]')?.setAttr ?
              (containerEl.querySelector('input[placeholder="python3"]') as HTMLInputElement).value = pythonPath
              : null;
          } catch (e) {
            alert(`Failed to detect Python: ${(e as Error).message}`);
          }
        })
    );

    // Default preset
    new Setting(containerEl)
      .setName('Default Preset')
      .setDesc('Default resume styling preset')
      .addDropdown((dropdown) =>
        dropdown
          .addOption('default', 'Default')
          .addOption('awesome-cv', 'Awesome CV')
          .addOption('classic', 'Classic')
          .addOption('modern', 'Modern')
          .setValue(this.plugin.settings.defaultPreset)
          .onChange(async (value) => {
            this.plugin.settings.defaultPreset = value;
            await this.plugin.saveSettings();
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
      new Setting(containerEl).addToggle((toggle) =>
        toggle
          .setValue(this.plugin.settings.defaultFormats.includes(fmt))
          .onChange(async (value) => {
            if (value && !this.plugin.settings.defaultFormats.includes(fmt)) {
              this.plugin.settings.defaultFormats.push(fmt);
            } else if (!value) {
              this.plugin.settings.defaultFormats = this.plugin.settings.defaultFormats.filter(
                (f) => f !== fmt
              );
            }
            await this.plugin.saveSettings();
          })
      );
    }
  }
}

// Fix for toggle label
PluginSettingTab.prototype.addToggle = function (callback: any) {
  const setting = new Setting(this as any);
  return setting.addToggle(callback);
};

declare global {
  interface Setting {
    setName(name: string): this;
    setDesc(desc: string): this;
  }
}
