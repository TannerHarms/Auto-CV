export function applyDetectedPythonPath(containerEl: ParentNode, pythonPath: string): void {
  const inputEl = containerEl.querySelector('input[placeholder="python3"]') as HTMLInputElement | null;
  if (inputEl) {
    inputEl.value = pythonPath;
  }
}

export function toggleFormatSelection(
  currentFormats: string[],
  formatName: string,
  enabled: boolean
): string[] {
  if (enabled) {
    return currentFormats.includes(formatName)
      ? currentFormats
      : [...currentFormats, formatName];
  }

  return currentFormats.filter((format: string) => format !== formatName);
}