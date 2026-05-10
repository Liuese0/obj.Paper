"""Thin window title strip (matches the wordmark row in obj.Paper Mockup.html).

Sits at the very top of the central widget, above the menu bar. Shows the
LShift wordmark `«` followed by `obj.Paper — <filename>` and a Terracotta
dot when the document has unsaved changes (spec §11).
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget

from .. import theme as T
from ..document import Document
from ..i18n import i18n, t


class TitleStrip(QFrame):
    def __init__(self, document: Document, parent: QWidget | None = None):
        super().__init__(parent)
        self._doc = document
        self.setObjectName("titleStrip")
        self.setFixedHeight(30)
        self.setStyleSheet(
            "QFrame#titleStrip{"
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            " stop:0 #EFEAD9, stop:1 #E8E2CF);"
            f"border-bottom:1px solid {T.BORDER};"
            "}"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(0)

        lay.addStretch(1)

        self.wordmark = QLabel()
        self.wordmark.setTextFormat(Qt.TextFormat.RichText)
        self.wordmark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.wordmark)

        lay.addStretch(1)

        document.dirtyChanged.connect(lambda *_: self.refresh())
        document.pathChanged.connect(lambda *_: self.refresh())
        document.changed.connect(self.refresh)
        i18n().languageChanged.connect(lambda *_: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        path = self._doc.path
        name = os.path.basename(path) if path else (self._doc.title or t("dialog.untitled"))
        dot_html = ""
        if self._doc.dirty:
            dot_html = f"<span style='color:{T.ACCENT};font-size:13px;'> ●</span>"
        self.wordmark.setText(
            f"<span style='font-family:Georgia,\"Times New Roman\",serif;color:{T.ACCENT};"
            f"font-weight:700;font-size:13px;letter-spacing:-0.5px;'>«</span>"
            f"<span style='font-family:Georgia,\"Times New Roman\",serif;color:{T.INK};"
            f"font-weight:600;font-size:12px;letter-spacing:0.02em;'> obj.Paper </span>"
            f"<span style='font-family:Georgia,\"Times New Roman\",serif;color:{T.DUST};"
            f"font-size:12px;'>— {name}</span>"
            f"{dot_html}"
        )
