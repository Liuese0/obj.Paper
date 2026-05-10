"""Entry point: `python -m obj_paper`."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from . import __version__, theme as T
from .widgets.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("obj.Paper")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("LShift")
    # NOTE: don't set ApplicationDisplayName. Qt would auto-append
    # " - obj.Paper" to every window title, duplicating the brand we
    # already include via MainWindow.setWindowTitle().
    app.setStyleSheet(T.app_stylesheet())

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
