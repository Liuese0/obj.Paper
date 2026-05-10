"""Center editing area: scrollable list of block widgets.

- Owns a `Document` reference and stays in sync with it.
- Supports drag-drop from the palette via `application/x-objpaper-block`.
- Renders `[+ Add block]` between every pair of blocks.
- Handles selection, move-up/down, duplicate, delete, type-change.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QPoint, QRect, QEvent
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent, QPainter, QColor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)

from .. import theme as T
from ..document import BlockData, Document
from ..i18n import t, i18n
from .block_chrome import BlockChrome
from .blocks import make_widget
from .insert_between import InsertBetween
from .palette import PALETTE_MIME


class _DropIndicator(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{T.ACCENT};border-radius:1px;")
        self.setFixedHeight(2)
        self.hide()


class Canvas(QFrame):
    """Scrollable editing area bound to a `Document`."""

    selectionChanged = pyqtSignal(str)  # block id or ""
    settingsRequested = pyqtSignal()    # user clicked Document Settings
    documentChanged = pyqtSignal()      # debounced update target for preview

    def __init__(self, document: Document, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("canvas")
        self.setStyleSheet(f"QFrame#canvas {{background:{T.BG};}}")
        self.setAcceptDrops(True)

        self._doc = document
        self._selected_id: str = ""
        self._widgets: list[BlockChrome] = []
        self._inserts: list[InsertBetween] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # canvas header bar (Document Settings + counts + zoom)
        head = QFrame()
        head.setStyleSheet(f"background:{T.SURFACE_2};border-bottom:1px solid {T.BORDER};")
        h = QHBoxLayout(head)
        h.setContentsMargins(16, 6, 16, 6)
        h.setSpacing(10)
        self.settings_btn = QPushButton("⚙ " + t("canvas.settings"))
        self.settings_btn.setObjectName("ghost")
        self.settings_btn.setStyleSheet(
            f"QPushButton#ghost {{background:{T.SURFACE};border:1px solid {T.BORDER};border-radius:5px;padding:3px 10px;font-size:11px;color:{T.INK};}}"
            f"QPushButton#ghost:hover {{border-color:{T.ACCENT};}}"
        )
        self.settings_btn.clicked.connect(self.settingsRequested)
        self.counts_lbl = QLabel("")
        self.counts_lbl.setObjectName("muted")
        self.counts_lbl.setStyleSheet(f"color:{T.DUST};font-size:11px;")
        zoom_btn = QPushButton(t("canvas.zoom") + " 100% ▾")
        zoom_btn.setObjectName("ghost")
        zoom_btn.setStyleSheet(
            f"QPushButton#ghost {{background:{T.SURFACE};border:1px solid {T.BORDER};border-radius:5px;padding:3px 10px;font-size:11px;color:{T.DUST};}}"
        )
        h.addWidget(self.settings_btn)
        h.addWidget(QLabel("·"))
        h.addWidget(self.counts_lbl, 1)
        h.addWidget(zoom_btn)
        outer.addWidget(head)

        # scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.viewport().setStyleSheet(f"background:{T.BG};")
        outer.addWidget(self.scroll, 1)

        wrap = QWidget()
        wrap.setStyleSheet(f"background:{T.BG};")
        wrap_lay = QVBoxLayout(wrap)
        wrap_lay.setContentsMargins(56, 24, 56, 32)
        wrap_lay.setSpacing(0)

        self._inner = QWidget()
        self._inner.setMaximumWidth(720)
        self._inner.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._inner_lay = QVBoxLayout(self._inner)
        self._inner_lay.setContentsMargins(0, 0, 0, 0)
        # 4px between every block / insert-between row so the floating badges
        # don't visually collide with the next block's content.
        self._inner_lay.setSpacing(4)
        wrap_lay.addWidget(self._inner, 0, Qt.AlignmentFlag.AlignHCenter)
        wrap_lay.addStretch(1)
        self.scroll.setWidget(wrap)

        self._drop_indicator = _DropIndicator(self._inner)

        # listen for doc changes (e.g. blocks replaced from open file)
        self._doc.blocksReplaced.connect(self._rebuild)
        self._doc.changed.connect(self._update_counts)

        i18n().languageChanged.connect(self._retranslate)
        self._rebuild()

    # ----- public ---
    @property
    def document(self) -> Document:
        return self._doc

    def select_block(self, block_id: str) -> None:
        self._selected_id = block_id
        for w in self._widgets:
            w.set_selected(w.block.id == block_id)
        self.selectionChanged.emit(block_id)

    def insert_new_block(self, type_id: str, index: int | None = None) -> str:
        from . import blocks as _blocks  # type: ignore  # noqa: F401

        block = BlockData.make(type_id, _default_data(type_id))
        idx = self._doc.insert_block(block, index)
        self._rebuild()
        self.select_block(block.id)
        QTimer = __import__("PyQt6.QtCore", fromlist=["QTimer"]).QTimer
        QTimer.singleShot(0, lambda: self._scroll_to(block.id))
        return block.id

    # ----- rebuild ---
    def _rebuild(self) -> None:
        # tear down
        while self._inner_lay.count():
            item = self._inner_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._widgets.clear()
        self._inserts.clear()

        ib = InsertBetween(0, parent=self._inner)
        ib.requested.connect(self._on_insert_request)
        self._inserts.append(ib)
        self._inner_lay.addWidget(ib)

        for i, block in enumerate(self._doc.blocks):
            w = make_widget(block, parent=self._inner)
            w.selected.connect(self.select_block)
            w.moveRequested.connect(self._on_move)
            w.duplicateRequested.connect(self._on_duplicate)
            w.deleteRequested.connect(self._on_delete)
            w.addParagraphBelowRequested.connect(self._on_add_paragraph)
            w.changed.connect(self._on_block_changed)
            self._widgets.append(w)
            self._inner_lay.addWidget(w)

            ib2 = InsertBetween(i + 1, parent=self._inner)
            ib2.requested.connect(self._on_insert_request)
            self._inserts.append(ib2)
            self._inner_lay.addWidget(ib2)

        if not self._doc.blocks:
            empty = QLabel(t("canvas.empty"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{T.DUST};font-size:12px;padding:32px;")
            self._inner_lay.addWidget(empty)

        self._inner_lay.addStretch(1)
        if self._selected_id:
            self.select_block(self._selected_id)
        self._update_counts()

    def _scroll_to(self, block_id: str) -> None:
        for w in self._widgets:
            if w.block.id == block_id:
                self.scroll.ensureWidgetVisible(w, 50, 50)
                break

    def _update_counts(self) -> None:
        from .. import render as render_mod
        n = self._doc.block_count()
        words = self._doc.word_count()
        pages = render_mod.estimate_pages(self._doc)
        self.counts_lbl.setText(f"{n} blocks · {words} words · {pages} pages")

    def _retranslate(self, _lang: str) -> None:
        self.settings_btn.setText("⚙ " + t("canvas.settings"))
        self._update_counts()

    # ----- handlers ---
    def _on_block_changed(self) -> None:
        self._doc.set_dirty(True)
        self._doc.changed.emit()
        self.documentChanged.emit()

    def _on_move(self, block_id: str, delta: int) -> None:
        self._doc.move_block(block_id, delta)
        self._rebuild()
        self.select_block(block_id)

    def _on_duplicate(self, block_id: str) -> None:
        idx = self._doc.index_of(block_id)
        if idx is None:
            return
        clone = self._doc.blocks[idx].clone()
        self._doc.insert_block(clone, idx + 1)
        self._rebuild()
        self.select_block(clone.id)

    def _on_delete(self, block_id: str) -> None:
        idx = self._doc.remove_block(block_id)
        if idx is None:
            return
        self._rebuild()
        if self._doc.blocks:
            self.select_block(self._doc.blocks[max(0, idx - 1)].id)
        else:
            self.select_block("")

    def _on_add_paragraph(self, block_id: str) -> None:
        idx = self._doc.index_of(block_id)
        self.insert_new_block("paragraph", (idx or -1) + 1)

    def _on_insert_request(self, type_id: str, index: int) -> None:
        self.insert_new_block(type_id, index)

    # ----- DnD ---
    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if e.mimeData().hasFormat(PALETTE_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e: QDragMoveEvent) -> None:
        if not e.mimeData().hasFormat(PALETTE_MIME):
            e.ignore()
            return
        e.acceptProposedAction()
        idx = self._index_at_pos(e.position().toPoint())
        self._show_indicator(idx)

    def dragLeaveEvent(self, e):
        self._drop_indicator.hide()

    def dropEvent(self, e: QDropEvent) -> None:
        if not e.mimeData().hasFormat(PALETTE_MIME):
            e.ignore()
            return
        type_id = bytes(e.mimeData().data(PALETTE_MIME)).decode("utf-8")
        idx = self._index_at_pos(e.position().toPoint())
        e.acceptProposedAction()
        self._drop_indicator.hide()
        self.insert_new_block(type_id, idx)

    def _index_at_pos(self, p: QPoint) -> int:
        # Map p (in self coords) to inner coords
        inner_pos = self._inner.mapFrom(self, p)
        for i, w in enumerate(self._widgets):
            top = w.geometry().top()
            mid = top + w.height() / 2
            if inner_pos.y() < mid:
                return i
        return len(self._widgets)

    def _show_indicator(self, idx: int) -> None:
        if not self._inserts:
            return
        idx = max(0, min(len(self._inserts) - 1, idx))
        ib = self._inserts[idx]
        rect = ib.geometry()
        self._drop_indicator.setGeometry(QRect(rect.x() + 12, rect.y() + rect.height() // 2 - 1, rect.width() - 24, 2))
        self._drop_indicator.show()
        self._drop_indicator.raise_()


def _default_data(type_id: str) -> dict:
    """Sensible defaults for newly-inserted blocks."""
    if type_id == "title":
        return {"text": ""}
    if type_id == "authors":
        return {"authors": [{"name": "", "affiliation": "", "email": "", "corresponding": False}]}
    if type_id == "abstract":
        return {"text": "", "keywords": ""}
    if type_id == "heading":
        return {"level": 1, "text": "", "numbered": True}
    if type_id == "paragraph":
        return {"text": ""}
    if type_id == "equation":
        return {"latex": "", "label": ""}
    if type_id == "figure":
        return {"image_path": "", "caption": "", "width_pct": 80}
    if type_id == "table":
        return {"rows": [["", ""], ["", ""]], "caption": ""}
    if type_id == "list":
        return {"items": [""], "ordered": False}
    if type_id == "code":
        return {"language": "python", "code": "", "caption": "", "show_lines": True}
    if type_id == "references":
        return {"style": "ieee", "bibtex": ""}
    if type_id == "pagebreak":
        return {}
    return {}
