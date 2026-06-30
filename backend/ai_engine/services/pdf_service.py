"""Generate PDF study notes from structured AI summaries."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer


class PDFGenerationError(Exception):
    """Raised when PDF output cannot be created."""


def _bullet_list(items: list[str], style) -> ListFlowable | None:
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    if not cleaned:
        return None
    return ListFlowable(
        [ListItem(Paragraph(item, style)) for item in cleaned],
        bulletType="bullet",
        start="•",
        leftIndent=18,
    )


def _definitions_list(rows: list[dict[str, str]], body_style, term_style) -> list:
    flowables = []
    for row in rows:
        term = str(row.get("term") or "").strip()
        definition = str(row.get("definition") or "").strip()
        if not term or not definition:
            continue
        flowables.append(Paragraph(f"<b>{term}</b>: {definition}", body_style))
        flowables.append(Spacer(1, 0.08 * inch))
    return flowables


def build_notes_pdf(summary: dict[str, Any]) -> bytes:
    """Render structured study notes into PDF bytes."""
    if not summary:
        raise PDFGenerationError("Summary payload is empty.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=str(summary.get("lesson_title") or "Study Notes"),
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "NotesTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "NotesSection",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#1e40af"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "NotesBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )
    footer_style = ParagraphStyle(
        "NotesFooter",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#64748b"),
    )

    story = []
    title = str(summary.get("lesson_title") or "Lesson Study Notes")
    story.append(Paragraph(title, title_style))
    story.append(
        Paragraph(
            "AI-generated study notes from YouTube transcript text (not video image analysis).",
            footer_style,
        )
    )
    story.append(Spacer(1, 0.15 * inch))

    sections: list[tuple[str, list[str] | None]] = [
        ("Key Concepts", summary.get("key_concepts") or []),
        ("Important Points", summary.get("important_points") or []),
        ("Examples", summary.get("examples") or []),
        ("Revision Notes", summary.get("revision_notes") or []),
        ("Possible Quiz Points", summary.get("possible_quiz_points") or []),
    ]

    definitions = summary.get("definitions") or []
    if definitions:
        story.append(Paragraph("Definitions", section_style))
        story.extend(_definitions_list(definitions, body_style, section_style))

    for heading, items in sections:
        if not items:
            continue
        story.append(Paragraph(heading, section_style))
        bullet = _bullet_list(items if isinstance(items, list) else [], body_style)
        if bullet:
            story.append(bullet)
        story.append(Spacer(1, 0.12 * inch))

    if len(story) <= 3:
        raise PDFGenerationError("PDF content is empty after formatting.")

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    if not pdf_bytes:
        raise PDFGenerationError("PDF builder returned empty output.")
    return pdf_bytes


def save_notes_pdf(summary: dict[str, Any], *, filename: str) -> str:
    """
    Generate PDF bytes and save under media/pdf_notes/.

    Returns the relative storage path (e.g. pdf_notes/lesson_1_notes.pdf).
    """
    pdf_bytes = build_notes_pdf(summary)
    media_root = Path(settings.MEDIA_ROOT)
    target_dir = media_root / "pdf_notes"
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(filename).name
    if not safe_name.lower().endswith(".pdf"):
        safe_name = f"{safe_name}.pdf"

    full_path = target_dir / safe_name
    full_path.write_bytes(pdf_bytes)

    return str(Path("pdf_notes") / safe_name).replace("\\", "/")
