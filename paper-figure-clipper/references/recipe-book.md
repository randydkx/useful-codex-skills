# Recipe Book — copy-pasteable command snippets

> **Domain note**: every concrete example below (SparseGPT scan, SparseGPT algorithm clip, etc.) is from an LLM-compression batch — the **commands** are domain-agnostic, only the example PDF path and `<Method>` directory name change between subfields.

Assumes:
- The dedicated venv lives at `~/.codex/venvs/paper-figure-clipper`.
- `clip.py` lives at `~/.codex/skills/paper-figure-clipper/scripts/clip.py`.
- **All `clip.py` output goes to the staging dir `/tmp/paper-figs/<Method>/`** — never directly to `<output>/_figs/<Method>/`. Only PNGs actually referenced by the final note get promoted to `<output>/_figs/<Method>/` after the note is saved (see SKILL.md §"Integration with cs-paper-reader" step 3). This keeps the cloud-synced deliverable lean.

For brevity, alias once:

```bash
CLIP=~/.codex/skills/paper-figure-clipper/scripts/clip.py
```

## R1. First-pass enumerate every figure & table in a paper

```bash
"$CLIP" scan \
  --pdf "(ICML 2023) SparseGPT-...One-Shot.pdf" \
  --out-dir "/tmp/paper-figs/SparseGPT"
cat /tmp/paper-figs/SparseGPT/manifest.json | jq '.entries[] | {label, page, body_refs, caption: (.caption[:60])}'
```

After this you know **what figures exist** before you decide what to cite. Manifest entries look like:

```json
{
  "type": "Figure",
  "label": "Figure 1",
  "page": 1,
  "bbox_pt": [305.0, 498.0, 545.0, 540.0],
  "caption": "Figure 1: Sparsity pattern...",
  "body_refs": 4,
  "image": "/tmp/paper-figs/SparseGPT/figure_1_p1.png"
}
```

**Use `body_refs` to prioritize which crops to embed**: it counts how many times the paper's body text mentions `Figure N` / `Fig. N` / `Table N` (excluding the caption itself). A figure with `body_refs ≥ 3` is almost always central to the paper's narrative; one with `body_refs = 1` is usually supplementary. Sort the manifest by `body_refs` descending and embed the top 3-5 first.

## R2. Crop a single algorithm with auto-bounding

```bash
"$CLIP" clip \
  --pdf "(ICML 2023) SparseGPT-...One-Shot.pdf" \
  --out "/tmp/paper-figs/SparseGPT/algorithm_1_p5.png" \
  algorithm --label "Algorithm 1" --page 5
```

Add `--page` whenever you know the page — it speeds up the search and avoids ambiguity when "Algorithm 1" is mentioned in body text on a different page.

## R3. Crop a specific equation

```bash
"$CLIP" clip \
  --pdf P.pdf \
  --out "/tmp/paper-figs/SparseGPT/equation_3_p3.png" \
  equation --label "3" --page 3
```

If the equation is unnumbered, switch to `bbox` mode after measuring the rect from a one-shot full-page render.

## R4. Crop an explicit bbox (last-resort precise control)

```bash
"$CLIP" clip --pdf P.pdf --out o.png \
  bbox --page 4 --x0 54 --y0 100 --x1 300 --y1 250 \
  --padding 0    # hairline
```

To measure the bbox: render the full page once at 72 DPI, open it in any image viewer that shows cursor position, multiply pixel coords by 1 (since 72 DPI = 1 px/pt).

## R4.5. Bad-crop salvage — 4 bbox candidates + contact sheet

Use this **only** when a single `clip` attempt visibly truncated a critical artifact (algorithm with only its title, missing last lines, half a figure). Do not run by default — it spends ~4× the budget. Per SKILL.md (cs-paper-reader) §"Image-Rich Notes" step 2, apply to at most the top-1 / top-2 critical figures of the paper; all others keep the `scan` output as-is.

The pattern: **4 bbox candidates ordered tight → wider → taller → context-rich**, side-by-side preview, promote the winner, delete the rest. **You pick the actual coordinates** — start from the failing `clip` call's JSON output (`{"page": ..., "bbox_pt": [...]}`) and decide reasonable expansion deltas based on what's actually missing on the page. The bboxes below are placeholders; replace every `<...>` with values you've reasoned about for this specific PDF.

```bash
PDF="<paper.pdf>"
METHOD="<Method>"
ART="<artifact>_p<page>"     # canonical basename, e.g. algorithm_1_p5
DIR="/tmp/paper-figs/${METHOD}/${ART}_candidates"
mkdir -p "$DIR"

# 4 candidates: A tight (the failing bbox or close to it), B taller (extend y1),
# C wider (also extend x0/x1), D context (largest margins all sides).
# Use the failing call's bbox_pt as your starting reference; expand each axis
# only as much as the visible truncation requires.
"$CLIP" clip --pdf "$PDF" --out "$DIR/${ART}_A_tight.png"   --dpi 300 \
  bbox --page <page> --x0 <x0> --y0 <y0> --x1 <x1> --y1 <y1>
"$CLIP" clip --pdf "$PDF" --out "$DIR/${ART}_B_tall.png"    --dpi 300 \
  bbox --page <page> --x0 <x0> --y0 <y0> --x1 <x1> --y1 <y1 + small>
"$CLIP" clip --pdf "$PDF" --out "$DIR/${ART}_C_wide.png"    --dpi 300 \
  bbox --page <page> --x0 <x0 - small> --y0 <y0> --x1 <x1 + small> --y1 <y1 + small>
"$CLIP" clip --pdf "$PDF" --out "$DIR/${ART}_D_context.png" --dpi 300 \
  bbox --page <page> --x0 <x0 - larger> --y0 <y0 - small> --x1 <x1 + larger> --y1 <y1 + larger>

# Build a 2x2 contact sheet for visual inspection
python3 - <<PY
from pathlib import Path
from PIL import Image, ImageDraw
paths = sorted(Path("$DIR").glob("${ART}_*.png"))
thumbs = []
for p in paths:
    img = Image.open(p).convert("RGB"); img.thumbnail((900, 360))
    canvas = Image.new("RGB", (920, 410), "white")
    ImageDraw.Draw(canvas).text((10, 8), p.name, fill="black")
    canvas.paste(img, (10, 40))
    thumbs.append(canvas)
w = max(t.width for t in thumbs) * 2
h = max(t.height for t in thumbs) * 2
sheet = Image.new("RGB", (w, h), "white")
for i, t in enumerate(thumbs):
    sheet.paste(t, ((i % 2) * t.width, (i // 2) * t.height))
sheet.save("$DIR/contact_sheet.png")
print("$DIR/contact_sheet.png")
PY
```

Open `contact_sheet.png`, pick the candidate that fully contains the artifact with reasonable padding (no neighboring body text bleeding in), then promote only that one to the canonical name and drop the rest:

```bash
WINNER=A_tight   # or B_tall / C_wide / D_context
cp "$DIR/${ART}_${WINNER}.png" "/tmp/paper-figs/${METHOD}/${ART}.png"
rm -r "$DIR"
```

After this, the standard promote step (SKILL.md `paper-figure-clipper` §"Integration" step 4) picks up `/tmp/paper-figs/${METHOD}/${ART}.png` like any other crop — no change to downstream commands.

If all 4 still cut the artifact, the deltas were too conservative — re-run with larger expansion on the failing axis. If even a very large D crosses a page boundary, fall back to R5 (full-page render) for both pages.

## R5. Render a full page (fallback)

```bash
"$CLIP" page --pdf P.pdf --out /tmp/paper-figs/SparseGPT/page_5.png --page 5 --dpi 200
```

Use this only when both `scan` and `clip` fail (e.g. for scanned-image PDFs without text layer).

## R6. Citation pattern inside a note

When drafting the note, use the **final** relative path (`_figs/<Method>/...`), not the `/tmp/` staging path. After the note is saved, promote referenced PNGs from staging to `<output>/_figs/<Method>/` (see SKILL.md §"Integration with cs-paper-reader" step 4):

```markdown
### 3.2 一次性逐列剪枝

SparseGPT 的核心循环列在伪代码 (Algorithm 1) 中：每处理一列后，立刻把误差通过 OBS update 公式分摊到右侧未剪枝的列上。

![Algorithm 1 — SparseGPT 单层剪枝主循环](_figs/SparseGPT/algorithm_1_p5.png)

关键点：Hessian 更新只依赖右下子矩阵（详见图中 6-9 行）。
```

Three rules for citation:
1. Alt text inside `![ ]` stays minimal — `<Label> — <≤25 字 topic>` only. The "why this image is here" goes in the red-font body block above/below the image (see SKILL.md step 3).
2. Always reference the artifact by its paper-given name ("Algorithm 1", "Figure 2(b)") so readers can cross-check.
3. Surrounding prose should call out the **specific lines / labels / colors** the reader should look for.

## R7. Common gotchas

| Gotcha | Fix |
|---|---|
| `clip equation` returns "label not found" | The equation is unnumbered (used `\notag`). Use `clip bbox`. |
| `clip algorithm` returns column-wide blob | The algorithm block lacks rules (uses `verbatim` not `algorithm` env). Use `clip bbox`. |
| Scan finds 0 figures | PDF has no caption-style figure markers (e.g. Asian-language thesis). Use `clip` with manual labels. |
| Re-rendered crop is blurry | Source figure is a low-res embedded raster — higher DPI cannot fix it. Note this in the caption. |
| Output file is enormous | Lower DPI (`--dpi 150`) or crop tighter (`--padding 0`). |

## R8. Batch enumeration across a directory

```bash
for pdf in *.pdf; do
  stem="${pdf%.pdf}"
  method="${stem##*) }"
  "$CLIP" scan --pdf "$pdf" --out-dir "/tmp/paper-figs/${method}"
done
```

Then `/tmp/paper-figs/<Method>/manifest.json` per method lets `cs-paper-reader` look up "what figures do I have for Method X" without re-running pdffigures2. The manifest stays in `/tmp/` — only the referenced PNGs ever get promoted to `<output>/_figs/<Method>/`, so the final directory never contains a `manifest.json`.
