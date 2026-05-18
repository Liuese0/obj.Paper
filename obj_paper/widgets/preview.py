"""Right-side preview pane (spec §5.4).

Two tabs:
- Preview: live A4 document render via QTextBrowser
- Reference PDF: external PDF via QPdfView (best effort; falls back to a
  message if QtPdf isn't available)

The preview re-renders 500ms after the last document change.
"""

from __future__ import annotations

from datetime import datetime, timezone

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPointF, QUrl
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .. import render as render_mod
from .. import theme as T
from ..document import Document
from ..i18n import t, i18n


class _Tab(QPushButton):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(22)
        self.setFlat(True)
        self._restyle()

    def _restyle(self):
        self.setStyleSheet(
            f"QPushButton{{padding:0 10px;border-radius:11px;font-size:11px;color:{T.DUST};background:transparent;border:1px solid transparent;}}"
            f"QPushButton:checked{{background:white;color:{T.ACCENT};border:1px solid {T.ACCENT};font-weight:500;}}"
        )


class Preview(QFrame):
    requestRefresh = pyqtSignal()

    def __init__(self, document: Document, parent=None):
        super().__init__(parent)
        self.setObjectName("preview")
        self.setStyleSheet(f"QFrame#preview {{background:#FFFFFF;border-left:1px solid {T.BORDER};}}")
        self._doc = document
        self._last_render_at: datetime | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # header with tabs + buttons
        header = QFrame()
        header.setStyleSheet(f"background:#FFFFFF;border-bottom:1px solid {T.BORDER};")
        head = QHBoxLayout(header)
        head.setContentsMargins(8, 6, 8, 6)
        head.setSpacing(2)

        tabs_wrap = QFrame()
        tabs_wrap.setStyleSheet(f"background:{T.SURFACE_2};border:1px solid {T.BORDER};border-radius:13px;padding:2px;")
        tab_lay = QHBoxLayout(tabs_wrap)
        tab_lay.setContentsMargins(2, 2, 2, 2)
        tab_lay.setSpacing(2)
        self.tab_preview = _Tab(t("preview.tab_preview"))
        self.tab_reference = _Tab(t("preview.tab_reference"))
        self.tab_preview.setChecked(True)
        self.tab_preview.clicked.connect(lambda: self._set_tab(0))
        self.tab_reference.clicked.connect(lambda: self._set_tab(1))
        tab_lay.addWidget(self.tab_preview)
        tab_lay.addWidget(self.tab_reference)
        head.addWidget(tabs_wrap)
        head.addStretch(1)

        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setToolTip(t("preview.refresh"))
        self.refresh_btn.setFixedSize(24, 24)
        self.refresh_btn.setStyleSheet(
            f"QPushButton{{background:{T.SURFACE};border:1px solid {T.BORDER};border-radius:5px;color:{T.DUST};}}"
        )
        self.refresh_btn.clicked.connect(self.render_now)
        head.addWidget(self.refresh_btn)

        self.open_btn = QPushButton("⇪")
        self.open_btn.setToolTip(t("preview.open_pdf"))
        self.open_btn.setFixedSize(24, 24)
        self.open_btn.setStyleSheet(
            f"QPushButton{{background:{T.SURFACE};border:1px solid {T.BORDER};border-radius:5px;color:{T.DUST};}}"
        )
        self.open_btn.clicked.connect(self._open_pdf)
        head.addWidget(self.open_btn)

        outer.addWidget(header)

        # stacked content
        self.stack = QStackedWidget()
        outer.addWidget(self.stack, 1)

        # — preview page
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setStyleSheet(
            "QTextBrowser{background:#FFFFFF;border:none;padding:18px 18px 8px 18px;}"
        )
        self.stack.addWidget(self.browser)

        # — reference PDF page
        self._pdf_widget = self._build_pdf_widget()
        self.stack.addWidget(self._pdf_widget)

        # footer page nav
        foot = QFrame()
        foot.setStyleSheet(f"background:#FFFFFF;border-top:1px solid {T.BORDER};")
        fl = QHBoxLayout(foot)
        fl.setContentsMargins(8, 4, 8, 4)
        fl.setSpacing(8)
        self.page_label = QLabel("1 / 1")
        self.page_label.setStyleSheet(f"font-family:'JetBrains Mono',monospace;color:{T.INK};font-size:11px;")
        self.live_label = QLabel("● live")
        self.live_label.setStyleSheet(f"color:{T.SUCCESS};font-size:10.5px;")
        fl.addStretch(1)
        fl.addWidget(self.page_label)
        fl.addWidget(self.live_label)
        fl.addStretch(1)
        outer.addWidget(foot)

        # debounce
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(500)
        self._debounce.timeout.connect(self.render_now)

        self._doc.changed.connect(self._schedule)
        self._doc.blocksReplaced.connect(self.render_now)

        i18n().languageChanged.connect(self._retranslate)
        self.render_now()

    # ----- public ---
    def schedule_render(self) -> None:
        self._schedule()

    def render_now(self) -> None:
        # Pass the browser's inner viewport width so render.py can scale the
        # page card (and every font / margin inside) to fit. Subtract the
        # 18-px left+right padding we apply in the QTextBrowser stylesheet so
        # the card stays clear of the scrollbar gutter.
        viewport_w = max(180, self.browser.viewport().width() - 36)
        html = render_mod.document_to_html(self._doc, mode="preview", preview_width=viewport_w)
        self.browser.setHtml(html)
        self._last_render_at = datetime.now(timezone.utc)
        self._update_meta()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        # Re-render with the new viewport width so the WYSIWYG scale follows
        # the pane as the user drags the splitter. Debounced to avoid a
        # render storm during the drag.
        self._schedule()

    # ----- ---
    def _schedule(self) -> None:
        self._debounce.start()

    def _set_tab(self, idx: int) -> None:
        self.tab_preview.setChecked(idx == 0)
        self.tab_reference.setChecked(idx == 1)
        self.stack.setCurrentIndex(idx)

    def _retranslate(self, _lang):
        self.tab_preview.setText(t("preview.tab_preview"))
        self.tab_reference.setText(t("preview.tab_reference"))
        self.refresh_btn.setToolTip(t("preview.refresh"))
        self.open_btn.setToolTip(t("preview.open_pdf"))
        self._update_meta()

    def _update_meta(self) -> None:
        from .. import render as render_mod
        pages = render_mod.estimate_pages(self._doc)
        self.page_label.setText(f"1 / {pages}")

    # ----- pdf -------
    def _build_pdf_widget(self) -> QWidget:
        try:
            from PyQt6.QtPdfWidgets import QPdfView
            from PyQt6.QtPdf import QPdfDocument

            self._pdf_doc = QPdfDocument(self)
            self._pdf_view = QPdfView(self)
            self._pdf_view.setDocument(self._pdf_doc)
            self._pdf_view.setStyleSheet(f"background:{T.SURFACE_2};")
            return self._pdf_view
        except Exception:
            self._pdf_doc = None
            self._pdf_view = None
            placeholder = QLabel(t("preview.no_pdf"))
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet(f"color:{T.DUST};font-size:12px;background:{T.SURFACE_2};")
            return placeholder

    def _open_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, t("preview.open_pdf"), "", "PDF (*.pdf)")
        if not path:
            return
        if self._pdf_doc is None:
            return
        self._pdf_doc.load(path)
        self._set_tab(1)
