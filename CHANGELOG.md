# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-19

### Added
- Initial release of Auto CV
- Python CLI for building CVs/resumes from Obsidian-style markdown vaults
- Support for three output formats: HTML, DOCX, LaTeX/PDF
- Multiple built-in style presets (Default, Awesome CV, Classic)
- Obsidian plugin for building resumes directly from vault
- Natural markdown body syntax (headers, metadata, bullets)
- YAML frontmatter support for resume metadata
- LLM agents for polish, tailoring, and layout suggestions
- Full test suite (108 tests)
- Comprehensive documentation and examples

### Features
- **Markdown-based resume authoring** - Write your resume in natural markdown format
- **Multiple output formats** - Generate HTML, DOCX, and LaTeX/PDF from one source
- **Style presets** - Choose from built-in templates or create custom styles
- **Obsidian integration** - Build resumes directly from your Obsidian vault
- **Asset support** - Include images and custom CSS/JavaScript
- **PDF output** - LaTeX compilation to professional PDF documents
- **LLM enhancement** (optional) - Polish content, tailor to job postings, suggest layouts

### Fixed
- Improved error handling and user feedback
- Better Python executable detection across platforms
- Enhanced Obsidian plugin UI with better modals and notifications

## [Unreleased]

### Planned
- GitHub Actions CI/CD pipeline
- Obsidian Community Plugins registry submission
- Additional style presets
- Template customization tools
- Web-based editor (optional SaaS)
