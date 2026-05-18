"""Block widget implementations for all 12 block types.

Each `Block*Widget` extends `BlockChrome` and binds itself to a `BlockData`.
Widgets emit `BlockChrome.changed` when content mutates so the canvas can sync
the `Document`.

Spec §6.2 dictates the field set per type. Visuals follow `obj.Paper Mockup.html`.

The registry exposes `make_widget(BlockData)` for the canvas and a public
`@register_block(type_id)` decorator (spec §17.2 extensibility hook).
"""

from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QAction, QFont, QFontMetrics, QPixmap, QImage
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QButtonGroup,
    QRadioButton,
    QHeaderView,
)

from .. import theme as T
from ..document import BlockData
from ..i18n import t, i18n
from .block_chrome import BlockChrome
from .inline_toolbar import get_inline_toolbar


# ---------- registry ----------
_REGISTRY: dict[str, type[BlockChrome]] = {}


def register_block(type_id: str):
    def deco(cls: type[BlockChrome]):
        _REGISTRY[type_id] = cls
        return cls

    return deco


def make_widget(block: BlockData, parent: QWidget | None = None) -> BlockChrome:
    cls = _REGISTRY.get(block.type)
    if cls is None:
        cls = ParagraphBlockWidget  # safe fallback
    return cls(block, parent)


def registered_types() -> list[str]:
    return list(_REGISTRY.keys())


# ---------- helpers ----------
class AutoTextEdit(QTextEdit):
    """A QTextEdit that grows to fit its content height — never shows its
    own scrollbar. Adjusts on every content change AND every resize, so the
    height stays correct when the canvas pane is resized."""

    def __init__(self, min_lines: int = 1, parent: QWidget | None = None):
        super().__init__(parent)
        self._min_lines = max(1, min_lines)
        self.setAcceptRichText(False)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().contentsChanged.connect(self._adjust)
        QTimer.singleShot(0, self._adjust)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._adjust()

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self._adjust)

    def _adjust(self) -> None:
        # The QTimer.singleShot / document.contentsChanged hookups can fire
        # after this widget has been deleteLater()'d (its Python object is
        # still alive, but the underlying QTextEdit is gone). Touching the
        # destroyed C++ object raises RuntimeError on Windows — swallow it.
        try:
            doc = self.document()
            w = self.viewport().width()
            if w > 0:
                doc.setTextWidth(w)
            line_h = QFontMetrics(self.font()).lineSpacing()
            content_h = int(doc.size().height())
            new_h = max(content_h + 8, line_h * self._min_lines + 8)
            if new_h != self.height():
                self.setFixedHeight(new_h)
                self.updateGeometry()
        except RuntimeError:
            return


def _make_serif_textedit(text: str, placeholder: str, font_size: int = 14, min_lines: int = 1) -> AutoTextEdit:
    edit = AutoTextEdit(min_lines=min_lines)
    edit.setPlaceholderText(placeholder)
    edit.setPlainText(text)
    f = QFont("Times New Roman")
    f.setPointSize(font_size - 4 if font_size > 6 else font_size)
    f.setStyleHint(QFont.StyleHint.Serif)
    edit.setFont(f)
    return edit


def _attach_inline_toolbar(edit: QTextEdit) -> None:
    tb = get_inline_toolbar()
    edit.installEventFilter(_FocusFilter(edit))
    edit.selectionChanged.connect(lambda: tb.attach(edit))


from PyQt6.QtCore import QObject, QEvent


class _FocusFilter(QObject):
    def __init__(self, edit: QTextEdit):
        super().__init__(edit)
        self._edit = edit

    def eventFilter(self, obj, ev):
        try:
            if ev.type() == QEvent.Type.FocusIn:
                get_inline_toolbar().attach(self._edit)
            elif ev.type() == QEvent.Type.FocusOut:
                # If the toolbar singleton has been destroyed by now (rare,
                # during app shutdown) we just swallow the failure.
                QTimer.singleShot(120, _safe_hide_inline_toolbar)
        except RuntimeError:
            pass
        return False


def _safe_hide_inline_toolbar() -> None:
    try:
        get_inline_toolbar().hide()
    except RuntimeError:
        pass


# ---------- TITLE ----------
@register_block("title")
class TitleBlockWidget(BlockChrome):
    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(block, parent)
        self.edit = _make_serif_textedit(
            block.data.get("text", ""),
            t("placeholder.title"),
            font_size=22,
            min_lines=1,
        )
        f = self.edit.font()
        f.setPointSize(20)
        f.setBold(True)
        self.edit.setFont(f)
        self.edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.edit.setStyleSheet(f"color:{T.INK};text-align:center;")
        _attach_inline_toolbar(self.edit)
        self.add_widget(self.edit)
        self.edit.textChanged.connect(self._on_change)

    def _on_change(self):
        self.block.data["text"] = self.edit.toPlainText()
        self.changed.emit()


# ---------- AUTHORS ----------
@register_block("authors")
class AuthorsBlockWidget(BlockChrome):
    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(block, parent)
        if "authors" not in block.data or not block.data["authors"]:
            block.data["authors"] = [{"name": "", "affiliation": "", "email": "", "corresponding": False}]
        self._rows_layout = QVBoxLayout()
        self._rows_layout.setSpacing(6)
        self.add_layout(self._rows_layout)
        self._add_button = QPushButton(t("label.add_author"))
        self._add_button.setObjectName("ghost")
        self._add_button.setStyleSheet(
            f"QPushButton#ghost {{color:{T.ACCENT};background:transparent;border:none;font-size:11px;text-align:left;}}"
            f"QPushButton#ghost:hover {{color:{T.ACCENT_HOVER};}}"
        )
        self._add_button.clicked.connect(self._add_author)
        self.add_widget(self._add_button)
        self._rebuild_rows()

    def _rebuild_rows(self):
        # clear
        while self._rows_layout.count():
            it = self._rows_layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        for idx, author in enumerate(self.block.data["authors"]):
            row = QWidget()
            r = QHBoxLayout(row)
            r.setContentsMargins(0, 0, 0, 0)
            r.setSpacing(6)
            name = QLineEdit(author.get("name", ""))
            name.setPlaceholderText(t("placeholder.author_name"))
            aff = QLineEdit(author.get("affiliation", ""))
            aff.setPlaceholderText(t("placeholder.author_affiliation"))
            email = QLineEdit(author.get("email", ""))
            email.setPlaceholderText(t("placeholder.author_email"))
            cb = QCheckBox("†")
            cb.setToolTip(t("label.corresponding"))
            cb.setChecked(bool(author.get("corresponding")))
            del_btn = QPushButton("✕")
            del_btn.setObjectName("blockCtrl")
            del_btn.setFixedSize(22, 22)
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            def bind(idx=idx, name=name, aff=aff, email=email, cb=cb):
                def update():
                    self.block.data["authors"][idx] = {
                        "name": name.text(),
                        "affiliation": aff.text(),
                        "email": email.text(),
                        "corresponding": cb.isChecked(),
                    }
                    self.changed.emit()

                name.textChanged.connect(update)
                aff.textChanged.connect(update)
                email.textChanged.connect(update)
                cb.stateChanged.connect(update)

            bind()

            del_btn.clicked.connect(lambda checked=False, i=idx: self._remove_author(i))

            r.addWidget(name, 2)
            r.addWidget(aff, 3)
            r.addWidget(email, 2)
            r.addWidget(cb, 0)
            r.addWidget(del_btn, 0)
            self._rows_layout.addWidget(row)

    def _add_author(self):
        self.block.data["authors"].append({"name": "", "affiliation": "", "email": "", "corresponding": False})
        self._rebuild_rows()
        self.changed.emit()

    def _remove_author(self, idx: int):
        if 0 <= idx < len(self.block.data["authors"]) and len(self.block.data["authors"]) > 1:
            del self.block.data["authors"][idx]
            self._rebuild_rows()
            self.changed.emit()


# ---------- ABSTRACT ----------
@register_block("abstract")
class AbstractBlockWidget(BlockChrome):
    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(block, parent)
        kw_row = QHBoxLayout()
        kw_label = QLabel("KEYWORDS")
        kw_label.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace;font-size:9.5px;font-weight:600;"
            f"letter-spacing:1.4px;color:{T.DUST};"
        )
        self.kw_edit = QLineEdit(block.data.get("keywords", ""))
        self.kw_edit.setPlaceholderText(t("placeholder.keywords"))
        self.kw_edit.textChanged.connect(self._on_kw)
        kw_row.addWidget(kw_label)
        kw_row.addWidget(self.kw_edit, 1)
        self.add_layout(kw_row)

        self.body = _make_serif_textedit(
            block.data.get("text", ""), t("placeholder.abstract"), font_size=14, min_lines=4
        )
        _attach_inline_toolbar(self.body)
        self.add_widget(self.body)
        self.body.textChanged.connect(self._on_body)

        # word count footer
        self.foot = QLabel("")
        self.foot.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace;font-size:10.5px;color:{T.DUST};"
        )
        self.add_widget(self.foot)
        self._refresh_count()

    def _on_kw(self):
        self.block.data["keywords"] = self.kw_edit.text()
        self.changed.emit()

    def _on_body(self):
        self.block.data["text"] = self.body.toPlainText()
        self._refresh_count()
        self.changed.emit()

    def _refresh_count(self):
        words = len([w for w in self.body.toPlainText().split() if w])
        rec = "● within IEEE recommendation" if words <= 250 else "⚠ above 250 words"
        color = T.SUCCESS if words <= 250 else T.ERROR
        self.foot.setText(f"{words} / 250 words")
        self.foot.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace;font-size:10.5px;color:{color};"
        )


# ---------- HEADING ----------
@register_block("heading")
class HeadingBlockWidget(BlockChrome):
    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(block, parent)
        block.data.setdefault("level", 1)
        block.data.setdefault("numbered", True)

        row = QHBoxLayout()
        self.level_combo = QComboBox()
        self.level_combo.addItems([t("label.h1"), t("label.h2"), t("label.h3")])
        self.level_combo.setCurrentIndex(int(block.data["level"]) - 1)
        self.level_combo.setFixedWidth(64)
        self.level_combo.currentIndexChanged.connect(self._on_level)
        self.numbered_cb = QCheckBox("№")
        self.numbered_cb.setChecked(bool(block.data["numbered"]))
        self.numbered_cb.stateChanged.connect(self._on_num)

        row.addWidget(self.level_combo)
        row.addWidget(self.numbered_cb)
        row.addStretch(1)
        self.add_layout(row)

        self.edit = _make_serif_textedit(
            block.data.get("text", ""), t("placeholder.heading"), font_size=16, min_lines=1
        )
        f = self.edit.font()
        f.setPointSize(15)
        f.setBold(True)
        self.edit.setFont(f)
        _attach_inline_toolbar(self.edit)
        self.add_widget(self.edit)
        self.edit.textChanged.connect(self._on_text)

    def _on_level(self, idx: int):
        self.block.data["level"] = idx + 1
        self.refresh_badge()
        self.changed.emit()

    def _on_num(self, _state):
        self.block.data["numbered"] = self.numbered_cb.isChecked()
        self.changed.emit()

    def _on_text(self):
        self.block.data["text"] = self.edit.toPlainText()
        self.changed.emit()


# ---------- PARAGRAPH ----------
@register_block("paragraph")
class ParagraphBlockWidget(BlockChrome):
    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(block, parent)
        self.edit = _make_serif_textedit(
            block.data.get("text", ""),
            t("placeholder.paragraph"),
            font_size=14,
            min_lines=2,
        )
        _attach_inline_toolbar(self.edit)
        self.add_widget(self.edit)
        self.edit.textChanged.connect(self._on_text)

    def _on_text(self):
        self.block.data["text"] = self.edit.toPlainText()
        self.changed.emit()


# ---------- EQUATION ----------
class _ScaledFormulaLabel(QLabel):
    """A QLabel that holds a source pixmap and rescales it to fit the
    available width on every resize. Never lets the rendered formula spill
    out of its parent block."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._source: QPixmap | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_source(self, pm: QPixmap) -> None:
        self._source = pm
        self._refit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._refit()

    def _refit(self) -> None:
        if self._source is None or self._source.isNull():
            return
        avail_w = max(40, self.width() - 8)
        src = self._source
        if src.width() <= avail_w:
            scaled = src
        else:
            scaled = src.scaledToWidth(avail_w, Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(scaled)
        # Lock the label's height to the rendered image so the parent's
        # autosizing layout knows exactly how much room to reserve.
        self.setFixedHeight(scaled.height() + 8)


@register_block("equation")
class EquationBlockWidget(BlockChrome):
    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(block, parent)
        block.data.setdefault("latex", "")
        block.data.setdefault("label", "")
        block.data.setdefault("size", 18)  # rendered font size in points

        row = QHBoxLayout()
        label_lbl = QLabel(t("label.eq_label"))
        label_lbl.setStyleSheet(f"font-size:11px;color:{T.DUST};")
        self.label_edit = QLineEdit(block.data["label"])
        self.label_edit.setPlaceholderText(t("placeholder.equation_label"))
        self.label_edit.setFixedWidth(160)
        size_lbl = QLabel("Size")
        size_lbl.setStyleSheet(f"font-size:11px;color:{T.DUST};")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(10, 36)
        self.size_spin.setSuffix(" pt")
        self.size_spin.setValue(int(block.data["size"]))
        row.addWidget(label_lbl)
        row.addWidget(self.label_edit)
        row.addStretch(1)
        row.addWidget(size_lbl)
        row.addWidget(self.size_spin)
        self.add_layout(row)

        self.src = QPlainTextEdit(block.data["latex"])
        self.src.setPlaceholderText(t("placeholder.equation"))
        self.src.setFixedHeight(60)
        self.src.setStyleSheet(
            f"QPlainTextEdit{{font-family:'JetBrains Mono',monospace;font-size:12px;"
            f"background:#FBF9F2;border:1px solid {T.BORDER};border-radius:4px;padding:6px;}}"
        )
        self.add_widget(self.src)

        self.preview_lbl = _ScaledFormulaLabel()
        self.add_widget(self.preview_lbl)

        self.src.textChanged.connect(self._on_src)
        self.label_edit.textChanged.connect(self._on_label)
        self.size_spin.valueChanged.connect(self._on_size)
        self._render_preview()

    def _on_src(self):
        self.block.data["latex"] = self.src.toPlainText()
        self._render_preview()
        self.changed.emit()

    def _on_label(self):
        self.block.data["label"] = self.label_edit.text()
        self.changed.emit()

    def _on_size(self, v: int):
        self.block.data["size"] = v
        self._render_preview()
        self.changed.emit()

    def _render_preview(self):
        from .. import latex as latex_mod

        try:
            png = latex_mod.render_latex_png(
                self.src.toPlainText() or "?",
                dpi=180,
                fontsize=int(self.block.data.get("size", 18)),
            )
            img = QImage.fromData(png, "PNG")
            self.preview_lbl.set_source(QPixmap.fromImage(img))
        except Exception as e:
            self.preview_lbl.setText(f"⚠ {e}")


# ---------- FIGURE ----------
@register_block("figure")
class FigureBlockWidget(BlockChrome):
    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(block, parent)
        block.data.setdefault("image_path", "")
        block.data.setdefault("caption", "")
        block.data.setdefault("width_pct", 80)

        row = QHBoxLayout()
        self.choose_btn = QPushButton(t("label.choose_image"))
        self.choose_btn.clicked.connect(self._pick)
        self.path_lbl = QLabel(block.data["image_path"] or "—")
        self.path_lbl.setStyleSheet(f"color:{T.DUST};font-family:'JetBrains Mono',monospace;font-size:11px;")
        self.path_lbl.setWordWrap(True)
        row.addWidget(self.choose_btn)
        row.addWidget(self.path_lbl, 1)
        self.add_layout(row)

        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(120)
        self.preview.setStyleSheet(
            f"background:repeating-linear-gradient(45deg,{T.SURFACE_2} 0 8px,{T.BG} 8px 16px);"
            f"border:1px dashed {T.BORDER};border-radius:4px;color:{T.DUST};"
        )
        self.add_widget(self.preview)

        width_row = QHBoxLayout()
        wlbl = QLabel("Width %")
        wlbl.setStyleSheet(f"color:{T.DUST};font-size:11px;")
        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 100)
        self.width_spin.setValue(int(block.data["width_pct"]))
        self.width_spin.valueChanged.connect(self._on_width)
        width_row.addWidget(wlbl)
        width_row.addWidget(self.width_spin)
        width_row.addStretch(1)
        self.add_layout(width_row)

        self.caption = QLineEdit(block.data["caption"])
        self.caption.setPlaceholderText(t("placeholder.figure_caption"))
        self.caption.textChanged.connect(self._on_caption)
        self.add_widget(self.caption)

        self._refresh_preview()

    def _pick(self):
        path, _ = QFileDialog.getOpenFileName(self, t("label.choose_image"), "", "Images (*.png *.jpg *.jpeg *.svg *.pdf)")
        if path:
            self.block.data["image_path"] = path
            self.path_lbl.setText(path)
            self._refresh_preview()
            self.changed.emit()

    def _on_caption(self):
        self.block.data["caption"] = self.caption.text()
        self.changed.emit()

    def _on_width(self, v: int):
        self.block.data["width_pct"] = v
        self.changed.emit()

    def _refresh_preview(self):
        path = self.block.data.get("image_path", "")
        if not path:
            self.preview.setText("(no image)")
            self.preview.setPixmap(QPixmap())
            return
        pm = QPixmap(path)
        if pm.isNull():
            self.preview.setText(f"⚠ cannot load: {path}")
            return
        scaled = pm.scaledToWidth(320, Qt.TransformationMode.SmoothTransformation)
        self.preview.setPixmap(scaled)


# ---------- TABLE ----------
@register_block("table")
class TableBlockWidget(BlockChrome):
    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(block, parent)
        if "rows" not in block.data:
            block.data["rows"] = [["Header A", "Header B"], ["", ""]]
        block.data.setdefault("caption", "")

        rows = block.data["rows"]
        self.table = QTableWidget(len(rows), len(rows[0]) if rows else 2)
        for r, row in enumerate(rows):
            for c, cell in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(str(cell)))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(
            f"QTableWidget{{background:{T.SURFACE};border:1px solid {T.BORDER};gridline-color:{T.BORDER};}}"
            f"QHeaderView::section{{background:{T.SURFACE_2};border:none;border-right:1px solid {T.BORDER};"
            f"border-bottom:1px solid {T.BORDER};padding:4px 6px;color:{T.INK};}}"
        )
        self.table.setMinimumHeight(140)
        self.table.itemChanged.connect(self._on_item)
        self.add_widget(self.table)

        ctrl_row = QHBoxLayout()
        add_row = QPushButton(t("label.add_row"))
        add_col = QPushButton(t("label.add_col"))
        add_row.clicked.connect(self._add_row)
        add_col.clicked.connect(self._add_col)
        ctrl_row.addWidget(add_row)
        ctrl_row.addWidget(add_col)
        ctrl_row.addStretch(1)
        self.add_layout(ctrl_row)

        self.caption = QLineEdit(block.data["caption"])
        self.caption.setPlaceholderText(t("placeholder.table_caption"))
        self.caption.textChanged.connect(self._on_caption)
        self.add_widget(self.caption)

    def _on_item(self, _item):
        self.block.data["rows"] = [
            [(self.table.item(r, c).text() if self.table.item(r, c) else "")
             for c in range(self.table.columnCount())]
            for r in range(self.table.rowCount())
        ]
        self.changed.emit()

    def _add_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        for c in range(self.table.columnCount()):
            self.table.setItem(r, c, QTableWidgetItem(""))
        self._on_item(None)

    def _add_col(self):
        c = self.table.columnCount()
        self.table.insertColumn(c)
        for r in range(self.table.rowCount()):
            self.table.setItem(r, c, QTableWidgetItem(""))
        self._on_item(None)

    def _on_caption(self):
        self.block.data["caption"] = self.caption.text()
        self.changed.emit()


# ---------- LIST ----------
@register_block("list")
class ListBlockWidget(BlockChrome):
    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(block, parent)
        block.data.setdefault("ordered", False)
        block.data.setdefault("items", ["First item"])

        ctrl = QHBoxLayout()
        self.bg = QButtonGroup(self)
        self.rb_unordered = QRadioButton(t("label.unordered"))
        self.rb_ordered = QRadioButton(t("label.ordered"))
        self.bg.addButton(self.rb_unordered)
        self.bg.addButton(self.rb_ordered)
        if block.data["ordered"]:
            self.rb_ordered.setChecked(True)
        else:
            self.rb_unordered.setChecked(True)
        self.rb_unordered.toggled.connect(self._on_kind)
        self.rb_ordered.toggled.connect(self._on_kind)
        ctrl.addWidget(self.rb_unordered)
        ctrl.addWidget(self.rb_ordered)
        ctrl.addStretch(1)
        self.add_layout(ctrl)

        self.editor = QPlainTextEdit("\n".join(block.data["items"]))
        self.editor.setPlaceholderText("- one item per line")
        self.editor.setFixedHeight(120)
        f = QFont("Times New Roman")
        f.setPointSize(11)
        self.editor.setFont(f)
        self.editor.textChanged.connect(self._on_items)
        self.add_widget(self.editor)

    def _on_kind(self):
        self.block.data["ordered"] = self.rb_ordered.isChecked()
        self.changed.emit()

    def _on_items(self):
        self.block.data["items"] = [
            ln for ln in self.editor.toPlainText().splitlines() if ln.strip()
        ]
        self.changed.emit()


# ---------- CODE ----------
_CODE_LANGS = ["python", "c", "cpp", "java", "javascript", "typescript", "rust", "go",
               "matlab", "ruby", "shell", "sql", "html", "css", "json", "yaml", "text"]


@register_block("code")
class CodeBlockWidget(BlockChrome):
    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(block, parent)
        block.data.setdefault("language", "python")
        block.data.setdefault("code", "")
        block.data.setdefault("show_lines", True)
        block.data.setdefault("caption", "")

        ctrl = QHBoxLayout()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(_CODE_LANGS)
        idx = _CODE_LANGS.index(block.data["language"]) if block.data["language"] in _CODE_LANGS else 0
        self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._on_lang)
        self.lines_cb = QCheckBox("Line numbers")
        self.lines_cb.setChecked(bool(block.data["show_lines"]))
        self.lines_cb.stateChanged.connect(self._on_lines)
        ctrl.addWidget(self.lang_combo)
        ctrl.addWidget(self.lines_cb)
        ctrl.addStretch(1)
        self.add_layout(ctrl)

        self.editor = QPlainTextEdit(block.data["code"])
        self.editor.setPlaceholderText(t("placeholder.code"))
        self.editor.setMinimumHeight(140)
        f = QFont("JetBrains Mono")
        f.setStyleHint(QFont.StyleHint.Monospace)
        f.setPointSize(11)
        self.editor.setFont(f)
        self.editor.setStyleSheet(
            f"QPlainTextEdit{{background:#FBF9F2;border:1px solid {T.BORDER};border-radius:4px;padding:8px;}}"
        )
        self.editor.textChanged.connect(self._on_code)
        self.add_widget(self.editor)

        self.caption = QLineEdit(block.data["caption"])
        self.caption.setPlaceholderText(t("placeholder.figure_caption"))
        self.caption.textChanged.connect(self._on_caption)
        self.add_widget(self.caption)

    def _on_lang(self, idx: int):
        self.block.data["language"] = self.lang_combo.itemText(idx)
        self.refresh_badge()
        self.changed.emit()

    def _on_lines(self, _s):
        self.block.data["show_lines"] = self.lines_cb.isChecked()
        self.changed.emit()

    def _on_code(self):
        self.block.data["code"] = self.editor.toPlainText()
        self.changed.emit()

    def _on_caption(self):
        self.block.data["caption"] = self.caption.text()
        self.changed.emit()


# ---------- REFERENCES ----------
_REF_STYLES = ["ieee", "apa", "mla", "chicago", "vancouver"]


@register_block("references")
class ReferencesBlockWidget(BlockChrome):
    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(block, parent)
        block.data.setdefault("style", "ieee")
        block.data.setdefault("bibtex", "")

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel(t("label.references_style")))
        self.style_combo = QComboBox()
        self.style_combo.addItems([s.upper() for s in _REF_STYLES])
        idx = _REF_STYLES.index(block.data["style"]) if block.data["style"] in _REF_STYLES else 0
        self.style_combo.setCurrentIndex(idx)
        self.style_combo.currentIndexChanged.connect(self._on_style)
        ctrl.addWidget(self.style_combo)
        ctrl.addStretch(1)
        self.add_layout(ctrl)

        self.editor = QPlainTextEdit(block.data["bibtex"])
        self.editor.setPlaceholderText(t("placeholder.references"))
        self.editor.setMinimumHeight(140)
        f = QFont("JetBrains Mono")
        f.setStyleHint(QFont.StyleHint.Monospace)
        f.setPointSize(11)
        self.editor.setFont(f)
        self.editor.textChanged.connect(self._on_bib)
        self.add_widget(self.editor)

    def _on_style(self, idx: int):
        self.block.data["style"] = _REF_STYLES[idx]
        self.changed.emit()

    def _on_bib(self):
        self.block.data["bibtex"] = self.editor.toPlainText()
        self.changed.emit()


# ---------- PAGE BREAK ----------
@register_block("pagebreak")
class PagebreakBlockWidget(BlockChrome):
    def __init__(self, block: BlockData, parent: QWidget | None = None):
        super().__init__(block, parent)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color:{T.MIST};border:1px dashed {T.MIST};")
        line.setFixedHeight(1)
        lbl = QLabel("PAGE BREAK")
        lbl.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.2em;"
            f"color:{T.MIST};text-align:center;"
        )
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.add_widget(line)
        self.add_widget(lbl)
