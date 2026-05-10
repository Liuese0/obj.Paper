"""Document format presets (spec §9).

Each preset returns a fresh `DocumentSettings` so callers can mutate freely.
The `apply_to(doc)` helper preserves the document content while replacing the
settings.
"""

from __future__ import annotations

from .document import Document, DocumentSettings


def _general() -> DocumentSettings:
    return DocumentSettings(
        body_font="Times New Roman", title_font="Times New Roman",
        body_size=12, line_spacing=1.5,
        paper="A4", orientation="portrait", columns=1,
        margin_top=25, margin_bottom=25, margin_left=25, margin_right=25,
        template="general",
    )


def _ieee() -> DocumentSettings:
    return DocumentSettings(
        body_font="Times New Roman", title_font="Times New Roman",
        body_size=10, line_spacing=1.0,
        paper="Letter", orientation="portrait", columns=2,
        margin_top=19, margin_bottom=25, margin_left=15, margin_right=15,
        template="ieee",
    )


def _acm() -> DocumentSettings:
    return DocumentSettings(
        body_font="Linux Libertine", title_font="Linux Libertine",
        body_size=10, line_spacing=1.15,
        paper="Letter", orientation="portrait", columns=2,
        margin_top=25, margin_bottom=25, margin_left=20, margin_right=20,
        template="acm",
    )


def _nature() -> DocumentSettings:
    return DocumentSettings(
        body_font="Arial", title_font="Arial",
        body_size=10, line_spacing=1.5,
        paper="A4", orientation="portrait", columns=1,
        margin_top=30, margin_bottom=30, margin_left=30, margin_right=30,
        template="nature",
    )


def _lncs() -> DocumentSettings:
    return DocumentSettings(
        body_font="Times New Roman", title_font="Times New Roman",
        body_size=10, line_spacing=1.2,
        paper="A4", orientation="portrait", columns=1,
        margin_top=25, margin_bottom=25, margin_left=25, margin_right=25,
        template="lncs",
    )


def _apa() -> DocumentSettings:
    return DocumentSettings(
        body_font="Times New Roman", title_font="Times New Roman",
        body_size=12, line_spacing=2.0,
        paper="Letter", orientation="portrait", columns=1,
        margin_top=30, margin_bottom=30, margin_left=30, margin_right=30,
        template="apa",
    )


TEMPLATES: dict[str, dict] = {
    "general": {"name": "General", "factory": _general},
    "ieee": {"name": "IEEE Conference", "factory": _ieee},
    "acm": {"name": "ACM SIGPLAN", "factory": _acm},
    "nature": {"name": "Nature Journals", "factory": _nature},
    "lncs": {"name": "Springer LNCS", "factory": _lncs},
    "apa": {"name": "APA Style", "factory": _apa},
}

TEMPLATE_ORDER = ["ieee", "acm", "nature", "lncs", "apa", "general"]


def make_settings(template_id: str) -> DocumentSettings:
    if template_id not in TEMPLATES:
        template_id = "general"
    return TEMPLATES[template_id]["factory"]()


def template_name(template_id: str) -> str:
    return TEMPLATES.get(template_id, TEMPLATES["general"])["name"]


def apply_to(doc: Document, template_id: str) -> None:
    """Replace document settings with the named preset, preserving blocks."""
    doc.replace_settings(make_settings(template_id))
