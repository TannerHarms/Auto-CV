import { afterEach, describe, expect, it, vi } from 'vitest';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

import {
  detectPythonExecutable,
  listProjectSections,
  PythonNotFoundError,
  resolvePythonExecutable,
  saveProjectFiles,
  systemTools,
} from '../src/utils';

describe('utils', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('falls back to preferred candidates when configured path is invalid', async () => {
    const existsSpy = vi.spyOn(systemTools, 'existsSync').mockImplementation((candidate: string) => {
      return candidate === 'C:/valid/python.exe';
    });
    const execSpy = vi.spyOn(systemTools, 'execFileAsync').mockImplementation(async (candidate: string) => {
      if (candidate === 'C:/valid/python.exe') {
        return { stdout: 'Python 3.12.2', stderr: '' } as { stdout: string; stderr: string };
      }
      throw new Error('not executable');
    });

    const resolved = await resolvePythonExecutable('C:/broken/python.exe', ['C:/valid/python.exe']);

    expect(resolved).toBe('C:/valid/python.exe');
    expect(existsSpy).toHaveBeenCalled();
    expect(execSpy).toHaveBeenCalled();
  });

  it('raises when no python executable can be found', async () => {
    vi.spyOn(systemTools, 'existsSync').mockReturnValue(false);
    vi.spyOn(systemTools, 'execFileAsync').mockRejectedValue(new Error('missing'));
    vi.spyOn(systemTools, 'platform').mockReturnValue('win32');

    await expect(detectPythonExecutable(undefined, [])).rejects.toBeInstanceOf(PythonNotFoundError);
  });

  it('updates existing header frontmatter but preserves existing header body and _style.yml', () => {
    const vaultPath = mkdtempSync(join(tmpdir(), 'auto-cv-vault-'));
    const projectName = 'existing-project';
    const projectDir = join(vaultPath, 'projects', projectName);
    mkdirSync(projectDir, { recursive: true });

    const headerPath = join(projectDir, 'header.md');
    const stylePath = join(projectDir, '_style.yml');
    const originalHeader = '---\ninclude:\n  - summary\n---\n# Custom Header\n';
    const originalStyle = 'preset: "awesome-cv"\nspacing:\n  page_margin: "0.6in"\n';
    writeFileSync(headerPath, originalHeader, 'utf-8');
    writeFileSync(stylePath, originalStyle, 'utf-8');

    saveProjectFiles(vaultPath, projectName, {
      include: ['summary', 'experience'],
      sectionOrder: ['summary', 'experience'],
      titleOverride: 'Should Not Apply',
      preset: 'modern',
      presetConfig: {
        colors: { primary: '#0a84ff' },
      },
      styleOverrides: {
        colors: { primary: '#ff0000' },
      },
    });

    const updatedHeader = readFileSync(headerPath, 'utf-8');
    expect(updatedHeader).toContain('include:');
    expect(updatedHeader).toContain('- summary');
    expect(updatedHeader).toContain('- experience');
    expect(updatedHeader).toContain('section_order:');
    expect(updatedHeader).toContain('# Custom Header');
    expect(updatedHeader).not.toContain('Should Not Apply');
    expect(readFileSync(stylePath, 'utf-8')).toBe(originalStyle);
  });

  it('creates header.md and _style.yml when they do not exist', () => {
    const vaultPath = mkdtempSync(join(tmpdir(), 'auto-cv-vault-'));
    const projectName = 'new-project';

    saveProjectFiles(vaultPath, projectName, {
      include: ['summary', 'experience'],
      sectionOrder: ['summary', 'experience'],
      titleOverride: 'ML Engineer',
      preset: 'classic',
      presetConfig: {
        colors: { primary: '#111111' },
        fonts: { heading: 'Roboto' },
      },
      styleOverrides: {
        colors: { primary: '#222222' },
      },
    });

    const projectDir = join(vaultPath, 'projects', projectName);
    const headerPath = join(projectDir, 'header.md');
    const stylePath = join(projectDir, '_style.yml');

    const header = readFileSync(headerPath, 'utf-8');
    const style = readFileSync(stylePath, 'utf-8');

    expect(header).toContain('include:');
    expect(header).toContain('- summary');
    expect(style).toContain('preset: "classic"');
    expect(style).toMatch(/size_base:\s*"?.+"?/);
  });

  it('listProjectSections scans project sections directory', () => {
    const vaultPath = mkdtempSync(join(tmpdir(), 'auto-cv-vault-'));
    const project = 'test-proj';
    const sectionsDir = join(vaultPath, 'projects', project, 'sections');
    mkdirSync(sectionsDir, { recursive: true });
    writeFileSync(join(sectionsDir, '03-experience.md'), '# Exp', 'utf-8');
    writeFileSync(join(sectionsDir, '03-experience-a.md'), '# Exp A', 'utf-8');
    writeFileSync(join(sectionsDir, '03b-experience-ML-forward.md'), '# ML', 'utf-8');

    const sections = listProjectSections(vaultPath, project);
    const filenames = sections.map(s => s.filename);
    expect(filenames).toContain('03-experience');
    expect(filenames).toContain('03-experience-a');
    expect(filenames).toContain('03b-experience-ML-forward');

    // Label strips numeric prefix including variant suffixes
    const expA = sections.find(s => s.filename === '03-experience-a')!;
    expect(expA.label).toBe('Experience A');
    const mlFwd = sections.find(s => s.filename === '03b-experience-ML-forward')!;
    expect(mlFwd.label).toBe('Experience ML Forward');
  });
});