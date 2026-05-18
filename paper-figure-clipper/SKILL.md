---
name: paper-figure-clipper
description: Precisely extract figures, tables, algorithms, equations, or arbitrary regions from research-paper PDFs, with bbox-anchored cropping (not percent-of-page heuristics). Companion to `cs-paper-reader` for image-rich note-taking.
---

# paper-figure-clipper

A small toolbox for getting **publication-quality, precisely-bounded** crops out of academic PDFs, so paper notes can be image-rich without manual screenshotting.

This skill is the companion to `cs-paper-reader`: when a note needs to cite a specific figure / table / algorithm / equation, the reader skill invokes this skill to produce the PNG.

## When to use this skill

Trigger this skill from inside `cs-paper-reader` (Mode A or Mode B) whenever the note benefits from showing an artifact verbatim. Concretely:

- The paper's **§3 method** depends on a non-trivial schematic (architecture diagram, data-flow chart, unit-cell figure — examples from an LLM-compression batch: SliceGPT's slicing diagram, OWL's outlier histogram).
- The paper's **§4 results** are easier to read as the original table than as transcribed numbers (e.g. multi-column ablations).
- The paper's **algorithm pseudocode** matters for reproducibility (any boxed `Algorithm N` with non-trivial control flow — e.g. SparseGPT's `Algorithm 1`).
- A **specific equation** is too complex to faithfully reproduce in Markdown and would be better shown as a rendered crop.

Do NOT use this skill for:
- Rendering an entire page (use `scripts/clip.py page` only as last-resort fallback).
- Decorative screenshots — every clip should be cited by name in the note.

## Three operation modes (use them in this order)

1. **`scan`** — Run `pdffigures2` over the whole PDF; emit a `manifest.json` listing every figure & table with bbox + caption + pre-rendered PNG + `body_refs` count. Use this once per paper to enumerate what's available.

   ```bash
   ~/.codex/skills/paper-figure-clipper/scripts/clip.py scan \
     --pdf "<paper.pdf>" \
     --out-dir "/tmp/paper-figs/<Method>"
   ```
   **Output path must be `/tmp/paper-figs/<Method>/`**, never `<output>/_figs/...`. `scan` emits the full set of figures + `manifest.json` + side-products; only PNGs actually referenced by the final note get promoted into `<output>/_figs/<Method>/` later (see §"Integration with cs-paper-reader" step 4). Writing scan output straight to `<output>/` pollutes the cloud-synced deliverable with unused crops.
   By default MuPDF re-renders each figure for sharper output (200 DPI). Add `--no-rerender` to skip and keep only pdffigures2's softer renderer; add `--keep-pdffigures2-output` to keep both side-by-side.

   The manifest includes `body_refs` per entry — how many times the body text references `Figure N` / `Fig. N` / `Table N`. **Sort by `body_refs` descending to prioritize embedding decisions**: figures with `body_refs ≥ 3` are almost always central; `body_refs = 1` is usually supplementary.

2. **`clip`** — When you want a specific artifact that `scan` may have missed (algorithm blocks, individual equations, sub-figures), invoke the precise locator:

   ```bash
   # Algorithm block (auto-bounded by horizontal rules)
   clip.py clip --pdf P --out o.png algorithm --label "Algorithm 1" --page 5

   # Figure / Table caption with body expansion
   clip.py clip --pdf P --out o.png figure --label "Figure 2"

   # Display equation by its (N) label
   clip.py clip --pdf P --out o.png equation --label "3"

   # Explicit bbox in PDF points (1pt = 1/72 inch)
   clip.py clip --pdf P --out o.png bbox --page 4 --x0 54 --y0 100 --x1 300 --y1 250
   ```

3. **`page`** — Fallback when neither of the above resolves; renders an entire page at 200 DPI. Always prefer `scan` or `clip` over `page`.

## Quality rules (the reason this skill exists)

- **No percent-of-page heuristics.** Every crop is anchored on a real PDF element: a text rect from `page.search_for`, a horizontal rule from `page.get_drawings()`, a table object from `page.find_tables()`, or an explicit bbox.
- **200 DPI default.** Below that, axis labels become unreadable. Override with `--dpi 300` for camera-ready quality (≈2× file size).
- **4-pt padding default** to avoid hairline crops; override `--padding 0` only if you need a perfectly tight bbox.
- **The PDF is rendered once, then cropped** — never scale a small crop up. This preserves anti-aliasing.
- **JSON-first output**: every command prints a single JSON line with `ok`, `page`, `bbox_pt`, `dpi`, `output`. Notes can grep these for citation.
- **Contact-sheet QA for multiple selected crops.** When several selected crops from one paper need visual QA, prefer inspecting one contact sheet in `/tmp/paper-figs/<Method>/qa_contact_sheet.png` rather than opening each PNG separately; promote only crops whose visible content matches the intended Figure/Table/Algorithm.

## Integration with cs-paper-reader

When `cs-paper-reader` is in Mode A or Mode B and decides a note needs a figure (see triggers above):

1. **First time per paper**: run `clip.py scan` to a **temp staging area** (`/tmp/paper-figs/<Method>/`). Read `manifest.json` to learn which figures exist and their captions.
   ```bash
   clip.py scan --pdf "<paper.pdf>" --out-dir "/tmp/paper-figs/<Method>"
   ```
2. **For each citation**: pick the relevant entry from the manifest, or run `clip.py clip` for items the scan missed (also to `/tmp/paper-figs/<Method>/`).
3. **While drafting, reference with the final relative path** (not the `/tmp/` staging path). Alt text is minimal; the explanation lives as a red-font body block above or below the image (Markdown viewers render alt text as hover tooltips, so anything inside `[ ]` is invisible to readers on first scroll):
   ```markdown
   <font color="red">**下方算法**</font>：<one to three sentences explaining the key lines the reader should look at>.

   ![Algorithm 1 — SparseGPT 单层剪枝主循环](_figs/SparseGPT/algorithm_1_p5.png)
   ```
   See `~/.codex/skills/cs-paper-reader/references/image-embedding-recipes.md` §0 for the position rule (schematic → image above with `下图解释`, results table → image below with `上表解释`, etc.) and the alt-text discipline (label + ≤ 25 字 topic only).
4. **After the note is finalized**: promote only the actually-referenced images to the permanent `<output>/_figs/<Method>/` directory. This avoids polluting the cloud-synced workspace with unused crops.
   ```bash
   grep -oE '!\[[^]]*\]\(([^)]+)\)' <note.md> | sed -E 's/.*\]\(([^)]+)\)/\1/' | while read img; do
     src="/tmp/paper-figs/<Method>/$(basename $img)"
     dst="<output>/$img"
     mkdir -p "$(dirname "$dst")"
     cp "$src" "$dst"
   done
   ```

**Key principle**: the cloud-synced directory only contains images that are actually referenced in notes. All intermediate/exploratory crops stay in `/tmp/` and are ephemeral.

## Naming convention for output PNGs

Use the same schema in both the `/tmp` staging dir and the final `<output>/_figs/` dir so promotion is a flat `cp`:

```
/tmp/paper-figs/<Method>/<type>_<label>_p<page>.png      # staging (clip.py writes here)
<output>/_figs/<Method>/<type>_<label>_p<page>.png       # final (only referenced PNGs end up here)
```

Examples (illustrative — `<Method>` is the paper's method/acronym, from any subfield):
- `_figs/SparseGPT/algorithm_1_p5.png`
- `_figs/OWL/figure_1_p2.png`
- `_figs/SliceGPT/table_3_p7.png`
- `_figs/FLAP/equation_4_p4.png`

This keeps file names deterministic so notes can pre-link images with the **final** relative path (`_figs/<Method>/...`) before promotion, and the promote step is just a basename-preserving copy.

## Limitations to be aware of

- `pdffigures2` is excellent on standard two-column CS papers (NeurIPS / ICML / ICLR / ACL). On single-column tech reports, accuracy drops — fall back to `clip` mode.
- Figures rendered as **embedded PNG/JPEG** with low source resolution will not improve at higher DPI. The clip will just enlarge pixels; check the source PDF first.
- `clip equation` assumes the equation has a numbered `(N)` label on the right margin. Unnumbered equations need explicit `bbox` mode.
- `clip algorithm` assumes the algorithm is bounded by horizontal rules (standard `algorithm` / `algorithm2e` LaTeX style). Non-rule-bounded pseudocode (e.g. ICML's `algorithmic` package without `algorithm` floats, ICLR templates using only top/bot section rules, or pseudo-code typeset inside a `figure` env) will fail with `{"ok": false, "error": "no horizontal rules above/below anchor on page N ..."}` and exit code 1. **This is by design** — silently returning a caption-only crop was a worse failure mode. When you hit this error, fall back to `clip bbox` (via the R4.5 4-candidate salvage recipe in `references/recipe-book.md`).

## See also

- `references/locator-design.md` — full design of the four locators (search / rules / figure-expansion / table-finder).
- `references/recipe-book.md` — copy-pasteable command snippets for the common cases.
- `~/.codex/skills/cs-paper-reader/SKILL.md` — the upstream paper-reading skill that triggers this one.
