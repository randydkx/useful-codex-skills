#!/usr/bin/env python3
"""Unified front-end for paper-figure-clipper.

Three subcommands:
  scan      Run pdffigures2 on the PDF and emit a manifest of all
            figures/tables with bboxes + captions + PNGs. This is the
            "explore" step; use it once per paper.

  clip      Crop a single region (figure / table / algorithm / equation
            / explicit bbox) to a PNG. Use this when you already know
            what you want and want a precise crop with PyMuPDF.

  page      Render a full page at high DPI (fallback when neither
            scan nor clip find what you need).

The two underlying scripts are clip_figures.py (pdffigures2 wrapper)
and clip_regions.py (PyMuPDF locators). This entry point exists so the
cs-paper-reader skill only has to remember one command.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VENV_PY = Path.home() / ".codex" / "venvs" / "paper-figure-clipper" / "bin" / "python"


def py() -> str:
    """Return the Python interpreter to use (prefer the dedicated venv)."""
    if VENV_PY.exists():
        return str(VENV_PY)
    return sys.executable


def run(cmd: list[str]) -> int:
    res = subprocess.run(cmd)
    return res.returncode


def cmd_scan(args: argparse.Namespace) -> int:
    cmd = [
        py(), str(SCRIPT_DIR / "clip_figures.py"),
        "--pdf", str(args.pdf),
        "--out-dir", str(args.out_dir),
        "--dpi", str(args.dpi),
    ]
    if args.no_rerender:
        cmd.append("--no-rerender")
    if args.keep_pdffigures2_output:
        cmd.append("--keep-pdffigures2-output")
    return run(cmd)


def cmd_clip(args: argparse.Namespace) -> int:
    sub_cmd = [
        py(), str(SCRIPT_DIR / "clip_regions.py"),
        "--pdf", str(args.pdf),
        "--out", str(args.out),
        "--dpi", str(args.dpi),
        "--padding", str(args.padding),
        args.kind,
    ]
    if args.kind == "bbox":
        sub_cmd += [
            "--page", str(args.page),
            "--x0", str(args.x0), "--y0", str(args.y0),
            "--x1", str(args.x1), "--y1", str(args.y1),
        ]
    else:
        sub_cmd += ["--label", args.label]
        if args.page is not None:
            sub_cmd += ["--page", str(args.page)]
        if args.kind in ("figure", "algorithm") and args.occurrence:
            sub_cmd += ["--occurrence", str(args.occurrence)]
    return run(sub_cmd)


def cmd_page(args: argparse.Namespace) -> int:
    """Render a full page at DPI; thin wrapper around pdftoppm fallback."""
    import fitz
    if not args.pdf.exists():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 2
    doc = fitz.open(str(args.pdf))
    try:
        if args.page < 1 or args.page > doc.page_count:
            print(f"page {args.page} out of range (1-{doc.page_count})",
                  file=sys.stderr)
            return 2
        page = doc[args.page - 1]
        zoom = args.dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(args.out))
        print(json.dumps({"ok": True, "page": args.page,
                          "size_pt": [page.rect.width, page.rect.height],
                          "dpi": args.dpi, "output": str(args.out)},
                         ensure_ascii=False))
        return 0
    finally:
        doc.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("scan",
                      help="Extract all figures/tables via pdffigures2")
    s.add_argument("--pdf", required=True, type=Path)
    s.add_argument("--out-dir", required=True, type=Path)
    s.add_argument("--dpi", type=int, default=200)
    s.add_argument("--no-rerender", action="store_true",
                   help="Skip MuPDF re-render (keep only pdffigures2's softer output)")
    s.add_argument("--keep-pdffigures2-output", action="store_true",
                   help="Also keep pdffigures2's softer PNG with .pdffigures2.png suffix")
    s.set_defaults(func=cmd_scan)

    c = sp.add_parser("clip", help="Crop a single region precisely")
    c.add_argument("--pdf", required=True, type=Path)
    c.add_argument("--out", required=True, type=Path)
    c.add_argument("--dpi", type=int, default=200)
    c.add_argument("--padding", type=float, default=4.0)
    c.add_argument("kind", choices=["figure", "algorithm", "equation", "bbox"])
    c.add_argument("--label", help='e.g. "Figure 1", "Algorithm 1", "3" (for equation)')
    c.add_argument("--page", type=int, default=None)
    c.add_argument("--occurrence", type=int, default=0)
    c.add_argument("--x0", type=float)
    c.add_argument("--y0", type=float)
    c.add_argument("--x1", type=float)
    c.add_argument("--y1", type=float)
    c.set_defaults(func=cmd_clip)

    pg = sp.add_parser("page", help="Render a full page (fallback)")
    pg.add_argument("--pdf", required=True, type=Path)
    pg.add_argument("--out", required=True, type=Path)
    pg.add_argument("--page", type=int, required=True)
    pg.add_argument("--dpi", type=int, default=200)
    pg.set_defaults(func=cmd_page)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
