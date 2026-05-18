#!/usr/bin/env python3
"""Run allenai/pdffigures2 on a single PDF and post-process the output.

pdffigures2 is the gold-standard non-neural figure extractor for CS
papers. It returns a JSON list of figures/tables with precise bboxes
and pre-rendered PNGs. This script is a thin wrapper that:

  1. Invokes the assembled JAR via `java -jar`.
  2. Optionally re-renders each figure at a higher DPI (pdffigures2
     defaults to 100 DPI; for paper-note screenshots we want 200+).
  3. Returns a JSON manifest suitable for Codex to cite.

Requirements:
  - `java` >= 11 on PATH (Scala 2.x can NOT build on JDK 25; LTS like
    21 is recommended).
  - The pdffigures2 fat JAR at `~/.codex/tools/pdffigures2-assembly.jar`
    (override via --jar).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import fitz  # for re-render at higher DPI


DEFAULT_JAR = Path.home() / ".codex" / "tools" / "pdffigures2-assembly.jar"


def run_pdffigures2(pdf: Path, work: Path, jar: Path) -> tuple[Path, Path]:
    """Run pdffigures2 in batch mode on a single PDF.

    Returns (data_dir, image_dir). pdffigures2 treats the -d and -m
    arguments as path *prefixes* — the basename appended onto each is
    `<input-stem><Type><N>...`. To keep output filenames clean we pass
    just the directory (with trailing slash) so the prefix is empty.
    """
    data_dir = work / "data"
    img_dir = work / "img"
    data_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)
    # pdffigures2 wants a directory of PDFs; we'll stage one.
    staging = work / "stage"
    staging.mkdir(exist_ok=True)
    staged_pdf = staging / pdf.name
    if not staged_pdf.exists():
        shutil.copy2(pdf, staged_pdf)
    # Trailing "/" makes the basename empty so output is `<dir>/<stem>...`.
    cmd = [
        "java",
        "-Djava.awt.headless=true",
        "-Dsun.java2d.cmm=sun.java2d.cmm.kcms.KcmsServiceProvider",
        "-jar", str(jar),
        "-d", str(data_dir) + "/",
        "-m", str(img_dir) + "/",
        "-i", "200",  # rasterize figures at 200 DPI
        str(staging) + "/",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"pdffigures2 failed (rc={res.returncode}):\n"
            f"stdout: {res.stdout[-500:]}\nstderr: {res.stderr[-500:]}"
        )
    return data_dir, img_dir


def collect_figures(data_dir: Path, img_dir: Path, pdf_stem: str) -> list[dict]:
    """Read pdffigures2's per-PDF JSON and pair each entry with its PNG.

    The naming convention with prefix `<dir>/<stem>_` produces:
      JSON: `<stem>.json` (NOT `<stem>_.json`; the trailing underscore from -d
            is part of the prefix, and pdffigures2 strips the underscore back).
      PNG:  `<stem>-<Figure|Table><N>-<seq>.png`
    """
    # Try a few candidate locations for the JSON.
    json_candidates = [
        data_dir / f"{pdf_stem}.json",
        data_dir / f"{pdf_stem}_.json",
    ] + sorted(data_dir.glob(f"{pdf_stem}*.json"))
    json_path = next((p for p in json_candidates if p.exists()), None)
    if json_path is None:
        raise FileNotFoundError(
            f"no pdffigures2 JSON output found in {data_dir} for stem {pdf_stem!r}"
        )
    entries = json.loads(json_path.read_text(encoding="utf-8"))
    out: list[dict] = []
    for e in entries:
        name = e.get("name", "")
        ftype = e.get("figType", "Figure")  # "Figure" or "Table"
        page = e.get("page", 0) + 1  # convert to 1-based
        bbox = e.get("regionBoundary", {})
        caption = e.get("caption", "")
        caption_bbox = e.get("captionBoundary", {})
        # pdffigures2 names files: <stem>-<Figure|Table><N>-<seq>.png
        glob_pat = f"{pdf_stem}-{ftype}{name}-*.png"
        img_candidates = sorted(img_dir.glob(glob_pat))
        img = str(img_candidates[0]) if img_candidates else None
        out.append({
            "type": ftype,            # "Figure" | "Table"
            "label": f"{ftype} {name}",
            "page": page,
            "bbox_pt": [
                round(bbox.get("x1", 0), 2),
                round(bbox.get("y1", 0), 2),
                round(bbox.get("x2", 0), 2),
                round(bbox.get("y2", 0), 2),
            ],
            "caption": caption,
            "caption_bbox_pt": [
                round(caption_bbox.get("x1", 0), 2),
                round(caption_bbox.get("y1", 0), 2),
                round(caption_bbox.get("x2", 0), 2),
                round(caption_bbox.get("y2", 0), 2),
            ] if caption_bbox else None,
            "image": img,
        })
    return out


def count_body_refs(pdf: Path, entries: list[dict]) -> None:
    """Count in-body mentions of each Figure N / Table N and write to entries.

    The signal answers "how important is this figure to the paper's narrative?"
    A figure cited 5+ times in body text is almost always central; a figure
    cited once is often supplementary. Models choosing which crops to embed
    in a note should prefer high body_refs entries.

    Counting rules:
      - Use PyMuPDF's text extraction (whole document, ordered by page).
      - Strip the caption region itself before counting, so "Figure 1:" in
        the caption doesn't inflate Figure 1's count.
      - Match case-sensitively: "Figure 3" / "Fig. 3" / "Fig 3" / "Table 3".
      - Match on word boundaries so "Figure 3" doesn't pick up "Figure 30".
      - Also count the parenthesized form "(Fig. 3)" / "(Figure 3)".
    """
    try:
        doc = fitz.open(str(pdf))
    except Exception:
        for e in entries:
            e["body_refs"] = None
        return
    try:
        # Build per-page text, then strip caption bbox regions for each entry.
        page_texts: list[str] = []
        for p in doc:
            page_texts.append(p.get_text("text"))
        full_text = "\n".join(page_texts)
        # Strip the caption rect text per entry. We approximate by also stripping
        # the literal caption string when long enough (>= 30 chars), since the
        # caption itself contains the label.
        stripped = full_text
        for e in entries:
            cap = (e.get("caption") or "").strip()
            if len(cap) >= 30:
                stripped = stripped.replace(cap, "")
        for e in entries:
            ftype = e["type"]  # "Figure" or "Table"
            num = e["label"].split()[-1]  # "1", "2", "A.3", etc.
            # Escape number for regex (handles "A.3").
            num_re = re.escape(num)
            if ftype == "Figure":
                # Match Figure N, Fig. N, Fig N (with word boundary on the number).
                pat = rf"(?:\bFigure\s+{num_re}\b|\bFig\.?\s+{num_re}\b)"
            else:  # Table
                pat = rf"\bTable\s+{num_re}\b"
            e["body_refs"] = len(re.findall(pat, stripped))
    finally:
        doc.close()


def rerender_at_dpi(pdf: Path, entries: list[dict], out_dir: Path, dpi: int) -> None:
    """Re-render each figure's bbox at a configurable DPI using PyMuPDF.

    pdffigures2's raster output can look slightly soft because it uses
    PDFBox's renderer. Re-rendering through MuPDF at the same bbox gives
    sharper text and consistent quality across the batch. The rendered
    file overwrites the soft version at `<out>/<type>_<label>_p<page>.png`.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf))
    try:
        for e in entries:
            x0, y0, x1, y1 = e["bbox_pt"]
            if x1 <= x0 or y1 <= y0:
                continue
            page = doc[e["page"] - 1]
            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            clip = fitz.Rect(x0, y0, x1, y1)
            pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
            fname = f"{e['type'].lower()}_{e['label'].split()[-1]}_p{e['page']}.png"
            target = out_dir / fname
            pix.save(str(target))
            e["image"] = str(target)
    finally:
        doc.close()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pdf", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path,
                   help="Where to write the figures + manifest.json")
    p.add_argument("--jar", type=Path, default=DEFAULT_JAR,
                   help="Path to pdffigures2-assembly.jar")
    p.add_argument("--dpi", type=int, default=200,
                   help="Re-render DPI (passed to pdffigures2 AND re-rendered via MuPDF)")
    p.add_argument("--no-rerender", action="store_true",
                   help="Skip MuPDF re-render (keep only pdffigures2's softer output). "
                        "By default MuPDF re-render runs and overwrites the soft version.")
    p.add_argument("--keep-pdffigures2-output", action="store_true",
                   help="Keep pdffigures2's softer PNG alongside the MuPDF re-render. "
                        "Off by default to avoid storage duplication.")
    p.add_argument("--keep-work", action="store_true",
                   help="Keep pdffigures2 intermediate work dir for debugging")
    args = p.parse_args()

    if not args.pdf.exists():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 2
    if not args.jar.exists():
        print(f"pdffigures2 JAR not found: {args.jar}\n"
              "Build with: cd ~/.codex/tools/pdffigures2 && sbt assembly\n"
              "Then copy/link the resulting jar to ~/.codex/tools/pdffigures2-assembly.jar",
              file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="pdffigures2_"))
    try:
        data_dir, img_dir = run_pdffigures2(args.pdf, work, args.jar)
        entries = collect_figures(data_dir, img_dir, args.pdf.stem)
        # Count in-body references so consumers can prioritize centrally-cited
        # figures. Cheap (one text pass + ~14 regex scans).
        count_body_refs(args.pdf, entries)
        # If user wants pdffigures2's softer output kept, copy it with a
        # `.pdffigures2.png` suffix; otherwise we let the MuPDF rerender
        # below produce the canonical PNG at the predictable name.
        if args.keep_pdffigures2_output:
            for e in entries:
                if e["image"] and Path(e["image"]).exists():
                    target = args.out_dir / (Path(e["image"]).stem + ".pdffigures2.png")
                    shutil.copy2(e["image"], target)
        if not args.no_rerender:
            rerender_at_dpi(args.pdf, entries, args.out_dir, args.dpi)
        else:
            # Without rerender, fall back to pdffigures2 output at canonical name.
            for e in entries:
                if e["image"] and Path(e["image"]).exists():
                    fname = f"{e['type'].lower()}_{e['label'].split()[-1]}_p{e['page']}.png"
                    target = args.out_dir / fname
                    shutil.copy2(e["image"], target)
                    e["image"] = str(target)
        manifest = {
            "pdf": str(args.pdf),
            "dpi": args.dpi,
            "entries": entries,
        }
        manifest_path = args.out_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps({
            "ok": True,
            "manifest": str(manifest_path),
            "n_figures": sum(1 for e in entries if e["type"] == "Figure"),
            "n_tables": sum(1 for e in entries if e["type"] == "Table"),
        }, ensure_ascii=False))
        return 0
    finally:
        if not args.keep_work:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
