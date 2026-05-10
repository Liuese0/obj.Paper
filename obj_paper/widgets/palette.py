"""Left-side block palette (spec §5.2).

- Search field with realtime filter
- STRUCTURE / CONTENT / ACADEMIC groups
- TEMPLATES grid (6 presets)
- Drag source (custom mime) and double-click signal for insertion
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QMimeData, QPoint, QSize, pyqtSignal
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QGridLayout,
)

from .. import theme as T
from ..i18n import t, i18n
from ..templates import TEMPLATES, TEMPLATE_ORDER


PALETTE_MIME = "application/x-objpaper-block"
TEMPLATE_MIME = "application/x-objpaper-template"


PALETTE_GROUPS = [
    ("group.structure", [
        ("title", "𝐀"),
        ("authors", "👤"),
        ("abstract", "¶"),
        ("pagebreak", "—"),
    ]),
    ("group.content", [
        ("heading", "H"),
        ("paragraph", "¶"),
        ("list", "≡"),
        ("code", "{ }"),
    ]),
    ("group.academic", [
        ("equation", "Σ"),
        ("figure", "▣"),
        ("table", "⊞"),
        ("references", "§"),
    ]),
]


class PaletteItem(QFrame):
    """Single draggable row inside a palette group."""

    insertRequested = pyqtSignal(str)  # block type id

    def __init__(self, type_id: str, glyph: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._type = type_id
        self._glyph = glyph
        self.setObjectName("paletteItem")
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setMinimumHeight(30)
        self.setProperty("active", False)
        self._restyle()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(10)

        self.icon = QLabel(glyph)
        self.icon.setFixedSize(22, 22)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setStyleSheet(
            f"background:{T.BG};border:1px solid {T.BORDER};border-radius:4px;color:{T.DUST};"
            f"font-size:12px;font-family:'JetBrains Mono',monospace;"
        )
        self.label = QLabel(t(f"block.{type_id}"))
        self.label.setStyleSheet(f"color:{T.INK};font-size:12px;")
        lay.addWidget(self.icon)
        lay.addWidget(self.label, 1)

        self._press_pos: QPoint | None = None
        i18n().languageChanged.connect(self._retranslate)

    def _retranslate(self, _lang: str) -> None:
        self.label.setText(t(f"block.{self._type}"))

    def _restyle(self):
        self.setStyleSheet(
            f"QFrame#paletteItem {{background:transparent;border-radius:6px;border:1px solid transparent;}}"
            f"QFrame#paletteItem:hover {{background:{T.SURFACE_2};}}"
        )

    # drag source
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press_pos = e.pos()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._press_pos is None or not (e.buttons() & Qt.MouseButton.LeftButton):
            return
        if (e.pos() - self._press_pos).manhattanLength() < 8:
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(PALETTE_MIME, self._type.encode("utf-8"))
        drag.setMimeData(mime)
        drag.setPixmap(self._make_drag_pix())
        drag.setHotSpot(QPoint(20, 12))
        drag.exec(Qt.DropAction.CopyAction)

    def mouseDoubleClickEvent(self, e):
        self.insertRequested.emit(self._type)

    def _make_drag_pix(self) -> QPixmap:
        pm = QPixmap(220, 36)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(Qt.GlobalColor.white)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 220, 36, 6, 6)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(46, 23, self.label.text())
        painter.end()
        return pm


class TemplateButton(QPushButton):
    """Apply-template chip in the palette footer."""

    applyRequested = pyqtSignal(str)

    def __init__(self, template_id: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._tid = template_id
        info = TEMPLATES[template_id]
        self.setText(info["name"].split()[0])
        self.setFixedHeight(26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        is_default = template_id == "general"
        if is_default:
            self.setStyleSheet(
                f"QPushButton{{background:{T.ACCENT};color:white;border:1px solid {T.ACCENT};"
                f"border-radius:5px;font-weight:500;font-size:11px;}}"
                f"QPushButton:hover{{background:{T.ACCENT_HOVER};}}"
            )
        else:
            self.setStyleSheet(
                f"QPushButton{{background:{T.ACCENT_LIGHT};color:{T.ACCENT};border:1px solid transparent;"
                f"border-radius:5px;font-size:11px;}}"
                f"QPushButton:hover{{border-color:{T.ACCENT};}}"
            )
        self.clicked.connect(lambda: self.applyRequested.emit(self._tid))


class Palette(QFrame):
    """The full left palette panel."""

    insertRequested = pyqtSignal(str)
    templateApplyRequested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("palette")
        self.setStyleSheet(
            f"QFrame#palette {{background:{T.SURFACE};border-right:1px solid {T.BORDER};}}"
        )
        self.setFixedWidth(T.PALETTE_WIDTH)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # search
        search_wrap = QWidget()
        sw = QHBoxLayout(search_wrap)
        sw.setContentsMargins(12, 12, 12, 8)
        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍 " + t("palette.search"))
        self.search.textChanged.connect(self._filter)
        sw.addWidget(self.search)
        outer.addWidget(search_wrap)

        # scroll
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll, 1)
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(8, 4, 8, 8)
        body_lay.setSpacing(10)
        scroll.setWidget(body)

        self._items: list[PaletteItem] = []
        self._group_widgets: list[tuple[QLabel, list[PaletteItem]]] = []
        for group_key, items in PALETTE_GROUPS:
            header = QLabel(t(group_key))
            header.setObjectName("panelHeader")
            header.setStyleSheet(
                f"QLabel#panelHeader {{color:{T.ACCENT};font-size:10px;font-weight:600;letter-spacing:1.4px;padding:6px 6px 2px 6px;}}"
            )
            body_lay.addWidget(header)
            group_items: list[PaletteItem] = []
            for type_id, glyph in items:
                pi = PaletteItem(type_id, glyph)
                pi.insertRequested.connect(self.insertRequested)
                self._items.append(pi)
                group_items.append(pi)
                body_lay.addWidget(pi)
            self._group_widgets.append((header, group_items))

        # templates
        tpl_header = QLabel(t("group.templates"))
        tpl_header.setObjectName("panelHeader")
        tpl_header.setStyleSheet(
            f"QLabel#panelHeader {{color:{T.ACCENT};font-size:10px;font-weight:600;letter-spacing:1.4px;padding:10px 6px 4px 6px;}}"
        )
        body_lay.addWidget(tpl_header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        grid.setContentsMargins(2, 2, 2, 2)
        for idx, tid in enumerate(TEMPLATE_ORDER):
            btn = TemplateButton(tid)
            btn.applyRequested.connect(self.templateApplyRequested)
            grid.addWidget(btn, idx // 2, idx % 2)
        body_lay.addLayout(grid)
        body_lay.addStretch(1)

        # footer hint
        hint = QLabel(t("palette.tip"))
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        hint.setStyleSheet(
            f"QLabel#muted {{color:{T.DUST};font-size:10.5px;padding:10px 14px;border-top:1px solid {T.BORDER};"
            f"background:{T.SURFACE};}}"
        )
        outer.addWidget(hint)

        self._tpl_header = tpl_header
        i18n().languageChanged.connect(self._retranslate)
        self._retranslate(i18n().lang)

    def _retranslate(self, _lang):
        self.search.setPlaceholderText("🔍 " + t("palette.search"))
        for header, _items in self._group_widgets:
            # find which key by current text — simpler: store keys
            pass
        self._tpl_header.setText(t("group.templates"))
        # Group headers carry their own keys
        keys = [k for k, _ in PALETTE_GROUPS]
        for (header, _), key in zip(self._group_widgets, keys):
            header.setText(t(key))

    def _filter(self, text: str) -> None:
        text = text.strip().lower()
        for it in self._items:
            visible = True
            if text:
                visible = text in it.label.text().lower() or text in it._type.lower()
            it.setVisible(visible)
