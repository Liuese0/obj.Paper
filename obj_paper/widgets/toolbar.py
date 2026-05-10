"""Top toolbar (spec §5.1, §10), styled to match `obj.Paper Mockup.html`.

Layout:  [Save] [Export ▾] | [↶] [↷] | [B] [I] [U] [S] | [∑] [🔗] | … | doc-chip | [한국어 ▾]
- SVG icons (obj_paper.icons) instead of emoji glyphs.
- Save is a filled Terracotta primary button.
- Export is an outlined Terracotta button on white.
- B/I/U/S use Source-Serif/Times-style typography (the mockup uses serif
  weights to mimic actual formatting).
- Doc-context chip shows "{template} · {paper} · {body_font} {body_size}pt".
- Language chip is the lone Terracotta-tinted call-to-action on the right.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QWidget,
)

from .. import theme as T
from ..i18n import t, i18n
from ..icons import svg_pixmap
from ..templates import template_name


def _icon(name: str, color: str = T.INK, size: int = 14) -> QIcon:
    """Wrap an SVG into a QIcon."""
    return QIcon(svg_pixmap(name, size=size, color=color))


class _ToolBtn(QPushButton):
    """28-px-tall pill button matching the mockup's TB_BTN style."""

    def __init__(
        self,
        text: str = "",
        parent: QWidget | None = None,
        icon_name: str | None = None,
        icon_color: str | None = None,
        icon_size: int = 14,
    ):
        super().__init__(text, parent)
        self.setFixedHeight(28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon_name:
            self.setIcon(_icon(icon_name, color=icon_color or T.INK, size=icon_size))
            self.setIconSize(QSize(icon_size, icon_size))


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
        self.setStyleSheet(
            f"QFrame#topToolbar {{background:{T.SURFACE};border-bottom:1px solid {T.BORDER};}}"
        )
        self.setFixedHeight(48)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(8)

        # ── Save (filled accent) ───────────────────────────────────
        self.save_btn = _ToolBtn(
            "  " + t("tb.save"), icon_name="save", icon_color="#FFFFFF", icon_size=14
        )
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self.saveRequested)
        lay.addWidget(self.save_btn)

        # ── Export (outlined accent on white) + caret ──────────────
        self.export_btn = _ToolBtn(
            "  " + t("tb.export") + "    ",
            icon_name="download",
            icon_color=T.ACCENT,
            icon_size=13,
        )
        self.export_btn.setObjectName("accentOutline")
        # caret on the right edge — set as a trailing icon by appending text+arrow.
        self._update_export_caret()
        self.export_btn.clicked.connect(self._show_export_menu)
        lay.addWidget(self.export_btn)

        lay.addWidget(self._sep())

        # ── Undo / Redo (icon only) ────────────────────────────────
        self.undo_btn = _ToolBtn(icon_name="undo", icon_color=T.INK)
        self.redo_btn = _ToolBtn(icon_name="redo", icon_color=T.INK)
        self.undo_btn.setToolTip(t("menu.undo"))
        self.redo_btn.setToolTip(t("menu.redo"))
        self.undo_btn.clicked.connect(self.undoRequested)
        self.redo_btn.clicked.connect(self.redoRequested)
        for b in (self.undo_btn, self.redo_btn):
            b.setFixedWidth(36)
            lay.addWidget(b)

        lay.addWidget(self._sep())

        # ── Bold / Italic / Underline / Strike (serif chips) ───────
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
            b.setFixedWidth(34)
            lay.addWidget(b)

        lay.addWidget(self._sep())

        # ── ∑ (mono) and 🔗 link (svg) ─────────────────────────────
        self.math_btn = _ToolBtn("∑")
        self.math_btn.setStyleSheet(
            f"QPushButton{{font-family:'JetBrains Mono','Cascadia Code',monospace;"
            f"font-size:13px;color:{T.INK};}}"
        )
        self.math_btn.setFixedWidth(34)
        self.math_btn.setToolTip(t("menu.inline_math"))
        self.math_btn.clicked.connect(self.inlineMathRequested)
        self.link_btn = _ToolBtn(icon_name="link", icon_color=T.INK)
        self.link_btn.setFixedWidth(34)
        self.link_btn.setToolTip(t("menu.link"))
        self.link_btn.clicked.connect(self.insertLinkRequested)
        lay.addWidget(self.math_btn)
        lay.addWidget(self.link_btn)

        lay.addStretch(1)

        # ── Document context chip ─────────────────────────────────
        self.context_lbl = QLabel("")
        self.context_lbl.setStyleSheet(
            f"font-family:'JetBrains Mono','Cascadia Code',monospace;font-size:11px;color:{T.DUST};"
            f"background:{T.BG};padding:4px 8px;border:1px solid {T.BORDER};border-radius:4px;"
        )
        lay.addWidget(self.context_lbl)
        lay.addWidget(self._sep())

        # ── Language chip (Terracotta-tinted CTA) ─────────────────
        self.lang_btn = _ToolBtn("한국어    ")
        self.lang_btn.setObjectName("langChip")
        self.lang_btn.setIcon(_icon("caret", color=T.ACCENT, size=10))
        self.lang_btn.setIconSize(QSize(10, 10))
        self.lang_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.lang_btn.clicked.connect(self.languageToggleRequested)
        lay.addWidget(self.lang_btn)

        i18n().languageChanged.connect(self._retranslate)

    # ----- public API ----------------------------------------------------
    def update_context(self, settings) -> None:
        name = template_name(settings.template)
        self.context_lbl.setText(f"{name} · {settings.paper} · {settings.body_font} {settings.body_size}pt")

    def update_lang(self, lang: str) -> None:
        self.lang_btn.setText("한국어    " if lang == "ko" else "English    ")

    # ----- internals -----------------------------------------------------
    def _sep(self) -> QFrame:
        s = QFrame()
        s.setFixedSize(1, 20)
        s.setStyleSheet(f"background:{T.BORDER};")
        return s

    def _serif(self, extra: str) -> str:
        return (
            f"QPushButton{{font-family:'Times New Roman',Georgia,serif;font-size:14px;"
            f"color:{T.INK};{extra}}}"
        )

    def _update_export_caret(self) -> None:
        # The caret SVG is set as a trailing pixmap by re-rendering text with
        # a unicode caret + manually positioning. Simplest: append a small
        # "▾" glyph in the existing label.
        cur_text = self.export_btn.text().rstrip() + "  ▾"
        self.export_btn.setText(cur_text)

    def _show_export_menu(self) -> None:
        m = QMenu(self)
        a_pdf = QAction(t("export.pdf"), m)
        a_pdf.setIcon(_icon("page", color=T.ACCENT, size=12))
        a_html = QAction(t("export.html"), m)
        a_html.setIcon(_icon("code", color=T.ACCENT, size=12))
        a_pdf.triggered.connect(lambda: self.exportPdfRequested.emit())
        a_html.triggered.connect(lambda: self.exportHtmlRequested.emit())
        m.addAction(a_pdf)
        m.addAction(a_html)
        m.exec(self.export_btn.mapToGlobal(self.export_btn.rect().bottomLeft()))

    def _retranslate(self, lang: str) -> None:
        self.save_btn.setText("  " + t("tb.save"))
        self.export_btn.setText("  " + t("tb.export") + "    ▾")
        self.update_lang(lang)
        self.undo_btn.setToolTip(t("menu.undo"))
        self.redo_btn.setToolTip(t("menu.redo"))
        self.math_btn.setToolTip(t("menu.inline_math"))
        self.link_btn.setToolTip(t("menu.link"))
