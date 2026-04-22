/**
 * Utility functions for Python detection and subprocess execution.
 */

import { execFile } from 'child_process';
import { promisify } from 'util';
import { existsSync, readdirSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { platform } from 'os';
import { join } from 'path';

const execFileAsync = promisify(execFile);

export const systemTools = {
  execFileAsync,
  existsSync,
  platform,
};

export class PythonNotFoundError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'PythonNotFoundError';
  }
}

export class AutoResumeNotFoundError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AutoResumeNotFoundError';
  }
}

function validatePythonExecutable(candidate: string): Promise<boolean> {
  return systemTools.execFileAsync(candidate, ['--version'])
    .then(({ stdout, stderr }) => {
      const output = `${stdout || ''}${stderr || ''}`;
      return output.includes('Python');
    })
    .catch(() => false);
}

/**
 * Try to detect Python executable on the system.
 */
export async function detectPythonExecutable(
  pythonPath?: string,
  preferredCandidates: string[] = []
): Promise<string> {
  if (pythonPath && systemTools.existsSync(pythonPath)) {
    if (await validatePythonExecutable(pythonPath)) {
      return pythonPath;
    }
  }

  const isWindows = systemTools.platform() === 'win32';
  const pythonCandidates = isWindows
    ? ['python', 'python3', 'py']
    : ['python3', 'python'];

  const orderedCandidates = [
    ...preferredCandidates.filter((p) => !!p),
    ...pythonCandidates,
  ];

  for (const candidate of orderedCandidates) {
    try {
      if (systemTools.existsSync(candidate) || ['python', 'python3', 'py'].includes(candidate)) {
        const ok = await validatePythonExecutable(candidate);
        if (ok) {
          return candidate;
        }
      }
    } catch {
      // Continue to next candidate
    }
  }

  throw new PythonNotFoundError(
    'Python executable not found. Please ensure Python 3.9+ is installed and in your PATH.'
  );
}

/**
 * Resolve interpreter to use for plugin operations.
 */
export async function resolvePythonExecutable(
  configuredPath: string,
  preferredCandidates: string[] = []
): Promise<string> {
  const normalizedPath = configuredPath?.trim();
  if (normalizedPath) {
    if (systemTools.existsSync(normalizedPath) && await validatePythonExecutable(normalizedPath)) {
      return normalizedPath;
    }
  }
  return detectPythonExecutable(undefined, preferredCandidates);
}

/**
 * Check if auto-cv is installed in the Python environment.
 */
export async function checkAutoResumeInstalled(pythonExe: string): Promise<void> {
  try {
    const { stdout } = await systemTools.execFileAsync(pythonExe, ['-m', 'pip', 'show', 'auto-cv']);
    if (!stdout.includes('Name: auto-cv')) {
      throw new AutoResumeNotFoundError(
        `auto-cv not installed for interpreter: ${pythonExe}. Install with: "${pythonExe}" -m pip install auto-cv`
      );
    }
  } catch (err) {
    if (err instanceof AutoResumeNotFoundError) {
      throw err;
    }
    throw new AutoResumeNotFoundError(
      `auto-cv not installed for interpreter: ${pythonExe}. Install with: "${pythonExe}" -m pip install auto-cv`
    );
  }
}

/**
 * Get the installed auto-cv version.
 */
export async function getAutoResumeVersion(pythonExe: string): Promise<string> {
  try {
    const { stdout } = await systemTools.execFileAsync(pythonExe, ['-m', 'auto_cv', '--version']);
    return stdout.trim();
  } catch {
    return 'unknown';
  }
}

/**
 * Run auto-cv build command.
 */
export async function buildResume(
  pythonExe: string,
  vaultPath: string,
  outputPath: string,
  formats: string[],
  project?: string
): Promise<void> {
  const args = ['-m', 'auto_cv', 'build', vaultPath];

  args.push('-o', outputPath);

  if (project) {
    args.push('-p', project);
  }

  for (const fmt of formats) {
    args.push('-f', fmt);
  }

  try {
    await systemTools.execFileAsync(pythonExe, args, {
      cwd: vaultPath,
      maxBuffer: 10 * 1024 * 1024,
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
        NO_COLOR: '1',
      },
    });
  } catch (error: unknown) {
    const stderr =
      typeof error === 'object' && error !== null && 'stderr' in error
        ? String((error as { stderr?: unknown }).stderr || '')
        : '';
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Build failed: ${stderr || message}`);
  }
}

/**
 * List available projects in a master vault.
 */
export async function listProjects(
  pythonExe: string,
  vaultPath: string
): Promise<string[]> {
  try {
    const { stdout } = await systemTools.execFileAsync(pythonExe, [
      '-m', 'auto_cv', 'list-projects', vaultPath,
    ], {
      cwd: vaultPath,
      env: {
        ...process.env,
        PYTHONIOENCODING: 'utf-8',
        NO_COLOR: '1',
      },
    });

    const names: string[] = [];
    for (const line of stdout.split('\n')) {
      const trimmed = line.trim();
      if (trimmed.startsWith('│') || trimmed.startsWith('|')) {
        const cells = trimmed.split(/[│|]/).map(c => c.trim()).filter(Boolean);
        if (cells.length >= 1 && cells[0] !== 'Project' && cells[0] !== 'Path') {
          names.push(cells[0]);
        }
      }
    }
    return names;
  } catch {
    return [];
  }
}

/**
 * Check if a vault uses the master/projects layout.
 */
export function isMasterVault(vaultPath: string): boolean {
  return systemTools.existsSync(join(vaultPath, '_master'));
}

// ---------------------------------------------------------------------------
// Wizard helpers
// ---------------------------------------------------------------------------

export interface SectionInfo {
  filename: string;
  label: string;
}

export interface PresetData {
  preset?: string;
  colors?: Record<string, string>;
  fonts?: Record<string, string>;
  spacing?: Record<string, string>;
  html?: {
    layout?: string;
  };
  [key: string]: unknown;
}

export interface ProjectData {
  include: string[];
  section_order: string[];
  config: Record<string, string>;
  style: {
    preset: string;
    colors: Record<string, string>;
    fonts: Record<string, string>;
    spacing: Record<string, string>;
    htmlLayout: string;
  };
  /** All section files found in this project's sections/ directory. */
  projectSections: SectionInfo[];
}

/**
 * List section files in _master/sections/.
 */
export function listMasterSections(vaultPath: string): SectionInfo[] {
  const sectionsDir = join(vaultPath, '_master', 'sections');
  if (!existsSync(sectionsDir)) return [];

  return readdirSync(sectionsDir)
    .filter(f => f.endsWith('.md'))
    .sort()
    .map(f => {
      const filename = f.replace(/\.md$/, '');
      const label = filename
        .replace(/^\d+[a-zA-Z]?-/, '')
        .replace(/-/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
      return { filename, label };
    });
}

/**
 * List section files in a project's sections/ directory.
 */
export function listProjectSections(vaultPath: string, project: string): SectionInfo[] {
  const sectionsDir = join(vaultPath, 'projects', project, 'sections');
  if (!existsSync(sectionsDir)) return [];

  return readdirSync(sectionsDir)
    .filter(f => f.endsWith('.md'))
    .sort()
    .map(f => {
      const filename = f.replace(/\.md$/, '');
      const label = filename
        .replace(/^\d+\w?-/, '')
        .replace(/-/g, ' ')
        .replace(/\b\w/g, c => c.toUpperCase());
      return { filename, label };
    });
}

/**
 * Fetch all preset configs as JSON from the CLI.
 */
export async function fetchPresets(
  pythonExe: string,
): Promise<Record<string, PresetData>> {
  try {
    const { stdout } = await systemTools.execFileAsync(pythonExe, [
      '-m', 'auto_cv', 'list-presets', '--json',
    ], {
      env: { ...process.env, PYTHONIOENCODING: 'utf-8', NO_COLOR: '1' },
    });
    const parsed: unknown = JSON.parse(stdout);
    return (parsed as Record<string, PresetData>) || {};
  } catch {
    return {};
  }
}

/**
 * Parse a _project.yml file content into structured data.
 */
function parseProjectYaml(text: string): {
  include: string[];
  section_order: string[];
  config: Record<string, string>;
} {
  const result = {
    include: [] as string[],
    section_order: [] as string[],
    config: {} as Record<string, string>,
  };

  const includeMatch = text.match(/^include:\s*\n((?:[ \t]+- .+\n?)*)/m);
  if (includeMatch) {
    result.include = [...includeMatch[1].matchAll(/[ \t]+- (.+)/g)].map(m => m[1].trim());
  }

  const orderMatch = text.match(/^section_order:\s*\n((?:[ \t]+- .+\n?)*)/m);
  if (orderMatch) {
    result.section_order = [...orderMatch[1].matchAll(/[ \t]+- (.+)/g)].map(m => m[1].trim());
  }

  const configMatch = text.match(/^config:\s*\n((?:[ \t]+\w.+\n?)*)/m);
  if (configMatch) {
    for (const m of configMatch[1].matchAll(/[ \t]+(\w[\w-]*):\s*"?([^"\n]+)"?/g)) {
      result.config[m[1]] = m[2].trim();
    }
  }

  return result;
}

/**
 * Parse a project header.md file with YAML frontmatter into structured data.
 */
function parseProjectHeaderMd(text: string): {
  include: string[];
  section_order: string[];
  config: Record<string, string>;
} {
  const result = {
    include: [] as string[],
    section_order: [] as string[],
    config: {} as Record<string, string>,
  };

  // Split frontmatter from body
  const fmMatch = text.match(/^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$/);
  if (!fmMatch) return result;

  const frontmatter = fmMatch[1];
  const body = fmMatch[2].trim();

  // Parse include and section_order from frontmatter
  const includeMatch = frontmatter.match(/^include:\s*\n((?:[ \t]+- .+\n?)*)/m);
  if (includeMatch) {
    result.include = [...includeMatch[1].matchAll(/[ \t]+- (.+)/g)].map(m => m[1].trim());
  }

  const orderMatch = frontmatter.match(/^section_order:\s*\n((?:[ \t]+- .+\n?)*)/m);
  if (orderMatch) {
    result.section_order = [...orderMatch[1].matchAll(/[ \t]+- (.+)/g)].map(m => m[1].trim());
  }

  // Parse body for title override (*italic text*)
  if (body) {
    const italicTitleMatch = body.match(/^\*([^*]+)\*$/m);
    if (italicTitleMatch) {
      result.config['title'] = italicTitleMatch[1].trim();
    } else {
      const headingTitleMatch = body.match(/^##\s+(.+)$/m);
      if (headingTitleMatch) {
        result.config['title'] = headingTitleMatch[1].trim();
      }
    }
  }

  return result;
}

function extractProjectHeaderBody(text: string): string {
  const fmMatch = text.match(/^---\s*\n([\s\S]*?)\n---\s*\n?([\s\S]*)$/);
  if (!fmMatch) return '';
  return fmMatch[2].replace(/\r\n/g, '\n').trim();
}

function updateProjectHeaderBody(existingBody: string, titleOverride: string): string {
  const normalizedBody = existingBody.replace(/\r\n/g, '\n').trim();
  const lines = normalizedBody ? normalizedBody.split('\n') : [];
  const titleLineIndex = lines.findIndex(line => {
    const trimmed = line.trim();
    return (/^\*[^*].*\*$/.test(trimmed) && !/^\*\*.*\*\*$/.test(trimmed)) || /^##\s+.+$/.test(trimmed);
  });

  if (titleOverride) {
    const nextTitleLine = `*${titleOverride}*`;
    if (titleLineIndex >= 0) {
      lines[titleLineIndex] = nextTitleLine;
    } else {
      lines.push(nextTitleLine);
    }
  } else if (titleLineIndex >= 0) {
    lines.splice(titleLineIndex, 1);
  }

  return lines.join('\n').trim();
}

/**
 * Parse a _style.yml file content into structured data.
 */
function parseStyleYaml(text: string): {
  preset: string;
  colors: Record<string, string>;
  fonts: Record<string, string>;
  spacing: Record<string, string>;
  htmlLayout: string;
} {
  const result = {
    preset: 'classic',
    colors: {} as Record<string, string>,
    fonts: {} as Record<string, string>,
    spacing: {} as Record<string, string>,
    htmlLayout: '',
  };

  const presetMatch = text.match(/^preset:\s*(.+)/m);
  if (presetMatch) result.preset = presetMatch[1].trim().replace(/^["']|["']$/g, '');

  for (const section of ['colors', 'fonts', 'spacing'] as const) {
    const regex = new RegExp(`^${section}:\\s*\\n((?:[ \\t]+\\w.+\\n?)*)`, 'm');
    const match = text.match(regex);
    if (match) {
      for (const kv of match[1].matchAll(/[ \t]+(\w[\w_-]*):\s*"?([^"\n]+)"?/g)) {
        result[section][kv[1]] = kv[2].trim();
      }
    }
  }

  const htmlMatch = text.match(/^html:\s*\n((?:[ \t]+\w.+\n?)*)/m);
  if (htmlMatch) {
    const layoutMatch = htmlMatch[1].match(/layout:\s*"?([^"\n]+)"?/);
    if (layoutMatch) result.htmlLayout = layoutMatch[1].trim();
  }

  return result;
}

/**
 * Load project config and style for an existing project.
 */
export function loadProjectData(vaultPath: string, project: string): ProjectData {
  const projectDir = join(vaultPath, 'projects', project);

  const defaults: ProjectData = {
    include: [],
    section_order: [],
    config: {},
    style: { preset: 'classic', colors: {}, fonts: {}, spacing: {}, htmlLayout: '' },
    projectSections: listProjectSections(vaultPath, project),
  };

  // Prefer header.md, fall back to _project.yml
  const headerMd = join(projectDir, 'header.md');
  const projYml = join(projectDir, '_project.yml');
  if (existsSync(headerMd)) {
    const parsed = parseProjectHeaderMd(readFileSync(headerMd, 'utf-8'));
    defaults.include = parsed.include;
    defaults.section_order = parsed.section_order;
    defaults.config = parsed.config;
  } else if (existsSync(projYml)) {
    const parsed = parseProjectYaml(readFileSync(projYml, 'utf-8'));
    defaults.include = parsed.include;
    defaults.section_order = parsed.section_order;
    defaults.config = parsed.config;
  }

  const styleYml = join(projectDir, '_style.yml');
  if (existsSync(styleYml)) {
    defaults.style = parseStyleYaml(readFileSync(styleYml, 'utf-8'));
  }

  return defaults;
}

/**
 * Save project header.md and _style.yml files.
 */
export function saveProjectFiles(
  vaultPath: string,
  project: string,
  data: {
    include: string[];
    sectionOrder: string[];
    titleOverride: string;
    preset: string;
    presetConfig?: Record<string, unknown>;
    styleOverrides: {
      colors?: Record<string, string>;
      fonts?: Record<string, string>;
      spacing?: Record<string, string>;
      htmlLayout?: string;
    };
  },
): void {
  const projectDir = join(vaultPath, 'projects', project);
  const headerPath = join(projectDir, 'header.md');
  const stylePath = join(projectDir, '_style.yml');
  mkdirSync(join(projectDir, 'sections'), { recursive: true });
  mkdirSync(join(projectDir, 'output'), { recursive: true });

  // Build header.md with YAML frontmatter
  let headerMd = '---\n';
  headerMd += 'include:\n';
  for (const inc of data.include) {
    headerMd += `  - ${inc}\n`;
  }
  if (data.sectionOrder.length > 0) {
    headerMd += 'section_order:\n';
    for (const s of data.sectionOrder) {
      headerMd += `  - ${s}\n`;
    }
  }
  headerMd += '---\n';

  const headerExists = existsSync(headerPath);
  const existingBody = headerExists
    ? extractProjectHeaderBody(readFileSync(headerPath, 'utf-8'))
    : '';
  // Preserve existing body content for established projects; only apply title
  // override when creating a new header file.
  const nextBody = headerExists
    ? existingBody
    : updateProjectHeaderBody(existingBody, data.titleOverride);
  if (nextBody) {
    headerMd += `${nextBody}\n`;
  }
  writeFileSync(headerPath, headerMd, 'utf-8');

  const styleConfig = buildFullStyleConfig(data.preset, data.presetConfig, data.styleOverrides);
  let styleYml = '# Auto-CV Style Configuration\n';
  styleYml += '# All values below are configurable. Edit any value and rebuild.\n';
  styleYml += `# Preset: ${data.preset}\n\n`;
  styleYml += dumpYaml(styleConfig);
  if (!existsSync(stylePath)) {
    writeFileSync(stylePath, styleYml, 'utf-8');
  }
}

function buildFullStyleConfig(
  preset: string,
  presetConfig: Record<string, unknown> | undefined,
  styleOverrides: {
    colors?: Record<string, string>;
    fonts?: Record<string, string>;
    spacing?: Record<string, string>;
    htmlLayout?: string;
  },
): Record<string, unknown> {
  const base = defaultStyleConfig(preset);
  const presetBase = deepCloneObject(presetConfig);
  deepMergeRecord(base, presetBase);
  base.preset = preset;

  if (styleOverrides.colors && Object.keys(styleOverrides.colors).length > 0) {
    const existingColors = isRecord(base.colors) ? base.colors : {};
    base.colors = { ...existingColors, ...styleOverrides.colors };
  }
  if (styleOverrides.fonts && Object.keys(styleOverrides.fonts).length > 0) {
    const existingFonts = isRecord(base.fonts) ? base.fonts : {};
    base.fonts = { ...existingFonts, ...styleOverrides.fonts };
  }
  if (styleOverrides.spacing && Object.keys(styleOverrides.spacing).length > 0) {
    const existingSpacing = isRecord(base.spacing) ? base.spacing : {};
    base.spacing = { ...existingSpacing, ...styleOverrides.spacing };
  }
  if (styleOverrides.htmlLayout) {
    const existingHtml = isRecord(base.html) ? base.html : {};
    base.html = { ...existingHtml, layout: styleOverrides.htmlLayout };
  }

  return base;
}

function deepMergeRecord(base: Record<string, unknown>, overrides: Record<string, unknown>): void {
  for (const [key, value] of Object.entries(overrides)) {
    if (isRecord(base[key]) && isRecord(value)) {
      deepMergeRecord(base[key] as Record<string, unknown>, value);
    } else {
      base[key] = value;
    }
  }
}

function defaultStyleConfig(preset: string): Record<string, unknown> {
  return {
    preset,
    colors: {
      primary: '#2C3E50',
      secondary: '#7F8C8D',
      accent: '#3498DB',
      text: '#333333',
      heading: '#2C3E50',
      background: '#FFFFFF',
      link: '#3498DB',
      border: '#BDC3C7',
    },
    fonts: {
      heading: 'Helvetica',
      body: 'Georgia',
      mono: 'Courier New',
      size_base: '11pt',
      size_heading: '14pt',
      size_name: '24pt',
      size_small: '9pt',
      size_bullet: '9pt',
    },
    spacing: {
      page_margin: '0.75in',
      section_gap: '12pt',
      entry_gap: '8pt',
      line_height: '1.3',
      header_to_content: '1mm',
      skill_label_width: '4.5cm',
      bullet_before: '-4.0mm',
      bullet_list_topsep: '-1.5mm',
      bullet_after: '-4.0mm',
      bullet_marker: 'bullet',
    },
    latex: {
      template_set: 'default',
      engine: 'pdflatex',
      document_class: 'article',
      paper_size: 'letterpaper',
      font_package: 'helvet',
      font_dir: '',
      latex_style: '',
      use_icons: false,
      extra_packages: [],
      extra_preamble: '',
    },
    docx: {
      page_width_inches: 8.5,
      page_height_inches: 11.0,
      use_columns: false,
    },
    html: {
      layout: 'top-header',
      include_photo: false,
      responsive: true,
      print_friendly: true,
      custom_css_file: null,
      custom_js_file: null,
      include_nav: false,
    },
  };
}

function deepCloneObject(value: unknown): Record<string, unknown> {
  if (!isRecord(value)) return {};
  return JSON.parse(JSON.stringify(value)) as Record<string, unknown>;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function dumpYaml(value: unknown, indent = 0): string {
  if (!isRecord(value)) {
    return `${formatYamlScalar(value)}\n`;
  }

  const lines: string[] = [];
  const pad = ' '.repeat(indent);
  for (const [key, val] of Object.entries(value)) {
    if (isRecord(val)) {
      lines.push(`${pad}${key}:`);
      lines.push(dumpYaml(val, indent + 2).trimEnd());
    } else if (Array.isArray(val)) {
      if (val.length === 0) {
        lines.push(`${pad}${key}: []`);
      } else {
        lines.push(`${pad}${key}:`);
        for (const item of val) {
          if (isRecord(item)) {
            lines.push(`${' '.repeat(indent + 2)}-`);
            lines.push(dumpYaml(item, indent + 4).trimEnd());
          } else {
            lines.push(`${' '.repeat(indent + 2)}- ${formatYamlScalar(item)}`);
          }
        }
      }
    } else {
      lines.push(`${pad}${key}: ${formatYamlScalar(val)}`);
    }
  }

  return `${lines.join('\n')}\n`;
}

function formatYamlScalar(value: unknown): string {
  if (typeof value === 'string') {
    const escaped = value.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
    return `"${escaped}"`;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  if (value === null || value === undefined) {
    return 'null';
  }
  return `"${String(value).replace(/"/g, '\\"')}"`;
}
