"""PDF and HTML exporters."""

from __future__ import annotations

import os
from PyQt6.QtCore import QMarginsF, QSizeF, Qt
from PyQt6.QtGui import QPageLayout, QPageSize, QTextDocument
from PyQt6.QtPrintSupport import QPrinter

from . import render
from .document import Document


_PAGE_MAP = {
    "A4": QPageSize.PageSizeId.A4,
    "Letter": QPageSize.PageSizeId.Letter,
    "Legal": QPageSize.PageSizeId.Legal,
    "B5": QPageSize.PageSizeId.B5,
}


def export_pdf(doc: Document, path: str) -> None:
    """Render the document to a single PDF using QPrinter + QTextDocument."""
    page_id = _PAGE_MAP.get(doc.settings.paper, QPageSize.PageSizeId.A4)

    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)

    layout = QPageLayout(
        QPageSize(page_id),
        QPageLayout.Orientation.Portrait if doc.settings.orientation == "portrait" else QPageLayout.Orientation.Landscape,
        QMarginsF(
            doc.settings.margin_left,
            doc.settings.margin_top,
            doc.settings.margin_right,
            doc.settings.margin_bottom,
        ),
        QPageLayout.Unit.Millimeter,
    )
    printer.setPageLayout(layout)

    qdoc = QTextDocument()
    qdoc.setDefaultStyleSheet("")
    qdoc.setHtml(render.document_to_html(doc, mode="export-pdf"))
    qdoc.setDocumentMargin(0)
    # Page size in points: QTextDocument uses logical pixels @ printer DPI.
    qdoc.setPageSize(QSizeF(printer.pageRect(QPrinter.Unit.Point).size()))
    qdoc.print(printer)


def export_html(doc: Document, path: str) -> None:
    """Render the document to a single self-contained `.html` file."""
    html = render.document_to_html(doc, mode="export-html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
