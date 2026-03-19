# Contributing to Auto CV

Thank you for your interest in contributing to Auto CV! We welcome contributions from the community.

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ (for Obsidian plugin development)
- Git
- A code editor (VS Code recommended)

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/TannerHarms/Auto-CV.git
   cd Auto-CV
   ```

2. **Set up Python environment:**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

## Development Workflow

### Creating a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### Committing Changes
Use conventional commits format:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation
- `style:` for code style changes
- `refactor:` for code refactoring
- `test:` for adding tests

Example:
```bash
git commit -m "feat: add new resume template option"
```

### Running Tests Before Commit
```bash
# Python tests
pytest tests/ -q

# Plugin build
npm run build --prefix obsidian-plugin

# Code quality
ruff check src/
```

### Pushing Changes
```bash
git push origin feature/your-feature-name
```

### Creating a Pull Request
1. Go to GitHub and create a Pull Request
2. Fill out the template with clear description and testing info
3. Link any related issues (#123)
4. Request review from maintainers

## Code Style

### Python
- PEP 8 compliant
- 100 character line length
- Type hints where possible
- Docstrings for public functions

### TypeScript
- ESLint compliant
- Prettier formatted
- Clear variable names
- Comments for complex logic

## Testing Guidelines

### Python Tests
- Add tests for new features in `tests/`
- Maintain > 80% code coverage
- Test both happy paths and error cases
- Run `pytest tests/ -v` before committing

### Obsidian Plugin Testing
- Complete the [plugin test checklist](OBSIDIAN_PLUGIN_TEST_CHECKLIST.md)
- Test in both light and dark themes
- Test on Windows, macOS, and Linux if possible
- Test with your own vault configuration

## Documentation

### Updating Docs
When adding features:
1. Update relevant README sections
2. Add examples if applicable
3. Update CHANGELOG.md
4. Add docstrings to code

### Writing Good Documentation
- Be clear and concise
- Include examples
- Link to related documentation
- Explain the "why" not just the "what"

## Reporting Issues

### Bug Reports
- Search existing issues first
- Use the bug report template
- Include reproduction steps
- Provide system information
- Attach error messages/screenshots

### Feature Requests
- Use the feature request template
- Explain the use case
- Suggest an implementation (optional)
- Consider backwards compatibility

## Review Process

1. **Automated checks:**
   - Tests must pass (GitHub Actions)
   - Code must be properly formatted
   - No linting errors

2. **Code review:**
   - At least one maintainer review required
   - Address feedback and re-request review
   - Request reviews from domain experts for complex changes

3. **Testing:**
   - Reviewer tests locally
   - Checks plugin functionality (if applicable)
   - Verifies no regressions

4. **Merge:**
   - Squash commits if appropriate
   - Use clear commit message
   - Delete feature branch

## Directory Structure Reference

```
Auto-CV/
├── src/auto_cv/           # Python package
│   ├── models/            # Data models
│   ├── parser/            # Vault parsing
│   ├── renderers/         # Output generation
│   ├── agents/            # LLM agents
│   ├── styles/            # Style presets
│   └── templates/         # Jinja2 templates
├── tests/                 # Python tests
├── obsidian-plugin/       # Obsidian plugin
│   ├── src/              # TypeScript source
│   ├── manifest.json     # Plugin metadata
│   └── package.json      # Dependencies
├── examples/             # Example vaults
└── docs/                 # Documentation
```

## Common Tasks

### Adding a New Style Preset
1. Create `src/auto_cv/styles/presets/your-preset.yml`
2. Add example values based on existing presets
3. Test with example vaults
4. Update README with preset description
5. Add tests if adding new style properties

### Fixing a Bug
1. Create issue with bug report
2. Create feature branch: `fix/issue-description`
3. Write test that reproduces bug
4. Fix the bug
5. Verify test passes
6. Submit PR with issue number

### Adding Python Tests
1. Create test in `tests/test_*.py`
2. Use descriptive test names
3. Test both success and failure paths
4. Run `pytest tests/test_yourfile.py -v`
5. Add to PR description which tests were added

### Building Obsidian Plugin
1. `cd obsidian-plugin`
2. `npm install` (if needed)
3. `npm run dev` (watch mode) or `npm run build` (production)
4. Copy files to Obsidian plugins folder
5. Test in Obsidian

## Getting Help

- **Documentation:** Check README.md and DEVELOPMENT.md
- **Issues:** Search closed issues for similar problems
- **Discussions:** Start a discussion for questions
- **Maintainers:** Tag maintainers in issues if stuck

## Recognition

Contributors will be acknowledged in:
- README.md contributors section
- CHANGELOG.md
- GitHub contributor graph

## Code of Conduct

Please be respectful and professional in all interactions. This project is for everyone.

Thank you for contributing! 🎉
