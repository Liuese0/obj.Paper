"""JSON v2 round-trip + v1 backward compat (spec §11)."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from obj_paper.document import BlockData, Document, DocumentSettings, starter_document


def test_starter_document_basics():
    d = starter_document()
    assert d.block_count() >= 5
    assert d.word_count() > 0
    assert d.dirty is False
    assert d.settings.template == "general"


def test_v2_roundtrip(tmp_path):
    d = starter_document()
    d.title = "round_trip"
    payload = d.to_json()
    assert payload["version"] == 2
    raw = json.dumps(payload, ensure_ascii=False)
    d2 = Document.from_json(json.loads(raw))
    assert d2.title == "round_trip"
    assert d2.block_count() == d.block_count()
    for a, b in zip(d.blocks, d2.blocks):
        assert a.type == b.type
        assert a.data == b.data


def test_save_load_disk(tmp_path):
    d = starter_document()
    p = tmp_path / "out.pw"
    d.save(str(p))
    assert os.path.exists(p)
    d2 = Document.load(str(p))
    assert d2.block_count() == d.block_count()
    assert d2.path == str(p)
    assert d2.dirty is False


def test_v1_backward_compat():
    """v1 used a flat `{title, blocks}` layout without a settings dict."""
    v1 = {
        "version": 1,
        "title": "old doc",
        "blocks": [
            {"id": "x", "type": "paragraph", "data": {"text": "hello"}},
            {"id": "y", "type": "title", "data": {"text": "World"}},
        ],
    }
    d = Document.from_json(v1)
    assert d.title == "Untitled"  # meta absent → default
    assert len(d.blocks) == 2
    assert d.blocks[0].type == "paragraph"
    assert d.settings.template == "general"


def test_block_crud():
    d = Document(title="t")
    a = BlockData.make("paragraph", {"text": "A"})
    b = BlockData.make("paragraph", {"text": "B"})
    d.insert_block(a)
    d.insert_block(b)
    assert d.block_count() == 2
    d.move_block(a.id, +1)
    assert d.blocks[0].id == b.id
    d.remove_block(b.id)
    assert d.block_count() == 1


def test_dirty_tracking(tmp_path):
    d = Document(title="t")
    p = tmp_path / "f.pw"
    d.save(str(p))
    assert d.dirty is False
    d.insert_block(BlockData.make("paragraph", {"text": "x"}))
    assert d.dirty is True
    d.save(str(p))
    assert d.dirty is False
