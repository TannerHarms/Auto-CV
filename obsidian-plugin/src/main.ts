/**
 * Main plugin entry point.
 */

import { Plugin, Notice } from 'obsidian';
import * as fs from 'fs';
import * as path from 'path';
import { AutoResumeSettingTab, AutoResumeSettings, DEFAULT_SETTINGS } from './settings';
import {
  BuildModal,
  BuildOptions,
  ProgressModal,
  BuildWizard,
  WizardResult,
  WizardConfig,
  WizardPreset,
} from './modals';
import {
  buildResume,
  checkAutoResumeInstalled,
  detectPythonExecutable,
  PythonNotFoundError,
  AutoResumeNotFoundError,
  resolvePythonExecutable,
  listProjects,
  isMasterVault,
  listMasterSections,
  fetchPresets,
  loadProjectData,
  ProjectData,
  saveProjectFiles,
} from './utils';

export default class AutoResumePlugin extends Plugin {
  settings!: AutoResumeSettings;
  isBuilding = false;

  private getPreferredPythonCandidates(): string[] {
    const adapterWithBasePath = this.app.vault.adapter as unknown as { basePath?: string };
    const vaultRoot = adapterWithBasePath.basePath || process.cwd();
    return [
      `${vaultRoot}\\.venv\\Scripts\\python.exe`,
      `${vaultRoot}\\..\\.venv\\Scripts\\python.exe`,
      `${vaultRoot}/.venv/bin/python`,
      `${vaultRoot}/../.venv/bin/python`,
    ];
  }

  async onload() {
    await this.loadSettings();

    // Only warn at startup if this is first install (no python path set)
    if (!this.settings.pythonExecutable) {
      try {
        const detectedPath = await detectPythonExecutable(
          undefined,
          this.getPreferredPythonCandidates()
        );
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
      name: 'Build resume/CV',
      callback: () => this.openBuildModal(),
    });

    // Add ribbon icon
    this.addRibbonIcon('file-text', 'Build resume/CV', () => this.openBuildModal());

  }

  onunload() {}

  async loadSettings() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }

  private async openBuildModal() {
    if (this.isBuilding) {
      new Notice('⏳ Build already in progress...');
      return;
    }

    if (!this.settings.pythonExecutable) {
      new Notice('❌ Python path not configured. Please set it in Auto CV settings.', 8000);
      return;
    }

    const adapterWithBasePath = this.app.vault.adapter as unknown as { basePath?: string };
    const vaultRoot = adapterWithBasePath.basePath || process.cwd();

    if (isMasterVault(vaultRoot)) {
      await this.openWizard(vaultRoot);
    } else {
      const modal = new BuildModal(
        this.app,
        this.settings.defaultFormats,
        this.settings.defaultOutputFolder,
        (options: BuildOptions) => this.executeBuild(options)
      );
      modal.open();
    }
  }

  private async openWizard(vaultRoot: string) {
    // Gather data for the wizard (projects, sections, presets)
    let projects: string[] = [];
    try {
      projects = await listProjects(this.settings.pythonExecutable, vaultRoot);
    } catch { /* fall through with empty list */ }

    const sections = listMasterSections(vaultRoot);
    let presets: Record<string, WizardPreset> = {};
    try {
      presets = await fetchPresets(this.settings.pythonExecutable);
    } catch { /* fall through with empty presets */ }

    // Load existing project configs
    const projectConfigs: Record<string, ProjectData> = {};
    for (const p of projects) {
      projectConfigs[p] = loadProjectData(vaultRoot, p);
    }

    const config: WizardConfig = {
      projects,
      projectConfigs,
      sections,
      presets,
      defaultFormats: this.settings.defaultFormats,
      defaultOutputPath: this.settings.defaultOutputFolder,
    };

    const wizard = new BuildWizard(
      this.app,
      config,
      (result: WizardResult) => this.handleWizardResult(vaultRoot, result)
    );
    wizard.open();
  }

  private async handleWizardResult(vaultRoot: string, result: WizardResult) {
    // Save project files
    saveProjectFiles(vaultRoot, result.projectName, {
      include: result.include,
      sectionOrder: result.sectionOrder,
      titleOverride: result.titleOverride,
      preset: result.presetName,
      styleOverrides: result.styleOverrides,
    });

    // Build
    await this.executeBuild({
      formats: result.formats,
      outputPath: result.outputPath,
      project: result.projectName,
    });
  }

  private async executeBuild(options: BuildOptions) {
    if (this.isBuilding) return;
    this.isBuilding = true;

    const adapterWithBasePath = this.app.vault.adapter as unknown as { basePath?: string };
    const vaultRoot = adapterWithBasePath.basePath || process.cwd();

    const progressModal = new ProgressModal(this.app, 'Initializing build...');
    progressModal.open();

    try {
      const pythonExe = await resolvePythonExecutable(
        this.settings.pythonExecutable,
        this.getPreferredPythonCandidates()
      );

      // Persist resolved path so future runs use the same interpreter.
      if (pythonExe !== this.settings.pythonExecutable) {
        this.settings.pythonExecutable = pythonExe;
        await this.saveSettings();
      }

      progressModal.updateMessage('Verifying auto-cv is installed...');
      await checkAutoResumeInstalled(pythonExe);

      progressModal.updateMessage(`Building resume to ${options.outputPath}...`);

      // Resolve output path relative to vault root
      let absoluteOutputPath = path.isAbsolute(options.outputPath)
        ? options.outputPath
        : path.join(vaultRoot, options.outputPath);

      // When building a project, default output into projects/<name>/output/
      if (options.project && !path.isAbsolute(options.outputPath) && options.outputPath === this.settings.defaultOutputFolder) {
        absoluteOutputPath = path.join(vaultRoot, 'projects', options.project, 'output');
      }

      await buildResume(
        pythonExe,
        vaultRoot,
        absoluteOutputPath,
        options.formats,
        options.project
      );

      progressModal.close();
      new Notice(`✅ Resume built successfully to ${options.outputPath}`, 8000);
      console.log('Build successful:', options.outputPath);
    } catch (error) {
      progressModal.close();

      const message = error instanceof Error ? error.message : String(error);
      let userMessage = '❌ Build failed: ' + message;

      if (error instanceof PythonNotFoundError) {
        userMessage = '❌ Python not found: ' + message;
      } else if (error instanceof AutoResumeNotFoundError) {
        userMessage = '❌ Auto CV not installed: ' + message;
      }

      new Notice(userMessage, 10000);
      console.error('Auto CV Build failed:', message);
      console.error('Auto CV Full error:', error);

      // Write error to log file in vault root so user can read it
      try {
        const logPath = path.join(vaultRoot, 'auto-cv-error.log');
        const timestamp = new Date().toISOString();
        const stack = error instanceof Error ? error.stack || '' : '';
        fs.writeFileSync(logPath, `[${timestamp}]\n${message}\n\nStack:\n${stack}\n`, 'utf-8');
        new Notice(`Error details written to auto-cv-error.log in vault root`, 8000);
      } catch { /* ignore logging failure */ }
    } finally {
      this.isBuilding = false;
    }
  }
}
