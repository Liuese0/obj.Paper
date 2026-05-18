"""Main window — assembles every panel and wires global behavior.

Spec coverage:
- §5: 3-pane layout via QSplitter so the preview is resizable (240–480px)
- §10: PDF / HTML export wired to the toolbar dropdown and ⌘E
- §11: open / save / save-as / 30-second autosave
- §12: full keyboard map
- §13: instant language toggle
- §15: focus mode (F11)
- §16: external PDF reference tab
"""

from __future__ import annotations

import os

from PyQt6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QGuiApplication,
    QIcon,
    QKeySequence,
    QShortcut,
    QTextCursor,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import __version__, theme as T
from ..document import Document, starter_document
from ..i18n import i18n, t
from .canvas import Canvas
from .export_dialog import ExportDialog
from .palette import Palette
from .preview import Preview
from .settings_panel import SettingsPanel
from .status_bar import StatusBar
from .toolbar import TopToolbar


AUTOSAVE_MS = 30_000
INSERT_KEYS = [  # Insert menu shortcuts
    ("paragraph", "block.paragraph"),
    ("heading", "block.heading"),
    ("list", "block.list"),
    ("code", "block.code"),
    ("equation", "block.equation"),
    ("figure", "block.figure"),
    ("table", "block.table"),
    ("references", "block.references"),
    ("pagebreak", "block.pagebreak"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(T.WINDOW_MIN_W, T.WINDOW_MIN_H)
        self.resize(T.WINDOW_DEFAULT_W, T.WINDOW_DEFAULT_H)
        self.setObjectName("mainWindow")
        from ..icons import app_icon

        self.setWindowIcon(app_icon())

        # Restore the previous session if one exists. Falls back to the
        # starter document on first launch (or after a corrupt session).
        from ..session import load_session

        self._doc = load_session() or starter_document()
        self._focus_mode = False
        self._saved_geometry: bytes | None = None

        # ---- toolbar ----
        self._toolbar = TopToolbar(self)
        self._toolbar.saveRequested.connect(self.save)
        self._toolbar.exportPdfRequested.connect(self.export_pdf)
        self._toolbar.exportHtmlRequested.connect(self.export_html)
        self._toolbar.undoRequested.connect(self.undo)
        self._toolbar.redoRequested.connect(self.redo)
        self._toolbar.formatBoldRequested.connect(lambda: self._format("bold"))
        self._toolbar.formatItalicRequested.connect(lambda: self._format("italic"))
        self._toolbar.formatUnderlineRequested.connect(lambda: self._format("under"))
        self._toolbar.formatStrikeRequested.connect(lambda: self._format("strike"))
        self._toolbar.inlineMathRequested.connect(self._wrap_inline_math)
        self._toolbar.insertLinkRequested.connect(self._insert_link)
        self._toolbar.languageToggleRequested.connect(self._toggle_language)

        # ---- 3-pane body ----
        self._palette = Palette()
        self._palette.insertRequested.connect(lambda type_id: self._canvas.insert_new_block(type_id))
        self._palette.templateApplyRequested.connect(self._apply_template)

        self._canvas = Canvas(self._doc)
        self._canvas.settingsRequested.connect(self.toggle_settings)
        self._canvas.documentChanged.connect(lambda: self._doc.set_dirty(True))

        self._preview = Preview(self._doc)

        # splitter for canvas+preview (palette is fixed width)
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self._canvas)
        self._splitter.addWidget(self._preview)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 0)
        self._splitter.setSizes([900, T.PREVIEW_DEFAULT])
        self._preview.setMinimumWidth(T.PREVIEW_MIN)
        self._preview.setMaximumWidth(T.PREVIEW_MAX)

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)
        body_lay.addWidget(self._palette)
        body_lay.addWidget(self._splitter, 1)

        # central — Toolbar → 3-pane body. The OS native title bar shows
        # the file name (set via setWindowTitle); we don't draw our own.
        central = QWidget()
        central.setObjectName("central")
        central.setStyleSheet(f"QWidget#central{{background:{T.BG};}}")
        cl = QVBoxLayout(central)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addWidget(self._toolbar)
        cl.addWidget(body, 1)
        self.setCentralWidget(central)

        # status bar
        self._status = StatusBar(self._doc)
        self._status.languageRequested.connect(self._toggle_language)
        sb = QStatusBar()
        sb.addPermanentWidget(self._status, 1)
        sb.setStyleSheet(f"QStatusBar{{background:{T.SURFACE};border-top:1px solid {T.BORDER};padding:0;}}")
        self.setStatusBar(sb)

        # settings overlay
        self._settings_panel = SettingsPanel(self._doc, host=body)
        self._settings_panel.settingsChanged.connect(self._on_settings_changed)

        # menus and shortcuts
        self._actions: dict[str, QAction] = {}
        self._build_menus()
        self._wire_shortcuts()

        # Auto-session: snapshot the document to the user's app-data dir so
        # closing without saving (or a crash) never loses work.
        #  - 2 s after each edit (debounced), and
        #  - every 30 s as a safety net (spec §11).
        self._session_timer = QTimer(self)
        self._session_timer.setSingleShot(True)
        self._session_timer.setInterval(2000)
        self._session_timer.timeout.connect(self._save_session)

        self._autosave_timer = QTimer(self)
        self._autosave_timer.setInterval(AUTOSAVE_MS)
        self._autosave_timer.timeout.connect(self._save_session)
        self._autosave_timer.start()

        # connections
        self._doc.changed.connect(self._on_doc_changed)
        self._doc.changed.connect(self._session_timer.start)
        self._doc.dirtyChanged.connect(self._refresh_title)
        self._doc.pathChanged.connect(self._refresh_title)
        i18n().languageChanged.connect(self._retranslate)

        # initial paint
        self._refresh_title()
        self._toolbar.update_context(self._doc.settings)
        self._toolbar.update_lang(i18n().lang)

        # warm up matplotlib in the background so the first equation is snappy
        QTimer.singleShot(50, self._warm_up_latex)

    # ------------------------------------------------------------------
    # menu / shortcuts
    # ------------------------------------------------------------------
    def _build_menus(self) -> None:
        mb: QMenuBar = self.menuBar()
        mb.clear()

        # File
        m_file = mb.addMenu(t("menu.file"))
        self._add(m_file, "menu.new", QKeySequence.StandardKey.New, self.new_document)
        self._add(m_file, "menu.open", QKeySequence.StandardKey.Open, self.open_document)
        self._add(m_file, "menu.import_pdf", QKeySequence("Ctrl+I"), self.import_pdf)
        self._add(m_file, "menu.save", QKeySequence.StandardKey.Save, self.save)
        self._add(m_file, "menu.save_as", QKeySequence.StandardKey.SaveAs, self.save_as)
        m_file.addSeparator()
        self._add(m_file, "menu.export_pdf", QKeySequence("Ctrl+E"), self.export_pdf)
        self._add(m_file, "menu.export_html", QKeySequence("Ctrl+Shift+E"), self.export_html)
        m_file.addSeparator()
        self._add(m_file, "menu.exit", QKeySequence.StandardKey.Quit, self.close)

        # Edit
        m_edit = mb.addMenu(t("menu.edit"))
        self._add(m_edit, "menu.undo", QKeySequence.StandardKey.Undo, self.undo)
        self._add(m_edit, "menu.redo", QKeySequence.StandardKey.Redo, self.redo)
        m_edit.addSeparator()
        self._add(m_edit, "menu.move_up", QKeySequence("Alt+Up"), lambda: self._move_current(-1))
        self._add(m_edit, "menu.move_down", QKeySequence("Alt+Down"), lambda: self._move_current(+1))
        self._add(m_edit, "menu.duplicate", QKeySequence("Ctrl+D"), self._duplicate_current)
        self._add(m_edit, "menu.delete", QKeySequence("Ctrl+Backspace"), self._delete_current)
        m_edit.addSeparator()
        self._add(m_edit, "menu.add_paragraph", QKeySequence("Ctrl+Return"), self._add_paragraph_below)
        self._add(m_edit, "menu.change_type", QKeySequence("Ctrl+/"), self._show_change_type)

        # View
        m_view = mb.addMenu(t("menu.view"))
        self._add(m_view, "menu.focus_mode", QKeySequence("F11"), self.toggle_focus_mode)
        m_view.addSeparator()
        m_lang = m_view.addMenu(t("menu.language"))
        self._lang_menu = m_lang
        self._a_lang_en = QAction(t("menu.lang_en"), self)
        self._a_lang_ko = QAction(t("menu.lang_ko"), self)
        self._a_lang_en.setCheckable(True)
        self._a_lang_ko.setCheckable(True)
        self._a_lang_en.triggered.connect(lambda: i18n().set_lang("en"))
        self._a_lang_ko.triggered.connect(lambda: i18n().set_lang("ko"))
        m_lang.addAction(self._a_lang_en)
        m_lang.addAction(self._a_lang_ko)
        self._refresh_lang_check()

        # Insert (each block type quick action)
        m_insert = mb.addMenu(t("menu.insert"))
        for tid, key in INSERT_KEYS:
            act = QAction(t(key), self)
            act.triggered.connect(lambda checked=False, t_id=tid: self._canvas.insert_new_block(t_id))
            m_insert.addAction(act)
            self._actions[f"insert.{tid}"] = act

        # Format
        m_format = mb.addMenu(t("menu.format"))
        self._add(m_format, "menu.bold", QKeySequence.StandardKey.Bold, lambda: self._format("bold"))
        self._add(m_format, "menu.italic", QKeySequence.StandardKey.Italic, lambda: self._format("italic"))
        self._add(m_format, "menu.underline", QKeySequence.StandardKey.Underline, lambda: self._format("under"))
        self._add(m_format, "menu.inline_math", QKeySequence("Ctrl+M"), self._wrap_inline_math)
        self._add(m_format, "menu.link", QKeySequence("Ctrl+K"), self._insert_link)
        self._add(m_format, "menu.clear_format", QKeySequence("Ctrl+\\"), lambda: self._format("clear"))
        m_format.addSeparator()
        self._add(m_format, "menu.choose_template", QKeySequence("Ctrl+Shift+P"), self._show_template_picker)

        # Help
        m_help = mb.addMenu(t("menu.help"))
        self._add(m_help, "menu.about", None, self._show_about)

    def _wire_shortcuts(self) -> None:
        # Language toggle (independent of menu)
        sc = QShortcut(QKeySequence("Ctrl+Shift+L"), self)
        sc.activated.connect(self._toggle_language)

    def _add(self, menu, key: str, shortcut, fn) -> QAction:
        act = QAction(t(key), self)
        if shortcut is not None:
            if isinstance(shortcut, QKeySequence.StandardKey):
                act.setShortcut(QKeySequence(shortcut))
            else:
                act.setShortcut(shortcut)
        act.triggered.connect(lambda checked=False: fn())
        menu.addAction(act)
        self._actions[key] = act
        return act

    # ------------------------------------------------------------------
    # title / state
    # ------------------------------------------------------------------
    def _refresh_title(self) -> None:
        # OS title bars (Windows / macOS / GNOME / KDE) already prefix or
        # suffix the application name themselves, so we keep the window
        # title to just `<filename> ●` to avoid `obj.Paper — file - obj.Paper`
        # style duplication.
        path = self._doc.path
        name = os.path.basename(path) if path else t("dialog.untitled")
        marker = " ●" if self._doc.dirty else ""
        self.setWindowTitle(f"obj.Paper — {name}{marker}")
        # `windowFilePath` lets macOS show the proxy icon and the platform
        # add the standard " - <displayName>" suffix only when the OS does
        # so natively, instead of Qt forcing it.
        if path:
            self.setWindowFilePath(path)

    def _on_doc_changed(self) -> None:
        self._toolbar.update_context(self._doc.settings)

    def _on_settings_changed(self) -> None:
        self._toolbar.update_context(self._doc.settings)

    def _refresh_lang_check(self) -> None:
        cur = i18n().lang
        self._a_lang_en.setChecked(cur == "en")
        self._a_lang_ko.setChecked(cur == "ko")

    def _retranslate(self, lang: str) -> None:
        # rebuild menus to retranslate
        self._build_menus()
        self._toolbar.update_lang(lang)
        self._refresh_title()
        self._refresh_lang_check()

    def _toggle_language(self) -> None:
        i18n().toggle()

    # ------------------------------------------------------------------
    # file / export
    # ------------------------------------------------------------------
    def new_document(self) -> None:
        if not self._maybe_save_first():
            return
        from ..document import Document

        empty = Document(title="Untitled")
        self._doc.replace_with(empty)
        self._doc.set_path(None)
        self._refresh_title()

    def open_document(self) -> None:
        if not self._maybe_save_first():
            return
        path, _ = QFileDialog.getOpenFileName(self, t("menu.open"), "", "obj.Paper (*.pw *.json);;All files (*)")
        if not path:
            return
        try:
            from ..document import Document

            new_doc = Document.load(path)
            self._doc.replace_with(new_doc)
            self._refresh_title()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def import_pdf(self) -> None:
        """Open an existing PDF and turn it into an editable obj.Paper document.

        Text extraction is best-effort: born-digital PDFs come through
        cleanly, scanned PDFs trigger an error message instead of producing
        an empty document."""
        if not self._maybe_save_first():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, t("menu.import_pdf"), "", "PDF (*.pdf);;All files (*)"
        )
        if not path:
            return
        try:
            from ..pdf_import import import_pdf

            new_doc = import_pdf(path)
            # Imported docs aren't a .pw yet — keep the path empty so Save
            # forces Save-As and the user picks a .pw destination.
            self._doc.replace_with(new_doc)
            self._doc.set_path(None)
            self._doc.set_dirty(True)
            self._refresh_title()
        except Exception as e:
            QMessageBox.critical(self, t("menu.import_pdf"), str(e))

    def save(self) -> None:
        if not self._doc.path:
            self.save_as()
            return
        try:
            self._doc.save(self._doc.path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        self._refresh_title()
        self._status.refresh()
        self._save_session()  # keep session in sync with the .pw on disk

    def save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, t("menu.save_as"), self._doc.title or "untitled", "obj.Paper (*.pw);;JSON (*.json)"
        )
        if not path:
            return
        if not path.lower().endswith((".pw", ".json")):
            path += ".pw"
        try:
            self._doc.save(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
        self._refresh_title()
        self._save_session()  # keep session in sync with the .pw on disk

    def _maybe_save_first(self) -> bool:
        if not self._doc.dirty:
            return True
        ans = QMessageBox.question(
            self,
            t("dialog.confirm"),
            t("dialog.save_first"),
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if ans == QMessageBox.StandardButton.Cancel:
            return False
        if ans == QMessageBox.StandardButton.Save:
            self.save()
            return not self._doc.dirty
        return True

    def export_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, t("menu.export_pdf"), self._doc.title or "untitled", "PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        ExportDialog(self._doc, "pdf", path, parent=self).exec()

    def export_html(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, t("menu.export_html"), self._doc.title or "untitled", "HTML (*.html)")
        if not path:
            return
        if not path.lower().endswith(".html"):
            path += ".html"
        ExportDialog(self._doc, "html", path, parent=self).exec()

    def _save_session(self) -> None:
        """Persist the current document to the user's session file so the
        next launch can restore it — works even when the document has
        never been saved to a `.pw`."""
        from ..session import save_session

        save_session(self._doc)

    # ------------------------------------------------------------------
    # editor commands
    # ------------------------------------------------------------------
    def undo(self) -> None:
        edit = self._focused_text_edit()
        if edit:
            edit.undo()

    def redo(self) -> None:
        edit = self._focused_text_edit()
        if edit:
            edit.redo()

    def _format(self, kind: str) -> None:
        edit = self._focused_text_edit()
        if not edit:
            return
        cur = edit.textCursor()
        from PyQt6.QtGui import QTextCharFormat, QFont

        fmt = QTextCharFormat()
        if kind == "bold":
            fmt.setFontWeight(QFont.Weight.Normal if cur.charFormat().fontWeight() >= QFont.Weight.Bold else QFont.Weight.Bold)
        elif kind == "italic":
            fmt.setFontItalic(not cur.charFormat().fontItalic())
        elif kind == "under":
            fmt.setFontUnderline(not cur.charFormat().fontUnderline())
        elif kind == "strike":
            fmt.setFontStrikeOut(not cur.charFormat().fontStrikeOut())
        elif kind == "clear":
            fmt.setFontWeight(QFont.Weight.Normal)
            fmt.setFontItalic(False)
            fmt.setFontUnderline(False)
            fmt.setFontStrikeOut(False)
            cur.setCharFormat(fmt)
            return
        cur.mergeCharFormat(fmt)
        edit.mergeCurrentCharFormat(fmt)

    def _wrap_inline_math(self) -> None:
        edit = self._focused_text_edit()
        if not edit:
            return
        cur = edit.textCursor()
        if cur.hasSelection():
            cur.insertText(f"${cur.selectedText()}$")
        else:
            cur.insertText("$$")
            cur.movePosition(QTextCursor.MoveOperation.Left)
            edit.setTextCursor(cur)

    def _insert_link(self) -> None:
        edit = self._focused_text_edit()
        if not edit:
            return
        url, ok = QInputDialog.getText(self, t("menu.link"), "URL")
        if not ok or not url:
            return
        cur = edit.textCursor()
        if cur.hasSelection():
            text = cur.selectedText()
            cur.insertHtml(f'<a href="{url}">{text}</a>')
        else:
            cur.insertHtml(f'<a href="{url}">{url}</a>')

    def _focused_text_edit(self) -> QTextEdit | None:
        w = QApplication.focusWidget()
        if isinstance(w, QTextEdit):
            return w
        return None

    # ------------------------------------------------------------------
    # block-context commands
    # ------------------------------------------------------------------
    def _selected_block_id(self) -> str | None:
        bid = self._canvas._selected_id  # internal — fine within the same package
        return bid or None

    def _move_current(self, delta: int) -> None:
        bid = self._selected_block_id()
        if bid:
            self._canvas._on_move(bid, delta)

    def _duplicate_current(self) -> None:
        bid = self._selected_block_id()
        if bid:
            self._canvas._on_duplicate(bid)

    def _delete_current(self) -> None:
        bid = self._selected_block_id()
        if bid:
            self._canvas._on_delete(bid)

    def _add_paragraph_below(self) -> None:
        bid = self._selected_block_id()
        if bid:
            self._canvas._on_add_paragraph(bid)
        else:
            self._canvas.insert_new_block("paragraph")

    def _show_change_type(self) -> None:
        bid = self._selected_block_id()
        if not bid:
            return
        types = [k for k, _ in INSERT_KEYS] + ["title", "authors", "abstract"]
        labels = [t(f"block.{x}") for x in types]
        choice, ok = QInputDialog.getItem(self, t("menu.change_type"), t("menu.change_type"), labels, 0, False)
        if not ok:
            return
        idx = labels.index(choice)
        new_type = types[idx]
        block = self._doc._find(bid)
        if not block:
            return
        block.type = new_type
        # reset data to defaults of new type
        from .canvas import _default_data

        block.data = _default_data(new_type)
        self._doc._touch()
        self._canvas._rebuild()
        self._canvas.select_block(bid)

    def _show_template_picker(self) -> None:
        from ..templates import TEMPLATE_ORDER

        labels = [t(f"block.title")]  # noop placeholder to keep i18n live
        labels = [TEMPLATES_NAME(tid) for tid in TEMPLATE_ORDER]
        choice, ok = QInputDialog.getItem(
            self, t("menu.choose_template"), t("settings.apply_preset"), labels, 0, False
        )
        if not ok:
            return
        tid = TEMPLATE_ORDER[labels.index(choice)]
        self._apply_template(tid)

    def _apply_template(self, template_id: str) -> None:
        from ..templates import make_settings, template_name

        ans = QMessageBox.question(
            self,
            t("settings.confirm_template_title"),
            t("settings.confirm_template", name=template_name(template_id)),
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
        )
        if ans != QMessageBox.StandardButton.Ok:
            return
        self._doc.replace_settings(make_settings(template_id))
        self._toolbar.update_context(self._doc.settings)

    # ------------------------------------------------------------------
    # settings overlay
    # ------------------------------------------------------------------
    def toggle_settings(self) -> None:
        if self._settings_panel.is_open():
            self._settings_panel.close_panel()
        else:
            self._settings_panel.open_panel()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._settings_panel.reposition()

    # ------------------------------------------------------------------
    # focus mode
    # ------------------------------------------------------------------
    def toggle_focus_mode(self) -> None:
        self._focus_mode = not self._focus_mode
        if self._focus_mode:
            self._saved_geometry = bytes(self.saveGeometry())
            self._palette.hide()
            self._preview.hide()
            self._toolbar.hide()
            self.statusBar().hide()
            self.menuBar().setVisible(False)
            self.showFullScreen()
        else:
            self._palette.show()
            self._preview.show()
            self._toolbar.show()
            self.statusBar().show()
            self.menuBar().setVisible(True)
            self.showNormal()
            if self._saved_geometry is not None:
                self.restoreGeometry(self._saved_geometry)

    def keyPressEvent(self, e):
        if self._focus_mode and e.key() == Qt.Key.Key_Escape:
            self.toggle_focus_mode()
            return
        super().keyPressEvent(e)

    # ------------------------------------------------------------------
    # close
    # ------------------------------------------------------------------
    def closeEvent(self, e):
        # Stop the recurring timers BEFORE writing the final session — a
        # pending tick that fires after `self` is half-destroyed crashes
        # the process on Windows.
        for timer in (self._session_timer, self._autosave_timer):
            try:
                timer.stop()
            except Exception:
                pass
        # Hide the floating inline toolbar so its target reference doesn't
        # outlive the canvas' QTextEdits during shutdown.
        try:
            from .inline_toolbar import get_inline_toolbar

            get_inline_toolbar().detach()
        except Exception:
            pass
        # Take one final snapshot so the next launch resumes exactly where
        # the user left off. The auto-session makes the "save before
        # closing?" prompt redundant — closing never destroys work.
        try:
            self._save_session()
        except Exception:
            pass
        super().closeEvent(e)

    # ------------------------------------------------------------------
    # misc
    # ------------------------------------------------------------------
    def _show_about(self) -> None:
        QMessageBox.information(
            self,
            t("menu.about"),
            t("about.text", version=__version__),
        )

    def _warm_up_latex(self) -> None:
        try:
            from .. import latex as latex_mod

            latex_mod.warm_up()
        except Exception:
            pass


def TEMPLATES_NAME(tid: str) -> str:
    """Late import to keep this module's top imports tight."""
    from ..templates import template_name

    return template_name(tid)
