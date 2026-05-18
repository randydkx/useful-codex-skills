# Locator Design

The four locators in `clip_regions.py` cover ~95% of real paper artifacts. Each is anchored on a *real* PDF element, never on a percent-of-page heuristic.

## 1. `algorithm` — bounded by horizontal rules

LaTeX `algorithm` / `algorithm2e` environments are framed by exactly two horizontal rules (top + bottom) drawn as either stroke segments (`item[0] == "l"`) or thin rectangles (`item[0] == "re"`).

Algorithm:
1. `page.search_for("Algorithm N")` → list of caption-text rects.
2. Pick the rect that lies *between* two near-horizontal rules (so we exclude the rare mention of "Algorithm 1" in body text).
3. Detect columns: bucket text-block `x0` values; if any block starts past the page midpoint, the page is 2-column.
4. Restrict to the caption's column.
5. Top edge = max y of rules above the caption; bottom edge = min y of rules below.

False-positive defenses:
- Filter rules by length (`> 60 pt`) so we ignore hairline decorations.
- Deduplicate near-identical y-coordinates within 1pt.
- Reject if no enclosing pair found; fall back to "column width × small vertical margin".

## 2. `figure` — caption-anchored body expansion

Captions like "Figure 1: ..." appear *below* the figure body in 99% of CS papers. So:
1. Find the caption rect.
2. Get all text blocks in the same column with `y_bottom < caption.y_top`.
3. The figure body is the gap between the lowest *paragraph* block (≥ 2 lines) and the caption.
4. If no paragraph above (figure at column top), extend up to `page.rect.y0 + 30` (header margin).

Why "paragraph" not "any block": axis labels and inline figure annotations are single-line text blocks that would otherwise be excluded from the crop. Requiring multi-line excludes only real prose.

## 3. `table` — caption-anchored with `find_tables()` priority

Tables behave like figures (caption below body), but PyMuPDF has a dedicated `page.find_tables()` that gives us bboxes directly. Strategy:
1. Search for "Table N" caption rect.
2. Run `page.find_tables()`; collect all detected table bboxes.
3. Pick the table whose bbox overlaps the caption's column AND is vertically nearest (above OR below) within 40 pt.
4. Merge the table bbox with the caption rect for the final crop.
5. Fall back to `expand_to_figure` if `find_tables()` returns nothing.

## 4. `equation` — labelled display-math

Display equations end with `\tag{N}` or `\label{eq:N}` which renders as `(N)` flush-right in the column. Strategy:
1. `page.search_for("(N)")` → all rects.
2. Filter to rects whose `x1` is within 25 pt of the column's right edge (eliminating in-text references like "as shown in (3)").
3. Vertical extent: top = bottom of the previous block in the same column; bottom = top of the next block.
4. Horizontal extent: full column.

Limitations: works only for numbered equations. Unnumbered ones (`\notag`) must be cropped with explicit `bbox` mode.

## 5. Column detection

`detect_columns` uses the simplest reliable heuristic:
- Get all non-empty text blocks (`page.get_text("blocks")`).
- If any block's `x0` is past `page.rect.width * 0.5`, assume 2 columns.
- Left column: from `min(x0)` to just before the smallest `x0` in the right half.
- Right column: from there to `page.rect.x1 - 5`.

This fails on:
- Single-column papers that have right-aligned author affiliations on the title page → safe to ignore (we don't usually crop the title).
- Three-column layouts → none in mainstream CS conferences.

## 6. Padding & DPI choices

- **Default padding = 4 pt** (~1.4 mm at 72 dpi): enough to avoid text touching the crop edge without including the next paragraph.
- **Default DPI = 200**: at 200 DPI, an 8-point label renders ~22 pixels tall — clearly readable in a Markdown viewer. 100 DPI is too low (12-pixel labels alias); 300 DPI doubles file size for no readability gain.
- Both can be overridden per-clip.

## 7. Failure modes & fallbacks

| Failure | Symptom | Fallback |
|---|---|---|
| Caption found but no enclosing rules | algorithm crop too short | `clip bbox` with explicit coords |
| Two figures share a caption | crop includes both | manual bbox; the body has no rule to split them |
| Figure on different page than caption | crop is empty paragraph | manual `--page` override on caption search |
| Scanned PDF (no text layer) | `search_for` returns empty | OCR first (out of scope for this skill) |

For scanned PDFs, recommend running `ocrmypdf` to add a text layer before using this skill.
