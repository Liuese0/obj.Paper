"""Floating inline-formatting toolbar (spec §7).

Shows above the block when text is selected. B / I / U / S / ∑ / 🔗 / clear.
The toolbar operates on the currently focused QTextEdit.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QAction, QKeySequence, QTextCharFormat, QFont, QTextCursor
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QTextEdit, QWidget, QInputDialog

from .. import theme as T
from ..i18n import t


class InlineToolbar(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("inlineToolbar")
        self.setStyleSheet(
            f"QFrame#inlineToolbar {{"
            f"background:{T.INK};border-radius:8px;padding:4px;"
            f"}}"
            "QPushButton{background:transparent;border:none;color:white;"
            "border-radius:4px;padding:0;min-width:24px;min-height:22px;}"
            f"QPushButton:hover{{background:rgba(255,255,255,.12);}}"
        )
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.hide()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(2)

        self._buttons: list[QPushButton] = []

        def add(label: str, tip: str, on_click):
            btn = QPushButton(label)
            btn.setToolTip(tip)
            btn.setFixedSize(26, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(on_click)
            self._buttons.append(btn)
            lay.addWidget(btn)
            return btn

        bold_btn = add("B", t("menu.bold"), self._toggle_bold)
        bold_btn.setStyleSheet(
            f"font-family:'Times New Roman',serif;font-weight:700;font-size:13px;color:white;"
            f"background:transparent;border:none;border-radius:4px;"
        )
        italic_btn = add("I", t("menu.italic"), self._toggle_italic)
        italic_btn.setStyleSheet(
            f"font-family:'Times New Roman',serif;font-style:italic;font-size:13px;color:white;"
            f"background:transparent;border:none;border-radius:4px;"
        )
        under_btn = add("U", t("menu.underline"), self._toggle_underline)
        under_btn.setStyleSheet(
            "text-decoration:underline;font-family:'Times New Roman',serif;font-size:13px;color:white;"
            "background:transparent;border:none;border-radius:4px;"
        )
        strike_btn = add("S", "Strike", self._toggle_strike)
        strike_btn.setStyleSheet(
            "text-decoration:line-through;font-family:'Times New Roman',serif;font-size:13px;color:white;"
            "background:transparent;border:none;border-radius:4px;"
        )
        self._sep(lay)
        add("∑", t("menu.inline_math"), self._wrap_math)
        add("🔗", t("menu.link"), self._insert_link)
        self._sep(lay)
        add("⨯", t("menu.clear_format"), self._clear)

        self._target: QTextEdit | None = None

    def _sep(self, lay: QHBoxLayout) -> None:
        s = QFrame()
        s.setFixedSize(1, 14)
        s.setStyleSheet("background:rgba(255,255,255,.2);")
        lay.addWidget(s)

    # ---- target management ----
    def attach(self, edit: QTextEdit) -> None:
        if self._target is edit:
            return
        if self._target is not None:
            try:
                self._target.selectionChanged.disconnect(self._maybe_show)
            except TypeError:
                pass
        self._target = edit
        edit.selectionChanged.connect(self._maybe_show)

    def detach(self) -> None:
        if self._target is not None:
            try:
                self._target.selectionChanged.disconnect(self._maybe_show)
            except TypeError:
                pass
            self._target = None
        self.hide()

    def _maybe_show(self) -> None:
        edit = self._target
        if edit is None:
            self.hide()
            return
        cur = edit.textCursor()
        if not cur.hasSelection():
            self.hide()
            return
        rect = edit.cursorRect(cur)
        global_pos = edit.viewport().mapToGlobal(rect.topLeft())
        self.adjustSize()
        x = global_pos.x() - self.width() // 2
        y = global_pos.y() - self.height() - 6
        self.move(QPoint(max(8, x), max(0, y)))
        self.show()

    # ---- formatting ops ----
    def _apply_format(self, fmt: QTextCharFormat) -> None:
        if not self._target:
            return
        cur = self._target.textCursor()
        if not cur.hasSelection():
            return
        cur.mergeCharFormat(fmt)
        self._target.mergeCurrentCharFormat(fmt)

    def _toggle_bold(self) -> None:
        if not self._target:
            return
        cur = self._target.textCursor()
        weight = QFont.Weight.Bold if cur.charFormat().fontWeight() < QFont.Weight.Bold else QFont.Weight.Normal
        fmt = QTextCharFormat()
        fmt.setFontWeight(weight)
        self._apply_format(fmt)

    def _toggle_italic(self) -> None:
        if not self._target:
            return
        cur = self._target.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontItalic(not cur.charFormat().fontItalic())
        self._apply_format(fmt)

    def _toggle_underline(self) -> None:
        if not self._target:
            return
        cur = self._target.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not cur.charFormat().fontUnderline())
        self._apply_format(fmt)

    def _toggle_strike(self) -> None:
        if not self._target:
            return
        cur = self._target.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(not cur.charFormat().fontStrikeOut())
        self._apply_format(fmt)

    def _wrap_math(self) -> None:
        if not self._target:
            return
        cur = self._target.textCursor()
        if not cur.hasSelection():
            return
        sel = cur.selectedText()
        cur.insertText(f"${sel}$")

    def _insert_link(self) -> None:
        if not self._target:
            return
        url, ok = QInputDialog.getText(self._target, t("menu.link"), "URL")
        if not ok or not url:
            return
        cur = self._target.textCursor()
        if cur.hasSelection():
            text = cur.selectedText()
            cur.insertHtml(f'<a href="{url}">{text}</a>')
        else:
            cur.insertHtml(f'<a href="{url}">{url}</a>')

    def _clear(self) -> None:
        if not self._target:
            return
        cur = self._target.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Normal)
        fmt.setFontItalic(False)
        fmt.setFontUnderline(False)
        fmt.setFontStrikeOut(False)
        cur.setCharFormat(fmt)


_singleton: InlineToolbar | None = None


def get_inline_toolbar() -> InlineToolbar:
    global _singleton
    if _singleton is None:
        _singleton = InlineToolbar()
    return _singleton
