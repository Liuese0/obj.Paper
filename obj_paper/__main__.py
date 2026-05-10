"""Entry point: `python -m obj_paper`."""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

from . import __version__, theme as T
from .widgets.main_window import MainWindow


def main() -> int:
    QGuiApplication.setApplicationDisplayName("obj.Paper")
    app = QApplication(sys.argv)
    app.setApplicationName("obj.Paper")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("LShift")
    app.setStyleSheet(T.app_stylesheet())

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
