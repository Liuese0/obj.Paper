# obj.Paper

> Block-based academic paper editor with live PDF preview. Built in PyQt6.
> Brand: **LShift** (`<<`).

`obj.Paper` lets you write academic papers as a stack of typed **blocks** —
title, authors, abstract, headings, paragraphs, equations, figures, tables,
code, references, and more — while a live PDF-style preview tracks your edits
in real time. One click exports a PDF or a single-file HTML.

This repository implements [`spec.md`](spec.md) v1.0.

---

## Features (v1.0 spec coverage)

| Spec | Feature | Status |
|------|---------|--------|
| §3   | Parchment / Terracotta color system | ✅ |
| §4   | UI + document typography (Times NR, Arial, Georgia, …) | ✅ |
| §5   | 3-pane layout: palette · canvas · preview | ✅ |
| §5.4 | Resizable preview pane (240–480px) | ✅ |
| §6   | All 12 block types | ✅ |
| §7   | Floating inline B/I/U/S/∑/🔗 toolbar | ✅ |
| §8   | Slide-in Document Settings panel | ✅ |
| §9   | 6 paper-format templates (IEEE/ACM/Nature/LNCS/APA/General) | ✅ |
| §10  | PDF export (QPrinter) + HTML export (single file, base64 LaTeX) | ✅ |
| §11  | `.pw` JSON v2 with v1 backward compat + 30 s autosave | ✅ |
| §12  | Full keymap (14 shortcuts) | ✅ |
| §13  | Instant 한국어 ↔ English toggle | ✅ |
| §14  | Status bar (saved · blocks · words · pages · language) | ✅ |
| §15  | Focus mode (F11) | ✅ |
| §16  | Reference PDF tab via QPdfView | ✅ |
| §17.2| `@register_block` extension hook | ✅ |

LaTeX in equations and inline `$…$` is rendered through matplotlib's
mathtext parser into base64 PNGs, so no system-wide LaTeX install is needed.

---

## Quick start

```bash
git clone https://github.com/Liuese0/obj.Paper.git
cd obj.Paper
pip install -r requirements.txt
python -m obj_paper
```

Requires Python 3.11+ and the runtime dependencies in `requirements.txt`.

On Linux you may need a few system libs for Qt to start:

```bash
sudo apt-get install -y libegl1 libxkbcommon0 libdbus-1-3 libfontconfig1
```

---

## Build a standalone binary (Windows / macOS)

`scripts/build.py` drives PyInstaller in one-folder mode and packages the
output as `obj.Paper-windows.zip` or `obj.Paper-macos.dmg` (matches
spec.md §18).

```bash
pip install -r requirements.txt -r requirements-dev.txt
python scripts/build.py --clean
```

Outputs land under `dist/`:

| Host | Output |
|------|--------|
| Windows | `dist/obj.Paper/obj.Paper.exe` (one-folder) and `dist/obj.Paper-windows.zip` |
| macOS   | `dist/obj.Paper.app` (one-folder bundle) and `dist/obj.Paper-macos.dmg` |
| Linux   | `dist/obj.Paper/obj.Paper` — smoke build only, not part of the v1.0 release matrix |

The build script auto-converts `obj.Paper Icon 64.png` into `.ico` /
`.icns` via Pillow before invoking PyInstaller, so the .exe and .app
get the right native icon resource baked in.

### macOS Gatekeeper

The .app bundle isn't code-signed for v1.0 (spec §18). First-run users
have to unblock it manually:

```bash
xattr -d com.apple.quarantine "/Applications/obj.Paper.app"
```

…or right-click → Open → confirm.

### GitHub Actions

`.github/workflows/build.yml` builds both platforms on every tag push
(`v*`) — `windows-latest` and `macos-latest` runners run the same
`scripts/build.py` and attach the artifacts to a GitHub Release. Trigger
manually with **Run workflow** on the Actions tab if you need a build
without tagging.

---

## Project layout

```
obj_paper/
├── __main__.py          # python -m obj_paper
├── theme.py             # color tokens + global QSS (spec §3, §4)
├── i18n.py              # EN/KO singleton (spec §13)
├── document.py          # Document / BlockData / DocumentSettings (spec §6, §11)
├── templates.py         # 6 format presets (spec §9)
├── render.py            # block → HTML for preview/export (spec §6, §10)
├── latex.py             # matplotlib LaTeX → base64 PNG (cached)
├── exporters.py         # PDF (QPrinter) + HTML
└── widgets/
    ├── block_chrome.py     # frame, badge, hover/select chrome (spec §5.3)
    ├── blocks.py           # 12 block widgets + @register_block registry
    ├── inline_toolbar.py   # floating format toolbar (spec §7)
    ├── insert_between.py   # [+ Add block] (spec §5.3)
    ├── palette.py          # left panel (spec §5.2)
    ├── canvas.py           # center panel + drag-drop (spec §5.3)
    ├── preview.py          # right panel + Reference PDF (spec §5.4, §16)
    ├── settings_panel.py   # slide-in Document Settings (spec §8)
    ├── toolbar.py          # top toolbar
    ├── status_bar.py       # bottom status bar (spec §14)
    ├── export_dialog.py    # PDF/HTML progress dialog (spec §10)
    └── main_window.py      # menu, shortcuts, autosave, focus mode
```

`obj.Paper Mockup.html` is the original Claude Design handoff — kept as a
visual reference, not used at runtime.

---

## Keyboard map (spec §12)

| | Windows / Linux | macOS |
|---|---|---|
| Save | Ctrl+S | ⌘S |
| Save As | Ctrl+Shift+S | ⌘⇧S |
| Open | Ctrl+O | ⌘O |
| New document | Ctrl+N | ⌘N |
| Export PDF | Ctrl+E | ⌘E |
| Export HTML | Ctrl+Shift+E | ⌘⇧E |
| Undo / Redo | Ctrl+Z / Ctrl+Y | ⌘Z / ⌘⇧Z |
| Bold / Italic / Underline | Ctrl+B / I / U | ⌘B / I / U |
| Inline math wrap | Ctrl+M | ⌘M |
| Insert link | Ctrl+K | ⌘K |
| Clear formatting | Ctrl+\ | ⌘\ |
| Move block up / down | Alt+↑ / Alt+↓ | ⌥↑ / ⌥↓ |
| Duplicate block | Ctrl+D | ⌘D |
| Delete block | Ctrl+Backspace | ⌘⌫ |
| Add paragraph below | Ctrl+Enter | ⌘Return |
| Change block type | Ctrl+/ | ⌘/ |
| Choose template | Ctrl+Shift+P | ⌘⇧P |
| Focus mode | F11 | ⌘^F |
| Toggle language | Ctrl+Shift+L | ⌘⇧L |

---

## Save format

`.pw` (or `.json`) files use spec §11's v2 schema:

```json
{
  "version": 2,
  "meta": { "created": "...", "modified": "...", "title": "..." },
  "settings": { "body_font": "...", "paper": "A4", ... },
  "blocks": [
    { "id": "uuid", "type": "title", "data": { "text": "..." }, "settings": {...} },
    ...
  ]
}
```

v1 documents (flat `{title, blocks}` shape) are still loadable; their settings
default to the General template.

---

## Extending the editor

```python
from obj_paper.widgets.block_chrome import BlockChrome
from obj_paper.widgets.blocks import register_block

@register_block("my_callout")
class CalloutBlockWidget(BlockChrome):
    def __init__(self, block, parent=None):
        super().__init__(block, parent)
        # ...
```

Drop the module into your install and import it during boot. The palette only
shows the built-in groups today, but the registry already accepts the new type
and the JSON serializer round-trips unknown fields verbatim.

---

## Testing

```bash
QT_QPA_PLATFORM=offscreen pytest tests/ -v
```

24 tests cover JSON round-trip, v1 backward compat, block CRUD/dirty
tracking, per-block HTML rendering, equation numbering, code highlighting,
and template application.

---

## License

MIT. See [LICENSE](LICENSE).
