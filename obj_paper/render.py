"""Document → HTML rendering.

Used in three places:
- preview pane (mode="preview"): A4 page card with inline styles
- HTML export (mode="export-html"): standalone single-file HTML
- PDF export (mode="export-pdf"): QTextDocument-friendly subset

Inline math `$…$` inside paragraph/abstract/heading text is converted to
embedded `<img>` via `latex.render_latex_data_uri`. Bracketed citations like
`[[cite:smith2020]]` collapse to a numeric `[N]` based on first-seen order.
"""

from __future__ import annotations

import html
import re
from typing import Iterable

from . import theme as T
from .document import BlockData, Document, DocumentSettings
from . import latex


# ---------- helpers ----------
_INLINE_MATH_RE = re.compile(r"\$([^$\n]+)\$")
_CITE_RE = re.compile(r"\[\[cite:([^\]]+)\]\]")


def _esc(s: str) -> str:
    return html.escape(s or "", quote=False)


def _inline_math(text: str) -> str:
    """Replace `$...$` with embedded LaTeX PNG images."""

    def repl(m: re.Match) -> str:
        try:
            uri = latex.render_latex_data_uri(m.group(1))
        except Exception:
            return _esc(m.group(0))
        return f'<img src="{uri}" style="vertical-align:middle;height:1.1em;" alt="formula"/>'

    return _INLINE_MATH_RE.sub(repl, text)


def _cite(text: str, citation_keys: list[str]) -> str:
    """Replace `[[cite:key]]` with numeric `[N]`."""

    def repl(m: re.Match) -> str:
        key = m.group(1).strip()
        if key not in citation_keys:
            citation_keys.append(key)
        return f"[{citation_keys.index(key) + 1}]"

    return _CITE_RE.sub(repl, text)


def _process_inline(text: str, citation_keys: list[str]) -> str:
    """Apply citation + math substitutions on top of HTML-escaped text."""
    safe = _esc(text)
    safe = _cite(safe, citation_keys)
    return _inline_math(safe)


# ---------- per-block renderers ----------
def estimate_words(block: BlockData) -> int:
    text_fields = []
    if block.type in ("title", "heading", "paragraph"):
        text_fields.append(block.data.get("text", ""))
    elif block.type == "abstract":
        text_fields.append(block.data.get("text", ""))
        text_fields.append(block.data.get("keywords", ""))
    elif block.type == "list":
        text_fields.extend(block.data.get("items", []))
    elif block.type == "code":
        text_fields.append(block.data.get("code", ""))
    elif block.type == "authors":
        for a in block.data.get("authors", []):
            text_fields.append(a.get("name", ""))
    return sum(len([w for w in (s or "").split() if w]) for s in text_fields)


def _heading_number(level: int, counters: dict[int, int]) -> str:
    """1.1.1 numbering. Resets deeper counters when a higher level increments."""
    counters[level] = counters.get(level, 0) + 1
    for deeper in (level + 1, level + 2):
        counters.pop(deeper, None)
    parts = [str(counters.get(i, 0)) for i in range(1, level + 1)]
    return ".".join(parts) + "."


# ---------- counters used across render passes ----------
class RenderState:
    def __init__(self, settings: DocumentSettings):
        self.settings = settings
        self.heading_counters: dict[int, int] = {}
        self.fig_n = 0
        self.tab_n = 0
        self.eq_n = 0
        self.citation_keys: list[str] = []


def _block_html(block: BlockData, st: RenderState, mode: str) -> str:
    fn = _RENDERERS.get(block.type)
    if not fn:
        return f"<p style='color:{T.ERROR}'>Unknown block: {_esc(block.type)}</p>"
    return fn(block, st, mode)


def _r_title(b: BlockData, st: RenderState, mode: str) -> str:
    text = _process_inline(b.data.get("text", ""), st.citation_keys)
    return (
        f'<h1 style="text-align:center;font-family:{st.settings.title_font!r}, serif;'
        f'font-size:1.8em;font-weight:700;margin:0 0 12pt 0;line-height:1.2;">'
        f"{text}</h1>"
    )


def _r_authors(b: BlockData, st: RenderState, mode: str) -> str:
    authors = b.data.get("authors", [])
    if not authors:
        return ""
    affiliations: list[str] = []
    name_parts: list[str] = []
    for a in authors:
        aff = a.get("affiliation", "")
        if aff and aff not in affiliations:
            affiliations.append(aff)
        idx = affiliations.index(aff) + 1 if aff else None
        marker = ""
        if idx:
            marker = f"<sup style='color:{T.ACCENT}'>{idx}{'†' if a.get('corresponding') else ''}</sup>"
        name_parts.append(f"{_esc(a.get('name',''))}{marker}")
    aff_lines = "".join(
        f"<sup>{i+1}</sup>{_esc(aff)} &nbsp; " for i, aff in enumerate(affiliations) if aff
    )
    cor_email = next((a.get("email", "") for a in authors if a.get("corresponding")), "")
    cor_line = (
        f"<div style='font-family:\"JetBrains Mono\",monospace;font-size:.78em;color:{T.MIST};margin-top:4pt;'>† {_esc(cor_email)}</div>"
        if cor_email
        else ""
    )
    return (
        f"<div style='text-align:center;margin:0 0 12pt 0;'>"
        f"<div style='font-size:1.05em'>{', &nbsp;'.join(name_parts)}</div>"
        f"<div style='font-size:.85em;color:{T.DUST};margin-top:4pt'>{aff_lines}</div>"
        f"{cor_line}"
        f"</div>"
    )


def _r_abstract(b: BlockData, st: RenderState, mode: str) -> str:
    text = _process_inline(b.data.get("text", ""), st.citation_keys)
    keywords = _esc(b.data.get("keywords", ""))
    kw = (
        f"<div style='font-family:\"JetBrains Mono\",monospace;font-size:.78em;letter-spacing:.08em;color:{T.DUST};margin-top:6pt'>"
        f"<strong>KEYWORDS</strong> &nbsp;{keywords}</div>"
        if keywords
        else ""
    )
    return (
        f"<div style='margin:0 auto 12pt auto;max-width:90%'>"
        f"<div style='font-weight:700;letter-spacing:.06em;font-size:.9em;margin-bottom:4pt;color:{T.INK}'>ABSTRACT</div>"
        f"<p style='margin:0;text-align:justify;line-height:{st.settings.line_spacing};'>{text}</p>"
        f"{kw}"
        f"</div>"
    )


def _r_heading(b: BlockData, st: RenderState, mode: str) -> str:
    level = max(1, min(3, int(b.data.get("level", 1))))
    text = _process_inline(b.data.get("text", ""), st.citation_keys)
    numbered = b.data.get("numbered", True) and st.settings.section_numbering
    number = _heading_number(level, st.heading_counters) + " " if numbered else ""
    sizes = {1: "1.35em", 2: "1.15em", 3: "1.05em"}
    return (
        f"<h{level} style='font-family:{st.settings.title_font!r}, serif;font-size:{sizes[level]};"
        f"font-weight:700;margin:14pt 0 6pt 0;line-height:1.3;'>"
        f"<span style='color:{T.ACCENT};margin-right:6pt'>{_esc(number).strip()}</span>{text}"
        f"</h{level}>"
    )


def _r_paragraph(b: BlockData, st: RenderState, mode: str) -> str:
    text = _process_inline(b.data.get("text", ""), st.citation_keys)
    align = b.settings.get("alignment", "justify") if b.settings else "justify"
    return (
        f"<p style='margin:6pt 0;text-align:{align};line-height:{st.settings.line_spacing};'>"
        f"{text}</p>"
    )


def _r_equation(b: BlockData, st: RenderState, mode: str) -> str:
    src = b.data.get("latex", "")
    try:
        uri = latex.render_latex_data_uri(src, dpi=240, fontsize=18)
        img = f"<img src='{uri}' style='max-width:80%;height:auto' alt='equation'/>"
    except Exception:
        img = f"<code style='font-family:\"JetBrains Mono\",monospace;font-style:italic'>{_esc(src)}</code>"
    number_html = ""
    if st.settings.equation_numbering:
        st.eq_n += 1
        number_html = (
            f"<td style='width:48pt;text-align:right;color:{T.DUST};vertical-align:middle;'>({st.eq_n})</td>"
        )
    label_attr = f"id='eq-{_esc(b.data.get('label',''))}'" if b.data.get("label") else ""
    return (
        f"<table {label_attr} cellspacing='0' cellpadding='0' style='width:100%;margin:8pt 0;'>"
        f"<tr><td style='text-align:center;vertical-align:middle;'>{img}</td>{number_html}</tr>"
        f"</table>"
    )


def _r_figure(b: BlockData, st: RenderState, mode: str) -> str:
    src = b.data.get("image_path", "") or b.data.get("image_data_uri", "")
    width = b.data.get("width_pct", 80)
    caption = _esc(b.data.get("caption", ""))
    placeholder = (
        f"<div style='aspect-ratio:16/8;background:repeating-linear-gradient(45deg,{T.SURFACE_2} 0 8px,{T.BG} 8px 16px);"
        f"border:1px dashed {T.BORDER};display:flex;align-items:center;justify-content:center;color:{T.DUST};"
        f"font-family:\"JetBrains Mono\",monospace;font-size:.8em;'>{_esc(b.data.get('placeholder','figure placeholder'))}</div>"
    )
    img = (
        f"<img src='{_esc(src)}' style='max-width:{int(width)}%;height:auto;display:block;margin:0 auto;'/>"
        if src
        else placeholder
    )
    label = ""
    if st.settings.figure_numbering and caption:
        st.fig_n += 1
        label = f"<strong style='color:{T.ACCENT}'>Fig. {st.fig_n}</strong> "
    cap = (
        f"<div style='text-align:center;font-size:.85em;color:{T.INK};margin-top:6pt;'>{label}{caption}</div>"
        if caption
        else ""
    )
    return f"<figure style='margin:8pt 0;'>{img}{cap}</figure>"


def _r_table(b: BlockData, st: RenderState, mode: str) -> str:
    rows = b.data.get("rows", []) or []
    caption = _esc(b.data.get("caption", ""))
    label = ""
    if st.settings.table_numbering and caption:
        st.tab_n += 1
        label = f"<strong style='color:{T.ACCENT}'>Table {st.tab_n}</strong> "
    cells_html = []
    for r, row in enumerate(rows):
        tag = "th" if r == 0 else "td"
        cells = "".join(
            f"<{tag} style='border:1px solid {T.BORDER};padding:6pt 8pt;font-size:.9em;'>{_esc(c)}</{tag}>"
            for c in row
        )
        cells_html.append(f"<tr>{cells}</tr>")
    cap = f"<caption style='caption-side:top;font-size:.85em;margin-bottom:4pt;'>{label}{caption}</caption>" if caption else ""
    return (
        f"<table cellspacing='0' cellpadding='0' style='border-collapse:collapse;margin:8pt auto;width:100%;'>{cap}"
        f"{''.join(cells_html)}</table>"
    )


def _r_list(b: BlockData, st: RenderState, mode: str) -> str:
    items = b.data.get("items", []) or []
    ordered = bool(b.data.get("ordered", False))
    tag = "ol" if ordered else "ul"
    li = "".join(f"<li style='margin:2pt 0'>{_process_inline(i or '', st.citation_keys)}</li>" for i in items)
    return f"<{tag} style='margin:6pt 0 6pt 22pt;line-height:{st.settings.line_spacing};'>{li}</{tag}>"


def _r_code(b: BlockData, st: RenderState, mode: str) -> str:
    code = b.data.get("code", "")
    language = b.data.get("language", "text")
    show_lines = bool(b.data.get("show_lines", False))
    caption = _esc(b.data.get("caption", ""))
    try:
        from pygments import highlight
        from pygments.lexers import get_lexer_by_name, TextLexer
        from pygments.formatters import HtmlFormatter

        try:
            lexer = get_lexer_by_name(language, stripall=False)
        except Exception:
            lexer = TextLexer()
        formatter = HtmlFormatter(noclasses=True, style="friendly", linenos="inline" if show_lines else False)
        body = highlight(code, lexer, formatter)
    except Exception:
        body = (
            f"<pre style='font-family:\"JetBrains Mono\",monospace;font-size:.85em;"
            f"background:#FBF9F2;border:1px solid {T.BORDER};border-radius:4px;padding:8pt 10pt;'>"
            f"{_esc(code)}</pre>"
        )
    cap = (
        f"<div style='font-size:.78em;color:{T.DUST};margin-top:4pt'>{caption}</div>"
        if caption
        else ""
    )
    return f"<div style='margin:8pt 0;'>{body}{cap}</div>"


def _r_references(b: BlockData, st: RenderState, mode: str) -> str:
    bib = b.data.get("bibtex", "")
    items = _parse_bibtex(bib)
    if not items:
        return f"<p style='color:{T.DUST};font-style:italic'>(no references)</p>"
    style = b.data.get("style", "ieee")
    lis = []
    for i, e in enumerate(items, 1):
        line = _format_reference(e, style, i)
        lis.append(f"<li id='ref-{e.get('key','')}' style='margin:2pt 0'>{line}</li>")
    return (
        f"<h2 style='font-family:{st.settings.title_font!r}, serif;font-size:1.15em;margin:14pt 0 6pt 0;'>References</h2>"
        f"<ol style='margin:0 0 0 22pt;font-size:.9em'>{''.join(lis)}</ol>"
    )


def _r_pagebreak(b: BlockData, st: RenderState, mode: str) -> str:
    if mode == "preview":
        return f"<div style='border-top:1px dashed {T.BORDER};margin:18pt 0;text-align:center;color:{T.MIST};font-size:.7em;letter-spacing:.2em'>PAGE BREAK</div>"
    return "<div style='page-break-after:always'></div>"


_RENDERERS = {
    "title": _r_title,
    "authors": _r_authors,
    "abstract": _r_abstract,
    "heading": _r_heading,
    "paragraph": _r_paragraph,
    "equation": _r_equation,
    "figure": _r_figure,
    "table": _r_table,
    "list": _r_list,
    "code": _r_code,
    "references": _r_references,
    "pagebreak": _r_pagebreak,
}


# ---------- BibTeX (minimal) ----------
_BIB_ENTRY = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,(.+?)\}\s*(?=@|\Z)", re.DOTALL)
_BIB_FIELD = re.compile(r"(\w+)\s*=\s*[{\"]([^{}\"]+)[}\"]")


def _parse_bibtex(src: str) -> list[dict]:
    out = []
    for entry in _BIB_ENTRY.finditer(src or ""):
        kind, key, body = entry.group(1), entry.group(2), entry.group(3)
        fields = {m.group(1).lower(): m.group(2).strip() for m in _BIB_FIELD.finditer(body)}
        fields.update({"_kind": kind, "key": key})
        out.append(fields)
    return out


def _format_reference(e: dict, style: str, n: int) -> str:
    author = _esc(e.get("author", ""))
    title = _esc(e.get("title", ""))
    journal = _esc(e.get("journal", e.get("booktitle", "")))
    year = _esc(e.get("year", ""))
    if style == "ieee":
        return f"[{n}] {author}, “{title},” <em>{journal}</em>, {year}."
    if style == "apa":
        return f"{author} ({year}). {title}. <em>{journal}</em>."
    return f"[{n}] {author}. <em>{title}</em>. {journal}, {year}."


# ---------- top-level ----------
def document_to_html(doc: Document, mode: str = "preview") -> str:
    st = RenderState(doc.settings)
    body = "\n".join(_block_html(b, st, mode) for b in doc.blocks)

    page_w_mm, page_h_mm = _paper_mm(doc.settings)
    margins = (
        doc.settings.margin_top,
        doc.settings.margin_right,
        doc.settings.margin_bottom,
        doc.settings.margin_left,
    )
    page_style = (
        f"max-width:{page_w_mm}mm;min-height:{page_h_mm}mm;"
        f"padding:{margins[0]}mm {margins[1]}mm {margins[2]}mm {margins[3]}mm;"
        f"background:{T.SURFACE};color:{T.INK};"
        f"font-family:{doc.settings.body_font!r}, serif;"
        f"font-size:{doc.settings.body_size}pt;line-height:{doc.settings.line_spacing};"
        f"box-sizing:border-box;margin:0 auto;"
        f"box-shadow:0 18px 36px -12px rgba(44,40,32,.18), 0 2px 6px rgba(44,40,32,.06);"
    )

    if mode == "export-pdf":
        # QTextDocument-friendly: no shadow, no max-width
        return (
            f"<html><head><meta charset='utf-8'></head><body "
            f"style='font-family:{doc.settings.body_font!r}, serif;"
            f"font-size:{doc.settings.body_size}pt;line-height:{doc.settings.line_spacing};color:{T.INK};'>"
            f"{body}</body></html>"
        )

    if mode == "export-html":
        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<title>{_esc(doc.title)}</title>"
            "<style>"
            f"body{{margin:0;padding:24px;background:{T.BG};}}"
            f".page{{{page_style}}}"
            "@media print { body{background:white;padding:0;} .page{box-shadow:none;margin:0;} }"
            "</style></head><body>"
            f"<div class='page'>{body}</div></body></html>"
        )

    # preview
    return (
        f"<html><body style='margin:0;padding:0;background:{T.SURFACE_2};'>"
        f"<div style='{page_style}'>{body}</div></body></html>"
    )


def _paper_mm(s: DocumentSettings) -> tuple[float, float]:
    table = {
        "A4": (210.0, 297.0),
        "Letter": (215.9, 279.4),
        "Legal": (215.9, 355.6),
        "B5": (176.0, 250.0),
    }
    w, h = table.get(s.paper, table["A4"])
    return (h, w) if s.orientation == "landscape" else (w, h)


def estimate_pages(doc: Document) -> int:
    """Crude page estimate (status bar).

    ~3500 chars per A4 page at 12pt. Page breaks add a page each.
    """
    chars = 0
    extra = 0
    for b in doc.blocks:
        if b.type == "pagebreak":
            extra += 1
        else:
            chars += len(b.data.get("text", "") or "")
            chars += len(b.data.get("code", "") or "")
            chars += sum(len(i or "") for i in b.data.get("items", []) or [])
    body = max(1, (chars + 3499) // 3500)
    return body + extra
