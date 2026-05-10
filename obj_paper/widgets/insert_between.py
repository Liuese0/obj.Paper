"""'+ Add block' button that appears between blocks on hover (spec §5.3)."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QEvent
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu, QPushButton, QWidget, QHBoxLayout, QFrame

from .. import theme as T
from ..i18n import t


_INSERT_TYPES = [
    ("paragraph", "block.paragraph"),
    ("heading", "block.heading"),
    ("list", "block.list"),
    ("code", "block.code"),
    ("equation", "block.equation"),
    ("figure", "block.figure"),
    ("table", "block.table"),
    ("references", "block.references"),
    ("pagebreak", "block.pagebreak"),
]


class InsertBetween(QWidget):
    """A row that reveals a Terracotta button on hover and emits `requested(type)`."""

    requested = pyqtSignal(str, int)  # block_type, insert_index

    def __init__(self, index: int, parent: QWidget | None = None):
        super().__init__(parent)
        self._index = index
        self.setFixedHeight(22)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self._left = QFrame()
        self._left.setFixedHeight(1)
        self._left.setObjectName("divider")
        self._left.setStyleSheet(f"background:{T.ACCENT};")
        self._left.setVisible(False)
        self._left.setMinimumWidth(20)

        self._btn = QPushButton(f"＋ {t('canvas.add_block')}")
        self._btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn.setStyleSheet(
            f"QPushButton {{background:white;border:1px solid {T.ACCENT};color:{T.ACCENT};"
            "border-radius:10px;padding:1px 10px;font-size:11px;font-weight:500;}"
            f"QPushButton:hover {{background:{T.ACCENT_LIGHT};}}"
        )
        self._btn.clicked.connect(self._show_menu)
        self._btn.setVisible(False)

        self._right = QFrame()
        self._right.setFixedHeight(1)
        self._right.setStyleSheet(f"background:{T.ACCENT};")
        self._right.setVisible(False)
        self._right.setMinimumWidth(20)

        lay.addWidget(self._left, 1)
        lay.addWidget(self._btn, 0)
        lay.addWidget(self._right, 1)

    def set_index(self, index: int) -> None:
        self._index = index

    def enterEvent(self, e: QEvent) -> None:
        self._set_visible(True)

    def leaveEvent(self, e: QEvent) -> None:
        self._set_visible(False)

    def _set_visible(self, on: bool) -> None:
        self._left.setVisible(on)
        self._right.setVisible(on)
        self._btn.setVisible(on)

    def _show_menu(self) -> None:
        m = QMenu(self)
        for type_id, label_key in _INSERT_TYPES:
            act = QAction(t(label_key), m)
            act.triggered.connect(lambda checked=False, tid=type_id: self.requested.emit(tid, self._index))
            m.addAction(act)
        m.exec(self._btn.mapToGlobal(self._btn.rect().bottomLeft()))
