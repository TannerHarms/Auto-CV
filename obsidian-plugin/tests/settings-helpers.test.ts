// @vitest-environment jsdom

import { describe, expect, it } from 'vitest';

import { applyDetectedPythonPath, toggleFormatSelection } from '../src/settings-helpers';

describe('settings helpers', () => {
  it('applies the detected python path to the settings input', () => {
    document.body.innerHTML = '<input placeholder="python3" value="">';

    applyDetectedPythonPath(document, 'C:/Python312/python.exe');

    const inputEl = document.querySelector('input[placeholder="python3"]') as HTMLInputElement;
    expect(inputEl.value).toBe('C:/Python312/python.exe');
  });

  it('adds formats without duplicating existing values', () => {
    expect(toggleFormatSelection(['html'], 'docx', true)).toEqual(['html', 'docx']);
    expect(toggleFormatSelection(['html'], 'html', true)).toEqual(['html']);
  });

  it('removes disabled formats', () => {
    expect(toggleFormatSelection(['html', 'docx'], 'docx', false)).toEqual(['html']);
  });
});