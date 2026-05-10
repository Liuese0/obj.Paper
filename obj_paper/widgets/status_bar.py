"""Status bar (spec §14)."""

from __future__ import annotations

from datetime import datetime, timezone

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from .. import theme as T
from ..document import Document
from ..i18n import t, i18n
from .. import render as render_mod


def _ago_text(when: datetime | None) -> str:
    if when is None:
        return t("status.never")
    delta = (datetime.now(timezone.utc) - when).total_seconds()
    if delta < 60:
        return t("ago.just_now")
    if delta < 3600:
        return t("ago.minutes", n=int(delta // 60))
    return t("ago.hours", n=int(delta // 3600))


class StatusBar(QFrame):
    languageRequested = pyqtSignal()  # user clicked the language chip

    def __init__(self, document: Document, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setStyleSheet(f"QFrame#statusBar {{background:{T.SURFACE};border-top:1px solid {T.BORDER};}}")
        self.setFixedHeight(28)
        self._doc = document

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(16)

        self.dot = QLabel("●")
        self.save_lbl = QLabel("")
        self.save_lbl.setStyleSheet(f"color:{T.INK};font-size:11px;")
        lay.addWidget(self.dot)
        lay.addWidget(self.save_lbl)
        lay.addWidget(self._sep())

        self.blocks_lbl = self._make_metric()
        self.words_lbl = self._make_metric()
        self.pages_lbl = self._make_metric()
        for w in (self.blocks_lbl[0], self.blocks_lbl[1], self.words_lbl[0], self.words_lbl[1], self.pages_lbl[0], self.pages_lbl[1]):
            lay.addWidget(w)

        lay.addStretch(1)

        self.encoding_lbl = QLabel(t("status.encoding"))
        self.encoding_lbl.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace;color:{T.DUST};font-size:10.5px;"
        )
        lay.addWidget(self.encoding_lbl)
        lay.addWidget(self._sep())

        self.lang_btn = QPushButton("한국어 ▾")
        self.lang_btn.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;color:{T.ACCENT};font-size:11px;font-weight:500;padding:0;}}"
            f"QPushButton:hover{{color:{T.ACCENT_HOVER};}}"
        )
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.clicked.connect(self.languageRequested)
        lay.addWidget(self.lang_btn)

        document.changed.connect(self.refresh)
        document.dirtyChanged.connect(lambda *_: self.refresh())
        document.pathChanged.connect(lambda *_: self.refresh())
        document.blocksReplaced.connect(self.refresh)

        i18n().languageChanged.connect(lambda *_: self.refresh())

        self._timer = QTimer(self)
        self._timer.setInterval(15_000)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

        self.refresh()

    def _make_metric(self):
        key = QLabel("")
        key.setStyleSheet(
            f"font-family:'JetBrains Mono',monospace;color:{T.MIST};font-size:10.5px;letter-spacing:.04em;"
        )
        val = QLabel("")
        val.setStyleSheet(f"color:{T.INK};font-size:11px;font-weight:500;")
        return key, val

    def _sep(self) -> QFrame:
        s = QFrame()
        s.setFixedSize(1, 14)
        s.setStyleSheet(f"background:{T.BORDER};")
        return s

    def refresh(self) -> None:
        # save status
        when = self._doc.last_saved_at
        if self._doc.dirty:
            self.dot.setText("●")
            self.dot.setStyleSheet(f"color:{T.ACCENT};")
            self.save_lbl.setText(t("status.unsaved"))
        else:
            self.dot.setText("●")
            self.dot.setStyleSheet(f"color:{T.SUCCESS};")
            ago = _ago_text(when)
            self.save_lbl.setText(t("status.saved") + " · " + ago)

        # metrics
        self.blocks_lbl[0].setText(t("status.blocks"))
        self.blocks_lbl[1].setText(str(self._doc.block_count()))
        self.words_lbl[0].setText(t("status.words"))
        self.words_lbl[1].setText(f"{self._doc.word_count():,}")
        self.pages_lbl[0].setText(t("status.pages"))
        self.pages_lbl[1].setText(str(render_mod.estimate_pages(self._doc)))

        # language chip
        self.lang_btn.setText("한국어 ▾" if i18n().lang == "ko" else "English ▾")
        self.encoding_lbl.setText(t("status.encoding"))
