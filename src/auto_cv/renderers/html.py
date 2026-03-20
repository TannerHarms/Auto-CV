"""HTML renderer — generates a styled HTML resume site."""

from __future__ import annotations

import shutil
from pathlib import Path

import markdown as md
from jinja2 import Environment, FileSystemLoader

from auto_cv.models.resume import Resume, Section, SectionType
from auto_cv.models.style import StyleConfig
from auto_cv.renderers.base import BaseRenderer

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "html"


class HtmlRenderer(BaseRenderer):
    def render(self, resume: Resume, style: StyleConfig, output_dir: Path) -> Path:
        html_dir = self.prepare_output_dir(output_dir, "html")
        html_dir.mkdir(parents=True, exist_ok=True)

        env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=True,
            keep_trailing_newline=True,
        )
        env.filters["markdown"] = _render_markdown
        env.globals["SectionType"] = SectionType

        layout = style.html.layout
        css_vars = style.to_css_variables()

        # --- Copy assets ---
        self._copy_assets(resume, html_dir)

        ordered_sections = resume.ordered_sections()

        # --- Multi-page layout: one HTML file per section ---
        if layout == "multi-page":
            return self._render_multi_page(
                env, resume, style, css_vars, ordered_sections, html_dir
            )

        # --- Main resume page ---
        template_name = f"layouts/{layout}/base.html.j2"
        try:
            tmpl = env.get_template(template_name)
        except Exception:
            tmpl = env.get_template("layouts/top-header/base.html.j2")

        has_pages = bool(resume.pages)
        index_html = tmpl.render(
            resume=resume,
            style=style,
            css_vars=css_vars,
            sections=resume.ordered_sections(),
            pages=resume.ordered_pages(),
            has_pages=has_pages,
            custom_css=self._read_override(resume.overrides.custom_css_path),
            custom_js=self._read_override(resume.overrides.custom_js_path),
        )
        index_path = html_dir / "index.html"
        index_path.write_text(index_html, encoding="utf-8")

        # --- Extra pages ---
        try:
            page_tmpl = env.get_template(f"layouts/{layout}/page.html.j2")
        except Exception:
            page_tmpl = env.get_template("layouts/top-header/page.html.j2")

        for page in resume.ordered_pages():
            page_html = page_tmpl.render(
                resume=resume,
                style=style,
                css_vars=css_vars,
                page=page,
                pages=resume.ordered_pages(),
                has_pages=has_pages,
                custom_css=self._read_override(resume.overrides.custom_css_path),
                custom_js=self._read_override(resume.overrides.custom_js_path),
            )
            (html_dir / f"{page.id}.html").write_text(page_html, encoding="utf-8")

        return index_path

    # ------------------------------------------------------------------

    def _render_multi_page(
        self,
        env: Environment,
        resume: Resume,
        style: StyleConfig,
        css_vars: dict[str, str],
        ordered_sections: list[Section],
        html_dir: Path,
    ) -> Path:
        """Generate one HTML file per section with shared navigation."""
        try:
            tmpl = env.get_template("layouts/multi-page/base.html.j2")
        except Exception:
            tmpl = env.get_template("layouts/top-header/base.html.j2")

        has_pages = bool(resume.pages)
        custom_css = self._read_override(resume.overrides.custom_css_path)
        custom_js = self._read_override(resume.overrides.custom_js_path)

        # Generate index.html showing the first section
        first_section = ordered_sections[0] if ordered_sections else None
        index_html = tmpl.render(
            resume=resume,
            style=style,
            css_vars=css_vars,
            sections=ordered_sections,
            all_sections=ordered_sections,
            active_section=first_section,
            active_section_id=first_section.id if first_section else None,
            pages=resume.ordered_pages(),
            has_pages=has_pages,
            custom_css=custom_css,
            custom_js=custom_js,
        )
        index_path = html_dir / "index.html"
        index_path.write_text(index_html, encoding="utf-8")

        # Generate one HTML file per section
        for section in ordered_sections:
            section_html = tmpl.render(
                resume=resume,
                style=style,
                css_vars=css_vars,
                sections=ordered_sections,
                all_sections=ordered_sections,
                active_section=section,
                active_section_id=section.id,
                pages=resume.ordered_pages(),
                has_pages=has_pages,
                custom_css=custom_css,
                custom_js=custom_js,
            )
            (html_dir / f"{section.id}.html").write_text(
                section_html, encoding="utf-8"
            )

        # Vault pages
        try:
            page_tmpl = env.get_template("layouts/multi-page/page.html.j2")
        except Exception:
            page_tmpl = env.get_template("layouts/top-header/page.html.j2")

        for page in resume.ordered_pages():
            page_html = page_tmpl.render(
                resume=resume,
                style=style,
                css_vars=css_vars,
                page=page,
                pages=resume.ordered_pages(),
                has_pages=has_pages,
                custom_css=custom_css,
                custom_js=custom_js,
            )
            (html_dir / f"page-{page.id}.html").write_text(page_html, encoding="utf-8")

        return index_path

    def _copy_assets(self, resume: Resume, html_dir: Path) -> None:
        """Copy vault assets/ directory to output."""
        # We need the vault path — derive from override paths or skip
        for attr in ("resume_sty_path", "custom_css_path", "custom_js_path"):
            p = getattr(resume.overrides, attr)
            if p:
                vault_dir = Path(p).parent
                assets_src = vault_dir / "assets"
                if assets_src.is_dir():
                    assets_dst = html_dir / "assets"
                    shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)
                    return

    @staticmethod
    def _read_override(path: str | None) -> str:
        if path and Path(path).exists():
            return Path(path).read_text(encoding="utf-8")
        return ""


def _render_markdown(text: str) -> str:
    """Convert markdown text to HTML."""
    return md.markdown(text, extensions=["tables", "fenced_code", "nl2br"])
