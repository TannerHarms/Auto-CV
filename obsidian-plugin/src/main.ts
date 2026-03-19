/**
 * Main plugin entry point.
 */

import { Plugin, Notice } from 'obsidian';
import { AutoResumeSettingTab, AutoResumeSettings, DEFAULT_SETTINGS } from './settings';
import { BuildModal, BuildOptions } from './modals';
import { buildResume, checkAutoResumeInstalled } from './utils';

export default class AutoResumePlugin extends Plugin {
  settings: AutoResumeSettings;

  async onload() {
    await this.loadSettings();

    // Check if auto-cv is installed
    try {
      await checkAutoResumeInstalled(this.settings.pythonExecutable);
    } catch (e) {
      console.warn('Auto CV not found:', (e as Error).message);
      new Notice(
        'Auto CV not installed. Install with: pip install auto-cv\nConfigure Python path in settings.'
      );
    }

    // Register settings tab
    this.addSettingTab(new AutoResumeSettingTab(this.app, this));

    // Register "Build Resume" command
    this.addCommand({
      id: 'build-resume',
      name: 'Build Resume',
      callback: () => this.openBuildModal(),
    });

    // Add ribbon icon
    this.addRibbonIcon('document', 'Build Resume', () => this.openBuildModal());

    console.log('Auto CV plugin loaded');
  }

  onunload() {
    console.log('Auto CV plugin unloaded');
  }

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }

  private openBuildModal() {
    const modal = new BuildModal(
      this.app,
      this.settings.defaultFormats,
      this.settings.defaultOutputFolder,
      (options: BuildOptions) => this.executeBuild(options)
    );
    modal.open();
  }

  private async executeBuild(options: BuildOptions) {
    try {
      // Get vault root directory
      const vaultRoot = this.app.vault.adapter.basePath || process.cwd();

      // Execute build via Python CLI
      new Notice(`Building resume to ${options.outputPath}...`);

      await buildResume(
        this.settings.pythonExecutable,
        vaultRoot,
        options.outputPath,
        options.formats,
        this.settings.defaultPreset
      );

      new Notice(`Resume built successfully to ${options.outputPath}`);
    } catch (error) {
      const message = (error as Error).message;
      console.error('Build failed:', message);
      new Notice(`Build failed: ${message}`, 10000);
    }
  }
}
