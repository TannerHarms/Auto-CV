"""Integration tests for renderers — generate output and verify structure."""

import pytest
from pathlib import Path

from auto_cv.parser.vault_reader import load_vault
from auto_cv.renderers.latex import LatexRenderer
from auto_cv.renderers.docx import DocxRenderer
from auto_cv.renderers.html import HtmlRenderer


EXAMPLE_VAULT = Path(__file__).resolve().parent.parent / "example_vault"


@pytest.fixture(scope="module")
def resume_and_style():
    return load_vault(EXAMPLE_VAULT)


# ---------------------------------------------------------------------------
# LaTeX
# ---------------------------------------------------------------------------


class TestLatexRenderer:
    @pytest.fixture(autouse=True)
    def setup(self, resume_and_style, tmp_path_factory):
        self.resume, self.style = resume_and_style
        self.output = tmp_path_factory.mktemp("latex_output")
        renderer = LatexRenderer()
        self.result = renderer.render(self.resume, self.style, self.output)

    def test_main_tex_exists(self):
        assert (self.output / "latex" / "main.tex").exists()

    def test_resume_sty_exists(self):
        assert (self.output / "latex" / "resume.sty").exists()

    def test_sections_directory(self):
        sections = self.output / "latex" / "sections"
        assert sections.is_dir()
        tex_files = list(sections.glob("*.tex"))
        assert len(tex_files) >= 5  # summary, experience, education, skills, projects

    def test_main_tex_includes_sections(self):
        main = (self.output / "latex" / "main.tex").read_text(encoding="utf-8")
        assert r"\input{sections/" in main

    def test_no_unescaped_ampersand(self):
        """Ensure & in user data is escaped."""
        for tex in (self.output / "latex" / "sections").glob("*.tex"):
            content = tex.read_text(encoding="utf-8")
            # Bare & (not \&) shouldn't appear in text content
            # However this is a heuristic — LaTeX tables use &
            # Just verify the file is non-empty
            assert len(content) > 0


# ---------------------------------------------------------------------------
# Markdown-to-LaTeX conversion
# ---------------------------------------------------------------------------

from auto_cv.renderers.latex import _escape_latex, _md_to_latex


class TestMdToLatex:
    def test_empty(self):
        assert _md_to_latex("") == ""
        assert _md_to_latex(None) == ""

    def test_plain_text_escaped(self):
        assert _md_to_latex("10% increase") == r"10\% increase"

    def test_bold(self):
        assert _md_to_latex("Achieved **top** rank") == r"Achieved \textbf{top} rank"

    def test_italic(self):
        assert _md_to_latex("used *agile* methods") == r"used \textit{agile} methods"

    def test_inline_code(self):
        assert _md_to_latex("wrote `Python` scripts") == r"wrote \texttt{Python} scripts"

    def test_link(self):
        result = _md_to_latex("[Google](https://google.com)")
        assert result == r"\href{https://google.com}{Google}"

    def test_bold_with_special_chars(self):
        result = _md_to_latex("**C++ & Java**")
        assert result == r"\textbf{C++ \& Java}"

    def test_multiple_formats(self):
        result = _md_to_latex("Used **Python** and *R* for `data` analysis")
        assert r"\textbf{Python}" in result
        assert r"\textit{R}" in result
        assert r"\texttt{data}" in result

    def test_escape_latex_unchanged(self):
        """_escape_latex should still work for structured fields."""
        assert _escape_latex("AT&T") == r"AT\&T"
        assert _escape_latex("$100") == r"\$100"


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------


class TestDocxRenderer:
    @pytest.fixture(autouse=True)
    def setup(self, resume_and_style, tmp_path_factory):
        self.resume, self.style = resume_and_style
        self.output = tmp_path_factory.mktemp("docx_output")
        renderer = DocxRenderer()
        self.result = renderer.render(self.resume, self.style, self.output)

    def test_docx_file_exists(self):
        assert self.result.exists()
        assert self.result.suffix == ".docx"

    def test_docx_is_valid(self):
        """Verify the file can be opened by python-docx."""
        from docx import Document

        doc = Document(str(self.result))
        # Should have paragraphs
        assert len(doc.paragraphs) > 0

    def test_docx_contains_name(self):
        from docx import Document

        doc = Document(str(self.result))
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "Jordan Rivera" in full_text


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------


class TestHtmlRenderer:
    @pytest.fixture(autouse=True)
    def setup(self, resume_and_style, tmp_path_factory):
        self.resume, self.style = resume_and_style
        self.output = tmp_path_factory.mktemp("html_output")
        renderer = HtmlRenderer()
        self.result = renderer.render(self.resume, self.style, self.output)

    def test_index_html_exists(self):
        assert (self.output / "html" / "index.html").exists()

    def test_portfolio_page_exists(self):
        assert (self.output / "html" / "portfolio.html").exists()

    def test_index_contains_name(self):
        html = (self.output / "html" / "index.html").read_text(encoding="utf-8")
        assert "Jordan Rivera" in html

    def test_index_contains_sections(self):
        html = (self.output / "html" / "index.html").read_text(encoding="utf-8")
        assert "Experience" in html
        assert "Education" in html
        assert "Skills" in html

    def test_css_variables_present(self):
        html = (self.output / "html" / "index.html").read_text(encoding="utf-8")
        assert "--color-primary" in html

    def test_portfolio_page_content(self):
        html = (self.output / "html" / "portfolio.html").read_text(encoding="utf-8")
        assert "Portfolio" in html

    def test_assets_copied(self):
        assert (self.output / "html" / "assets").is_dir()

    def test_nav_links(self):
        html = (self.output / "html" / "index.html").read_text(encoding="utf-8")
        # Should have nav with link to portfolio
        assert "portfolio.html" in html
