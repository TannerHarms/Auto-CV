/**
 * Utility functions for Python detection and subprocess execution.
 */

import { execFile } from 'child_process';
import { promisify } from 'util';
import { existsSync } from 'fs';
import { platform } from 'os';

const execFileAsync = promisify(execFile);

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

/**
 * Try to detect Python executable on the system.
 */
export async function detectPythonExecutable(pythonPath?: string): Promise<string> {
  // If user provided a path, try it
  if (pythonPath && existsSync(pythonPath)) {
    return pythonPath;
  }

  const isWindows = platform() === 'win32';
  const pythonCandidates = isWindows 
    ? ['python', 'python3', 'py']
    : ['python3', 'python'];

  for (const candidate of pythonCandidates) {
    try {
      // Try to get version
      const { stdout } = await execFileAsync(candidate, ['--version']);
      if (stdout) {
        return candidate;
      }
    } catch (e) {
      // Continue to next candidate
    }
  }

  throw new PythonNotFoundError(
    'Python executable not found. Please ensure Python 3.9+ is installed and in your PATH.'
  );
}

/**
 * Check if auto-cv is installed in the Python environment.
 */
export async function checkAutoResumeInstalled(pythonExe: string): Promise<void> {
  try {
    const { stdout } = await execFileAsync(pythonExe, ['-m', 'pip', 'show', 'auto-cv']);
    if (!stdout.includes('Name: auto-cv')) {
      throw new AutoResumeNotFoundError('auto-cv package not found');
    }
  } catch (e) {
    throw new AutoResumeNotFoundError(
      'auto-cv not installed. Install with: pip install auto-cv'
    );
  }
}

/**
 * Get the installed auto-cv version.
 */
export async function getAutoResumeVersion(pythonExe: string): Promise<string> {
  try {
    const { stdout } = await execFileAsync(pythonExe, ['-m', 'auto_cv', '--version']);
    return stdout.trim();
  } catch (e) {
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
  preset: string
): Promise<void> {
  const args = ['-m', 'auto_cv', 'build', vaultPath];

  // Add output
  args.push('-o', outputPath);

  // Add preset
  if (preset && preset !== 'default') {
    args.push('-s', preset);
  }

  // Add formats
  for (const fmt of formats) {
    args.push('-f', fmt);
  }

  try {
    const result = await execFileAsync(pythonExe, args, {
      maxBuffer: 10 * 1024 * 1024, // 10MB buffer
    });
    
    if (!result.stdout) {
      throw new Error('Build completed but produced no output');
    }
  } catch (error: any) {
    throw new Error(`Build failed: ${error.stderr || error.message}`);
  }
}
