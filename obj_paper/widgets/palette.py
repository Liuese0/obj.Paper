"""Left-side block palette (spec §5.2).

Visual reference: `obj.Paper Mockup.html` ─ each group header is rendered as
`[LABEL] ──────────── ▾`, the search bar carries a `⌘K` kbd hint, and items
that have a registered shortcut display it in mono font on the right edge.

- Search field with realtime filter
- STRUCTURE / CONTENT / ACADEMIC groups (header chip + divider + caret)
- TEMPLATES grid (6 presets, 2 columns, current template highlighted)
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
from ..icons import TYPE_TO_ICON, svg_pixmap
from ..templates import TEMPLATES, TEMPLATE_ORDER


PALETTE_MIME = "application/x-objpaper-block"
TEMPLATE_MIME = "application/x-objpaper-template"


# Each group entry: (i18n key for header, [(type_id, optional shortcut hint)])
# The icon for each type comes from `obj_paper.icons.TYPE_TO_ICON` so block
# badges, palette items, and any future status surface stay in sync.
PALETTE_GROUPS: list[tuple[str, list[tuple[str, str | None]]]] = [
    ("group.structure", [
        ("title", None),
        ("authors", None),
        ("abstract", None),
        ("pagebreak", "⌥⏎"),
    ]),
    ("group.content", [
        ("heading", None),
        ("paragraph", None),
        ("list", None),
        ("code", None),
    ]),
    ("group.academic", [
        ("equation", "⌘M"),
        ("figure", None),
        ("table", None),
        ("references", None),
    ]),
]


class _GroupHeader(QWidget):
    """`STRUCTURE ────────── ▾` row at the top of each palette group."""

    def __init__(self, key: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._key = key
        self.setFixedHeight(22)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 8, 6, 4)
        lay.setSpacing(8)

        self.label = QLabel(t(key))
        self.label.setStyleSheet(
            f"color:{T.ACCENT};font-size:10px;font-weight:600;letter-spacing:1.4px;"
        )
        lay.addWidget(self.label)

        rule = QFrame()
        rule.setFrameShape(QFrame.Shape.NoFrame)
        rule.setFixedHeight(1)
        rule.setStyleSheet(f"background:{T.BORDER};")
        rule.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        lay.addWidget(rule, 1)

        caret = QLabel("▾")
        caret.setStyleSheet(f"color:{T.MIST};font-size:9px;")
        lay.addWidget(caret)

        i18n().languageChanged.connect(lambda *_: self.label.setText(t(self._key)))


class PaletteItem(QFrame):
    """Single draggable row inside a palette group."""

    insertRequested = pyqtSignal(str)  # block type id

    def __init__(self, type_id: str, hint: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self._type = type_id
        self._hint = hint
        self._hover = False
        self.setObjectName("paletteItem")
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setFixedHeight(34)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(10)

        # Icon chip: 22×22 BG-tinted rounded square holding a 12×12 SVG glyph
        # rendered through obj_paper.icons.svg_pixmap.
        self.icon = QLabel()
        self.icon.setFixedSize(22, 22)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setStyleSheet(
            f"background:{T.BG};border:1px solid {T.BORDER};border-radius:4px;"
        )
        icon_name = TYPE_TO_ICON.get(type_id, "page")
        self.icon.setPixmap(svg_pixmap(icon_name, size=12, color=T.DUST))

        self.label = QLabel(t(f"block.{type_id}"))
        self.label.setStyleSheet(f"color:{T.INK};font-size:12px;")
        lay.addWidget(self.icon)
        lay.addWidget(self.label, 1)

        if hint:
            self.hint_lbl = QLabel(hint)
            self.hint_lbl.setStyleSheet(
                f"color:{T.MIST};font-size:10px;font-family:'JetBrains Mono',monospace;"
            )
            lay.addWidget(self.hint_lbl)
        else:
            self.hint_lbl = None

        self._press_pos: QPoint | None = None
        self._restyle()
        i18n().languageChanged.connect(self._retranslate)

    def _retranslate(self, _lang: str) -> None:
        self.label.setText(t(f"block.{self._type}"))

    def _restyle(self) -> None:
        if self._hover:
            self.setStyleSheet(
                f"QFrame#paletteItem {{background:{T.SURFACE_2};border-radius:6px;border:1px solid transparent;}}"
            )
        else:
            self.setStyleSheet(
                f"QFrame#paletteItem {{background:transparent;border-radius:6px;border:1px solid transparent;}}"
            )

    def enterEvent(self, e):
        self._hover = True
        self._restyle()

    def leaveEvent(self, e):
        self._hover = False
        self._restyle()

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
        self.set_active(template_id == "general")

    def set_active(self, active: bool) -> None:
        if active:
            self.setStyleSheet(
                f"QPushButton{{background:{T.ACCENT};color:white;border:1px solid {T.ACCENT};"
                f"border-radius:5px;font-weight:500;font-size:11px;letter-spacing:.02em;}}"
                f"QPushButton:hover{{background:{T.ACCENT_HOVER};}}"
            )
        else:
            self.setStyleSheet(
                f"QPushButton{{background:{T.ACCENT_LIGHT};color:{T.ACCENT};border:1px solid transparent;"
                f"border-radius:5px;font-size:11px;letter-spacing:.02em;}}"
                f"QPushButton:hover{{border-color:{T.ACCENT};}}"
            )
        self.clicked.connect(lambda: self.applyRequested.emit(self._tid))


class _SearchField(QFrame):
    """Search bar with leading icon and trailing kbd hint (⌘K)."""

    textChanged = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("paletteSearch")
        self.setFixedHeight(30)
        self.setStyleSheet(
            f"QFrame#paletteSearch{{background:{T.BG};border:1px solid {T.BORDER};border-radius:7px;}}"
            f"QFrame#paletteSearch:focus-within{{border-color:{T.ACCENT};}}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 6, 0)
        lay.setSpacing(8)

        ico = QLabel()
        ico.setFixedSize(13, 13)
        ico.setPixmap(svg_pixmap("search", size=13, color=T.MIST))
        lay.addWidget(ico)

        self.input = QLineEdit()
        self.input.setPlaceholderText(t("palette.search"))
        self.input.setFrame(False)
        self.input.setStyleSheet(
            f"QLineEdit{{background:transparent;border:none;color:{T.INK};font-size:12px;padding:0;}}"
            f"QLineEdit::placeholder{{color:{T.MIST};}}"
        )
        self.input.textChanged.connect(self.textChanged)
        lay.addWidget(self.input, 1)

        self.kbd = QLabel("⌘K")
        self.kbd.setStyleSheet(
            f"background:{T.SURFACE};border:1px solid {T.BORDER};border-radius:3px;"
            f"color:{T.DUST};font-size:10px;font-family:'JetBrains Mono',monospace;"
            f"padding:1px 5px;"
        )
        lay.addWidget(self.kbd)

        i18n().languageChanged.connect(
            lambda *_: self.input.setPlaceholderText(t("palette.search"))
        )


class _FooterTip(QLabel):
    """`Tip · 블록을 캔버스로...` footer with a Mist-colored 'Tip ·' prefix."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setStyleSheet(
            f"QLabel{{color:{T.DUST};font-size:10.5px;padding:10px 14px;"
            f"border-top:1px solid {T.BORDER};background:#FFFFFF;}}"
        )
        self._refresh()
        i18n().languageChanged.connect(lambda *_: self._refresh())

    def _refresh(self) -> None:
        self.setText(
            f"<span style='color:{T.MIST}'>Tip ·</span> "
            f"<span style='color:{T.DUST}'>{t('palette.tip')}</span>"
        )


class Palette(QFrame):
    """The full left palette panel."""

    insertRequested = pyqtSignal(str)
    templateApplyRequested = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("palette")
        self.setStyleSheet(
            f"QFrame#palette {{background:#FFFFFF;border-right:1px solid {T.BORDER};}}"
        )
        self.setFixedWidth(T.PALETTE_WIDTH)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # search
        search_wrap = QWidget()
        sw = QHBoxLayout(search_wrap)
        sw.setContentsMargins(12, 12, 12, 8)
        self.search = _SearchField()
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
        body_lay.setSpacing(2)
        scroll.setWidget(body)

        self._items: list[PaletteItem] = []
        self._group_headers: list[tuple[str, _GroupHeader]] = []
        for group_key, items in PALETTE_GROUPS:
            header = _GroupHeader(group_key)
            body_lay.addWidget(header)
            self._group_headers.append((group_key, header))
            for type_id, hint in items:
                pi = PaletteItem(type_id, hint)
                pi.insertRequested.connect(self.insertRequested)
                self._items.append(pi)
                body_lay.addWidget(pi)
            body_lay.addSpacing(6)

        # templates
        self._tpl_header = _GroupHeader("group.templates")
        body_lay.addWidget(self._tpl_header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        grid.setContentsMargins(2, 4, 2, 2)
        self._tpl_buttons: list[TemplateButton] = []
        for idx, tid in enumerate(TEMPLATE_ORDER):
            btn = TemplateButton(tid)
            btn.applyRequested.connect(self.templateApplyRequested)
            grid.addWidget(btn, idx // 2, idx % 2)
            self._tpl_buttons.append(btn)
        body_lay.addLayout(grid)
        body_lay.addStretch(1)

        # footer hint
        outer.addWidget(_FooterTip())

    def _filter(self, text: str) -> None:
        text = text.strip().lower()
        for it in self._items:
            visible = True
            if text:
                visible = text in it.label.text().lower() or text in it._type.lower()
            it.setVisible(visible)

    def set_active_template(self, template_id: str) -> None:
        """Highlight the palette template chip that matches the current document."""
        for btn in self._tpl_buttons:
            btn.set_active(btn._tid == template_id)
