"""Inline SVG icon set, lifted from `obj.Paper Mockup.html`.

The mockup renders icons with `stroke="currentColor"`. We substitute the
`{color}` placeholder at render time so a single source can paint in any
palette token. The icons share a 24×24 viewBox so they composite cleanly at
any output size; pass the target pixel size to `svg_pixmap`.

To add a new icon, register its SVG body (everything inside `<svg>`) under a
short name. Use `fill="none"` on shapes you only want stroked, and reference
the color via `{color}` (for stroked icons) or `{fill}` (for filled ones).
"""

from __future__ import annotations

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer


# All icons share viewBox="0 0 24 24". Body only — `<svg>` wrapper is added
# by `_render`. Use {color} where the stroke/fill color should appear.
ICONS: dict[str, str] = {
    "search": (
        '<circle cx="11" cy="11" r="7" fill="none" stroke="{color}" stroke-width="2"/>'
        '<path d="m20 20-3.5-3.5" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>'
    ),
    "page": (
        '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" '
        'fill="none" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"/>'
        '<path d="M14 3v6h6" fill="none" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"/>'
    ),
    "user": (
        '<path d="M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" '
        'fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
        '<circle cx="10" cy="7" r="4" fill="none" stroke="{color}" stroke-width="1.8"/>'
    ),
    "abstract": (
        '<rect x="4" y="4" width="16" height="16" rx="2" fill="none" stroke="{color}" stroke-width="1.8"/>'
        '<path d="M8 9h8M8 13h8M8 17h5" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>'
    ),
    "para": (
        '<path d="M13 4v16M17 4v16M9 4h8a4 4 0 0 1 0 8H9z" '
        'fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "list": (
        '<path d="M8 6h12M8 12h12M8 18h12" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>'
        '<circle cx="3.5" cy="6" r="1" fill="{color}"/>'
        '<circle cx="3.5" cy="12" r="1" fill="{color}"/>'
        '<circle cx="3.5" cy="18" r="1" fill="{color}"/>'
    ),
    "code": (
        '<path d="m16 6 4 6-4 6M8 6l-4 6 4 6" '
        'fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "fig": (
        '<rect x="3" y="4" width="18" height="16" rx="2" fill="none" stroke="{color}" stroke-width="1.8"/>'
        '<circle cx="9" cy="10" r="2" fill="none" stroke="{color}" stroke-width="1.8"/>'
        '<path d="m3 18 5-5 5 5 4-4 4 4" fill="none" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"/>'
    ),
    "table": (
        '<rect x="3" y="4" width="18" height="16" rx="1.5" fill="none" stroke="{color}" stroke-width="1.8"/>'
        '<path d="M3 10h18M3 16h18M9 4v16M15 4v16" fill="none" stroke="{color}" stroke-width="1.8"/>'
    ),
    "ref": (
        '<path d="M4 4v16h16" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>'
        '<path d="M8 16V8M12 16v-5M16 16v-9" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round"/>'
    ),
    "pageBreak": (
        '<path d="M3 12h18" fill="none" stroke="{color}" stroke-width="1.8" '
        'stroke-dasharray="3 2" stroke-linecap="round"/>'
    ),
    "heading": (
        '<path d="M6 4v16M18 4v16M6 12h12" '
        'fill="none" stroke="{color}" stroke-width="2.2" stroke-linecap="round"/>'
    ),
    "sigma": (
        '<path d="M18 6H6l6 6-6 6h12" '
        'fill="none" stroke="{color}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>'
    ),
    # ── toolbar / chrome ──────────────────────────────────────────────
    "save": (
        '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z" '
        'fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>'
        '<path d="M17 21v-8H7v8M7 3v5h8" '
        'fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>'
    ),
    "download": (
        '<path d="M12 3v12m0 0 4-4m-4 4-4-4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" '
        'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "undo": (
        '<path d="M9 14 4 9l5-5" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M4 9h11a5 5 0 0 1 5 5v0a5 5 0 0 1-5 5h-4" '
        'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>'
    ),
    "redo": (
        '<path d="m15 14 5-5-5-5" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M20 9H9a5 5 0 0 0-5 5v0a5 5 0 0 0 5 5h4" '
        'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>'
    ),
    "link": (
        '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" '
        'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>'
        '<path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" '
        'fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>'
    ),
    "caret": (
        '<path d="M7 10l5 5 5-5z" fill="{color}"/>'
    ),
    "refresh": (
        '<path d="M3 12a9 9 0 0 1 15.5-6.3L21 8" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>'
        '<path d="M21 3v5h-5" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        '<path d="M21 12a9 9 0 0 1-15.5 6.3L3 16" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round"/>'
        '<path d="M3 21v-5h5" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "open": (
        '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" '
        'fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>'
    ),
    "gear": (
        '<circle cx="12" cy="12" r="3" fill="none" stroke="{color}" stroke-width="2"/>'
        '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 '
        '1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h0a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" '
        'fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round"/>'
    ),
    "more": (
        '<circle cx="6" cy="12" r="1.5" fill="{color}"/>'
        '<circle cx="12" cy="12" r="1.5" fill="{color}"/>'
        '<circle cx="18" cy="12" r="1.5" fill="{color}"/>'
    ),
    "arrUp": (
        '<path d="m6 14 6-6 6 6" fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "arrDown": (
        '<path d="m6 10 6 6 6-6" fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>'
    ),
    "plus": (
        '<path d="M12 5v14M5 12h14" fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round"/>'
    ),
}


# Mapping from block type → icon name in ICONS. Centralized so palette,
# block badges, and any future status surface use the same glyph per type.
TYPE_TO_ICON: dict[str, str] = {
    "title": "page",
    "authors": "user",
    "abstract": "abstract",
    "pagebreak": "pageBreak",
    "heading": "heading",
    "paragraph": "para",
    "list": "list",
    "code": "code",
    "equation": "sigma",
    "figure": "fig",
    "table": "table",
    "references": "ref",
}


def svg_pixmap(name: str, size: int = 12, color: str = "#7A7268") -> QPixmap:
    """Render an icon to a QPixmap. Uses the screen's device pixel ratio so
    the output stays crisp on retina/HiDPI displays."""
    body = ICONS.get(name)
    if body is None:
        # blank pixmap — caller should never hit this in practice.
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        return pm

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        f'width="{size}" height="{size}">{body.format(color=color)}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))

    # Render at 2× internally for crisp scaling, then setDevicePixelRatio.
    scale = 2
    pm = QPixmap(size * scale, size * scale)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()
    pm.setDevicePixelRatio(float(scale))
    return pm


# ---------- application icon ----------
# Square 256×256 mark built from the LShift brand chevrons (`«` doubled).
# Pure paths so we don't depend on any system font being installed.
_APP_ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">'
    '<defs>'
    '<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
    '<stop offset="0" stop-color="#F3F0E9"/>'
    '<stop offset="1" stop-color="#E8E2CF"/>'
    '</linearGradient>'
    '</defs>'
    # rounded card
    '<rect x="0" y="0" width="256" height="256" rx="52" ry="52" fill="url(#bg)"/>'
    '<rect x="2" y="2" width="252" height="252" rx="50" ry="50" fill="none" '
    'stroke="#D8D3C9" stroke-width="2"/>'
    # top «
    '<g stroke="#D97757" stroke-width="22" fill="none" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M120 56 L70 100 L120 144"/>'
    '<path d="M186 56 L136 100 L186 144"/>'
    '</g>'
    # bottom «  (offset down + slightly right for the stair-step look)
    '<g stroke="#D97757" stroke-width="22" fill="none" opacity="0.92" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M132 112 L82 156 L132 200"/>'
    '<path d="M198 112 L148 156 L198 200"/>'
    '</g>'
    # subtle LShift wordmark bottom-right
    '<text x="240" y="240" font-family="Inter, \'Segoe UI\', system-ui, sans-serif" '
    'font-size="14" fill="#B0A99E" text-anchor="end" font-weight="500" '
    'letter-spacing="0.5">LShift</text>'
    '</svg>'
)


def _render_svg_to_pixmap(svg: str, size: int) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()
    return pm


def app_icon():
    """Build a multi-resolution QIcon for the application from the brand SVG.

    QIcon picks the closest-matching size from its internal pixmap cache,
    so providing 16 / 24 / 32 / 48 / 64 / 128 / 256 keeps the icon crisp
    in the OS taskbar, Alt-Tab switcher, and window decorations.
    """
    from PyQt6.QtGui import QIcon

    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_render_svg_to_pixmap(_APP_ICON_SVG, size))
    return icon
