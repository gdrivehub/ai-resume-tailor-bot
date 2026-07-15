"""
Extracts plain text from uploaded resume files (PDF or DOCX).
Uses pdfplumber as primary PDF extractor with PyMuPDF (fitz) as a fallback
for scanned/complex PDFs, and python-docx / docx2txt for Word files.
"""
from __future__ import annotations

import os

import docx2txt
import fitz  # PyMuPDF
import pdfplumber
from docx import Document

from app.logger import logger


class UnsupportedFileTypeError(Exception):
    pass


def extract_text_from_pdf(path: str) -> str:
    text_parts: list[str] = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
        text = "\n".join(text_parts).strip()
        if text:
            return text
        logger.info("pdfplumber extracted no text, falling back to PyMuPDF for {}", path)
    except Exception as e:
        logger.warning("pdfplumber failed on {}: {}. Falling back to PyMuPDF.", path, e)

    # Fallback: PyMuPDF (handles more edge cases / some scanned layouts)
    text_parts = []
    with fitz.open(path) as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts).strip()


def extract_text_from_docx(path: str) -> str:
    try:
        doc = Document(path)
        parts = [p.text for p in doc.paragraphs if p.text.strip()]
        # Also grab table cell text (many resumes use tables for layout)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        parts.append(cell.text.strip())
        text = "\n".join(parts).strip()
        if text:
            return text
    except Exception as e:
        logger.warning("python-docx failed on {}: {}. Falling back to docx2txt.", path, e)

    return docx2txt.process(path).strip()


def extract_resume_text(path: str) -> str:
    """
    Detects file type by extension and extracts plain text.
    Raises UnsupportedFileTypeError for anything else.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        text = extract_text_from_pdf(path)
    elif ext in (".docx", ".doc"):
        text = extract_text_from_docx(path)
    elif ext == ".txt":
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    else:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '{ext}'. Please upload a PDF, DOCX, or TXT resume."
        )

    if not text or len(text.strip()) < 30:
        raise ValueError(
            "Could not extract readable text from this file. It may be a scanned "
            "image-only document. Please upload a text-based PDF or DOCX."
        )
    return text
