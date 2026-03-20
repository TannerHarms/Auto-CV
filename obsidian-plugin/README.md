# Auto CV - Obsidian Plugin

An Obsidian plugin that allows you to build professional CVs and resumes directly from your Obsidian vault using the Auto CV CLI.

## Features

- **Multiple Output Formats**: Generate resumes in HTML, DOCX, and LaTeX/PDF
- **Style Presets**: Choose from nine built-in resume styles (Classic, Modern, Minimal, Academic, Awesome-CV, Creative, Elegant, Executive, Technical)
- **Vault Integration**: Build resumes directly from your Obsidian vault structure
- **Easy Configuration**: Simple settings panel for Python path, default preset, and output folder
- **No Server Required**: Runs locally on your machine using the Python CLI

## Requirements

- Obsidian 1.4.0 or higher
- Python 3.9 or higher
- Auto CV CLI (`auto-cv` Python package)

## Installation

### 1. Install Python Package

```bash
pip install auto-cv
```

### 2. Install Obsidian Plugin

Option A: From Obsidian Community Plugins

Search for **Auto CV** in Settings → Community Plugins → Browse.

Option B: Manual Installation

```bash
# Clone this repository
git clone https://github.com/TannerHarms/Auto-CV.git

# Navigate to the plugin directory
cd Auto-CV/obsidian-plugin

# Install dependencies
npm install

# Build the plugin
npm run dev  # for development
npm run build  # for production

# Copy the plugin to your Obsidian plugins folder
# On Windows: $HOME/.obsidian/plugins/auto-cv-obsidian
# On macOS: ~/.obsidian/plugins/auto-cv-obsidian
# On Linux: ~/.config/obsidian/plugins/auto-cv-obsidian
```

## Configuration

1. Open Obsidian Settings → Community Plugins → Auto CV
2. Configure the following:
   - **Python Executable**: Path to your Python executable (or click "Auto-Detect")
   - **Default Preset**: Choose your preferred resume template
   - **Default Output Folder**: Where to save generated resumes (relative to vault root)
   - **Default Formats**: Select which formats to generate by default

## Usage

### Building a Resume

1. Click the "Build Resume" ribbon icon (document icon in the left sidebar)
   - Or use the command palette (Ctrl/Cmd + P) and search for "Build Resume"

2. In the Build Modal:
   - Select which formats you want to generate
   - Confirm the output folder
   - Click "Build"

3. The plugin will execute the Python CLI and generate your resume

### Vault Structure

Your Obsidian vault should follow this structure:

```
vault/
├── header.md            # Name, contact, section ordering
├── _style.yml           # Style preset + overrides (optional)
├── sections/            # Resume sections
│   ├── 01-summary.md
│   ├── 02-experience.md
│   ├── 03-education.md
│   └── ... other sections
└── assets/              # Images and resources
    └── ... images
```

## Resume Section Format

Sections use natural Markdown format:

```markdown
# Section Title

## Entry Title
**Organization** | Location | Date

Bullet point describing your work
Another achievement or responsibility

## Another Entry
**Company** | City | Jan 2020 - Present

More accomplishments...
```

## Development

### Build Commands

```bash
# Install dependencies
..\tools\with-node.ps1 npm.cmd install

# Development build (watches for changes)
..\tools\with-node.ps1 npm.cmd run dev

# Production build
..\tools\with-node.ps1 npm.cmd run build

# Run tests
..\tools\with-node.ps1 npm.cmd test
```

If your Windows terminal does not have `node` or `npm` on `PATH`, use `..\tools\with-node.ps1` as shown above, or dot-source it once per terminal session.

### Project Structure

```text
src/
├── main.ts           # Plugin entry point
├── modals.ts         # UI modals for building
├── settings.ts       # Settings panel
├── utils.ts          # Python execution utilities
└── manifest.json     # Plugin metadata
```

## Troubleshooting

### Python Not Found

- Ensure Python 3.9+ is installed
- Click "Auto-Detect" in settings, or manually set the Python executable path

### Auto CV Not Installed

- Install with: `pip install auto-cv`
- Verify installation: `python -m pip show auto-cv`

### Build Fails

1. Check the error message in the Obsidian notification
2. Open Developer Tools (Ctrl/Cmd + Shift + I) and check the console
3. Verify your vault structure matches the expected format
4. Try building from the command line directly:

   ```bash
   python -m auto_cv build /path/to/vault --output ./output
   ```

## Support

For issues, feature requests, or questions:

- Open an issue on GitHub
- Check the [Auto CV documentation](https://github.com/TannerHarms/Auto-CV)

## License

MIT License - feel free to use for personal and commercial projects.

## Credits

Built on top of the [Auto CV](https://github.com/TannerHarms/Auto-CV) CLI tool.
