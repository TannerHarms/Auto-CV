# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-07-15

### Added

- **Nine style presets**: awesome-cv, classic, modern, minimal, academic, creative, elegant, executive, technical
- **Preset-aware DOCX rendering**: each preset produces a distinctly styled Word document (headers, section headings, fonts, colours)
- **Preset-aware LaTeX rendering**: all nine presets compile cleanly with preset-specific `\cvname`, `\cvaddress`, section headings, skill/award/service commands
- **Six HTML layouts**: top-header, sidebar, cards, multi-page, latex-mirror, awesome-cv
- **Six complete example vaults** with preview screenshots
- **header.md format**: name, title, and contact info in natural markdown (replaces old `_config.yml`)
- **Project-aware builds**: `auto-cv build vault -p project-name` for role-specific resumes
- **GitHub Actions**: CI for Python tests, plugin build, and release workflow
- **Obsidian plugin**: build modal with format/preset selection, auto-detect Python, progress tracking
- **Release workflow**: tag-triggered GitHub release with plugin assets for Obsidian marketplace

### Features

- Three output formats from one source: HTML, DOCX, LaTeX/PDF
- Natural markdown body syntax (headers, bold metadata, bullets)
- YAML frontmatter for section metadata and ordering
- LLM agents (optional): polish, tailor, layout suggestions
- Custom CSS/JS injection for HTML output
- Asset support (photos, images)
- Comprehensive test suite (142 tests)

## [Unreleased]
