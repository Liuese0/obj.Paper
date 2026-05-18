#!/usr/bin/env python3
"""Build obj.Paper binaries for the host OS.

Runs end-to-end:
  1. Converts `obj.Paper Icon 64.png` to `.ico` (Windows) and `.icns` (macOS)
     into obj_paper/assets/ so PyInstaller can embed the proper icon
     resource.
  2. Runs PyInstaller against `obj.Paper.spec`.
  3. Packages the output:
       Windows  → `dist/obj.Paper-windows.zip`
       macOS    → `dist/obj.Paper-macos.dmg`
       Linux    → leaves `dist/obj.Paper/` as-is (smoke / sanity only).

Usage:
    python scripts/build.py [--clean]
"""

from __future__ import annotations

import argparse
import os
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND_PNG = ROOT / "obj.Paper Icon 64.png"
ASSETS = ROOT / "obj_paper" / "assets"
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def _ensure_pillow():
    try:
        import PIL  # noqa: F401

        return
    except ImportError:
        print("Pillow is required for icon conversion. Install with:")
        print("  pip install Pillow")
        sys.exit(2)


def make_ico() -> Path:
    """Pillow can write multi-size .ico directly from a single source."""
    _ensure_pillow()
    from PIL import Image

    ASSETS.mkdir(parents=True, exist_ok=True)
    ico = ASSETS / "icon.ico"
    src = Image.open(BRAND_PNG).convert("RGBA")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    src.save(ico, format="ICO", sizes=sizes)
    print(f"  wrote {ico.relative_to(ROOT)}  ({ico.stat().st_size:,} B)")
    return ico


def make_icns() -> Path:
    """Try Pillow's ICNS writer first; fall back to native `iconutil` on macOS."""
    _ensure_pillow()
    from PIL import Image

    ASSETS.mkdir(parents=True, exist_ok=True)
    icns = ASSETS / "icon.icns"

    try:
        src = Image.open(BRAND_PNG).convert("RGBA")
        # Pillow ICNS expects square images. We upscale to 1024 once for the
        # largest variant; ICNS handles internal sizing from there.
        big = src.resize((1024, 1024), Image.Resampling.LANCZOS)
        big.save(icns, format="ICNS")
        print(f"  wrote {icns.relative_to(ROOT)}  ({icns.stat().st_size:,} B)")
        return icns
    except Exception as e:
        print(f"  Pillow .icns write failed ({e}); trying iconutil…")

    if sys.platform != "darwin":
        # iconutil only ships on macOS — skip on Linux CI smoke builds
        print("  iconutil unavailable on this OS; skipping .icns")
        return icns

    iconset = ASSETS / "icon.iconset"
    iconset.mkdir(exist_ok=True)
    from PIL import Image  # type: ignore

    src = Image.open(BRAND_PNG).convert("RGBA")
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for s in sizes:
        scaled = src.resize((s, s), Image.Resampling.LANCZOS)
        scaled.save(iconset / f"icon_{s}x{s}.png")
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(icns)], check=True)
    shutil.rmtree(iconset, ignore_errors=True)
    return icns


def ensure_icon_formats() -> None:
    print("> generating platform icon formats")
    if sys.platform == "win32" or "--all-icons" in sys.argv:
        make_ico()
    if sys.platform == "darwin" or "--all-icons" in sys.argv:
        make_icns()
    if sys.platform.startswith("linux"):
        # PyInstaller on Linux happily accepts the PNG.
        print(f"  (Linux: using {BRAND_PNG.name} directly)")


def run_pyinstaller(clean: bool) -> None:
    print("> running PyInstaller")
    args = [sys.executable, "-m", "PyInstaller", "obj.Paper.spec", "--noconfirm"]
    if clean:
        args.append("--clean")
    subprocess.run(args, cwd=ROOT, check=True)


def zip_folder(src_dir: Path, out_zip: Path) -> None:
    print(f"> zipping {src_dir.name} → {out_zip.name}")
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in src_dir.rglob("*"):
            zf.write(path, path.relative_to(src_dir.parent))


def make_dmg(app_path: Path, out_dmg: Path) -> None:
    """macOS: hdiutil bundles the .app into a compressed DMG."""
    print(f"> creating DMG → {out_dmg.name}")
    if out_dmg.exists():
        out_dmg.unlink()
    subprocess.run(
        [
            "hdiutil",
            "create",
            "-volname",
            "obj.Paper",
            "-srcfolder",
            str(app_path),
            "-ov",
            "-format",
            "UDZO",
            str(out_dmg),
        ],
        check=True,
    )


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def directory_size(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Pass --clean to PyInstaller (rebuild from scratch)",
    )
    args = parser.parse_args()

    if not BRAND_PNG.exists():
        print(f"ERROR: brand PNG missing at {BRAND_PNG}")
        return 1

    ensure_icon_formats()
    run_pyinstaller(args.clean)

    bundle_dir = DIST / "obj.Paper"
    print(f"> bundle ready: {bundle_dir.relative_to(ROOT)}  "
          f"({human_size(directory_size(bundle_dir))} unpacked)")

    if sys.platform == "win32":
        out_zip = DIST / "obj.Paper-windows.zip"
        zip_folder(bundle_dir, out_zip)
        print(f"  artifact: {out_zip.relative_to(ROOT)}  "
              f"({human_size(out_zip.stat().st_size)})")
    elif sys.platform == "darwin":
        app_path = DIST / "obj.Paper.app"
        if not app_path.exists():
            # When spec doesn't produce a separate .app, fall back to bundle_dir
            app_path = bundle_dir
        out_dmg = DIST / "obj.Paper-macos.dmg"
        make_dmg(app_path, out_dmg)
        print(f"  artifact: {out_dmg.relative_to(ROOT)}  "
              f"({human_size(out_dmg.stat().st_size)})")
    else:
        print("  (Linux: skipping platform packaging — smoke build only)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
