"""Document data model — the single source of truth for editor state.

Every block lives as a `BlockData` dict-like dataclass. Block widgets read/write
the underlying `BlockData` fields. The `Document` aggregate emits `changed`
whenever its content is mutated so the canvas/preview can react.

Save format follows spec §11 (JSON v2). v1 documents load best-effort.
"""

from __future__ import annotations

import copy
import json
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------- types ----------
@dataclass
class BlockData:
    id: str
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    settings: dict[str, Any] = field(
        default_factory=lambda: {
            "alignment": "left",
            "spacing_before": 12,
            "spacing_after": 12,
        }
    )

    @classmethod
    def make(cls, type_id: str, data: dict[str, Any] | None = None) -> "BlockData":
        return cls(id=_new_id(), type=type_id, data=dict(data or {}))

    def clone(self) -> "BlockData":
        new = copy.deepcopy(self)
        new.id = _new_id()
        return new

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


@dataclass
class DocumentSettings:
    """Spec §8 fields. Use `apply_preset` for §9 templates."""

    body_font: str = "Times New Roman"
    title_font: str = "Times New Roman"
    body_size: int = 12
    line_spacing: float = 1.5
    paper: str = "A4"
    orientation: str = "portrait"
    margin_top: int = 25
    margin_bottom: int = 25
    margin_left: int = 25
    margin_right: int = 25
    columns: int = 1
    section_numbering: bool = True
    figure_numbering: bool = True
    table_numbering: bool = True
    equation_numbering: bool = True
    template: str = "general"


# ---------- aggregate ----------
class Document(QObject):
    """Mutable document. Mutators emit `changed`, file state changes emit `dirtyChanged`."""

    changed = pyqtSignal()  # any block / settings change
    dirtyChanged = pyqtSignal(bool)
    pathChanged = pyqtSignal(object)  # str | None
    blocksReplaced = pyqtSignal()  # blocks list reset (open/new doc)

    def __init__(
        self,
        title: str = "Untitled",
        blocks: list[BlockData] | None = None,
        settings: DocumentSettings | None = None,
    ):
        super().__init__()
        self.title = title
        self.created = _now_iso()
        self.modified = _now_iso()
        self.settings = settings or DocumentSettings()
        self.blocks: list[BlockData] = list(blocks or [])
        self._path: str | None = None
        self._dirty = False
        self._last_saved_at: datetime | None = None
        self._lock = threading.Lock()

    # ----- file state -----
    @property
    def path(self) -> str | None:
        return self._path

    def set_path(self, p: str | None) -> None:
        if p == self._path:
            return
        self._path = p
        self.pathChanged.emit(p)

    @property
    def dirty(self) -> bool:
        return self._dirty

    def set_dirty(self, v: bool) -> None:
        if v == self._dirty:
            return
        self._dirty = v
        self.dirtyChanged.emit(v)

    @property
    def last_saved_at(self) -> datetime | None:
        return self._last_saved_at

    # ----- block CRUD -----
    def insert_block(self, block: BlockData, index: int | None = None) -> int:
        if index is None or index >= len(self.blocks):
            self.blocks.append(block)
            idx = len(self.blocks) - 1
        else:
            idx = max(0, index)
            self.blocks.insert(idx, block)
        self._touch()
        return idx

    def remove_block(self, block_id: str) -> int | None:
        for i, b in enumerate(self.blocks):
            if b.id == block_id:
                del self.blocks[i]
                self._touch()
                return i
        return None

    def move_block(self, block_id: str, delta: int) -> None:
        for i, b in enumerate(self.blocks):
            if b.id == block_id:
                j = max(0, min(len(self.blocks) - 1, i + delta))
                if i != j:
                    self.blocks.insert(j, self.blocks.pop(i))
                    self._touch()
                return

    def index_of(self, block_id: str) -> int | None:
        for i, b in enumerate(self.blocks):
            if b.id == block_id:
                return i
        return None

    def replace_settings(self, s: DocumentSettings) -> None:
        self.settings = s
        self._touch()

    def update_block_data(self, block_id: str, **fields: Any) -> None:
        b = self._find(block_id)
        if not b:
            return
        b.data.update(fields)
        self._touch()

    def _find(self, block_id: str) -> BlockData | None:
        for b in self.blocks:
            if b.id == block_id:
                return b
        return None

    def _touch(self) -> None:
        self.modified = _now_iso()
        self.set_dirty(True)
        self.changed.emit()

    # ----- statistics for status bar (spec §14) -----
    def word_count(self) -> int:
        from . import render

        n = 0
        for b in self.blocks:
            n += render.estimate_words(b)
        return n

    def block_count(self) -> int:
        return len(self.blocks)

    # ----- serialization (spec §11) -----
    def to_json(self) -> dict:
        return {
            "version": 2,
            "meta": {
                "created": self.created,
                "modified": self.modified,
                "title": self.title,
            },
            "settings": asdict(self.settings),
            "blocks": [asdict(b) for b in self.blocks],
        }

    @classmethod
    def from_json(cls, payload: dict) -> "Document":
        meta = payload.get("meta", {})
        settings_d = payload.get("settings", {}) or {}
        blocks_d = payload.get("blocks", []) or []

        clean = {k: v for k, v in settings_d.items() if k in DocumentSettings().__dict__}
        settings = DocumentSettings(**clean)

        blocks: list[BlockData] = []
        for raw in blocks_d:
            bd = BlockData(
                id=raw.get("id") or _new_id(),
                type=raw.get("type", "paragraph"),
                data=raw.get("data", {}),
                settings=raw.get("settings")
                or {"alignment": "left", "spacing_before": 12, "spacing_after": 12},
            )
            blocks.append(bd)

        d = cls(
            title=meta.get("title", "Untitled"),
            blocks=blocks,
            settings=settings,
        )
        d.created = meta.get("created", _now_iso())
        d.modified = meta.get("modified", _now_iso())
        return d

    def save(self, path: str) -> None:
        with self._lock:
            self.modified = _now_iso()
            payload = self.to_json()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self.set_path(path)
            self.title = payload["meta"]["title"]
            self._last_saved_at = datetime.now(timezone.utc)
            self.set_dirty(False)

    @classmethod
    def load(cls, path: str) -> "Document":
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        d = cls.from_json(payload)
        d.set_path(path)
        d._last_saved_at = datetime.now(timezone.utc)
        d.set_dirty(False)
        return d

    # ----- batch replace (open new file) -----
    def replace_with(self, other: "Document") -> None:
        self.title = other.title
        self.created = other.created
        self.modified = other.modified
        self.settings = other.settings
        self.blocks = list(other.blocks)
        self.set_path(other.path)
        self._last_saved_at = other.last_saved_at
        self.blocksReplaced.emit()
        self.set_dirty(False)
        self.changed.emit()


def starter_document() -> Document:
    """Initial blocks for the first launch — mirrors the mockup content."""
    blocks = [
        BlockData.make("title", {"text": "Deep Learning for Real-Time Signal Analysis"}),
        BlockData.make(
            "authors",
            {
                "authors": [
                    {
                        "name": "이준영",
                        "affiliation": "강릉원주대학교 컴퓨터공학과",
                        "email": "",
                        "corresponding": False,
                    },
                    {
                        "name": "김창화",
                        "affiliation": "지도교수",
                        "email": "ch.kim@gwnu.ac.kr",
                        "corresponding": True,
                    },
                ]
            },
        ),
        BlockData.make(
            "abstract",
            {
                "keywords": "deep learning, signal processing, real-time, neural networks",
                "text": (
                    "This paper presents a novel approach to real-time signal "
                    "processing using deep neural networks optimized for embedded "
                    "inference. We propose a hybrid architecture that combines "
                    "temporal convolutional layers with a lightweight attention "
                    "mechanism, achieving sub-millisecond latency on commodity "
                    "hardware while maintaining state-of-the-art classification "
                    "accuracy."
                ),
            },
        ),
        BlockData.make("heading", {"level": 1, "text": "Introduction", "numbered": True}),
        BlockData.make(
            "paragraph",
            {
                "text": (
                    "Recent advances in deep learning have demonstrated remarkable "
                    "performance in signal classification tasks [1, 2]. However, "
                    "deploying such models in real-time embedded systems remains "
                    "challenging due to their computational footprint."
                )
            },
        ),
        BlockData.make(
            "equation",
            {
                "latex": r"\hat{y}_t = \sigma(W_a \cdot h_t + \sum_{i=1}^{k} \alpha_i x_{t-i})",
                "label": "eq:model",
            },
        ),
        BlockData.make("heading", {"level": 1, "text": "Related Work", "numbered": True}),
        BlockData.make(
            "paragraph",
            {
                "text": (
                    "Edge inference for time-series data has been studied "
                    "extensively. Lin et al. [3] introduced sparse temporal kernels."
                )
            },
        ),
        BlockData.make(
            "code",
            {
                "language": "python",
                "code": "def forward(self, x):\n    h = self.tcn(x)\n    return self.attn(h, h)",
                "caption": "",
                "show_lines": True,
            },
        ),
    ]
    d = Document(title="my_paper", blocks=blocks)
    d.set_dirty(False)
    return d
