# Batch Workflow (Mode B — Batch Reading)

> **Domain note**: this workflow is domain-agnostic. Concrete examples that appear below — method names (LaCo, OWL, FLAP, SparseGPT), batch theme names (`剪枝与稀疏化/`), specific phrases like `LLM 部署很贵` in the master grep, or mechanism-sentence examples like `表达式树进化剪枝公式` — come from an LLM-compression batch. When you run a batch in a different subfield (knowledge editing, retrieval, agents, training systems, alignment, etc.), replace the example tokens with your own; the workflow steps themselves stay the same.

Use this reference when the user asks you to read or rewrite notes for **multiple papers** in one unattended run. Covers both:

- **Fresh batch reading** — user points at a directory of PDFs with no existing notes.
- **Batch rewrite** — user has existing low-quality notes that need to be replaced.

Both paths use the same workflow; the only difference is whether Step F also deletes a stale note from the source dir.

This workflow was hardened against the specific failure modes observed when a prior batch produced 117 near-identical template-filled notes.

Mode B's job is to keep you honest across many papers, where the temptation to reuse a generic skeleton is highest.

---

## 1. Setup — runs exactly once per batch

### 1.0 Lock in the completion target (do this FIRST)

Before anything else, scan the user's request for a **hard completion target** — a phrase that pins down how many papers must be done. Examples: `务必 / 全部 / 一共 / 总共 N 篇 / 这些文章都读完 / 整章 / 全自动跑完`. Extract the explicit number, or count it yourself from the source (`ls <dir>/*.pdf | wc -l` for a bare directory; manifest line count otherwise). This number `N` becomes the progress table's header in §1.4 — see that section for the exact line.

`N` is the **single closed-loop terminator**. The batch is done when and only when N rows are 🟢 / ✅✅ / ⚠️ in `_progress_<batch>.md`. **Token-budget anxiety, response-length worry, "差不多了吧", or model-side fatigue are NOT legitimate stop conditions** — they don't appear in §3. If you finish a paper and there are still ⬜ rows below `N`, the next response immediately starts the next paper. No summary, no "我已完成 X / N，要继续吗", no checking in. The user is not in the loop — that's the point of batch mode (re-read SKILL.md §"Mode B" and `Step G`).

### 1.1 Locate the inputs

The user typically provides one or more of:
- A **manifest** file (e.g. `_manifest_345.md`) listing papers in order with their PDF paths.
- A **style spec** file (e.g. `_rewrite_style_spec.md`) — read it before doing anything.
- One or more **reference notes** that already meet the quality bar — read all of them; these are your calibration samples.
- An **intro / overview** file that maps method names to PDF paths.
- A bare **PDF directory** (no manifest, no spec, no refs).

**If the user only gives a PDF directory**, do NOT stop and ask. Build a manifest yourself:
1. Scan the directory for `*.pdf` files.
2. Parse each filename for `(Venue Year) MethodName-Paper Title.pdf` pattern.
3. Order by venue year if available, otherwise alphabetic.
4. Use this as the implicit manifest. Record `⚠️ 文件名不规范` for any PDF that doesn't match.

Only stop if the directory doesn't exist or has zero PDFs.

**If no reference note is provided**, use the bootstrap protocol in §2.B below — the first two notes self-reference, then become the batch's internal reference set.

### 1.2 Create or open the output directory

Conventions for the output directory:
- One directory per batch (per chapter / per topic), separate from the original `reading/` root.
- Name it after the batch's semantic theme (e.g. `剪枝与稀疏化/`, `低秩分解与参数共享/`, `知识编辑/`, `检索增强/`) — match the user's existing taxonomy if there is one.
- **Probe the directory once** before the first write — Chinese paths can fail in some shells:
  ```bash
  mkdir -p "<dir>"
  touch "<dir>/.probe" && rm "<dir>/.probe" || { echo "path unusable"; exit 1; }
  ```
  If the probe fails, stop and report — let the user pick an ASCII fallback name.

**Two trees, not one** (per SKILL.md §"Output Hygiene"). For every batch you actually maintain two directories:

| Tree | Purpose | Contents |
|---|---|---|
| `<output>/` (e.g. `剪枝与稀疏化/`) — cloud-synced, lean | The deliverable the user reads. | finalized `*.md` notes, `_progress_<batch>.md`, `_collision_warnings.md`, `_final_report_<batch>.md`, `_figs/<Method>/` (only images actually referenced by saved notes) |
| `/tmp/cs-paper-reader-<batch>/` — scratch, never synced | Intermediate evidence the model needs while writing. | `_evidence/<Method>.md`, `<Method>.raw.txt`, `<Method>.layout.txt`, `check_<short>.txt`, anything else used during drafting |

A separate `/tmp/paper-figs/<Method>/` tree holds candidate image crops + `manifest.json` from `paper-figure-clipper`; only referenced crops get promoted into `<output>/_figs/<Method>/` in Step F.

Create both trees at setup time:
```bash
mkdir -p "<output>" "/tmp/cs-paper-reader-<batch>/_evidence"
```

### 1.3 Move any already-approved reference note into the output directory

If a previously approved note exists in the source dir and the user said it's the gold standard, `mv` (not `cp`) it into the new output dir. Mark its row in the progress table as already-approved so you don't rewrite it. Read its content once as a calibration sample.

### 1.4 Create the progress table

In the output directory, create `_progress_<batch>.md`:

```markdown
# <Batch Name> 重写进度

> **完成目标 (hard)**: N 篇必须全部完成；只有 §3 红线允许提前停止。状态图例：⬜ 待写 / 🟢 已写完待人类抽查 / ✅✅ 人类已通过 / ⚠️ 异常需关注。

| 序号 | 状态 | 方法 | 行数 | §2-§3 公式数 | §4 数值数 | 备注 |
|---:|---|---|---:|---:|---:|---|
| 1 | ✅✅ | <ApprovedRef> | — | — | — | 已通过参照 |
| 2 | ⬜ | <Method> | | | | |
| ... |
```

The progress table is the **single source of truth**. Always update it after each note lands. If the session is interrupted, the next session resumes from the first ⬜ row.

### 1.5 Collect the Evidence Seven-Pack for every paper up front (optional but recommended)

If you can do this cheaply in parallel — separate from drafting — extract evidence for all papers first and store under `/tmp/cs-paper-reader-<batch>/_evidence/<Method>.md` (NOT under `<output>/`; per SKILL.md §"Output Hygiene", evidence files are intermediate scratch artifacts and must stay in `/tmp`). This makes the writing phase deterministic and recoverable: even if your session dies after writing 3 notes, the next session can resume on raw evidence without re-extracting PDFs. The on-disk `/tmp` location survives across sessions on macOS until reboot, which is the durability window we rely on.

---

## 2. Per-paper loop

For each paper P in manifest order (lowest unfinished number first):

### Bootstrap protocol (only applies to #1 and #2 when no external reference exists)

When the batch has no human-approved reference note:

1. **#1 and #2** are written under Mode A quality standards. Run forbidden-pattern, LaTeX residue, and per-note quantitative checks (`--strict`) as usual, but **skip the cross-note collision check** — there is nothing to compare against.
2. After #2 lands, **explicitly run** `compare_sections` between #1 and #2:
   ```bash
   python3 ~/.codex/skills/cs-paper-reader/scripts/check_note_quality.py \
     --note "<#2.md>" --refs "<#1.md>"
   ```
   If `COLLISION` fires, rewrite #2 with a sharper per-paper angle and re-check before continuing.
3. From #3 onward, pass `--refs <#1.md> <#2.md>` to `--strict` runs; from #6 onward, switch to `--compare-dir <output-dir>` and drop explicit `--refs`.
4. In `_progress_<batch>.md`, mark #1 and #2 with a `bootstrap` remark and surface them in the final report as **recommended for the user to spot-check first**.

If an external reference note (e.g. `_SAMPLE_X.md` or a prior-batch approved note) was provided, skip the bootstrap — use it directly via `--refs` and apply the cross-note collision check from #1.

### Step A — Evidence

If `/tmp/cs-paper-reader-<batch>/_evidence/<Method>.md` already exists from §1.5, read it. Otherwise:

1. Resolve the PDF path from the manifest or intro.
2. `pdftotext -layout "<pdf>" /tmp/cs-paper-reader-<batch>/check_<short>.txt` (and, if needed, `pdftoppm` for figures with embedded formulas).
3. Extract the Evidence Seven-Pack (see SKILL.md §"Reading Workflow") into `/tmp/cs-paper-reader-<batch>/_evidence/<Method>.md`.
4. If any of the seven items genuinely doesn't exist in the PDF, record it as `PDF 中未显式给出` — do not fabricate.
5. **(Optional but recommended for image-rich notes)** Run `paper-figure-clipper`'s `scan` mode to enumerate figures/tables once:
   ```bash
   ~/.codex/skills/paper-figure-clipper/scripts/clip.py scan \
     --pdf "<pdf>" --out-dir "/tmp/paper-figs/<Method>"
   ```
   Read the resulting `manifest.json` (it lives in `/tmp/paper-figs/<Method>/`, not in `<output>/`) and note which `Figure N` / `Table N` are worth citing — record them in the evidence file under a `## Available figures` section so the drafting step can refer back without re-scanning.

### Step B — Plan the unique angle (≤30 chars, **mandatory**)

Before drafting any prose, write one short sentence that captures **what this paper does that none of the already-approved notes covers**.

Examples (from an LLM-compression batch — for any other subfield write your own subfield-specific mechanism phrase):
- LaCo: "删层但不改 Transformer 形状"
- OWL: "非均匀层稀疏率，base pruner 不变"
- FLAP: "波动度×权重列范数，retraining-free"

This sentence is the antidote to the most common Mode B failure mode: writing a §3.1 that could be the §3.1 of any other paper in the batch. If you can't produce a sharp ≤30-character angle, you don't understand the paper well enough yet — go back to Step A.

### Step C — Draft the note

Use the SKILL.md template. Hard floors per note (default for **method-heavy** papers):
- §2-§3 combined ≥ 3 formulas from the PDF (with Eq. labels). Some papers put metric definitions in formal problem setup (§2) and use §3 mainly for the procedure.
- §4 ≥ 2 specific numbers with `Table X, column, dataset` annotation.
- §5 ≥ 2 specific compared methods with quantitative differences.
- Length 220–400 lines for typical method-heavy papers. **Soft expand to 400–550** when ALL three hold:
  1. §2-§3 combined formula tags ≥ 12 (paper is formula-dense — long symbol tables and derivations are unavoidable).
  2. §4 has ≥ 3 distinct ablation tables worth quoting numbers from (genuine experimental breadth, not just a main table).
  3. §6 zero-shot / scaling / efficiency / downstream results all present (paper covers multiple evaluation axes).

  Above 550 lines → before `Write`, run a quick inflation check:
  ```bash
  # 1. Detect ≥3 consecutive blank lines (almost always inflation)
  awk 'NF==0{c++; if(c>=3){print "BLANK_RUN at line " NR}; next} {c=0}' <draft>
  # 2. Detect symbols defined in both §2 symbol table AND §3 prose (duplicate definition)
  # 3. Detect §4 numbers re-quoted in §6/§7 (unless they're the headline result)
  ```
  Compress only inflation. **Never delete formula tags, table numbers, or per-paper mechanism explanations** to hit a line target — these are what `check_note_quality.py` counts as anchors. If after compression the note is still > 600 lines, accept it and add a `备注: 长但实` remark in the progress row.
- §1-§3 must not share ≥ 5 non-empty lines with any other note in the same batch (auto-check in Step D).

**Paper-type classification** (decide before drafting, record in progress remark):

| Type | Indicators | Quantitative floors |
|---|---|---|
| `method-heavy` (default) | introduces a new algorithm with formulas, proof, training objective | as above |
| `empirical-study` | benchmark / analysis paper, "study of X" titles, no novel algorithm | `--min-formula-tags 1 --min-section4-numbers 5 --min-pdf-anchors 8` |
| `system` | inference engines, kernels, infrastructure / framework / pipeline papers | `--min-formula-tags 1 --min-section4-numbers 3 --min-pdf-anchors 6` |

If unclear, default to `method-heavy`. Type goes into the `备注` column of `_progress_<batch>.md`.

**Evidence-on-demand**: read `/tmp/cs-paper-reader-<batch>/_evidence/<Method>.md` only when drafting this specific paper. Don't keep older papers' evidence in your active context — the on-disk file in `/tmp` is the **session-resumable scratch source** (durable within the current run / until reboot, per SKILL.md §"Output Hygiene"). If `/tmp` was cleared, re-extract from the PDF.

**Image-rich drafting** (when the paper warrants it — see SKILL.md §"Image-Rich Notes" for triggers, and **`references/image-embedding-recipes.md`** for 8 placement recipes mapping figure-types to note sections):

- After running `scan`, sort manifest entries by `body_refs` desc. Embed the top 3-5 first; figures with `body_refs ≥ 3` are usually central, `body_refs ≤ 1` is often supplementary (except R7-style ablation explainers — see recipes).
- Reference figures from the `/tmp/paper-figs/<Method>/` staging area (via the manifest from Step A.5) with relative Markdown links that point to the **final** location. Example (from an LLM-compression note — same path scheme works for any paper):
  ```markdown
  ![Figure 1 — OPT 系列在 50%、4:8、2:4 稀疏度下的困惑度对比](_figs/SparseGPT/figure_1_p2.png)
  ```
- For algorithm blocks / specific equations not in the scan manifest, invoke `clip.py clip` mid-draft (output to `/tmp/paper-figs/<Method>/`):
  ```bash
  ~/.codex/skills/paper-figure-clipper/scripts/clip.py clip \
    --pdf "<pdf>" --out "/tmp/paper-figs/<Method>/algorithm_1_p5.png" \
    algorithm --label "Algorithm 1" --page 5
  ```
- The alt text inside `![ ]` stays minimal — `<Label> — <≤25 字 topic>` only. The **why this crop is here** goes in a red-font body block (`<上图解释>` / `<下图解释>` / `<上表解释>` / `<下表解释>` / `<下方算法>`) on the opposite side of the image; see `~/.codex/skills/cs-paper-reader/references/image-embedding-recipes.md` §0 for the position rule.
- One image per ~80 lines of prose is a healthy density; more than 1 per 40 lines usually means you're substituting images for analysis.
- **After the note is written (Step F)**: promote only referenced images from `/tmp/` to `<batch>/_figs/<Method>/`. This keeps the cloud-synced directory lean.
  ```bash
  grep -oE '!\[[^]]*\]\(([^)]+)\)' <note.md> | sed -E 's/.*\]\(([^)]+)\)/\1/' | while read img; do
    mkdir -p "<batch>/$(dirname "$img")"
    cp "/tmp/paper-figs/<Method>/$(basename $img)" "<batch>/$img"
  done
  ```

### Step D — Self-check before writing the file

Run these checks on the draft:

1. **LaTeX residue grep** (silent killer):
   ```bash
   grep -nE '[^\\](rac\{|um_|qrt\{|lpha|eta\s|ambda|abla)' <draft>
   ```
   Must return empty. If anything matches, fix `rac{` → `\frac{`, `um_` → `\sum_`, `qrt{` → `\sqrt{`, `lpha` → `\alpha`, etc.

2. **Anti-template scan** — universal portion (scaffolds + LaTeX-residue placeholders):
   ```bash
   grep -nE 'EvidenceSpecificScore|ScorePlaceholder|_method\b|待填入|TODO|见后续|此处补充' <draft>
   ```
   Must return empty.

   **Plus the subfield-specific portion** — see `references/anti-template.md` §I for the LLM-compression appendix (e.g. `LLM 部署很贵|f_θ|min E\[d\(f|统一目标函数|剪枝单元 G|更适合 LLM`). For any other subfield, replace this regex with that subfield's appendix grep. If no subfield appendix exists yet, build one after reading the first 2-3 notes of the batch — list the recurring "could-be-any-paper" phrases and add them to `anti-template.md` as appendix §J / §K / …

3. **Numeric anchor sanity check**: for each table number you cite, open `/tmp/cs-paper-reader-<batch>/_evidence/<Method>.md` (or the raw PDF text under `/tmp/`) and confirm the number appears verbatim. Off-by-one transcription errors are the second most common batch failure.

4. **Cross-note uniqueness** (only after ≥ 3 notes exist in the batch dir):
   ```bash
   for old in <batch>/*.md; do
     diff <(sed -n '/^### 1\.1/,/^###/p' <draft>) \
          <(sed -n '/^### 1\.1/,/^###/p' "$old") \
        | grep -c '^>' || true
   done
   ```
   Any pair with ≥ 5 identical non-empty lines is a red-line trigger.

5. **Image-link sanity** (only if the note embeds crops).

   At draft time the images still live in `/tmp/paper-figs/<Method>/` — they are not promoted to `<output-dir>/_figs/<Method>/` until Step F. So this check has two phases:

   **Before save (Step D)** — verify every linked basename already exists in the staging dir:
   ```bash
   grep -oE '!\[[^]]*\]\(([^)]+)\)' <draft> | sed -E 's/.*\]\(([^)]+)\).*/\1/' | while read -r img; do
     [ -f "/tmp/paper-figs/<Method>/$(basename "$img")" ] \
       || echo "MISSING (pre-promote): $(basename "$img") not in /tmp/paper-figs/<Method>/"
   done
   ```
   If anything is missing, either `clip.py scan` / `clip.py clip` didn't produce that crop, or the link path has a typo. Re-run the clipper or fix the link before saving.

   **After Step F's promote** — re-run the same check against the final output dir:
   ```bash
   grep -oE '!\[[^]]*\]\(([^)]+)\)' <note.md> | sed -E 's/.*\]\(([^)]+)\).*/\1/' | while read -r img; do
     [ -f "<output-dir>/$img" ] || echo "MISSING (post-promote): $img"
   done
   ```
   Every embedded image must now resolve to an existing PNG under `<output-dir>/_figs/<Method>/`. A miss at this stage means Step F's `cp` skipped the file (basename mismatch, permission issue, etc.) — fix and re-promote before marking the row 🟢 in `_progress_<batch>.md`.

6. **§4 experiment-section redundancy self-audit** (mandatory; this is the last check before save).

   `check_note_quality.py` and the grep above catch *structural* duplication near each screenshot, but they cannot judge whether the §4 prose / Markdown tables / red-block explanations together carry information that the reader already saw earlier in the note. This step asks the agent to answer that question explicitly **in its own reasoning / reply** (Mode A) or in the progress-row remark (Mode B). The answer **never goes into the note itself** — see Step 6.b below and SKILL.md §"Image-Rich Notes" for the matching rule.

   **Step 6.a — Surface candidate redundancies** (machine pass):

   ```bash
   # (i) Adjacent Markdown table + image — Case B (G1) violation candidate
   awk '/!\[Table/{img=NR} /^\|.*\|/ && img && NR-img < 15 {print "DUP_CANDIDATE: Markdown table at line " NR " within 15 lines of image at " img}' <draft>

   # (ii) The same numeric value appearing 3+ times across §4 + later sections
   #     (a single number cited 3 times is almost always re-quoted somewhere it shouldn't be)
   grep -oE '[0-9]+\.[0-9]+' <draft> | sort | uniq -c | awk '$1 >= 3 {print "MULTI_QUOTE: value " $2 " appears " $1 " times"}'

   # (iii) §4 numbers re-appearing verbatim in §6 (核心贡献) or §7 (讨论与局限)
   #      §6/§7 should reference §4 by section number, not re-quote numbers.
   awk '/^## 四、/{in4=1} /^## 五、/{in4=0} in4 && match($0,/[0-9]+\.[0-9]+/){ printf "%s\n", substr($0,RSTART,RLENGTH) }' <draft> | sort -u > /tmp/s4_nums
   awk '/^## 六、|^## 七、/{in67=1} in67 && match($0,/[0-9]+\.[0-9]+/){ printf "%s\n", substr($0,RSTART,RLENGTH) }' <draft> | sort -u > /tmp/s67_nums
   comm -12 /tmp/s4_nums /tmp/s67_nums | awk 'NF{print "CROSS_SECTION_DUP: §4 number " $0 " is re-quoted in §6/§7"}'
   ```

   Hits from (i)/(ii)/(iii) are **candidates**, not certain failures — the agent must adjudicate each one.

   **Step 6.b — Walk through the experiment-redundancy checklist** (semantic pass, done by the agent in its own reasoning / response — **do NOT write the checklist into the `.md` file**; readers don't care about the process, only the product).

   Answer each line below for yourself before issuing the Write. Save only when every line is OK / FIXED / N/A. Surfacing this in the agent's reply (or thinking) is enough — the note itself stays clean.

   候选信号（来自 Step 6.a grep；填 N/A 表示无命中或确认为误报）：
   - DUP_CANDIDATE 数量: ____   处理: ____
   - MULTI_QUOTE 命中: ____     处理: ____
   - CROSS_SECTION_DUP 命中: ____ 处理: ____

   逐项确认（按 image-embedding-recipes.md G1/G2 四轴）：
   - [ ] G1 — §4 中每张表格截图，没有伴随一张 row/column 完全相同的 Markdown 表。
         （若并列，要么是 G1.a 跨论文合并 / G1.b 重新排序 / G1.c 明确标注"仅摘 N 行作为推理锚点"；否则删 Markdown。）
   - [ ] G2.alt-vs-redblock — 截图的 alt 文本（≤25字 topic）与下方红色解释开头第一句不同义。
   - [ ] G2.redblock-vs-prose — 红色解释里的数字不在紧邻段落 prose 中重复列出。
         （若 prose 已列三数，红色解释只挑反直觉的一个，或反之。）
   - [ ] G2.multi-image — §4 内没有两张截图承担同一个 claim；如有，仅留 body_refs 更高的一张。
   - [ ] G2.cross-section — §6/§7 没有 verbatim 重引 §4 的数字；它们要么按 §4.x 引用，要么改成抽象总结。
   - [ ] §4 的每个数字都能 grep 到 `/tmp/cs-paper-reader-<batch>/_evidence/<Method>.md` 或 raw/layout PDF text（已在 Step D.3 验过则填 OK）。

   保留例外（最多 1 处，需说明理由，在回复中说出来即可）：____

   **The above is a thinking template, not a note artifact**. Do not paste it into `<note>.md`. After walking through it, the note proceeds to Step E (Write) with the §4 cleaned up but no self-audit residue.

   **Adjudication rules** (apply during the walk-through):

   - DUP_CANDIDATE 必须逐条说明：是 Case A (subset，已标注 "仅摘 N 行") / Case C (re-keyed pivot) / 跨论文合并，还是 Case B (必删 Markdown 表)。
   - MULTI_QUOTE 三次以上的数字：通常是某个 headline 数字在 §1.3 + §4.2 + §6 都被引用——这是被允许的（headline 数字本来就是 contribution 锚点）；但其他被 3+ 次引用的数字几乎一定是冗余。
   - CROSS_SECTION_DUP 必须改成 §-reference，例如 §6 把 `"PPL=24.55"` 改成 `"§4.2 主结果（PPL 改善见表中 Wanda 对比）"`。

   **If any line cannot be answered OK / FIXED / N/A**, do not save the note. Revise §4 / §6 / §7 and re-run Step 6.a. If after one revision a line is still unresolved, save the note anyway, mark `⚠️ §4 冗余自检未通过` in the progress row (one-line reason), and let the user adjudicate. The progress row is where the audit failure gets recorded — never the note itself.

If any check fails, **revise the draft, don't save**. If two revision attempts still fail, save what you have, mark the row `⚠️` in the progress table with the reason, and continue — let the user decide whether to redo it.

### Step E — Write the file (one response, one Write call)

- Single `Write` call to `<output>/(Venue Year) MethodName-Paper Title.md`.
- Do not also try to update the progress table, run diffs, or delete an old file in the same response — that risks `max_output_tokens` truncation.

### Step F — Bookkeeping (next response)

In the response immediately after the Write:

1. Update the `_progress_<batch>.md` row: state → 🟢, fill in 行数 / §2-§3 公式数 / 数值数 / 备注.
2. Delete the old version of this note from the source dir (if any), so the new dir is the single source of truth.
3. Append the cross-note diff result to `<output>/_collision_warnings.md` only if a real collision was found.
4. **Promote referenced images** from `/tmp/paper-figs/<Method>/` to `<output>/_figs/<Method>/` (only PNGs cited in this note), then re-run the post-promote image-link sanity check from Step D.5. If any link is missing, fix before marking the row 🟢. Skip this step only if the note embeds no images.

### Step G — Announce and move on

One short line: `已完成 #N <Method> (行数 X / §2-§3 公式 Y / §4 数值 Z)`, then immediately start the next paper. No questions to the user.

---

## 2.5. Hard prohibition — no script-mode note generation

**You MUST NOT write any Python / shell / awk script that auto-generates the notes themselves.** This includes, but is not limited to:

- A `generate_notes.py` that loops over PDFs and writes a `.md` per paper from a template + the corresponding `/tmp/cs-paper-reader-<batch>/_evidence/<Method>.md`.
- A bash `for pdf in *.pdf; do … > note.md; done` that interpolates filled-in placeholders.
- Any chained pipeline that takes evidence files as input and emits drafts without the model re-reading and re-reasoning about each paper.

**Why this matters.** Scripts that fill a template from pre-extracted evidence can pass every check in `check_note_quality.py` (formula count, number count, anchor count, anti-template grep, collision diff) while producing notes that share an underlying narrative skeleton across the batch. The structural checks are necessary but not sufficient — they cannot distinguish "model understood this paper" from "model arranged this paper's evidence into the same template as the previous paper". A batch of script-generated notes that all pass `--strict` is exactly the failure mode this rule prevents.

**What IS allowed.** Scripts that perform pure data-prep / housekeeping with no semantic content:

- `pdftotext` / `pdftoppm` calls to produce raw text and page renders.
- Evidence extraction (`/tmp/cs-paper-reader-<batch>/_evidence/<Method>.md` collection of quotes, equations, table numbers) — these scripts are **just transcribing PDF excerpts**, not writing notes.
- Manifest construction, progress-table updates, collision diff invocations, image promote pipelines.
- Quality-check invocations (`check_note_quality.py`, grep residues, etc.).

The line is: **a script may move bytes around the filesystem; a script may NOT decide what a note says.**

**Execution discipline per paper.** Each note must be produced in the following shape:

1. The model reads the specific PDF (or its `/tmp/cs-paper-reader-<batch>/_evidence/<Method>.md`) **for this paper** in the current response or the immediately preceding one.
2. The model writes the note via **one `Write` tool call** in its own response — not via a `subprocess` / `os.system` invocation, not via a script's `open(path, 'w').write(template % vars)`.
3. The model's reasoning for that paper — the unique mechanism sentence (§2 Step B), the Evidence Seven-Pack ingestion, the per-paper §3.1 angle — must happen **inside the same conversation turn** as the Write call. The model cannot delegate this to a script.

If during a batch you find yourself tempted to write a "tiny helper script that just fills in the template", **stop and re-read this section**. That temptation is the exact failure mode. The correct response is to do one paper per response, by hand, even if the batch is large.

**Detection signal.** If your last 3 notes share a structural skeleton beyond §-headings (same number and ordering of subsections, same paragraph-count per subsection, same sentence-level scaffolding around quoted numbers), you have slid into script-mode even if no literal script exists. Stop, mark the affected rows `⚠️ script-mode risk` in `_progress_<batch>.md`, and rewrite the next paper from a blank draft after re-reading the PDF.

---

## 3. Red lines — when to actually stop

These are the only legitimate reasons to stop the batch:

1. **Path probe (§1.2) failed** — Chinese directory unusable.
2. **A required input file is missing** — manifest, style spec, or reference note can't be located.
3. **Three consecutive notes triggered the Step D anti-template scan and you couldn't fix them after one revision each.** This means the batch has a systemic problem — maybe the manifest is wrong, maybe the source PDFs all share a generic template, or maybe the reference notes are not actually representative.
4. **The progress table is corrupted** — concurrent writes, encoding issue, or you can't determine the next unfinished row.
5. **All papers in the batch are done.**

**Do not stop for**:
- A single paper with no Limitations section — write `PDF 中无 Limitations 章节` and continue.
- A PDF with a typo in a formula — copy faithfully, add `> 笔者注：原文此处…` and continue.
- One self-check failure on one note — revise once and move on. Mark `⚠️` if revision didn't fix it.
- Curiosity about whether the user is satisfied — they're not in the loop, that's the point of batch mode.
- **Reaching "a reasonable amount" short of the §1.0 hard target.** Finishing 24 of 47 is not done. Finishing 46 of 47 is not done. The only "done" is N of N, where N is the number locked in §1.0. If you catch yourself wanting to stop early because the conversation feels long or you're unsure the user still wants more, that is exactly the failure mode this rule guards against — keep going.

---

## 4. Final report

When the loop terminates because all papers are done (or because the user said stop), write `<output>/_final_report_<batch>.md`:

```markdown
# <Batch Name> 最终报告

## 总览
- 已完成: N / M
- 平均行数: X
- 平均 §2-§3 公式数: Y
- 平均 §4 数值数: Z

## 碰撞警告
（来自 _collision_warnings.md，若为空则写"无碰撞"）

## ⚠️ 建议人类优先抽查
1. <Method> — <reason>
2. ...

## ⭐ 质量最强（可作为后续批次的参照）
1. <Method> — <reason>
2. ...

## 整章 / 整批 路线小结
（≤ 200 字，概括这批论文覆盖的子方向）
```

Then announce: `<Batch Name> 全部完成` and **do not auto-start the next batch**. The user needs to inspect.

---

## 5. Resuming an interrupted session

If the session died mid-batch, the user will say "继续" or similar. To resume:

1. Read `<output>/_progress_<batch>.md`.
2. Find the first row whose state is not 🟢 / ✅✅ / ⚠️.
3. Restart from that paper at Step A. Do not re-do completed papers.
4. If the last incomplete paper has an evidence file under `/tmp/cs-paper-reader-<batch>/_evidence/<Method>.md` but no note file in `<output>/`, restart at Step B/C using that evidence file. (If `/tmp` was cleared by a reboot, the evidence file is gone — restart at Step A and re-extract.)
5. If the last incomplete paper has a partial note file (truncated mid-Write from `max_output_tokens`), discard the partial and restart at Step C.

Do not announce these heuristics every time — just resume.

---

## 6. Token budget heuristics

- **Each note Write is ~ 10–20k output tokens** depending on length and LaTeX density.
- If you find yourself reasoning about a single note for > 5k tokens before writing, stop and just write — over-deliberation crowds out the actual note within the response budget.
- xhigh reasoning_effort wastes output budget on visible chain-of-thought. medium or high is enough for paper-note tasks. If `model_reasoning_effort` is configurable in this run, prefer `high`.

---

## 7. What success looks like

- Every note in the batch directory passes the four Step D self-checks.
- The progress table is 100% 🟢 / ✅✅ at the end.
- `_collision_warnings.md` is short — ideally empty.
- A spot-check of any 2 random notes' §1.1 and §3.1 shows the per-paper angle (Step B) clearly visible in the first 5 lines.
- LaTeX renders cleanly: no `rac{`, no `\\sum`, no truncated `$$ ... $`.
- Every cited number can be `grep`'d in the corresponding `/tmp/cs-paper-reader-<batch>/_evidence/<Method>.md`.


---

## 8. Field-tested implementation snippets (2026-05-16)

These are additive implementation notes from an actual long batch of LLM-pruning papers. The **snippets themselves are domain-agnostic** (`pdftotext`, `pdftoppm`, draft-check-land sequence, mechanism-sentence discipline); the **method names appearing in examples** are illustrative only.

### 8.1 Preferred draft-check-land sequence

Use a temporary draft path first:

```bash
draft=/tmp/<Method>_note.md
target="<output-dir>/(Venue Year) MethodName-Paper Title.md"
python3 ~/.codex/skills/cs-paper-reader/scripts/check_note_quality.py \
  --note "$draft" \
  --compare-dir "<output-dir>" \
  --refs "<approved-ref-1.md>" "<approved-ref-2.md>" \
  --subfield "<subfield-name-if-applicable>"   # e.g. llm-compression; omit if no pattern file exists yet
cp "$draft" "$target"
```

Only after the script returns `OK` should you update `_progress_<batch>.md`. This is stricter than editing the target file directly and prevents half-written notes from becoming the source of truth.

**About `--subfield`**: pass the name (or path) of a file in `~/.codex/skills/cs-paper-reader/subfield-patterns/`. Without it, only universal forbidden patterns and LaTeX residues are checked — appropriate when reading a subfield with no pattern file yet. To author a new subfield's file, see `references/anti-template.md` §"How to specialize this file for a new subfield".

### 8.2 Raw/layout/PDF visual fallback

For every formula-heavy PDF, keep both text extractions:

```bash
pdftotext -raw    "$pdf" "/tmp/<Method>.raw.txt"
pdftotext -layout "$pdf" "/tmp/<Method>.layout.txt"
```

Use `raw.txt` for paragraph flow and `layout.txt` for tables / aligned equations. If either extraction produces suspicious notation (`||W| × |W||`, missing radicals, broken subscripts), render the page:

```bash
pdftoppm -f <page> -l <page> -png -r 180 "$pdf" "/tmp/<Method>_page"
```

Then inspect or crop the PNG before writing the formula. Prefer one visually verified formula over a plausible but wrong reconstruction from mangled text.

### 8.3 Exact-line collision check

The robust check is not a fuzzy similarity score. Count identical non-empty lines in the same subsection:

```bash
python3 ~/.codex/skills/cs-paper-reader/scripts/check_note_quality.py \
  --note "$draft" --compare-dir "$outdir" --refs "$ref1" "$ref2"
```

If §1.1 or §3.1 has ≥5 identical non-empty lines with an earlier note, rewrite the current note's angle/mechanism before saving.

### 8.4 Per-paper mechanism sentence

Before writing §3.1, force a short mechanism sentence:

```text
#N <Method> 独特机制：<≤30 字，必须包含本论文独有对象/操作>
```

Examples of acceptable specificity (from an LLM-compression batch — the **shape** is what to imitate; replace the domain vocabulary for any other subfield):
- `跨域敏感度累积保留权重`
- `表达式树进化剪枝公式`
- `层间互信息冗余线性分配`

Examples that are too generic (these failure shapes generalize across subfields — they are the kind of sentence that could describe any paper in the area):
- `选择重要权重并剪枝`
- `结构化压缩并恢复性能`

If the sentence is wrong after reading the PDF, correct it before drafting; a wrong mechanism sentence almost always predicts a generic §3.1.

### 8.5 Progress-row remarks

Use remarks to preserve source uncertainty rather than hiding it:

- `含作者 Limitations`
- `PDF 无独立 Limitations 章节；含 Impact Statement`
- `未确认正式录用`
- `公式经 PDF 页面渲染核对`

These remarks help the next session resume without rediscovering the same ambiguity.
