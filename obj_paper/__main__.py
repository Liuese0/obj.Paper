"""Entry point: `python -m obj_paper`."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from . import __version__, theme as T
from .icons import app_icon
from .widgets.main_window import MainWindow


def _register_windows_app_id() -> None:
    """Tell Windows this process is its own app, not python.exe.

    Without this, Windows groups every PyQt program under the Python
    interpreter's taskbar entry and uses python.exe's icon — so even
    after setWindowIcon() the bottom bar still shows a snake. Setting
    an explicit AppUserModelID fixes it (must happen before the first
    window is shown). Linux / macOS don't need this."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "com.lshift.objpaper.v1"
        )
    except Exception:
        # The call is purely cosmetic; never let it crash the app.
        pass


def main() -> int:
    _register_windows_app_id()

    app = QApplication(sys.argv)
    app.setApplicationName("obj.Paper")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("LShift")
    # LShift `«` brand mark — used by every top-level window, the OS
    # taskbar entry, the Alt-Tab switcher, and the macOS dock.
    app.setWindowIcon(app_icon())
    # NOTE: don't set ApplicationDisplayName. Qt would auto-append
    # " - obj.Paper" to every window title, duplicating the brand we
    # already include via MainWindow.setWindowTitle().
    app.setStyleSheet(T.app_stylesheet())

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
