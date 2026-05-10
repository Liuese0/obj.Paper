"""Snapshot-style assertions for each block type's HTML output."""

from __future__ import annotations

import re

import pytest

from obj_paper import render
from obj_paper.document import BlockData, Document, DocumentSettings


def _make(blocks):
    d = Document(title="t")
    for b in blocks:
        d.insert_block(b)
    d.set_dirty(False)
    return d


def test_title_renders_h1():
    d = _make([BlockData.make("title", {"text": "Hello"})])
    html = render.document_to_html(d, mode="preview")
    assert "<h1" in html and "Hello" in html


def test_authors_marks_corresponding():
    d = _make([
        BlockData.make("authors", {"authors": [
            {"name": "A", "affiliation": "X", "email": "", "corresponding": False},
            {"name": "B", "affiliation": "X", "email": "b@x", "corresponding": True},
        ]}),
    ])
    html = render.document_to_html(d, mode="preview")
    assert "†" in html
    assert "b@x" in html


def test_heading_numbering_resets():
    d = _make([
        BlockData.make("heading", {"level": 1, "text": "A"}),
        BlockData.make("heading", {"level": 2, "text": "A.1"}),
        BlockData.make("heading", {"level": 1, "text": "B"}),
        BlockData.make("heading", {"level": 2, "text": "B.1"}),
    ])
    html = render.document_to_html(d, mode="preview")
    assert ">1.<" in html
    assert ">1.1.<" in html
    assert ">2.<" in html
    assert ">2.1.<" in html


def test_paragraph_inline_math_becomes_image():
    d = _make([BlockData.make("paragraph", {"text": "Energy is $E=mc^2$ today."})])
    html = render.document_to_html(d, mode="preview")
    assert "data:image/png;base64," in html


def test_equation_numbering():
    d = _make([
        BlockData.make("equation", {"latex": "x"}),
        BlockData.make("equation", {"latex": "y"}),
    ])
    html = render.document_to_html(d, mode="preview")
    assert "(1)" in html and "(2)" in html


def test_code_with_pygments():
    d = _make([BlockData.make("code", {"language": "python", "code": "print(1)"})])
    html = render.document_to_html(d, mode="preview")
    assert "print" in html


def test_pagebreak_in_export_uses_css_break():
    d = _make([BlockData.make("pagebreak", {})])
    html = render.document_to_html(d, mode="export-pdf")
    assert "page-break-after" in html


def test_export_html_is_self_contained():
    d = _make([BlockData.make("title", {"text": "X"})])
    html = render.document_to_html(d, mode="export-html")
    assert html.startswith("<!DOCTYPE")
    assert "<title>" in html


def test_estimate_pages_minimum_one():
    d = _make([])
    assert render.estimate_pages(d) >= 1
