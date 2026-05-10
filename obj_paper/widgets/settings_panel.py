"""Slide-in Document Settings panel (spec §8).

Lives as an overlay on the right edge of the canvas. Translates fields
two-way to/from `DocumentSettings`. Template buttons trigger an "overwrite
current settings?" confirmation (spec §9).
"""

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve,
    QObject,
    QPropertyAnimation,
    QRect,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .. import theme as T
from ..document import Document, DocumentSettings
from ..i18n import t, i18n
from ..templates import TEMPLATE_ORDER, TEMPLATES, make_settings, template_name


class _SectionHeader(QLabel):
    def __init__(self, key: str):
        super().__init__("")
        self._key = key
        self.setStyleSheet(
            f"color:{T.ACCENT};font-size:10px;font-weight:600;letter-spacing:1.4px;padding:8px 0 4px 0;"
        )
        self.refresh()
        i18n().languageChanged.connect(lambda *_: self.refresh())

    def refresh(self) -> None:
        self.setText(t(self._key))


class SettingsPanel(QFrame):
    """Modal-ish overlay anchored to the right edge of `host`."""

    closed = pyqtSignal()
    settingsChanged = pyqtSignal()

    PANEL_WIDTH = 320

    def __init__(self, document: Document, host: QWidget):
        super().__init__(host)
        self._doc = document
        self._host = host
        self.setObjectName("settingsPanel")
        self.setStyleSheet(
            f"QFrame#settingsPanel {{background:{T.SURFACE};border-left:1px solid {T.BORDER};"
            f"border-top:1px solid {T.BORDER};border-bottom:1px solid {T.BORDER};}}"
        )
        self.hide()
        self._is_open = False
        self._suppress = False

        # outer
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        head = QFrame()
        head.setStyleSheet(f"background:{T.SURFACE};border-bottom:1px solid {T.BORDER};")
        h = QHBoxLayout(head)
        h.setContentsMargins(16, 10, 12, 10)
        title = QLabel("📄 " + t("settings.title"))
        title.setStyleSheet(f"font-size:13px;font-weight:600;color:{T.INK};")
        self._title_lbl = title
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;color:{T.DUST};font-size:14px;}}"
            f"QPushButton:hover{{color:{T.INK};}}"
        )
        close_btn.clicked.connect(self.close_panel)
        h.addWidget(title)
        h.addStretch(1)
        h.addWidget(close_btn)
        outer.addWidget(head)

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll, 1)
        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(16, 8, 16, 16)
        body_lay.setSpacing(8)
        scroll.setWidget(body)

        # Build sections
        body_lay.addWidget(_SectionHeader("settings.typography"))
        body_lay.addLayout(self._build_typography())

        body_lay.addWidget(_SectionHeader("settings.layout"))
        body_lay.addLayout(self._build_layout_section())

        body_lay.addWidget(_SectionHeader("settings.numbering"))
        body_lay.addLayout(self._build_numbering())

        body_lay.addWidget(_SectionHeader("settings.template"))
        body_lay.addLayout(self._build_template())
        body_lay.addStretch(1)

        i18n().languageChanged.connect(self._retranslate)
        self._refresh_from_doc()

    # ---------- show/hide ----------
    def open_panel(self) -> None:
        self._reposition()
        self.show()
        self.raise_()
        self._animate(open_=True)
        self._is_open = True

    def close_panel(self) -> None:
        if not self._is_open:
            return
        self._animate(open_=False)
        self._is_open = False
        self.closed.emit()

    def is_open(self) -> bool:
        return self._is_open

    def reposition(self) -> None:
        if self._is_open:
            self._reposition()

    def _reposition(self) -> None:
        host = self._host
        w = self.PANEL_WIDTH
        h = host.height()
        self.setGeometry(host.width() - w, 0, w, h)

    def _animate(self, open_: bool) -> None:
        host = self._host
        w = self.PANEL_WIDTH
        h = host.height()
        end_x = host.width() - w
        start_x = host.width() if open_ else end_x
        end_x_final = end_x if open_ else host.width()
        self.setGeometry(start_x, 0, w, h)
        anim = QPropertyAnimation(self, b"geometry", self)
        anim.setDuration(200)
        anim.setStartValue(QRect(start_x, 0, w, h))
        anim.setEndValue(QRect(end_x_final, 0, w, h))
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        if not open_:
            anim.finished.connect(self.hide)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    # ---------- builders ----------
    def _build_typography(self) -> QGridLayout:
        g = QGridLayout()
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(6)
        self._lbl_body_font = QLabel(t("settings.body_font"))
        self._lbl_title_font = QLabel(t("settings.title_font"))
        self._lbl_body_size = QLabel(t("settings.body_size"))
        self._lbl_line_spacing = QLabel(t("settings.line_spacing"))

        self.body_font = QComboBox()
        self.body_font.addItems(T.DOCUMENT_FONTS)
        self.title_font = QComboBox()
        self.title_font.addItems(T.DOCUMENT_FONTS)
        self.body_size = QComboBox()
        self.body_size.addItems([f"{n} pt" for n in T.BODY_SIZES])
        self.line_spacing = QSlider(Qt.Orientation.Horizontal)
        self.line_spacing.setRange(100, 250)  # 1.00 → 2.50
        self.line_spacing.setSingleStep(5)

        for i, (lbl, ed) in enumerate([
            (self._lbl_body_font, self.body_font),
            (self._lbl_title_font, self.title_font),
            (self._lbl_body_size, self.body_size),
            (self._lbl_line_spacing, self.line_spacing),
        ]):
            lbl.setStyleSheet(f"color:{T.DUST};font-size:11px;")
            g.addWidget(lbl, i, 0)
            g.addWidget(ed, i, 1)

        self.body_font.currentTextChanged.connect(self._push)
        self.title_font.currentTextChanged.connect(self._push)
        self.body_size.currentIndexChanged.connect(self._push)
        self.line_spacing.valueChanged.connect(self._push)
        return g

    def _build_layout_section(self) -> QGridLayout:
        g = QGridLayout()
        g.setHorizontalSpacing(8)
        g.setVerticalSpacing(6)

        self._lbl_paper = QLabel(t("settings.paper"))
        self.paper = QComboBox()
        self.paper.addItems(T.PAPER_SIZES)
        self.paper.currentIndexChanged.connect(self._push)

        self._lbl_orient = QLabel(t("settings.orientation"))
        orient_wrap = QWidget()
        orient_lay = QHBoxLayout(orient_wrap)
        orient_lay.setContentsMargins(0, 0, 0, 0)
        self.rb_portrait = QRadioButton(t("settings.portrait"))
        self.rb_landscape = QRadioButton(t("settings.landscape"))
        self._orient_group = QButtonGroup(self)
        self._orient_group.addButton(self.rb_portrait)
        self._orient_group.addButton(self.rb_landscape)
        self.rb_portrait.toggled.connect(self._push)
        self.rb_landscape.toggled.connect(self._push)
        orient_lay.addWidget(self.rb_portrait)
        orient_lay.addWidget(self.rb_landscape)
        orient_lay.addStretch(1)

        self._lbl_mt = QLabel(t("settings.margin_top"))
        self._lbl_mb = QLabel(t("settings.margin_bottom"))
        self._lbl_ml = QLabel(t("settings.margin_left"))
        self._lbl_mr = QLabel(t("settings.margin_right"))
        self.margin_top = self._mm_spin()
        self.margin_bottom = self._mm_spin()
        self.margin_left = self._mm_spin()
        self.margin_right = self._mm_spin()

        rows = [
            (self._lbl_paper, self.paper),
            (self._lbl_orient, orient_wrap),
            (self._lbl_mt, self.margin_top),
            (self._lbl_mb, self.margin_bottom),
            (self._lbl_ml, self.margin_left),
            (self._lbl_mr, self.margin_right),
        ]
        for i, (lbl, ed) in enumerate(rows):
            lbl.setStyleSheet(f"color:{T.DUST};font-size:11px;")
            g.addWidget(lbl, i, 0)
            g.addWidget(ed, i, 1)
        return g

    def _mm_spin(self) -> QSpinBox:
        s = QSpinBox()
        s.setRange(5, 80)
        s.setSuffix(" mm")
        s.valueChanged.connect(self._push)
        return s

    def _build_numbering(self) -> QVBoxLayout:
        v = QVBoxLayout()
        v.setSpacing(4)
        self.cb_section = QCheckBox(t("settings.section_numbering"))
        self.cb_figure = QCheckBox(t("settings.figure_numbering"))
        self.cb_table = QCheckBox(t("settings.table_numbering"))
        self.cb_equation = QCheckBox(t("settings.equation_numbering"))
        for cb in (self.cb_section, self.cb_figure, self.cb_table, self.cb_equation):
            cb.stateChanged.connect(self._push)
            v.addWidget(cb)
        return v

    def _build_template(self) -> QVBoxLayout:
        v = QVBoxLayout()
        v.setSpacing(6)
        self._template_buttons: list[tuple[str, QPushButton]] = []
        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        for idx, tid in enumerate(TEMPLATE_ORDER):
            btn = QPushButton(TEMPLATES[tid]["name"].split()[0])
            btn.setFixedHeight(28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, t_id=tid: self._on_template(t_id))
            self._template_buttons.append((tid, btn))
            grid.addWidget(btn, idx // 3, idx % 3)
        v.addLayout(grid)
        return v

    # ---------- sync ----------
    def _refresh_from_doc(self) -> None:
        self._suppress = True
        s = self._doc.settings
        self.body_font.setCurrentText(s.body_font)
        self.title_font.setCurrentText(s.title_font)
        if s.body_size in T.BODY_SIZES:
            self.body_size.setCurrentIndex(T.BODY_SIZES.index(s.body_size))
        self.line_spacing.setValue(int(s.line_spacing * 100))
        self.paper.setCurrentText(s.paper)
        self.rb_portrait.setChecked(s.orientation == "portrait")
        self.rb_landscape.setChecked(s.orientation == "landscape")
        self.margin_top.setValue(s.margin_top)
        self.margin_bottom.setValue(s.margin_bottom)
        self.margin_left.setValue(s.margin_left)
        self.margin_right.setValue(s.margin_right)
        self.cb_section.setChecked(s.section_numbering)
        self.cb_figure.setChecked(s.figure_numbering)
        self.cb_table.setChecked(s.table_numbering)
        self.cb_equation.setChecked(s.equation_numbering)
        self._refresh_template_styles(active=s.template)
        self._suppress = False

    def _refresh_template_styles(self, active: str) -> None:
        for tid, btn in self._template_buttons:
            is_active = tid == active
            if is_active:
                btn.setStyleSheet(
                    f"QPushButton{{background:{T.ACCENT};color:white;border:1px solid {T.ACCENT};border-radius:5px;font-size:11px;font-weight:500;}}"
                    f"QPushButton:hover{{background:{T.ACCENT_HOVER};}}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton{{background:{T.ACCENT_LIGHT};color:{T.ACCENT};border:1px solid transparent;border-radius:5px;font-size:11px;}}"
                    f"QPushButton:hover{{border-color:{T.ACCENT};}}"
                )

    def _push(self) -> None:
        if self._suppress:
            return
        s = DocumentSettings(
            body_font=self.body_font.currentText(),
            title_font=self.title_font.currentText(),
            body_size=T.BODY_SIZES[self.body_size.currentIndex()] if self.body_size.currentIndex() >= 0 else 12,
            line_spacing=self.line_spacing.value() / 100.0,
            paper=self.paper.currentText(),
            orientation="portrait" if self.rb_portrait.isChecked() else "landscape",
            margin_top=self.margin_top.value(),
            margin_bottom=self.margin_bottom.value(),
            margin_left=self.margin_left.value(),
            margin_right=self.margin_right.value(),
            columns=self._doc.settings.columns,
            section_numbering=self.cb_section.isChecked(),
            figure_numbering=self.cb_figure.isChecked(),
            table_numbering=self.cb_table.isChecked(),
            equation_numbering=self.cb_equation.isChecked(),
            template=self._doc.settings.template,
        )
        self._doc.replace_settings(s)
        self.settingsChanged.emit()

    def _on_template(self, template_id: str) -> None:
        ans = QMessageBox.question(
            self,
            t("settings.confirm_template_title"),
            t("settings.confirm_template", name=template_name(template_id)),
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )
        if ans != QMessageBox.StandardButton.Ok:
            return
        self._doc.replace_settings(make_settings(template_id))
        self._refresh_from_doc()
        self.settingsChanged.emit()

    # ---------- i18n ----------
    def _retranslate(self, _lang: str) -> None:
        self._title_lbl.setText("📄 " + t("settings.title"))
        self._lbl_body_font.setText(t("settings.body_font"))
        self._lbl_title_font.setText(t("settings.title_font"))
        self._lbl_body_size.setText(t("settings.body_size"))
        self._lbl_line_spacing.setText(t("settings.line_spacing"))
        self._lbl_paper.setText(t("settings.paper"))
        self._lbl_orient.setText(t("settings.orientation"))
        self.rb_portrait.setText(t("settings.portrait"))
        self.rb_landscape.setText(t("settings.landscape"))
        self._lbl_mt.setText(t("settings.margin_top"))
        self._lbl_mb.setText(t("settings.margin_bottom"))
        self._lbl_ml.setText(t("settings.margin_left"))
        self._lbl_mr.setText(t("settings.margin_right"))
        self.cb_section.setText(t("settings.section_numbering"))
        self.cb_figure.setText(t("settings.figure_numbering"))
        self.cb_table.setText(t("settings.table_numbering"))
        self.cb_equation.setText(t("settings.equation_numbering"))
