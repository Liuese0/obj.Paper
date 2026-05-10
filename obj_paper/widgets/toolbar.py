"""Top toolbar (spec §5.1, §10).

Save · Export ▾ · | · Undo · Redo · | · B I U S · | · ∑ 🔗 · spacer · doc-chip · Language."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QToolBar,
    QToolButton,
    QWidget,
)

from .. import theme as T
from ..i18n import t, i18n
from ..templates import template_name


class _ToolBtn(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(28)


class TopToolbar(QFrame):
    saveRequested = pyqtSignal()
    exportPdfRequested = pyqtSignal()
    exportHtmlRequested = pyqtSignal()
    undoRequested = pyqtSignal()
    redoRequested = pyqtSignal()
    formatBoldRequested = pyqtSignal()
    formatItalicRequested = pyqtSignal()
    formatUnderlineRequested = pyqtSignal()
    formatStrikeRequested = pyqtSignal()
    inlineMathRequested = pyqtSignal()
    insertLinkRequested = pyqtSignal()
    languageToggleRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("topToolbar")
        self.setStyleSheet(f"QFrame#topToolbar {{background:{T.SURFACE};border-bottom:1px solid {T.BORDER};}}")
        self.setFixedHeight(48)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(8)

        self.save_btn = _ToolBtn("💾  " + t("tb.save"))
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self.saveRequested)
        lay.addWidget(self.save_btn)

        self.export_btn = _ToolBtn("⬇  " + t("tb.export") + "  ▾")
        self.export_btn.setObjectName("accentOutline")
        self.export_btn.clicked.connect(self._show_export_menu)
        lay.addWidget(self.export_btn)

        lay.addWidget(self._sep())

        self.undo_btn = _ToolBtn("↶")
        self.redo_btn = _ToolBtn("↷")
        self.undo_btn.setToolTip(t("menu.undo"))
        self.redo_btn.setToolTip(t("menu.redo"))
        self.undo_btn.clicked.connect(self.undoRequested)
        self.redo_btn.clicked.connect(self.redoRequested)
        lay.addWidget(self.undo_btn)
        lay.addWidget(self.redo_btn)

        lay.addWidget(self._sep())

        self.bold_btn = _ToolBtn("B")
        self.italic_btn = _ToolBtn("I")
        self.under_btn = _ToolBtn("U")
        self.strike_btn = _ToolBtn("S")
        self.bold_btn.setStyleSheet(self._serif("font-weight:700;"))
        self.italic_btn.setStyleSheet(self._serif("font-style:italic;"))
        self.under_btn.setStyleSheet(self._serif("text-decoration:underline;"))
        self.strike_btn.setStyleSheet(self._serif("text-decoration:line-through;"))
        self.bold_btn.clicked.connect(self.formatBoldRequested)
        self.italic_btn.clicked.connect(self.formatItalicRequested)
        self.under_btn.clicked.connect(self.formatUnderlineRequested)
        self.strike_btn.clicked.connect(self.formatStrikeRequested)
        for b in (self.bold_btn, self.italic_btn, self.under_btn, self.strike_btn):
            lay.addWidget(b)

        lay.addWidget(self._sep())

        self.math_btn = _ToolBtn("∑")
        self.link_btn = _ToolBtn("🔗")
        self.math_btn.setToolTip(t("menu.inline_math"))
        self.link_btn.setToolTip(t("menu.link"))
        self.math_btn.clicked.connect(self.inlineMathRequested)
        self.link_btn.clicked.connect(self.insertLinkRequested)
        lay.addWidget(self.math_btn)
        lay.addWidget(self.link_btn)

        lay.addStretch(1)

        # doc context chip
        self.context_lbl = QLabel("")
        self.context_lbl.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace;font-size:11px;color:{T.DUST};"
            f"background:{T.BG};padding:4px 8px;border:1px solid {T.BORDER};border-radius:4px;"
        )
        lay.addWidget(self.context_lbl)
        lay.addWidget(self._sep())

        self.lang_btn = _ToolBtn("한국어 ▾")
        self.lang_btn.setObjectName("langChip")
        self.lang_btn.clicked.connect(self.languageToggleRequested)
        lay.addWidget(self.lang_btn)

        i18n().languageChanged.connect(self._retranslate)

    def update_context(self, settings) -> None:
        name = template_name(settings.template)
        self.context_lbl.setText(f"{name} · {settings.paper} · {settings.body_font} {settings.body_size}pt")

    def update_lang(self, lang: str) -> None:
        self.lang_btn.setText("한국어 ▾" if lang == "ko" else "English ▾")

    def _sep(self) -> QFrame:
        s = QFrame()
        s.setFixedSize(1, 20)
        s.setStyleSheet(f"background:{T.BORDER};")
        return s

    def _serif(self, extra: str) -> str:
        return f"QPushButton{{font-family:'Times New Roman',serif;font-size:13px;{extra}}}"

    def _show_export_menu(self) -> None:
        m = QMenu(self)
        a_pdf = QAction("📄 " + t("export.pdf"), m)
        a_html = QAction("🌐 " + t("export.html"), m)
        a_pdf.triggered.connect(lambda: self.exportPdfRequested.emit())
        a_html.triggered.connect(lambda: self.exportHtmlRequested.emit())
        m.addAction(a_pdf)
        m.addAction(a_html)
        m.exec(self.export_btn.mapToGlobal(self.export_btn.rect().bottomLeft()))

    def _retranslate(self, _lang: str) -> None:
        self.save_btn.setText("💾  " + t("tb.save"))
        self.export_btn.setText("⬇  " + t("tb.export") + "  ▾")
        self.update_lang(_lang)
        self.undo_btn.setToolTip(t("menu.undo"))
        self.redo_btn.setToolTip(t("menu.redo"))
        self.math_btn.setToolTip(t("menu.inline_math"))
        self.link_btn.setToolTip(t("menu.link"))
