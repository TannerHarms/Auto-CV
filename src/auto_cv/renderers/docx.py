"""DOCX renderer — generates a .docx resume using python-docx."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from auto_cv.models.resume import Resume, Section, SectionType
from auto_cv.models.style import StyleConfig
from auto_cv.renderers.base import BaseRenderer


def _hex_to_rgb(hex_color: str) -> RGBColor:
    h = hex_color.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


class DocxRenderer(BaseRenderer):
    def render(self, resume: Resume, style: StyleConfig, output_dir: Path) -> Path:
        docx_dir = output_dir / "docx"
        docx_dir.mkdir(parents=True, exist_ok=True)
        out_path = docx_dir / "resume.docx"

        doc = Document()
        self._setup_page(doc, style)
        self._render_header(doc, resume, style)

        for section in resume.ordered_sections():
            self._render_section(doc, section, style)

        doc.save(str(out_path))
        return out_path

    # ------------------------------------------------------------------
    # Page setup
    # ------------------------------------------------------------------

    def _setup_page(self, doc: Document, style: StyleConfig) -> None:
        section = doc.sections[0]
        section.page_width = Inches(style.docx.page_width_inches)
        section.page_height = Inches(style.docx.page_height_inches)
        margin = self._parse_margin(style.spacing.page_margin)
        section.top_margin = margin
        section.bottom_margin = margin
        section.left_margin = margin
        section.right_margin = margin

        # Apply font defaults to document based on style
        doc_style = doc.styles["Normal"]
        doc_style.font.name = style.fonts.body
        doc_style.font.size = Pt(float(style.fonts.size_base.replace("pt", "")))
        doc_style.font.color.rgb = _hex_to_rgb(style.colors.text)

    @staticmethod
    def _parse_margin(margin_str: str) -> Inches:
        s = margin_str.strip().lower()
        if s.endswith("cm"):
            return Inches(float(s[:-2]) / 2.54)
        if s.endswith("mm"):
            return Inches(float(s[:-2]) / 25.4)
        if s.endswith("pt"):
            return Inches(float(s[:-2]) / 72)
        # Default: assume inches
        return Inches(float(s.replace("in", "")))

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _render_header(self, doc: Document, resume: Resume, style: StyleConfig) -> None:
        # Name
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(resume.config.name)
        run.bold = True
        run.font.name = style.fonts.heading
        run.font.size = Pt(float(style.fonts.size_name.replace("pt", "")))
        run.font.color.rgb = _hex_to_rgb(style.colors.primary)

        # Title
        if resume.config.title:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(resume.config.title)
            run.font.size = Pt(12)
            run.font.color.rgb = _hex_to_rgb(style.colors.secondary)

        # Contact line
        contact = resume.config.contact
        parts: list[str] = []
        if contact.email:
            parts.append(contact.email)
        if contact.phone:
            parts.append(contact.phone)
        if contact.location:
            parts.append(contact.location)
        if contact.linkedin:
            parts.append(f"linkedin.com/in/{contact.linkedin}")
        if contact.github:
            parts.append(f"github.com/{contact.github}")
        if contact.website:
            parts.append(contact.website)

        if parts:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(" | ".join(parts))
            run.font.size = Pt(9)
            run.font.color.rgb = _hex_to_rgb(style.colors.text)

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------

    def _render_section(self, doc: Document, section: Section, style: StyleConfig) -> None:
        # Section heading with colored underline
        p = doc.add_paragraph()
        run = p.add_run(section.title)
        run.bold = True
        run.font.name = style.fonts.heading
        run.font.size = Pt(float(style.fonts.size_heading.replace("pt", "")))
        run.font.color.rgb = _hex_to_rgb(style.colors.heading)

        # Add bottom border to heading paragraph
        pPr = p._element.get_or_add_pPr()
        pBdr = pPr.makeelement(qn("w:pBdr"), {})
        bottom = pBdr.makeelement(qn("w:bottom"), {
            qn("w:val"): "single",
            qn("w:sz"): "4",
            qn("w:space"): "1",
            qn("w:color"): style.colors.primary.lstrip("#"),
        })
        pBdr.append(bottom)
        pPr.append(pBdr)

        # Dispatch to typed rendering
        handler = {
            SectionType.EXPERIENCE: self._render_experience,
            SectionType.EDUCATION: self._render_education,
            SectionType.SKILLS: self._render_skills,
            SectionType.PROJECTS: self._render_projects,
            SectionType.CERTIFICATIONS: self._render_certifications,
            SectionType.PUBLICATIONS: self._render_publications,
            SectionType.AWARDS: self._render_awards,
            SectionType.SUMMARY: self._render_summary,
        }.get(section.section_type, self._render_custom)

        handler(doc, section, style)

    def _render_experience(self, doc: Document, section: Section, style: StyleConfig) -> None:
        for entry in section.experience_entries:
            # Title line
            p = doc.add_paragraph()
            run = p.add_run(entry.title)
            run.bold = True
            run.font.size = Pt(11)
            run.font.color.rgb = _hex_to_rgb(style.colors.heading)

            if entry.dates:
                run = p.add_run(f"  |  {entry.dates.display}")
                run.font.size = Pt(9)
                run.font.color.rgb = _hex_to_rgb(style.colors.secondary)

            # Organization line
            p = doc.add_paragraph()
            run = p.add_run(entry.organization)
            run.italic = True
            run.font.color.rgb = _hex_to_rgb(style.colors.accent)
            if entry.location:
                run = p.add_run(f"  —  {entry.location}")
                run.font.size = Pt(9)
                run.font.color.rgb = _hex_to_rgb(style.colors.secondary)

            # Highlights
            for h in entry.highlights:
                p = doc.add_paragraph(style="List Bullet")
                run = p.add_run(h)
                run.font.size = Pt(10)

    def _render_education(self, doc: Document, section: Section, style: StyleConfig) -> None:
        for entry in section.education_entries:
            p = doc.add_paragraph()
            run = p.add_run(entry.degree)
            run.bold = True
            run.font.color.rgb = _hex_to_rgb(style.colors.heading)

            if entry.dates:
                run = p.add_run(f"  |  {entry.dates.display}")
                run.font.size = Pt(9)
                run.font.color.rgb = _hex_to_rgb(style.colors.secondary)

            p = doc.add_paragraph()
            run = p.add_run(entry.institution)
            run.italic = True
            run.font.color.rgb = _hex_to_rgb(style.colors.accent)
            if entry.location:
                run = p.add_run(f"  —  {entry.location}")
                run.font.size = Pt(9)
                run.font.color.rgb = _hex_to_rgb(style.colors.secondary)

            if entry.gpa:
                p = doc.add_paragraph()
                run = p.add_run(f"GPA: {entry.gpa}")
                run.font.size = Pt(10)

            for h in entry.highlights:
                p = doc.add_paragraph(style="List Bullet")
                run = p.add_run(h)
                run.font.size = Pt(10)

    def _render_skills(self, doc: Document, section: Section, style: StyleConfig) -> None:
        for cat in section.skill_categories:
            p = doc.add_paragraph()
            run = p.add_run(f"{cat.name}: ")
            run.bold = True
            run.font.size = Pt(10)
            run = p.add_run(", ".join(cat.skills))
            run.font.size = Pt(10)

    def _render_projects(self, doc: Document, section: Section, style: StyleConfig) -> None:
        for entry in section.project_entries:
            p = doc.add_paragraph()
            run = p.add_run(entry.name)
            run.bold = True
            run.font.color.rgb = _hex_to_rgb(style.colors.heading)

            if entry.dates:
                run = p.add_run(f"  |  {entry.dates.display}")
                run.font.size = Pt(9)
                run.font.color.rgb = _hex_to_rgb(style.colors.secondary)

            if entry.technologies:
                p = doc.add_paragraph()
                run = p.add_run(", ".join(entry.technologies))
                run.italic = True
                run.font.size = Pt(9)
                run.font.color.rgb = _hex_to_rgb(style.colors.secondary)

            if entry.description:
                p = doc.add_paragraph()
                run = p.add_run(entry.description)
                run.font.size = Pt(10)

            for h in entry.highlights:
                p = doc.add_paragraph(style="List Bullet")
                run = p.add_run(h)
                run.font.size = Pt(10)

    def _render_certifications(self, doc: Document, section: Section, style: StyleConfig) -> None:
        for entry in section.certification_entries:
            p = doc.add_paragraph()
            run = p.add_run(entry.name)
            run.bold = True
            run.font.color.rgb = _hex_to_rgb(style.colors.heading)

            if entry.date:
                run = p.add_run(f"  |  {entry.date}")
                run.font.size = Pt(9)
                run.font.color.rgb = _hex_to_rgb(style.colors.secondary)

            if entry.issuer:
                p = doc.add_paragraph()
                run = p.add_run(entry.issuer)
                run.italic = True
                run.font.size = Pt(10)
                run.font.color.rgb = _hex_to_rgb(style.colors.accent)

            if entry.url:
                p = doc.add_paragraph()
                run = p.add_run(entry.url)
                run.font.size = Pt(9)
                run.font.color.rgb = _hex_to_rgb(style.colors.link)

    def _render_publications(self, doc: Document, section: Section, style: StyleConfig) -> None:
        for entry in section.publication_entries:
            p = doc.add_paragraph()
            run = p.add_run(entry.title)
            run.bold = True
            run.font.color.rgb = _hex_to_rgb(style.colors.heading)

            if entry.date:
                run = p.add_run(f"  |  {entry.date}")
                run.font.size = Pt(9)
                run.font.color.rgb = _hex_to_rgb(style.colors.secondary)

            if entry.venue:
                p = doc.add_paragraph()
                run = p.add_run(entry.venue)
                run.italic = True
                run.font.size = Pt(10)
                run.font.color.rgb = _hex_to_rgb(style.colors.accent)

            if entry.authors:
                p = doc.add_paragraph()
                run = p.add_run(", ".join(entry.authors))
                run.font.size = Pt(9)

    def _render_awards(self, doc: Document, section: Section, style: StyleConfig) -> None:
        for entry in section.award_entries:
            p = doc.add_paragraph()
            run = p.add_run(entry.title)
            run.bold = True
            run.font.color.rgb = _hex_to_rgb(style.colors.heading)

            if entry.date:
                run = p.add_run(f"  |  {entry.date}")
                run.font.size = Pt(9)
                run.font.color.rgb = _hex_to_rgb(style.colors.secondary)

            if entry.issuer:
                p = doc.add_paragraph()
                run = p.add_run(entry.issuer)
                run.italic = True
                run.font.size = Pt(10)
                run.font.color.rgb = _hex_to_rgb(style.colors.accent)

            if entry.description:
                p = doc.add_paragraph()
                run = p.add_run(entry.description)
                run.font.size = Pt(10)

    def _render_summary(self, doc: Document, section: Section, style: StyleConfig) -> None:
        if section.raw_content.strip():
            p = doc.add_paragraph()
            run = p.add_run(section.raw_content.strip())
            run.font.size = Pt(10)

    def _render_custom(self, doc: Document, section: Section, style: StyleConfig) -> None:
        if section.raw_content.strip():
            for line in section.raw_content.strip().split("\n"):
                p = doc.add_paragraph()
                run = p.add_run(line)
                run.font.size = Pt(10)
