"""
Generates a clean, ATS-friendly PDF resume from the structured JSON
returned by the AI engine, using ReportLab.
"""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

ACCENT = colors.HexColor("#1F4E79")


def _styles():
    base = getSampleStyleSheet()
    styles = {
        "name": ParagraphStyle(
            "NameStyle", parent=base["Title"], fontSize=20, textColor=ACCENT,
            alignment=TA_CENTER, spaceAfter=2,
        ),
        "contact": ParagraphStyle(
            "ContactStyle", parent=base["Normal"], fontSize=9.5,
            alignment=TA_CENTER, spaceAfter=10, textColor=colors.HexColor("#333333"),
        ),
        "section": ParagraphStyle(
            "SectionStyle", parent=base["Heading2"], fontSize=12,
            textColor=ACCENT, spaceBefore=10, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "BodyStyle", parent=base["Normal"], fontSize=10.2, leading=14,
        ),
        "italic_small": ParagraphStyle(
            "ItalicSmall", parent=base["Normal"], fontSize=9.5,
            fontName="Helvetica-Oblique", textColor=colors.HexColor("#444444"),
            spaceAfter=2,
        ),
        "bold": ParagraphStyle(
            "BoldStyle", parent=base["Normal"], fontSize=10.5, fontName="Helvetica-Bold",
        ),
    }
    return styles


def build_resume_pdf(data: dict, output_path: str) -> str:
    s = _styles()
    doc = SimpleDocTemplate(
        output_path, pagesize=LETTER,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
    )
    story = []

    story.append(Paragraph(data.get("full_name", "Your Name"), s["name"]))
    if data.get("contact_line"):
        story.append(Paragraph(data["contact_line"], s["contact"]))

    def section(title: str):
        story.append(Paragraph(title.upper(), s["section"]))
        story.append(HRFlowable(width="100%", color=ACCENT, thickness=0.7, spaceAfter=6))

    if data.get("summary"):
        section("Professional Summary")
        story.append(Paragraph(data["summary"], s["body"]))

    if data.get("skills"):
        section("Skills")
        story.append(Paragraph(" • ".join(data["skills"]), s["body"]))

    if data.get("experience"):
        section("Experience")
        for job in data["experience"]:
            story.append(Paragraph(f"{job.get('title', '')} — {job.get('company', '')}", s["bold"]))
            meta = " | ".join(x for x in [job.get("location", ""), job.get("dates", "")] if x)
            if meta:
                story.append(Paragraph(meta, s["italic_small"]))
            bullets = job.get("bullets", [])
            if bullets:
                story.append(
                    ListFlowable(
                        [ListItem(Paragraph(b, s["body"])) for b in bullets],
                        bulletType="bullet", start="•", leftIndent=14,
                    )
                )
            story.append(Spacer(1, 6))

    if data.get("projects"):
        section("Projects")
        for proj in data["projects"]:
            story.append(Paragraph(proj.get("name", ""), s["bold"]))
            if proj.get("description"):
                story.append(Paragraph(proj["description"], s["body"]))
            bullets = proj.get("bullets", [])
            if bullets:
                story.append(
                    ListFlowable(
                        [ListItem(Paragraph(b, s["body"])) for b in bullets],
                        bulletType="bullet", start="•", leftIndent=14,
                    )
                )
            story.append(Spacer(1, 6))

    if data.get("education"):
        section("Education")
        for edu in data["education"]:
            story.append(Paragraph(f"{edu.get('degree', '')} — {edu.get('institution', '')}", s["bold"]))
            meta_bits = [x for x in [edu.get("dates", ""), edu.get("details", "")] if x]
            if meta_bits:
                story.append(Paragraph(" | ".join(meta_bits), s["body"]))
            story.append(Spacer(1, 4))

    if data.get("certifications"):
        section("Certifications")
        story.append(Paragraph(" • ".join(data["certifications"]), s["body"]))

    doc.build(story)
    return output_path
