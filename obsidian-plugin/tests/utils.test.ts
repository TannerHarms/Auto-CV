import { afterEach, describe, expect, it, vi } from 'vitest';

import { detectPythonExecutable, PythonNotFoundError, resolvePythonExecutable, systemTools } from '../src/utils';

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
});