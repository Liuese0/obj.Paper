"""LaTeX → PNG rendering via matplotlib's mathtext.

We avoid a full LaTeX install by using matplotlib's built-in mathtext parser,
which covers the common subset academic users need (greek, sub/super, sums,
fractions, brackets, common functions).

Each call is cached. Failures fall back to a typewriter-styled image so the
preview never breaks the layout.
"""

from __future__ import annotations

import base64
import io
import os
from functools import lru_cache

# Force a non-interactive backend so we can use matplotlib in any thread.
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib  # noqa: E402

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import mathtext  # noqa: E402


def _wrap(latex: str) -> str:
    """Make a math-mode string for matplotlib."""
    s = (latex or "").strip()
    if not s:
        s = "?"
    if s.startswith("$") and s.endswith("$"):
        return s
    return f"${s}$"


@lru_cache(maxsize=512)
def render_latex_png(latex: str, dpi: int = 220, fontsize: int = 14) -> bytes:
    """Render a LaTeX/mathtext string to a PNG byte string. Always returns bytes."""
    src = _wrap(latex)
    # Parser raises on syntax errors — swallow and render the raw source as
    # plain text so the user still sees something meaningful.
    try:
        parser = mathtext.MathTextParser("path")
        parser.parse(src, dpi=dpi, prop=None)
        rendered = src
    except Exception:
        rendered = latex.replace("\\", r"\\\\")  # show raw

    fig = plt.figure(figsize=(0.01, 0.01))
    fig.patch.set_alpha(0.0)
    try:
        text = fig.text(
            0,
            0,
            rendered,
            fontsize=fontsize,
            color="#2C2820",
        )
        fig.canvas.draw()
        bbox = text.get_window_extent()
        # Resize canvas to text bounding box with a tiny margin.
        w_in = (bbox.width + 6) / fig.dpi
        h_in = (bbox.height + 6) / fig.dpi
        fig.set_size_inches(max(w_in, 0.2), max(h_in, 0.2))
        text.set_position((0.5, 0.5))
        text.set_horizontalalignment("center")
        text.set_verticalalignment("center")

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, transparent=True, bbox_inches="tight", pad_inches=0.04)
        return buf.getvalue()
    finally:
        plt.close(fig)


def render_latex_data_uri(latex: str, dpi: int = 220, fontsize: int = 14) -> str:
    """Return a `data:image/png;base64,…` URI ready for `<img src=...>`."""
    png = render_latex_png(latex, dpi=dpi, fontsize=fontsize)
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def warm_up() -> None:
    """Pre-populate the parser cache. Call once during app boot."""
    try:
        render_latex_png("x")
    except Exception:
        pass
