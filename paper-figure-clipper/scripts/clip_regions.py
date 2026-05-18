#!/usr/bin/env python3
"""Clip a precisely-bounded region from a PDF page to a PNG.

This is the "low-level precise crop" tool. The caller specifies what to
clip, and how to find its bounding box:

  - by-search:  search for a text anchor (e.g. "Algorithm 1") and extend
                its bbox to the enclosing horizontal rules / column.
  - by-bbox:    explicit bbox in PDF points (1pt = 1/72 inch).
  - by-figure:  use PyMuPDF page.find_tables() / get_images() to locate
                a labelled object on a page.
  - by-equation: search for "Eq. N" / "Equation N" reference and crop the
                 nearest display-math block in that column.

Output is a tightly cropped PNG at a configurable DPI (default 200 — high
enough for paper figures without producing absurdly large files).

Design notes:
  - "High quality" means *correct bounding box first*, then high DPI.
    We never use percent-of-page heuristics — always anchor on real PDF
    elements (text rectangles, drawing rules, table objects).
  - We always render the *original page* at the target DPI, then crop in
    pixel space. This preserves anti-aliasing and avoids quality loss
    from scaling.
  - We add a small "padding" (default 4 pt) inside the bbox so the crop
    isn't flush against text. Override with --padding 0 for hairline.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

@dataclass
class Bbox:
    """1-based page number + bbox in PDF points (top-left origin)."""
    page: int
    x0: float
    y0: float
    x1: float
    y1: float

    def to_rect(self) -> fitz.Rect:
        return fitz.Rect(self.x0, self.y0, self.x1, self.y1)

    def pad(self, padding: float, page_rect: fitz.Rect) -> "Bbox":
        return Bbox(
            page=self.page,
            x0=max(page_rect.x0, self.x0 - padding),
            y0=max(page_rect.y0, self.y0 - padding),
            x1=min(page_rect.x1, self.x1 + padding),
            y1=min(page_rect.y1, self.y1 + padding),
        )


def horizontal_rules(page: fitz.Page) -> list[tuple[float, float, float]]:
    """Return (y, x_lo, x_hi) for all near-horizontal rules on the page.

    Both stroke segments ("l") and thin-rectangle hairlines ("re") count.
    Used to find the top/bottom of `algorithm` / `wraptable` blocks.
    """
    rules: list[tuple[float, float, float]] = []
    for d in page.get_drawings():
        for item in d.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 0.5 and abs(p1.x - p2.x) > 60:
                    rules.append((min(p1.y, p2.y), min(p1.x, p2.x), max(p1.x, p2.x)))
            elif item[0] == "re":
                r = item[1]
                if r.height < 1.0 and r.width > 60:
                    rules.append((r.y0, r.x0, r.x1))
    # Deduplicate near-identical rules
    rules.sort()
    out: list[tuple[float, float, float]] = []
    for r in rules:
        if not out or abs(r[0] - out[-1][0]) > 1.0:
            out.append(r)
    return out


def detect_columns(page: fitz.Page) -> list[tuple[float, float]]:
    """Heuristic: return list of (x_lo, x_hi) for each text column.

    Two-column papers (most CS conferences) have a clear gap. We bucket
    text-line x-starts and look for the gap.
    """
    blocks = page.get_text("blocks")
    if not blocks:
        return [(page.rect.x0, page.rect.x1)]
    xs = sorted({round(b[0], 0) for b in blocks if b[4].strip()})
    if not xs:
        return [(page.rect.x0, page.rect.x1)]
    page_w = page.rect.width
    # If there's any text block starting past the midpoint, assume 2 columns.
    if any(x > page_w * 0.5 for x in xs):
        # Left column: smallest start; right column: smallest start past midpoint.
        left_start = min(xs)
        right_candidates = [x for x in xs if x > page_w * 0.5]
        right_start = min(right_candidates) if right_candidates else page_w * 0.5
        # Right edge of left column = just before right_start.
        left_end = right_start - 5
        right_end = page.rect.x1 - 5
        return [(left_start - 2, left_end), (right_start - 2, right_end)]
    return [(min(xs) - 2, page.rect.x1 - 5)]


def column_for(x: float, columns: list[tuple[float, float]]) -> tuple[float, float]:
    for c in columns:
        if c[0] - 2 <= x <= c[1] + 2:
            return c
    # Fallback: closest column by x-center.
    return min(columns, key=lambda c: abs((c[0] + c[1]) / 2 - x))


# ---------------------------------------------------------------------------
# Locators (each returns a Bbox or raises ValueError)
# ---------------------------------------------------------------------------

def locate_by_search(
    doc: fitz.Document,
    query: str,
    page_hint: Optional[int] = None,
    occurrence: int = 0,
) -> tuple[fitz.Page, fitz.Rect]:
    """Locate the Nth occurrence of `query` in the document.

    `page_hint` (1-based) restricts the search to that page.
    `occurrence` (0-based) picks among multiple hits.
    """
    page_range = (
        [page_hint - 1] if page_hint else range(doc.page_count)
    )
    hits: list[tuple[fitz.Page, fitz.Rect]] = []
    for pg in page_range:
        page = doc[pg]
        for rect in page.search_for(query):
            hits.append((page, rect))
    if not hits:
        raise ValueError(f"text not found: {query!r}")
    if occurrence >= len(hits):
        raise ValueError(
            f"requested occurrence {occurrence} but only {len(hits)} hits for {query!r}"
        )
    return hits[occurrence]


def expand_to_rules(
    page: fitz.Page,
    anchor: fitz.Rect,
    columns: list[tuple[float, float]],
) -> Bbox:
    """Extend an anchor caption to the rules above and below it.

    Used for algorithm / floated-table blocks delimited by horizontal rules.
    Raises ValueError when the block isn't actually delimited by rules — better
    to fail loudly than silently return a caption-only crop (the old fallback
    behaviour produced ~26pt bboxes that downstream couldn't distinguish from
    a successful crop).
    """
    col = column_for(anchor.x0, columns)
    rules = [(y, x0, x1) for (y, x0, x1) in horizontal_rules(page)
             if x0 <= col[1] + 5 and x1 >= col[0] - 5]
    rules_above = [r for r in rules if r[0] < anchor.y0 - 1]
    rules_below = [r for r in rules if r[0] > anchor.y1 + 1]
    if not rules_above or not rules_below:
        missing = []
        if not rules_above:
            missing.append("above")
        if not rules_below:
            missing.append("below")
        raise ValueError(
            f"no horizontal rules {' and '.join(missing)} anchor on page "
            f"{page.number + 1} (col x={col[0]:.0f}-{col[1]:.0f}, anchor y="
            f"{anchor.y0:.0f}-{anchor.y1:.0f}); algorithm block not delimited "
            f"by rules — fall back to `bbox` mode (see recipe-book §R4.5)"
        )
    top = max(r[0] for r in rules_above)
    bot = min(r[0] for r in rules_below)
    return Bbox(page=page.number + 1, x0=col[0], y0=top, x1=col[1], y1=bot)


def expand_to_figure(
    page: fitz.Page,
    caption: fitz.Rect,
    columns: list[tuple[float, float]],
) -> Bbox:
    """Extend a `Figure N:` caption upward to cover the figure body.

    Strategy:
      1. Restrict search to the caption's column.
      2. Find the lowest *previous* text block that looks like a paragraph
         (i.e. starts at column-left and has narrow line spacing). Anything
         between that block's bottom and the caption is the figure.
      3. If no paragraph above, extend up to the page top margin.
    Captions may be "Figure 1:" or "Figure 1." — caller passes the rect of
    the matched anchor text; we extend horizontally to the column and
    vertically to the figure body.
    """
    col = column_for(caption.x0, columns)
    # Find caption full extent: search for the entire caption line text.
    # First, get all blocks in column above the caption.
    blocks = page.get_text("blocks")
    same_col = [
        b for b in blocks
        if col[0] - 5 <= b[0] <= col[1] + 5
        and b[3] < caption.y0 - 1
        and b[4].strip()
    ]
    if not same_col:
        # No body above — likely figure starts at top margin.
        top = page.rect.y0 + 30
    else:
        # The figure body is whatever sits between the last paragraph block
        # and the caption. But we want to keep the figure body, not the
        # paragraph text above it. So: top = the bottom of the closest
        # *paragraph* (multi-line block); the figure body has no text or
        # only labels.
        paragraphs = [b for b in same_col if b[4].count("\n") >= 1]
        if paragraphs:
            top = max(b[3] for b in paragraphs) + 2
        else:
            top = page.rect.y0 + 30
    # Find the bottom of the caption: extend until we hit the next text
    # block (caption text itself ends at some y > caption.y1).
    caption_blocks = [
        b for b in blocks
        if col[0] - 5 <= b[0] <= col[1] + 5
        and b[1] >= caption.y0 - 1
        and b[1] <= caption.y1 + 2
    ]
    if caption_blocks:
        bot = max(b[3] for b in caption_blocks) + 2
    else:
        bot = caption.y1 + 4
    return Bbox(page=page.number + 1, x0=col[0], y0=top, x1=col[1], y1=bot)


def expand_to_table(
    page: fitz.Page,
    caption: fitz.Rect,
    columns: list[tuple[float, float]],
) -> Bbox:
    """Extend a `Table N:` caption to cover the table body.

    Tables in 2-column CS papers usually appear ABOVE their caption (unlike
    figures which appear above too in fact). But some venues put captions
    above. We disambiguate: ask PyMuPDF's table finder for the table whose
    bbox is closest to the caption, vertically.
    """
    try:
        finder = page.find_tables()
        tables = list(finder.tables) if hasattr(finder, "tables") else list(finder)
    except Exception:
        tables = []
    if tables:
        # Pick the table whose bbox is vertically nearest the caption (above
        # or below) AND overlaps the caption's column.
        col = column_for(caption.x0, columns)
        best = None
        best_dist = float("inf")
        for t in tables:
            bb = t.bbox
            # bb may be a tuple of 4 floats or a Rect-like obj
            if hasattr(bb, "x0"):
                tx0, ty0, tx1, ty1 = bb.x0, bb.y0, bb.x1, bb.y1
            else:
                tx0, ty0, tx1, ty1 = bb
            # Must overlap the column.
            if tx1 < col[0] - 5 or tx0 > col[1] + 5:
                continue
            if ty1 < caption.y0:
                d = caption.y0 - ty1
            elif ty0 > caption.y1:
                d = ty0 - caption.y1
            else:
                d = 0
            if d < best_dist:
                best_dist = d
                best = (tx0, ty0, tx1, ty1)
        if best is not None and best_dist < 40:
            # Merge with caption.
            tx0, ty0, tx1, ty1 = best
            return Bbox(
                page=page.number + 1,
                x0=min(tx0, caption.x0),
                y0=min(ty0, caption.y0),
                x1=max(tx1, caption.x1),
                y1=max(ty1, caption.y1),
            )
    # Fallback: treat table like a figure (expand upward to paragraph).
    return expand_to_figure(page, caption, columns)


def locate_equation(
    doc: fitz.Document,
    eq_label: str,
    page_hint: Optional[int] = None,
) -> Bbox:
    """Locate display equation labelled `(eq_label)` on the right margin.

    We search for the literal label e.g. "(3)" near the right edge of a
    column, then expand left across the column to capture the formula.
    Vertical extent: from the previous text line above to the next below
    (single display-math row).
    """
    target = f"({eq_label})"
    page_range = [page_hint - 1] if page_hint else range(doc.page_count)
    candidates: list[tuple[fitz.Page, fitz.Rect, tuple[float, float]]] = []
    for pg in page_range:
        page = doc[pg]
        columns = detect_columns(page)
        # Find the rightmost text x for each column — this is the *effective*
        # right margin where display-equation labels sit. We use the median
        # of paragraph-block right edges so a single cross-column block
        # (e.g. a wide table that straddles columns) doesn't skew the value.
        blocks = page.get_text("blocks")
        col_right_edges: list[float] = []
        for c in columns:
            xs_in_col = sorted(
                b[2] for b in blocks
                if c[0] - 5 <= b[0] <= c[1] + 5
                and b[4].strip()
                # paragraph-ish blocks only (>= 1 newline = multi-line)
                and b[4].count("\n") >= 1
                # and the block's right edge actually stays inside the column
                and b[2] <= c[1] + 5
            )
            if xs_in_col:
                col_right_edges.append(xs_in_col[len(xs_in_col) // 2])
            else:
                col_right_edges.append(c[1])
        for rect in page.search_for(target):
            col_idx = None
            for i, c in enumerate(columns):
                if c[0] - 2 <= rect.x0 <= c[1] + 2:
                    col_idx = i
                    break
            if col_idx is None:
                continue
            right_edge = col_right_edges[col_idx]
            # A display-math label sits within 25 pt of the column's effective
            # right edge. In-line references like "shown in (3)" are typically
            # much further from the right edge.
            if rect.x1 >= right_edge - 25:
                candidates.append((page, rect, columns[col_idx]))
    if not candidates:
        raise ValueError(f"equation label not found: {target!r}")
    page, rect, col = candidates[0]
    # Find prev / next blocks to set vertical extent.
    blocks = page.get_text("blocks")
    same_col = [b for b in blocks if col[0] - 5 <= b[0] <= col[1] + 5]
    above = [b for b in same_col if b[3] < rect.y0 - 1]
    below = [b for b in same_col if b[1] > rect.y1 + 1]
    top = (max(b[3] for b in above) + 1) if above else rect.y0 - 8
    bot = (min(b[1] for b in below) - 1) if below else rect.y1 + 8
    return Bbox(page=page.number + 1, x0=col[0], y0=top, x1=col[1], y1=bot)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_bbox(
    doc: fitz.Document,
    bbox: Bbox,
    output: Path,
    dpi: int = 200,
    padding: float = 4.0,
) -> Path:
    page = doc[bbox.page - 1]
    padded = bbox.pad(padding, page.rect)
    clip = padded.to_rect()
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=clip, alpha=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(output))
    return output


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pdf", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path,
                   help="Output PNG path")
    p.add_argument("--dpi", type=int, default=200)
    p.add_argument("--padding", type=float, default=4.0,
                   help="Padding in PDF points around the located bbox")

    mode = p.add_subparsers(dest="mode", required=True)

    fig = mode.add_parser("figure",
                          help="Locate a Figure / Table by its caption text")
    fig.add_argument("--label", required=True,
                     help='Caption anchor, e.g. "Figure 1" or "Table 2"')
    fig.add_argument("--page", type=int, default=None,
                     help="1-based page hint")
    fig.add_argument("--occurrence", type=int, default=0,
                     help="Which match if multiple")

    algo = mode.add_parser("algorithm",
                           help="Locate an Algorithm block delimited by rules")
    algo.add_argument("--label", required=True,
                      help='e.g. "Algorithm 1"')
    algo.add_argument("--page", type=int, default=None)
    algo.add_argument("--occurrence", type=int, default=0)

    eq = mode.add_parser("equation",
                         help="Locate a display equation by its (N) label")
    eq.add_argument("--label", required=True,
                    help='Equation number without parentheses, e.g. "3"')
    eq.add_argument("--page", type=int, default=None)

    bb = mode.add_parser("bbox", help="Crop an explicit bbox (PDF points)")
    bb.add_argument("--page", type=int, required=True)
    bb.add_argument("--x0", type=float, required=True)
    bb.add_argument("--y0", type=float, required=True)
    bb.add_argument("--x1", type=float, required=True)
    bb.add_argument("--y1", type=float, required=True)

    args = p.parse_args()

    if not args.pdf.exists():
        print(f"PDF not found: {args.pdf}", file=sys.stderr)
        return 2

    doc = fitz.open(str(args.pdf))
    try:
        if args.mode == "bbox":
            box = Bbox(page=args.page, x0=args.x0, y0=args.y0,
                       x1=args.x1, y1=args.y1)
        elif args.mode == "algorithm":
            page, rect = locate_by_search(
                doc, args.label, args.page, args.occurrence)
            columns = detect_columns(page)
            box = expand_to_rules(page, rect, columns)
        elif args.mode == "figure":
            page, rect = locate_by_search(
                doc, args.label, args.page, args.occurrence)
            columns = detect_columns(page)
            if args.label.lower().startswith("table"):
                box = expand_to_table(page, rect, columns)
            else:
                box = expand_to_figure(page, rect, columns)
        elif args.mode == "equation":
            box = locate_equation(doc, args.label, args.page)
        else:
            print(f"unknown mode: {args.mode}", file=sys.stderr)
            return 2

        out = render_bbox(doc, box, args.out, dpi=args.dpi,
                          padding=args.padding)
        result = {
            "ok": True,
            "page": box.page,
            "bbox_pt": [round(box.x0, 2), round(box.y0, 2),
                        round(box.x1, 2), round(box.y1, 2)],
            "dpi": args.dpi,
            "output": str(out),
        }
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except ValueError as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 1
    finally:
        doc.close()


if __name__ == "__main__":
    sys.exit(main())
