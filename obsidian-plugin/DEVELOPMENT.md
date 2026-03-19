# Development Guide - Auto CV Obsidian Plugin

This guide covers how to develop, build, and test the Auto CV Obsidian plugin.

## Prerequisites

- Node.js 16+ and npm
- TypeScript knowledge
- Obsidian API knowledge (basic familiarity with Obsidian plugin architecture)
- Python 3.9+ and the `auto-cv` CLI installed locally

## Project Structure

```
obsidian-plugin/
├── manifest.json          # Plugin metadata and entry point config
├── package.json           # npm dependencies and scripts
├── tsconfig.json          # TypeScript configuration
├── esbuild.config.mjs     # Build configuration
├── styles.css             # Plugin UI styles
├── .eslintrc.json         # Code linting config
├── .gitignore             # Git ignore rules
├── README.md              # User documentation
├── DEVELOPMENT.md         # This file
└── src/
    ├── main.ts            # Plugin entry point and command registration
    ├── modals.ts          # UI modal components
    ├── settings.ts        # Settings panel and configuration
    └── utils.ts           # Python subprocess execution utilities
```

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Install Auto CV Locally

```bash
# From the parent directory (project root)
pip install -e .
```

This installs the Python package in development mode, so your plugin can call it.

## Development Workflow

### Building

```bash
# Development build with watch mode (rebuilds on changes)
npm run dev

# Production build (minified, optimized)
npm run build

# Watch mode without optimization
npm run watch
```

### Code Quality

```bash
# Lint TypeScript files
npm run lint

# Format code with Prettier
npm run format
```

### Testing in Obsidian

#### Option 1: Load Plugin from Folder

1. Enable **Restricted Mode** in Obsidian Settings → Community Plugins → Toggle off "Restricted mode"
2. Go to **Settings → Community Plugins → Manage**
3. Click **Install plugin from folder**
4. Select the `obsidian-plugin` directory
5. Enable the plugin

#### Option 2: Copy Built Plugin to Obsidian

```bash
# After building
# Windows
copy main.js your-vault/.obsidian/plugins/auto-cv-obsidian/
copy manifest.json your-vault/.obsidian/plugins/auto-cv-obsidian/
copy styles.css your-vault/.obsidian/plugins/auto-cv-obsidian/

# macOS/Linux
cp main.js ~/your-vault/.obsidian/plugins/auto-cv-obsidian/
cp manifest.json ~/your-vault/.obsidian/plugins/auto-cv-obsidian/
cp styles.css ~/your-vault/.obsidian/plugins/auto-cv-obsidian/
```

## Key Source Files

### main.ts
Entry point for the plugin. Responsibilities:
- Load plugin settings
- Check if auto-cv is installed
- Register the "Build Resume" command
- Add ribbon icon
- Handle build execution and error handling

Key functions:
- `onload()` - Initializes the plugin
- `openBuildModal()` - Opens the build configuration modal
- `executeBuild()` - Executes the Python subprocess

### modals.ts
UI modal components for user interaction:
- `BuildModal` - Modal for selecting formats, preset, and output folder
- `ProgressModal` - Shows build progress

### settings.ts
Plugin configuration and settings panel:
- `AutoResumeSettings` - Type definition for plugin settings
- `AutoResumeSettingTab` - Settings UI implementation

Manages:
- Python executable path (with auto-detection)
- Default preset selection
- Default output folder
- Default output formats

### utils.ts
Low-level utilities for Python execution:
- `detectPythonExecutable()` - Finds Python on system
- `checkAutoResumeInstalled()` - Verifies auto-cv package
- `buildResume()` - Executes Python CLI subprocess

## Common Development Tasks

### Add a New Setting

1. Update `AutoResumeSettings` in `settings.ts`:
```typescript
export interface AutoResumeSettings {
  // ... existing settings
  newSetting: string;
}
```

2. Add to `DEFAULT_SETTINGS`:
```typescript
export const DEFAULT_SETTINGS: AutoResumeSettings = {
  // ... existing defaults
  newSetting: 'default-value',
};
```

3. Add UI component in `AutoResumeSettingTab.display()`:
```typescript
new Setting(containerEl)
  .setName('New Setting')
  .setDesc('Description of the setting')
  .addText((text) =>
    text
      .setValue(this.plugin.settings.newSetting)
      .onChange(async (value) => {
        this.plugin.settings.newSetting = value;
        await this.plugin.saveSettings();
      })
  );
```

### Add a New Command

In `main.ts`:
```typescript
this.addCommand({
  id: 'my-new-command',
  name: 'My New Command',
  callback: () => this.myNewFunction(),
});
```

### Handle Build Output

The `buildResume()` function in `utils.ts` returns void but throws on error. Current implementation:

```typescript
export async function buildResume(
  pythonExe: string,
  vaultPath: string,
  outputPath: string,
  formats: string[],
  preset: string
): Promise<void>
```

To add progress tracking, enhance the function signature to accept a callback:

```typescript
export async function buildResume(
  pythonExe: string,
  vaultPath: string,
  outputPath: string,
  formats: string[],
  preset: string,
  onProgress?: (message: string) => void
): Promise<void>
```

## Debugging

### Obsidian Console

1. Open Obsidian Developer Tools: `Ctrl+Shift+I` (Windows) or `Cmd+Shift+I` (Mac)
2. Look at the **Console** tab for plugin logs
3. Use `console.log()` in TypeScript to debug

### Python Execution Issues

Check the Python subprocess output:
1. In `utils.ts`, add debugging to the `buildResume()` function:
```typescript
console.log('Build args:', args);
console.log('Build output:', result.stdout);
console.log('Build errors:', result.stderr);
```

2. Or test the Python CLI directly from terminal:
```bash
python -m auto_cv build /path/to/vault --output ./output
```

## Building for Distribution

### Create Release Build

```bash
npm run build
```

This creates `main.js` and validates TypeScript.

### Package Plugin

```bash
# Create a zip with plugin files for distribution
zip -r auto-cv-obsidian.zip manifest.json main.js styles.css
```

## Contributing

1. Follow TypeScript best practices
2. Lint before committing: `npm run lint`
3. Format code: `npm run format`
4. Test changes in a development vault
5. Update documentation if adding features

## Troubleshooting

### Plugin fails to load
- Check the console for errors (`Ctrl+Shift+I`)
- Ensure `manifest.json` is valid JSON
- Try rebuilding: `npm run build`

### Python detection fails
- Ensure Python is in your PATH
- Or set explicit Python path in plugin settings
- Test: `python --version` from terminal

### Build subprocess fails
- Check Python package is installed: `pip list | grep auto-cv`
- Test Python CLI directly: `python -m auto_cv build .`
- Check vault structure matches expected format

### Settings don't persist
- Ensure `await this.plugin.saveSettings()` is called
- Check browser console for any storage errors

## Resources

- [Obsidian Plugin Developer Documentation](https://docs.obsidian.md/Plugins/Getting+started/Build+a+plugin)
- [Obsidian Sample Plugin](https://github.com/obsidianmd/sample-plugin)
- [Obsidian API Documentation](https://docs.obsidian.md/Reference/TypeScript+API)
- [Auto CV CLI Documentation](../README.md)
