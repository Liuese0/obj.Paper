"""Import an existing PDF as an editable obj.Paper document.

Uses PyQt6's bundled QPdfDocument (no extra dependency). Text extraction
quality depends on the source PDF — born-digital PDFs come through cleanly,
scanned/image-only PDFs come through as empty pages (the caller should
warn the user).

Heuristics:
- The first short, single-line, non-empty paragraph on page 1 becomes the
  document title.
- Short single-line paragraphs elsewhere become H2 headings.
- Everything else becomes paragraph blocks.
- A `pagebreak` block is inserted between pages so the structure roughly
  mirrors the source PDF layout.
"""

from __future__ import annotations

import os
import re

from PyQt6.QtPdf import QPdfDocument

from .document import BlockData, Document


def _clean_paragraph(text: str) -> str:
    """Join soft line wraps inside a paragraph while preserving real breaks."""
    # QPdfDocument on some platforms uses \r for soft breaks within a page.
    # Treat it as a line-wrap separator (space), not a hard break.
    text = text.replace("\r\n", "\n").replace("\r", " ")
    # Collapse `word-\nword` hyphenations
    text = re.sub(r"-\n(\w)", r"\1", text)
    # Single newlines inside a paragraph → space; keep double newlines
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    # Collapse runs of whitespace
    return re.sub(r"[ \t]+", " ", text).strip()


def _extract_page_text(pdf: QPdfDocument, page: int) -> str:
    selection = pdf.getAllText(page)
    if selection is None:
        return ""
    raw = selection.text() or ""
    # Normalize QPdf's \r soft-break to a real space so paragraph
    # splitting below sees consistent line endings.
    return raw.replace("\r\n", "\n").replace("\r", "\n")


def import_pdf(path: str) -> Document:
    """Load `path` and return a new Document populated with imported blocks.

    Raises `RuntimeError` if the PDF can't be opened, or if no text could
    be extracted (image-only / scanned PDF)."""
    pdf = QPdfDocument(None)
    err = pdf.load(path)
    if err != QPdfDocument.Error.None_:
        raise RuntimeError(f"Failed to load PDF ({err.name})")

    blocks: list[BlockData] = []
    title_text: str | None = None
    total_pages = pdf.pageCount()
    total_chars = 0

    for page_idx in range(total_pages):
        raw = _extract_page_text(pdf, page_idx)
        if not raw.strip():
            continue
        total_chars += len(raw)

        # Split on blank lines into paragraphs
        for chunk in re.split(r"\n\s*\n", raw):
            cleaned = _clean_paragraph(chunk)
            if not cleaned:
                continue

            # Heuristic: short, single-line text behaves like a heading or title.
            short = len(cleaned) < 90 and "\n" not in chunk.strip() and len(cleaned) > 3

            if short and title_text is None and page_idx == 0:
                title_text = cleaned
                continue
            if short:
                blocks.append(
                    BlockData.make("heading", {"level": 2, "text": cleaned, "numbered": False})
                )
            else:
                blocks.append(BlockData.make("paragraph", {"text": cleaned}))

        if page_idx < total_pages - 1:
            blocks.append(BlockData.make("pagebreak", {}))

    # Trim trailing pagebreak if last page had no text
    while blocks and blocks[-1].type == "pagebreak":
        blocks.pop()

    if total_chars == 0:
        raise RuntimeError(
            "No text could be extracted from this PDF — it may be scanned "
            "or image-only. Use OCR first."
        )

    title = title_text or os.path.splitext(os.path.basename(path))[0]
    doc = Document(title=title)
    doc.insert_block(BlockData.make("title", {"text": title}))
    for b in blocks:
        doc.insert_block(b)
    doc.set_dirty(True)  # imported but not saved as .pw yet
    return doc
