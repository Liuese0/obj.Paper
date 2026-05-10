"""Block chrome — the visual frame around every block.

Responsibilities:
- Paint border (idle/hover/selected/dragging) and Blush background when selected.
- Floating type badge on top-left.
- Hover-revealed control cluster on top-right (Up / Down / More).
- Emit signals for the canvas to coordinate move/duplicate/delete and selection.

Block content widgets subclass `BlockChrome` and implement `_build_body(layout)`.
"""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import (
    QEvent,
    QMimeData,
    QPoint,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QStyleOption,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import theme as T
from ..document import BlockData
from ..i18n import t


_BADGE_LABELS = {
    "title": "TITLE",
    "authors": "AUTHORS",
    "abstract": "ABSTRACT",
    "heading": "HEADING",
    "paragraph": "PARAGRAPH",
    "equation": "EQUATION",
    "figure": "FIGURE",
    "table": "TABLE",
    "list": "LIST",
    "code": "CODE",
    "references": "REFERENCES",
    "pagebreak": "PAGE BREAK",
}


def block_badge_text(block: BlockData) -> str:
    base = _BADGE_LABELS.get(block.type, block.type.upper())
    if block.type == "heading":
        lvl = block.data.get("level", 1)
        return f"{base} · H{lvl}"
    if block.type == "code":
        lang = block.data.get("language", "text")
        return f"{base} · {lang}"
    return base


class BlockBadge(QLabel):
    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(parent)
        self._block = block
        self.setObjectName("blockBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(18)
        self.refresh()

    def refresh(self) -> None:
        self.setText(block_badge_text(self._block))
        color = T.block_badge_color(self._block.type)
        self.setStyleSheet(
            f"QLabel#blockBadge {{"
            f"background:{color}; color:white; "
            f"font-family:'JetBrains Mono','Cascadia Code',monospace; "
            f"font-size:9px; font-weight:600; letter-spacing:1.2px; "
            f"padding:0 7px; border-radius:4px;"
            f"}}"
        )
        self.adjustSize()


class _CtrlBtn(QPushButton):
    def __init__(self, text: str, tooltip: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("blockCtrl")
        self.setToolTip(tooltip)
        self.setFixedSize(22, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class BlockChrome(QFrame):
    """Frame that hosts a single block's content and emits chrome signals."""

    selected = pyqtSignal(str)  # block_id
    moveRequested = pyqtSignal(str, int)  # block_id, delta (-1 / +1)
    duplicateRequested = pyqtSignal(str)
    deleteRequested = pyqtSignal(str)
    addParagraphBelowRequested = pyqtSignal(str)
    changed = pyqtSignal()  # content mutated

    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(parent)
        self._block = block
        self._hover = False
        self._is_selected = False
        self._dragging = False
        self.setMouseTracking(True)
        self.setAutoFillBackground(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setObjectName("blockChrome")

        # Outer top margin reserves room for the badge that sits at the top
        # of the chrome. The badge can't extend ABOVE the chrome (Qt clips
        # children to parent geometry), so we place it inside the rounded
        # border, near the top edge.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 30, 16, 14)
        outer.setSpacing(0)
        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(8)
        outer.addLayout(self._body)

        self.badge = BlockBadge(block, parent=self)
        self.badge.move(14, 8)

        # control cluster (initially hidden)
        self._ctrl_panel = QWidget(self)
        ctrl_lay = QHBoxLayout(self._ctrl_panel)
        ctrl_lay.setContentsMargins(2, 2, 2, 2)
        ctrl_lay.setSpacing(2)
        self._btn_up = _CtrlBtn("↑", t("menu.move_up"))
        self._btn_down = _CtrlBtn("↓", t("menu.move_down"))
        self._btn_more = _CtrlBtn("⋮", t("menu.duplicate"))
        ctrl_lay.addWidget(self._btn_up)
        ctrl_lay.addWidget(self._btn_down)
        ctrl_lay.addWidget(self._btn_more)
        self._ctrl_panel.setStyleSheet(
            f"QWidget {{background:{T.BG};border:1px solid {T.BORDER};border-radius:6px;}}"
        )
        self._ctrl_panel.hide()

        self._btn_up.clicked.connect(lambda: self.moveRequested.emit(self._block.id, -1))
        self._btn_down.clicked.connect(lambda: self.moveRequested.emit(self._block.id, +1))
        self._btn_more.clicked.connect(self._show_more_menu)

        self._refresh_style()

    # ----- public -----
    @property
    def block(self) -> BlockData:
        return self._block

    def set_selected(self, sel: bool) -> None:
        if self._is_selected == sel:
            return
        self._is_selected = sel
        self._refresh_style()
        self._refresh_ctrl()

    def set_dragging(self, on: bool) -> None:
        self._dragging = on
        self.setStyleSheet(self.styleSheet())  # repaint
        self._refresh_style()

    def add_widget(self, w: QWidget) -> None:
        self._body.addWidget(w)

    def add_layout(self, lay) -> None:
        self._body.addLayout(lay)

    def emit_changed(self) -> None:
        self.changed.emit()

    def refresh_badge(self) -> None:
        self.badge.refresh()

    # ----- events -----
    def enterEvent(self, e: QEvent) -> None:
        self._hover = True
        self._refresh_style()
        self._refresh_ctrl()

    def leaveEvent(self, e: QEvent) -> None:
        self._hover = False
        self._refresh_style()
        self._refresh_ctrl()

    def mousePressEvent(self, e):
        self.selected.emit(self._block.id)
        super().mousePressEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # position control cluster on the top-right
        self._ctrl_panel.adjustSize()
        margin = 8
        x = max(0, self.width() - self._ctrl_panel.width() - margin)
        self._ctrl_panel.move(x, 4)

    # ----- internals -----
    def _refresh_style(self) -> None:
        if self._is_selected:
            border = f"2px solid {T.ACCENT}"
            bg = T.ACCENT_LIGHT
        elif self._hover:
            border = f"1px solid {T.ACCENT}"
            bg = T.SURFACE
        else:
            border = f"1px solid {T.BORDER}"
            bg = T.SURFACE
        # Padding is applied via the outer QVBoxLayout's contentsMargins;
        # adding QSS padding on top would double-pad and confuse the layout's
        # height calculation, which causes children to spill out of the frame.
        self.setStyleSheet(
            f"QFrame#blockChrome {{"
            f"background:{bg};"
            f"border:{border};"
            f"border-radius:8px;"
            f"}}"
        )

    def _refresh_ctrl(self) -> None:
        show = self._hover or self._is_selected
        self._ctrl_panel.setVisible(show)
        if show:
            self._ctrl_panel.adjustSize()
            self._ctrl_panel.move(max(0, self.width() - self._ctrl_panel.width() - 8), 4)
            self._ctrl_panel.raise_()

    def _show_more_menu(self) -> None:
        m = QMenu(self)
        m.addAction(_action(self, t("menu.duplicate"), lambda: self.duplicateRequested.emit(self._block.id)))
        m.addAction(_action(self, t("menu.add_paragraph"), lambda: self.addParagraphBelowRequested.emit(self._block.id)))
        m.addSeparator()
        m.addAction(_action(self, t("menu.delete"), lambda: self.deleteRequested.emit(self._block.id)))
        pos = self._btn_more.mapToGlobal(QPoint(0, self._btn_more.height()))
        m.exec(pos)


def _action(parent: QWidget, text: str, fn: Callable[[], None]) -> QAction:
    a = QAction(text, parent)
    a.triggered.connect(lambda checked=False: fn())
    return a
