"""LaTeX renderer — generates a structured LaTeX repo and optionally compiles to PDF."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from auto_cv.models.resume import Resume, Section, SectionType
from auto_cv.models.style import StyleConfig
from auto_cv.renderers.base import BaseRenderer

_TEMPLATES_BASE = Path(__file__).parent.parent / "templates" / "latex"

# Characters that must be escaped in LaTeX text
_LATEX_SPECIAL = re.compile(r"([&%$#_{}])")
_LATEX_TILDE = re.compile(r"~")
_LATEX_CARET = re.compile(r"\^")
_LATEX_BACKSLASH = re.compile(r"\\")


def _escape_latex(text: str) -> str:
    """Escape LaTeX special characters in user-supplied text."""
    if not text:
        return ""
    text = _LATEX_BACKSLASH.sub(r"\\textbackslash{}", text)
    text = _LATEX_SPECIAL.sub(r"\\\1", text)
    text = _LATEX_TILDE.sub(r"\\textasciitilde{}", text)
    text = _LATEX_CARET.sub(r"\\textasciicircum{}", text)
    return text


# Patterns for inline markdown → LaTeX conversion
_MD_CODE = re.compile(r"`([^`]+)`")
_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC = re.compile(r"\*(.+?)\*")


def _md_to_latex(text: str) -> str:
    """Convert inline markdown formatting to LaTeX equivalents, then escape
    any remaining special characters.  Handles: ``**bold**``, ``*italic*``,
    ``[text](url)``, and `` `code` ``.
    """
    if not text:
        return ""

    placeholders: list[str] = []

    def _ph(latex_str: str) -> str:
        idx = len(placeholders)
        placeholders.append(latex_str)
        return f"\x00PH{idx}\x00"

    # 1. Inline code  →  \texttt{...}
    def _code(m: re.Match) -> str:
        return _ph(f"\\texttt{{{_escape_latex(m.group(1))}}}")
    text = _MD_CODE.sub(_code, text)

    # 2. Links  →  \href{url}{text}
    def _link(m: re.Match) -> str:
        return _ph(f"\\href{{{m.group(2)}}}{{{_escape_latex(m.group(1))}}}")
    text = _MD_LINK.sub(_link, text)

    # 3. Bold  →  \textbf{...}
    def _bold(m: re.Match) -> str:
        return _ph(f"\\textbf{{{_escape_latex(m.group(1))}}}")
    text = _MD_BOLD.sub(_bold, text)

    # 4. Italic  →  \textit{...}
    def _italic(m: re.Match) -> str:
        return _ph(f"\\textit{{{_escape_latex(m.group(1))}}}")
    text = _MD_ITALIC.sub(_italic, text)

    # 5. Escape remaining plain text
    text = _escape_latex(text)

    # 6. Restore placeholders
    for idx, latex_str in enumerate(placeholders):
        text = text.replace(f"\x00PH{idx}\x00", latex_str)

    return text


def _templates_dir(template_set: str = "default") -> Path:
    """Return the template directory for a given template set."""
    d = _TEMPLATES_BASE / template_set
    if not d.is_dir():
        d = _TEMPLATES_BASE / "default"
    return d


class LatexRenderer(BaseRenderer):
    def render(self, resume: Resume, style: StyleConfig, output_dir: Path) -> Path:
        latex_dir = self.prepare_output_dir(output_dir, "latex")
        latex_dir.mkdir(parents=True, exist_ok=True)
        sections_dir = latex_dir / "sections"
        sections_dir.mkdir(exist_ok=True)

        template_set = style.latex.template_set
        tmpl_dir = _templates_dir(template_set)

        env = Environment(
            loader=FileSystemLoader(str(tmpl_dir)),
            block_start_string="<%",
            block_end_string="%>",
            variable_start_string="<<",
            variable_end_string=">>",
            comment_start_string="<#",
            comment_end_string="#>",
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        env.filters["escape_latex"] = _escape_latex
        env.filters["md_latex"] = _md_to_latex
        env.filters["strip_bullet"] = lambda s: re.sub(r"^\s*[-*]\s+", "", s)
        env.filters["split_emdash"] = lambda s: (
            {"name": s.split(" — ", 1)[0], "date": s.split(" — ", 1)[1]}
            if " — " in s
            else {"name": s.split(" – ", 1)[0], "date": s.split(" – ", 1)[1]}
            if " – " in s
            else {"name": s, "date": ""}
        )
        env.tests["starts_with_bold"] = lambda s: isinstance(s, str) and s.strip().startswith("**")
        env.tests["bullet_line"] = lambda s: isinstance(s, str) and bool(re.match(r"^\s*[-*]\s+", s))
        env.tests["has_emdash"] = lambda s: isinstance(s, str) and (" — " in s or " – " in s)

        # --- Copy static assets for the template set (e.g. .cls, .sty) ---
        static_dir = tmpl_dir / "static"
        if static_dir.is_dir():
            for asset in static_dir.iterdir():
                if asset.is_file():
                    shutil.copy2(asset, latex_dir / asset.name)

        # --- resume.sty (default template set only) ---
        if template_set == "default":
            if resume.overrides.resume_sty and resume.overrides.resume_sty_path:
                shutil.copy2(resume.overrides.resume_sty_path, latex_dir / "resume.sty")
            else:
                # Pick style-specific .sty.j2 from styles/ subdirectory
                style_name = style.latex.latex_style or style.preset or "classic"
                style_sty_path = f"styles/{style_name}.sty.j2"
                styles_dir = tmpl_dir / "styles"
                if (styles_dir / f"{style_name}.sty.j2").is_file():
                    sty_tmpl = env.get_template(style_sty_path)
                else:
                    # Fallback: try classic, then legacy resume.sty.j2
                    if (styles_dir / "classic.sty.j2").is_file():
                        sty_tmpl = env.get_template("styles/classic.sty.j2")
                    else:
                        sty_tmpl = env.get_template("resume.sty.j2")
                (latex_dir / "resume.sty").write_text(
                    sty_tmpl.render(style=style), encoding="utf-8"
                )

        # --- Ensure fonts/ directory exists for awesome-cv ---
        if template_set == "awesome-cv":
            fonts_dir = latex_dir / "fonts"
            fonts_dir.mkdir(exist_ok=True)

        # --- Copy user-configured font directory (for XeLaTeX/fontspec) ---
        if style.latex.font_dir:
            src_fonts = Path(style.latex.font_dir)
            if src_fonts.is_dir():
                dst_fonts = latex_dir / "fonts"
                dst_fonts.mkdir(exist_ok=True)
                for font_file in src_fonts.iterdir():
                    if font_file.is_file() and font_file.suffix.lower() in (
                        ".ttf", ".otf", ".woff", ".woff2",
                    ):
                        shutil.copy2(font_file, dst_fonts / font_file.name)

        # --- per-section .tex files ---
        ordered = resume.ordered_sections()
        section_filenames: list[str] = []
        for section in ordered:
            fname = f"{section.id}.tex"
            section_filenames.append(fname)
            tex_content = _render_section(env, section, style)
            (sections_dir / fname).write_text(tex_content, encoding="utf-8")

        # --- main.tex ---
        main_tmpl = env.get_template("main.tex.j2")
        (latex_dir / "main.tex").write_text(
            main_tmpl.render(
                resume=resume,
                style=style,
                section_filenames=section_filenames,
                escape_latex=_escape_latex,
                font_dir=None,  # Uses template default (fonts/)
            ),
            encoding="utf-8",
        )

        # --- compile ---
        _compile_latex(latex_dir, engine=style.latex.engine)

        pdf = latex_dir / "main.pdf"
        return pdf if pdf.exists() else latex_dir / "main.tex"


def _render_section(env: Environment, section: Section, style: StyleConfig) -> str:
    """Pick the right template for a section type and render it."""
    type_name = section.section_type.value
    template_name = f"section_{type_name}.tex.j2"

    try:
        tmpl = env.get_template(template_name)
    except Exception:
        tmpl = env.get_template("section_custom.tex.j2")

    return tmpl.render(section=section, style=style, escape_latex=_escape_latex)


def _compile_latex(latex_dir: Path, *, engine: str = "pdflatex") -> None:
    """Try to compile main.tex → PDF using latexmk."""
    latexmk = shutil.which("latexmk")
    if not latexmk:
        return  # Silently skip — CLI will warn

    if engine == "xelatex":
        engine_flag = "-xelatex"
    elif engine == "lualatex":
        engine_flag = "-lualatex"
    else:
        engine_flag = "-pdf"

    try:
        subprocess.run(
            [latexmk, engine_flag, "-interaction=nonstopmode", "-cd", str(latex_dir / "main.tex")],
            capture_output=True,
            timeout=120,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        pass
