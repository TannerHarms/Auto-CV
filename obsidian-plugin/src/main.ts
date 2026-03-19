/**
 * Main plugin entry point.
 */

import { Plugin, Notice } from 'obsidian';
import { AutoResumeSettingTab, AutoResumeSettings, DEFAULT_SETTINGS } from './settings';
import { BuildModal, BuildOptions, ProgressModal } from './modals';
import { buildResume, checkAutoResumeInstalled, detectPythonExecutable, PythonNotFoundError, AutoCvNotFoundError, BuildError } from './utils';

export default class AutoResumePlugin extends Plugin {
  settings: AutoResumeSettings;
  isBuilding = false;

  async onload() {
    await this.loadSettings();

    // Only warn at startup if this is first install (no python path set)
    if (!this.settings.pythonExecutable) {
      try {
        const detectedPath = await detectPythonExecutable();
        this.settings.pythonExecutable = detectedPath;
        await this.saveSettings();
        new Notice('✅ Python detected: ' + detectedPath);
      } catch (e) {
        new Notice('⚠️ Auto CV: Configure Python path in settings (Settings → Auto CV)', 10000);
      }
    } else {
      // Verify existing path still works
      try {
        await checkAutoResumeInstalled(this.settings.pythonExecutable);
      } catch (e) {
        const error = e as Error;
        console.warn('Auto CV check failed:', error.message);
        if (error.message.includes('auto-cv not installed')) {
          new Notice(
            '⚠️ Auto CV package not found. Install with: pip install auto-cv',
            8000
          );
        }
      }
    }

    // Register settings tab
    this.addSettingTab(new AutoResumeSettingTab(this.app, this));

    // Register "Build Resume" command
    this.addCommand({
      id: 'build-resume',
      name: 'Build Resume/CV',
      callback: () => this.openBuildModal(),
    });

    // Add ribbon icon
    this.addRibbonIcon('file-text', 'Build Resume/CV', () => this.openBuildModal());

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
    if (this.isBuilding) {
      new Notice('⏳ Build already in progress...');
      return;
    }

    if (!this.settings.pythonExecutable) {
      new Notice('❌ Python path not configured. Please set it in Auto CV settings.', 8000);
      return;
    }

    const modal = new BuildModal(
      this.app,
      this.settings.defaultFormats,
      this.settings.defaultOutputFolder,
      this.settings.defaultPreset,
      (options: BuildOptions) => this.executeBuild(options)
    );
    modal.open();
  }

  private async executeBuild(options: BuildOptions) {
    if (this.isBuilding) return;
    this.isBuilding = true;

    const progressModal = new ProgressModal(this.app, 'Initializing build...');
    progressModal.open();

    try {
      const vaultRoot = this.app.vault.adapter.basePath || process.cwd();

      progressModal.updateMessage('Verifying auto-cv is installed...');
      await checkAutoResumeInstalled(this.settings.pythonExecutable);

      progressModal.updateMessage(`Building resume to ${options.outputPath}...`);

      const result = await buildResume(
        this.settings.pythonExecutable,
        vaultRoot,
        options.outputPath,
        options.formats,
        options.preset
      );

      progressModal.close();
      new Notice(`✅ ${result.message}`, 8000);
      console.log('Build successful:', result.message);
    } catch (error) {
      progressModal.close();

      const message = error instanceof Error ? error.message : String(error);
      let userMessage = '❌ Build failed';

      if (error instanceof PythonNotFoundError) {
        userMessage = '❌ Python not found: ' + message;
      } else if (error instanceof AutoCvNotFoundError) {
        userMessage = '❌ Auto CV not installed: ' + message;
      } else if (error instanceof BuildError) {
        userMessage = '❌ ' + message;
      }

      new Notice(userMessage, 10000);
      console.error('Build failed:', message);
    } finally {
      this.isBuilding = false;
    }
  }
}
