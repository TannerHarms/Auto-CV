# Obsidian Plugin Testing Checklist

Complete this checklist to thoroughly test the Auto CV Obsidian plugin before distribution.

## Prerequisites

- [ ] Node.js 18+ installed
- [ ] Python 3.9+ installed
- [ ] `auto-cv` Python package installed: `pip install auto-cv`
- [ ] Obsidian (latest version)
- [ ] Test vault created or available

## Setup Testing

### Plugin Installation

- [ ] Navigate to `obsidian-plugin` directory
- [ ] Run `npm install` (dependencies install successfully)
- [ ] Run `npm run build` (plugin builds without errors)
- [ ] Copy `main.js`, `manifest.json`, and `styles.css` to Obsidian plugins folder:
  - Windows: `$HOME/.obsidian/plugins/auto-cv-obsidian/`
  - macOS: `~/.obsidian/plugins/auto-cv-obsidian/`
  - Linux: `~/.config/obsidian/plugins/auto-cv-obsidian/`
- [ ] Open Obsidian and toggle "Restricted mode" OFF (Settings → Community Plugins)
- [ ] Reload Obsidian (close and reopen vault, or use DevTools reload)
- [ ] Plugin appears in Community Plugins list
- [ ] Plugin can be enabled in Community Plugins settings

## Plugin Loading Tests

### Startup Behavior

- [ ] Plugin loads without errors in console
- [ ] If Python path not set, plugin shows helpful notification: "Configure Python path in settings"
- [ ] Plugin ribbon icon appears in left sidebar (document icon)
- [ ] "Build Resume/CV" command appears in command palette (Cmd/Ctrl+P)

### Settings Tab

- [ ] Settings tab accessible under "Auto CV" in Community Plugins settings
- [ ] All settings load with default values:
  - [ ] Python Executable field is empty or shows detected path
  - [ ] Default Preset dropdown shows options (Default, Awesome CV, Classic)
  - [ ] Default Output Folder shows "output"
  - [ ] Format toggles show HTML and DOCX checked

### Settings Functionality

- [ ] "Auto-Detect" button detects Python path and updates field
- [ ] Manually entering Python path saves correctly
- [ ] Changing preset selector persists after reload
- [ ] Changing output folder persists after reload
- [ ] Format checkboxes persist state after reload

## Build Modal Tests

### Modal Opening

- [ ] Click ribbon icon opens Build Modal
- [ ] "Build Resume/CV" command opens Build Modal
- [ ] Modal title shows "Build Resume/CV"
- [ ] Modal can be closed with "Cancel" button or ESC key

### Format Selection

- [ ] HTML, DOCX, and LaTeX/PDF checkboxes appear
- [ ] Checkboxes can be toggled on/off
- [ ] At least one format is checked by default (HTML, DOCX)
- [ ] Warning appears if no formats selected: "⚠️ Select at least one format"
- [ ] Build button disabled if no formats selected (or shows warning)

### Preset Selection

- [ ] Preset dropdown appears with label "Resume Style"
- [ ] Dropdown shows options: Default, Awesome CV, Classic
- [ ] Default preset is selected by default
- [ ] Can change preset before building

### Output Path

- [ ] Output directory field appears with label "Output Directory"
- [ ] Field shows "output" as default
- [ ] Can edit output path
- [ ] Relative paths work (e.g., "output", "build/resumes")
- [ ] Creates directory if it doesn't exist

### Modal UI Polish

- [ ] Info tooltip appears: "💡 Tip: Configure your vault with _config.yml and sections/ folder..."
- [ ] Layout is clean and intuitive
- [ ] Dark/Light theme respects Obsidian theme setting
- [ ] No console errors when opening/closing modal

## Build Execution Tests

### Success Build

- [ ] Select formats (at least HTML), confirm preset and output folder
- [ ] Click "Build" button
- [ ] Modal shows "⏳ Building Resume/CV"
- [ ] Progress message updates: "Verifying auto-cv is installed...", "Building resume..."
- [ ] Build completes without errors
- [ ] Success notification shows: "✅ Resume built successfully! Output: output"
- [ ] Output files exist in specified directory:
  - [ ] `output/html/index.html` (if HTML selected)
  - [ ] `output/docx/resume.docx` (if DOCX selected)
  - [ ] `output/latex/main.pdf` (if LaTeX selected)
- [ ] HTML resume opens in browser and displays correctly
- [ ] DOCX file opens in Word/LibreOffice with proper formatting
- [ ] PDF opens and shows correct content

### Error Handling - Missing Python

- [ ] Update Python path in settings to invalid path (e.g., "/nonexistent/python")
- [ ] Attempt to build
- [ ] Error notification shows: "❌ Python not found: ..."
- [ ] Console shows error details
- [ ] Notification persists long enough to read

### Error Handling - Missing auto-cv Package

- [ ] Use a Python installation without auto-cv installed
- [ ] Set Python path to that installation
- [ ] Attempt to build
- [ ] Error notification shows: "❌ Auto CV not installed: Install with: pip install auto-cv"
- [ ] User guidance is clear

### Error Handling - Invalid Vault

- [ ] Set output folder to a path that doesn't have write permissions
- [ ] Attempt to build
- [ ] Error notification shows: "❌ Build failed: ..." with helpful message
- [ ] Console shows detailed error

### Concurrent Build Prevention

- [ ] Start a build (select formats, click Build)
- [ ] While build is running, click Build button again
- [ ] Shows notification: "⏳ Build already in progress..."
- [ ] No duplicate builds start

## Vault Configuration Tests

### Valid Vault Setup

Create a test vault with proper structure:

```text
test-vault/
├── _config.yml
├── _style.yml (optional)
├── sections/
│   ├── 01-summary.md
│   ├── 02-experience.md
│   └── 03-education.md
└── assets/ (optional)
```

- [ ] Build succeeds with properly configured vault
- [ ] Output contains all sections

### Missing Config Files

- [ ] Remove `_config.yml` and attempt build
- [ ] Error message indicates missing config
- [ ] Guidance provided to user

### Empty Vault

- [ ] Create vault with just basic structure, no content
- [ ] Build completes (may with empty sections)
- [ ] No crash or error

## UI/UX Tests

### Notifications

- [ ] Notifications appear at top-right of Obsidian window
- [ ] Success notifications show ✅ emoji
- [ ] Error notifications show ❌ emoji
- [ ] Warnings show ⚠️ emoji
- [ ] Notifications auto-dismiss after 8 seconds (can close earlier)
- [ ] Multiple notifications can stack

### Theme Support

- [ ] Test with Obsidian Light theme
  - [ ] Modals are readable
  - [ ] Buttons are clickable
  - [ ] Checkboxes are visible
- [ ] Test with Obsidian Dark theme
  - [ ] Modals are readable
  - [ ] Buttons have good contrast
  - [ ] Text is not washed out
- [ ] Test with custom theme
  - [ ] Plugin adapts to theme colors

### Accessibility

- [ ] All buttons have hover effects
- [ ] All form inputs are keyboard-accessible
- [ ] Tab order is logical
- [ ] Can build entirely with keyboard (no mouse required)
- [ ] Form validation messages are clear

### Performance

- [ ] Plugin loads in < 2 seconds
- [ ] Setting changes don't cause lag
- [ ] Modal opens instantly
- [ ] Build execution is smooth (progress updates visible)

## Integration Tests

### Obsidian Integration

- [ ] Works with multiple vaults
- [ ] Works with vault in different locations (Desktop, Documents, OneDrive, etc.)
- [ ] Works with special characters in vault path
- [ ] Works with spaces in vault path
- [ ] Works with unicode characters in vault path

### Python Integration

- [ ] Works with Python from different sources:
  - [ ] System Python
  - [ ] Anaconda Python
  - [ ] Pyenv Python
  - [ ] Windows Store Python
- [ ] Works with different Python versions (3.10, 3.11, 3.12)

### Command Palette Integration

- [ ] Fuzzy search finds "Build Resume" command
- [ ] Command has proper description
- [ ] Command executes correctly

### Ribbon Icon

- [ ] Icon visible in ribbon
- [ ] Icon tooltip shows on hover
- [ ] Icon click opens Build Modal

## Edge Cases & Stress Tests

### Path Handling

- [ ] Long vault paths (> 260 characters) work on Windows
- [ ] Relative paths in output work correctly
- [ ] Absolute paths in output work correctly
- [ ] Paths with `../` work correctly

### Large Vaults

- [ ] Works with large vault (1000+ files)
- [ ] Works with large sections (10000+ words)
- [ ] Build time is reasonable (< 30 seconds)

### Special Vault Scenarios

- [ ] Vault with nested section folders works
- [ ] Vault with symlinks works
- [ ] Vault on network drive works (if applicable)
- [ ] Vault in read-only mode shows appropriate error

## Documentation & Help

### In-Plugin Help

- [ ] Info tooltip helpful and accurate
- [ ] Settings descriptions are clear
- [ ] Error messages are actionable

### External Documentation

- [ ] README.md accessible and helpful
- [ ] DEVELOPMENT.md covers plugin testing
- [ ] Links to auto-cv documentation work

## Final Sign-Off

If all checks pass:

- [ ] Plugin is production-ready
- [ ] Ready for Obsidian Community Plugins submission
- [ ] Ready to announce to users
- [ ] No known bugs or issues
- [ ] Performance is acceptable
- [ ] Error handling is robust
- [ ] User experience is smooth

### Known Issues (if any)

```text
(List any known limitations or issues here)
```

### Test Date: _______________

### Tester Name: _______________

### Test Environment: _______________
