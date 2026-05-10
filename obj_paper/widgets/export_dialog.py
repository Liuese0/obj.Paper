"""Export progress dialog (spec §10).

The actual PDF/HTML render is fast enough that we skip a worker thread; we just
show a busy indicator and report success/failure with a 'Open file / Open
folder' toast.
"""

from __future__ import annotations

import os
import subprocess
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from .. import exporters, theme as T
from ..document import Document
from ..i18n import t


def _open_path(path: str) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", path])
    elif sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore
    else:
        subprocess.Popen(["xdg-open", path])


class ExportDialog(QDialog):
    """Run an export, show progress, then offer 'open file/folder'."""

    def __init__(self, document: Document, kind: str, path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("export.title"))
        self.setMinimumWidth(360)
        self._document = document
        self._kind = kind
        self._path = path

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)

        self.title_lbl = QLabel(t("export.in_progress"))
        self.title_lbl.setStyleSheet(f"color:{T.INK};font-size:13px;font-weight:500;")
        lay.addWidget(self.title_lbl)

        self.path_lbl = QLabel(path)
        self.path_lbl.setStyleSheet(f"color:{T.DUST};font-size:11px;font-family:'JetBrains Mono',monospace;")
        self.path_lbl.setWordWrap(True)
        lay.addWidget(self.path_lbl)

        self.bar = QProgressBar()
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet(
            f"QProgressBar{{background:{T.SURFACE_2};border:1px solid {T.BORDER};border-radius:4px;height:8px;}}"
            f"QProgressBar::chunk{{background:{T.ACCENT};border-radius:4px;}}"
        )
        lay.addWidget(self.bar)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet(f"color:{T.DUST};font-size:11px;")
        lay.addWidget(self.status_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.open_file_btn = QPushButton(t("export.open_file"))
        self.open_folder_btn = QPushButton(t("export.open_folder"))
        self.close_btn = QPushButton(t("dialog.confirm"))
        self.close_btn.setObjectName("primary")
        for b in (self.open_file_btn, self.open_folder_btn):
            b.setEnabled(False)
        self.open_file_btn.clicked.connect(lambda: _open_path(self._path))
        self.open_folder_btn.clicked.connect(lambda: _open_path(os.path.dirname(self._path) or "."))
        self.close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.open_folder_btn)
        btn_row.addWidget(self.open_file_btn)
        btn_row.addWidget(self.close_btn)
        lay.addLayout(btn_row)

        QTimer.singleShot(50, self._run)

    def _run(self) -> None:
        try:
            if self._kind == "pdf":
                exporters.export_pdf(self._document, self._path)
            elif self._kind == "html":
                exporters.export_html(self._document, self._path)
            self._on_done()
        except Exception as e:
            self._on_fail(e)

    def _on_done(self) -> None:
        self.bar.setRange(0, 1)
        self.bar.setValue(1)
        self.title_lbl.setText(t("export.done"))
        self.title_lbl.setStyleSheet(f"color:{T.SUCCESS};font-size:13px;font-weight:500;")
        self.status_lbl.setText(self._path)
        self.open_file_btn.setEnabled(True)
        self.open_folder_btn.setEnabled(True)

    def _on_fail(self, e: Exception) -> None:
        self.bar.setRange(0, 1)
        self.bar.setValue(0)
        self.title_lbl.setText(t("export.fail", err=str(e)))
        self.title_lbl.setStyleSheet(f"color:{T.ERROR};font-size:13px;font-weight:500;")
