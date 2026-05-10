"""Verify each preset produces the expected layout (spec §9 table)."""

from __future__ import annotations

import pytest

from obj_paper.templates import TEMPLATE_ORDER, TEMPLATES, apply_to, make_settings, template_name
from obj_paper.document import Document, starter_document


@pytest.mark.parametrize("tid", TEMPLATE_ORDER)
def test_each_template_produces_consistent_settings(tid):
    s = make_settings(tid)
    assert s.template == tid
    assert s.body_size in (10, 11, 12, 13)
    assert s.paper in ("A4", "Letter")


def test_specific_template_values():
    ieee = make_settings("ieee")
    assert ieee.paper == "Letter" and ieee.columns == 2 and ieee.body_size == 10
    nat = make_settings("nature")
    assert nat.paper == "A4" and nat.columns == 1 and nat.body_font == "Arial"
    apa = make_settings("apa")
    assert apa.paper == "Letter" and apa.body_size == 12


def test_apply_to_preserves_blocks():
    d = starter_document()
    n = d.block_count()
    apply_to(d, "ieee")
    assert d.block_count() == n
    assert d.settings.template == "ieee"


def test_template_name_lookup():
    assert "IEEE" in template_name("ieee")
    assert "General" in template_name("general")
