# Auto-CV Project Audit Report

Date: 2026-03-19
Auditor: GitHub Copilot (GPT-5.3-Codex)

## Scope

This audit covered:

- Python test suite health
- CLI smoke testing for project-aware flows
- TypeScript/Obsidian plugin diagnostics surfaced by the workspace
- Targeted bug fixes for confirmed defects

## Verification Performed

1. Ran Python tests:
   - Command: `d:/OneDrive/Personal/Projects/Auto_Resume/.venv/Scripts/python.exe -m pytest -q`
   - Result: `121 passed`
2. Smoke-tested project listing:
   - Command: `python -m auto_cv list-projects local_test_vault`
   - Result: command succeeded and listed projects.
3. Smoke-tested project build:
   - Command: `python -m auto_cv build local_test_vault -p swe-fullstack -f html -o local_test_vault/output/html`
   - Result: build succeeded and produced HTML output.
4. Checked workspace diagnostics with `get_errors`.

## Bugs Found And Fixed

### 1. Obsidian settings tab had fragile plugin typing and an invalid module coupling

- Severity: Medium
- File: `obsidian-plugin/src/settings.ts`
- Issue:
  - `settings.ts` depended on `./main` for typing, causing editor diagnostics around module/type resolution in this workspace.
  - This also created unnecessary tight coupling between settings and entrypoint implementation.
- Fix:
  - Replaced direct `./main` type dependency with a local plugin interface extending Obsidian `Plugin` and containing only required members.

### 2. Auto-detect Python button did not reliably update the visible input field

- Severity: Medium
- File: `obsidian-plugin/src/settings.ts`
- Issue:
  - UI refresh logic checked for a non-standard property (`setAttr`) and could skip updating the textbox even after successful detection.
- Fix:
  - Replaced with explicit, standard input lookup and assignment (`inputEl.value = pythonPath`).

### 3. TypeScript strict-mode implicit `any` in settings format filter

- Severity: Low
- File: `obsidian-plugin/src/settings.ts`
- Issue:
  - `filter((f) => f !== fmt)` violated strict typing in this workspace diagnostics context.
- Fix:
  - Added explicit type annotation: `filter((f: string) => f !== fmt)`.

### 4. Configured Python path was trusted without validation

- Severity: Medium
- File: `obsidian-plugin/src/utils.ts`
- Issue:
  - `resolvePythonExecutable` returned a configured path without checking if it still existed/was executable.
  - This can happen after environment changes and causes avoidable runtime failures.
- Fix:
  - Added validation (`existsSync` + executable check) before accepting configured path.
  - Falls back to candidate detection when configured path is invalid.

## Remaining Risks / Gaps

1. Obsidian plugin build (`npm run build`) was not executed in this environment because `node.exe` is currently unavailable in PATH.
2. Documentation markdown lint issues are present in several `.md` files, but these were treated as style/maintenance items rather than runtime bugs.
3. This audit did not include UI-level manual interaction inside Obsidian; only code and CLI-level verification was performed.

## Improvement Suggestions (Not Implemented)

1. Add CI jobs for plugin TypeScript build and lint

- Run `npm run build` and `npm run lint` in CI to catch plugin regressions early.

1. Add plugin unit tests for settings behavior

- Especially around Python auto-detection UI updates and fallback behavior when interpreter paths break.

1. Add explicit integration tests for project-mode CLI

- Cover `build -p`, `list-projects`, and project include/override behavior in one end-to-end test path.

1. Improve output-path UX in CLI

- Current project build can produce nested output paths depending on renderer conventions (e.g., `.../output/html/html/index.html`).
- Consider normalizing/simplifying output directory semantics for less user confusion.

1. Add markdown lint auto-fix workflow for docs

- A lightweight docs lint/fix workflow would reduce noise in diagnostics and improve contributor experience.

## Summary

The codebase is currently healthy on Python test coverage and CLI smoke paths in this environment. Four concrete plugin/runtime bugs were identified and fixed, with no Python test regressions introduced by the fixes.
