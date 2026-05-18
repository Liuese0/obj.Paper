"""Crash-resistant session storage.

Keeps a JSON snapshot of the current document in the user's app-data
directory so closing the app (intentionally or by crash) never loses
work — the next launch picks up exactly where the previous one left off,
even if the document was never saved to a `.pw` file.

Cross-platform location (QStandardPaths.AppDataLocation):
  Windows  → %LOCALAPPDATA%\\LShift\\obj.Paper\\session.pw
  macOS    → ~/Library/Application Support/obj.Paper/session.pw
  Linux    → ~/.local/share/obj.Paper/session.pw
"""

from __future__ import annotations

import json
import os

from PyQt6.QtCore import QStandardPaths

from .document import Document


SESSION_FILENAME = "session.pw"


def _session_dir() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    if not base:
        base = os.path.expanduser("~/.obj.Paper")
    os.makedirs(base, exist_ok=True)
    return base


def session_path() -> str:
    return os.path.join(_session_dir(), SESSION_FILENAME)


def has_session() -> bool:
    return os.path.exists(session_path())


def save_session(doc: Document) -> None:
    """Snapshot `doc` to the session file. Best-effort: any IO/permission
    failure is swallowed so an autosave path issue can never crash the
    main UI thread."""
    try:
        payload = doc.to_json()
        # Remember the user-chosen save path (if any) so the next launch
        # can wire the document back up to its on-disk .pw file.
        payload["meta"]["session_path"] = doc.path
        payload["meta"]["session_dirty"] = doc.dirty
        tmp = session_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        # atomic-ish rename so a half-written file never replaces a good
        # one on power-loss / segfault between open() and close().
        os.replace(tmp, session_path())
    except Exception:
        pass


def load_session() -> Document | None:
    """Return a `Document` restored from the previous session, or `None`
    if no usable session exists."""
    if not has_session():
        return None
    try:
        with open(session_path(), "r", encoding="utf-8") as f:
            payload = json.load(f)
        d = Document.from_json(payload)
        meta = payload.get("meta", {})
        saved_path = meta.get("session_path")
        was_dirty = bool(meta.get("session_dirty", False))
        if saved_path and os.path.isfile(saved_path):
            d.set_path(saved_path)
        d.set_dirty(was_dirty)
        return d
    except Exception:
        return None


def clear_session() -> None:
    try:
        p = session_path()
        if os.path.exists(p):
            os.remove(p)
    except Exception:
        pass
