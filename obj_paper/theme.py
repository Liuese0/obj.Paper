"""Color tokens, typography, and the global Qt stylesheet for obj.Paper.

All visual tokens originate from `spec.md` §3 (color system) and §4 (typography).
Keep this file as the single source of truth — UI code reads constants from here.
"""

from __future__ import annotations

import sys

# ---------- color palette (spec §3.1) ----------
BG = "#F3F0E9"            # Parchment — app/canvas background
ACCENT = "#D97757"        # Terracotta — primary accent
ACCENT_HOVER = "#C06644"  # Deep Terra — hover
ACCENT_LIGHT = "#F2DED5"  # Blush — selected block bg
SURFACE = "#FDFCF8"       # Warm White — panels, preview page
SURFACE_2 = "#EAE7DE"     # Sand — dividers, inactive
INK = "#2C2820"           # Body text
DUST = "#7A7268"          # Secondary labels
MIST = "#B0A99E"          # Tertiary / inactive
BORDER = "#D8D3C9"        # Warm gray border
ERROR = "#C0392B"
SUCCESS = "#27AE60"
INFO = "#2980B9"

# ---------- layout constants (spec §5) ----------
PALETTE_WIDTH = 240
PREVIEW_MIN = 240
PREVIEW_DEFAULT = 340
PREVIEW_MAX = 480
WINDOW_MIN_W = 1280
WINDOW_MIN_H = 720
WINDOW_DEFAULT_W = 1440
WINDOW_DEFAULT_H = 900

# ---------- typography (spec §4) ----------
def _platform_font_stacks() -> dict[str, str]:
    if sys.platform == "darwin":
        return {
            "ui": '"SF Pro Text", "Helvetica Neue", "Inter", -apple-system, sans-serif',
            "mono": '"SF Mono", "Cascadia Code", "Consolas", monospace',
            "serif": '"Times New Roman", "Times", "Georgia", serif',
            "ko": '"Apple SD Gothic Neo", "Noto Sans CJK KR", sans-serif',
        }
    if sys.platform.startswith("win"):
        return {
            "ui": '"Segoe UI", "Inter", "Malgun Gothic", sans-serif',
            "mono": '"Cascadia Code", "Consolas", monospace',
            "serif": '"Times New Roman", "Georgia", serif',
            "ko": '"Malgun Gothic", "Noto Sans CJK KR", sans-serif',
        }
    return {
        "ui": '"Inter", "Segoe UI", "Noto Sans CJK KR", sans-serif',
        "mono": '"JetBrains Mono", "Cascadia Code", "Consolas", monospace',
        "serif": '"Times New Roman", "Liberation Serif", "Georgia", serif',
        "ko": '"Noto Sans CJK KR", "Noto Sans KR", sans-serif',
    }


FONTS = _platform_font_stacks()

# UI text scale (spec §4.3)
TITLE_PX = 13
PANEL_HEADER_PX = 11
BLOCK_LABEL_PX = 11
BODY_PX = 14
CAPTION_PX = 11

# Document fonts available in Document Settings (spec §4.2)
DOCUMENT_FONTS = [
    "Times New Roman",
    "Georgia",
    "Arial",
    "Helvetica Neue",
    "Courier New",
]

PAPER_SIZES = ["A4", "Letter", "Legal", "B5"]
BODY_SIZES = [9, 10, 11, 12, 13, 14]


def app_stylesheet() -> str:
    """Global QSS applied to the QApplication.

    Specific widgets layer additional styles via `setStyleSheet` or object names
    (e.g. `#primary` for the accent button).
    """
    return f"""
    QMainWindow, QWidget {{
        background: {BG};
        color: {INK};
        font-family: {FONTS['ui']};
        font-size: 12px;
    }}
    QMainWindow {{
        background: {BG};
    }}
    QToolTip {{
        background: {INK};
        color: white;
        border: 1px solid {BORDER};
        padding: 4px 8px;
        border-radius: 4px;
    }}
    QMenuBar {{
        background: {SURFACE};
        border-bottom: 1px solid {BORDER};
        padding: 2px 6px;
        font-size: 12px;
        color: {INK};
    }}
    QMenuBar::item {{
        padding: 4px 10px;
        background: transparent;
        border-radius: 4px;
    }}
    QMenuBar::item:selected {{
        background: {SURFACE_2};
    }}
    QMenu {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        padding: 4px;
        font-size: 12px;
        color: {INK};
    }}
    QMenu::item {{
        padding: 6px 18px 6px 14px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background: {ACCENT_LIGHT};
        color: {ACCENT};
    }}
    QMenu::separator {{
        height: 1px;
        background: {BORDER};
        margin: 4px 6px;
    }}
    QStatusBar {{
        background: {SURFACE};
        border-top: 1px solid {BORDER};
        font-size: 11px;
        color: {DUST};
    }}
    QStatusBar::item {{
        border: none;
    }}
    QSplitter::handle {{
        background: {BORDER};
    }}
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 4px 2px;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {MIST};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
        width: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 2px 4px;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background: {BORDER};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {MIST};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}
    QPushButton {{
        background: {BG};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 4px 10px;
        color: {INK};
        font-size: 12px;
    }}
    QPushButton:hover {{
        border-color: {ACCENT};
    }}
    QPushButton:pressed {{
        background: {SURFACE_2};
    }}
    QPushButton:disabled {{
        color: {MIST};
        border-color: {BORDER};
        background: {SURFACE_2};
    }}
    QPushButton#primary {{
        background: {ACCENT};
        border: 1px solid {ACCENT};
        color: white;
        font-weight: 500;
    }}
    QPushButton#primary:hover {{
        background: {ACCENT_HOVER};
        border-color: {ACCENT_HOVER};
    }}
    QPushButton#accentOutline {{
        background: white;
        border: 1px solid {ACCENT};
        color: {ACCENT};
    }}
    QPushButton#accentOutline:hover {{
        background: {ACCENT_LIGHT};
    }}
    QPushButton#langChip {{
        background: {ACCENT_LIGHT};
        border: 1px solid {ACCENT};
        color: {ACCENT};
        font-weight: 500;
    }}
    QPushButton#ghost {{
        background: transparent;
        border: 1px solid transparent;
        color: {INK};
    }}
    QPushButton#ghost:hover {{
        background: {SURFACE_2};
    }}
    QPushButton#blockCtrl {{
        background: transparent;
        border: none;
        color: {DUST};
        padding: 0px;
    }}
    QPushButton#blockCtrl:hover {{
        color: {ACCENT};
    }}
    QLineEdit {{
        background: {BG};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 4px 8px;
        color: {INK};
        selection-background-color: {ACCENT_LIGHT};
        selection-color: {INK};
    }}
    QLineEdit:focus {{
        border-color: {ACCENT};
    }}
    QTextEdit, QPlainTextEdit {{
        background: transparent;
        border: none;
        color: {INK};
        selection-background-color: {ACCENT_LIGHT};
        selection-color: {INK};
    }}
    QTextBrowser {{
        background: {SURFACE_2};
        border: none;
    }}
    QComboBox {{
        background: {BG};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 4px 8px;
        min-height: 18px;
        color: {INK};
    }}
    QComboBox:hover {{
        border-color: {ACCENT};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 20px;
    }}
    QComboBox QAbstractItemView {{
        background: {SURFACE};
        border: 1px solid {BORDER};
        selection-background-color: {ACCENT_LIGHT};
        selection-color: {ACCENT};
        outline: none;
    }}
    QSpinBox {{
        background: {BG};
        border: 1px solid {BORDER};
        border-radius: 6px;
        padding: 4px 6px;
        color: {INK};
    }}
    QSlider::groove:horizontal {{
        height: 4px;
        background: {SURFACE_2};
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {ACCENT};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {ACCENT};
        width: 14px;
        margin: -5px 0;
        border-radius: 7px;
    }}
    QCheckBox {{
        spacing: 8px;
        font-size: 12px;
        color: {INK};
    }}
    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        border-radius: 3px;
        border: 1px solid {BORDER};
        background: {SURFACE};
    }}
    QCheckBox::indicator:hover {{
        border-color: {ACCENT};
    }}
    QCheckBox::indicator:checked {{
        background: {ACCENT};
        border-color: {ACCENT};
    }}
    QRadioButton {{
        spacing: 6px;
        color: {INK};
    }}
    QRadioButton::indicator {{
        width: 14px;
        height: 14px;
        border-radius: 7px;
        border: 1px solid {BORDER};
        background: {SURFACE};
    }}
    QRadioButton::indicator:checked {{
        background: {ACCENT};
        border: 4px solid {ACCENT_LIGHT};
    }}
    QToolBar {{
        background: {SURFACE};
        border-bottom: 1px solid {BORDER};
        spacing: 6px;
        padding: 6px 10px;
    }}
    QToolBar::separator {{
        background: {BORDER};
        width: 1px;
        margin: 4px 6px;
    }}
    QFrame#divider {{
        background: {BORDER};
    }}
    QLabel#panelHeader {{
        color: {ACCENT};
        font-size: 10px;
        font-weight: 600;
        letter-spacing: 1.4px;
    }}
    QLabel#muted {{
        color: {DUST};
        font-size: 11px;
    }}
    QLabel#tertiary {{
        color: {MIST};
        font-size: 10px;
    }}
    """


def block_badge_color(block_type: str) -> str:
    """Spec §6.2: only `title` uses Terracotta to obey the 'max 3 accent uses' rule."""
    if block_type == "title":
        return ACCENT
    if block_type == "heading":
        return ACCENT_HOVER
    if block_type == "equation":
        return INFO
    if block_type == "code":
        return "#5d6d7e"
    return DUST
