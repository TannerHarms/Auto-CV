"""Style and theme data models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-schemes
# ---------------------------------------------------------------------------

class ColorScheme(BaseModel):
    primary: str = "#2C3E50"
    secondary: str = "#7F8C8D"
    accent: str = "#3498DB"
    text: str = "#333333"
    heading: str = "#2C3E50"
    background: str = "#FFFFFF"
    link: str = "#3498DB"
    border: str = "#BDC3C7"


class FontScheme(BaseModel):
    heading: str = "Helvetica"
    body: str = "Georgia"
    mono: str = "Courier New"
    size_base: str = "11pt"
    size_heading: str = "14pt"
    size_name: str = "24pt"
    size_small: str = "9pt"
    size_bullet: str = "9pt"


class SpacingScheme(BaseModel):
    page_margin: str = "0.75in"
    section_gap: str = "12pt"
    entry_gap: str = "8pt"
    line_height: str = "1.3"
    header_to_content: str = "1mm"
    skill_label_width: str = "4.5cm"
    bullet_before: str = "-4.0mm"   # legacy; prefers bullet_list_topsep when set
    bullet_list_topsep: str = "-1.5mm"  # topsep between entry header and bullets
    bullet_after: str = "-4.0mm"
    bullet_marker: str = "bullet"  # bullet, dash, endash, emdash, diamond


# ---------------------------------------------------------------------------
# Per-output options
# ---------------------------------------------------------------------------

class LatexOptions(BaseModel):
    template_set: str = "default"  # "default" or "awesome-cv"
    engine: str = "pdflatex"  # "pdflatex" or "xelatex"
    document_class: str = "article"
    paper_size: str = "letterpaper"
    font_package: str = "helvet"
    font_dir: str = ""  # Path to directory containing .ttf/.otf fonts (for XeLaTeX/fontspec)
    latex_style: str = ""  # Style file name (e.g. "modern"); auto-detected from preset if empty
    use_icons: bool = False
    extra_packages: list[str] = Field(default_factory=list)
    extra_preamble: str = ""


class DocxOptions(BaseModel):
    page_width_inches: float = 8.5
    page_height_inches: float = 11.0
    use_columns: bool = False


class HtmlOptions(BaseModel):
    layout: str = "top-header"  # "top-header", "sidebar", "cards"
    include_photo: bool = False
    responsive: bool = True
    print_friendly: bool = True
    custom_css_file: str | None = None  # Vault-relative path
    custom_js_file: str | None = None
    include_nav: bool = False


# ---------------------------------------------------------------------------
# Top-level style config
# ---------------------------------------------------------------------------

class StyleConfig(BaseModel):
    """Complete style configuration — loaded from preset + _style.yml overrides."""
    preset: str = "classic"
    colors: ColorScheme = Field(default_factory=ColorScheme)
    fonts: FontScheme = Field(default_factory=FontScheme)
    spacing: SpacingScheme = Field(default_factory=SpacingScheme)
    latex: LatexOptions = Field(default_factory=LatexOptions)
    docx: DocxOptions = Field(default_factory=DocxOptions)
    html: HtmlOptions = Field(default_factory=HtmlOptions)

    def merge(self, overrides: dict[str, Any]) -> StyleConfig:
        """Deep-merge overrides into this config, returning a new StyleConfig."""
        data = self.model_dump()
        _deep_merge(data, overrides)
        return StyleConfig.model_validate(data)

    def to_css_variables(self) -> dict[str, str]:
        """Export colors/fonts/spacing as CSS custom properties."""
        variables: dict[str, str] = {}
        for key, val in self.colors.model_dump().items():
            variables[f"--color-{key.replace('_', '-')}"] = val
        for key, val in self.fonts.model_dump().items():
            variables[f"--font-{key.replace('_', '-')}"] = val
        for key, val in self.spacing.model_dump().items():
            variables[f"--spacing-{key.replace('_', '-')}"] = val
        return variables


def _deep_merge(base: dict, overrides: dict) -> None:
    """Recursively merge overrides into base dict in-place."""
    for key, value in overrides.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
