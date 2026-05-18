---
name: cs-paper-reader
description: Use when the user wants to read, summarize, dissect, compare, or write structured Chinese Markdown notes for computer science research papers, especially from PDF/arXiv/conference papers. Supports both single-paper deep reads (Mode A) and unattended batch reading of an entire folder / chapter / manifest (Mode B). Produces deep paper-reading notes in a style with background, motivation, formal definitions, method details, formula explanations, experiments, differences from related work, contributions, limitations, and research ideas.
metadata:
  short-description: Deep Chinese CS paper notes (single + batch reading)
---

# CS Paper Reader

## Output Goal

Produce a Chinese Markdown paper-reading note modeled after the user's existing long-form notes: precise, structured, explanatory, and useful for research reuse. **Prefer deep interpretation over shallow summary.** Notes must be grounded in the actual PDF content, not in second-hand descriptions from a citation index or another note.

## Output Hygiene

**Display math formatting**: keep readable Markdown display equations in the normal multi-line form with standalone `$$` fence lines. Standalone `$$` lines are formatting-only and must be ignored by anti-template / collision checks; do not collapse formulas into one-line `$$...$$` blocks merely to avoid repeated fence-line collisions.

Evidence files, scan manifests, raw OCR/text dumps, exploratory crops, and other intermediate artifacts must stay under `/tmp` or another explicit scratch path, not inside the final reading output directory.

The final reading output directory should contain only:
- finalized Markdown notes;
- progress / final report / collision-warning files (`_progress_<batch>.md`, `_final_report_<batch>.md`, `_collision_warnings.md`);
- images actually referenced by the notes.

In Mode B, store per-paper evidence and `paper-figure-clipper` `manifest.json` files under a task-specific `/tmp` directory, for example `/tmp/cs-paper-reader-<batch>/`, and promote only referenced images into `<output>/_figs/<Method>/`.

## When To Use

Use this skill for computer science papers when the user asks to:
- 精读 / 解读 / 总结 / 拆解论文
- 写 `论文名称.md` 笔记
- 批量重写一个目录 / 章节 / manifest 里的多篇论文笔记
- 比较一组论文或梳理相关工作
- 提取公式、算法、实验、贡献、局限、可借鉴点
- 判断方法和某类范式 / 技术是否相似

If the task mainly needs PDF rendering / layout extraction, also call the `pdf` skill.

## Two Operating Modes

This skill has two modes. Decide which one at the start and announce it.

### Mode A — Single paper deep read

The default. The user provides one PDF or arXiv ID. Follow §"Reading Workflow" and write one note.

### Mode B — Batch reading

Triggered when any of these is true:
- The user points at a folder of PDFs and asks to "逐篇阅读 / 全部读完 / 整章 / 全自动".
- The user provides a manifest / progress file (e.g. `_manifest_XXX.md`, `_progress_XXX.md`).
- The user points at a folder containing multiple existing low-quality notes to rewrite.
- The user explicitly asks "一次性 / 全自动 / 跑完 / 重写整章".

Batch reading covers both **fresh batch reading** (no prior notes — generate from PDFs) and **batch rewrite** (replace existing low-quality notes). The workflow is the same; only Step §2.Step E's "delete old version" branch differs.

In Mode B, read **`references/batch-workflow.md`** first and follow it strictly. Mode B has additional requirements that Mode A does not (progress tracking, anti-template enforcement, response-budget splitting, etc.) — failing to honor them is the failure mode this skill was hardened against.

**🚫 Hard prohibition in Mode B**: you MUST NOT write a Python / shell script that auto-generates the notes themselves from templates + evidence files. Each note must be produced by the model itself in its own `Write` call, after re-reading and re-reasoning about that specific PDF. Scripts are allowed only for pure data-prep (pdftotext, evidence extraction, progress-table updates, quality-check invocations) — never for content generation. See `references/batch-workflow.md` §2.5 for the full rule and detection signals. Even when the user says "自动 / 全自动 / 批量", this prohibition still applies — "automated" means "no questions to the user between papers", NOT "delegate writing to a script".

## Reading Workflow (both modes)

1. **Identify source**: PDF / arXiv / OpenReview / ACL Anthology / PMLR / local Markdown. If only a citation is given, locate the actual PDF before writing anything.
2. **Extract the PDF with `pdftotext -layout`** into `/tmp/<shortname>.txt`. If the layout breaks formulas, also run `pdftoppm` and visually inspect the relevant pages. **Never write a note without opening the PDF.** "I know this paper from training data" is not acceptable — quote the PDF.
3. **Collect the Evidence Seven-Pack** before drafting any §1-§6 prose:
   1. The **problem statement sentence** from the abstract (verbatim quote).
   2. At least **one paragraph from the introduction that names a prior work and explains why it fails**.
   3. At least **two numbered equations** from the method section (with their Eq. number).
   4. The **Algorithm box / pseudocode** (or the closest equivalent).
   5. At least **two numerical results from the main table** (with table number, column name, dataset name).
   6. At least **one ablation table/figure** with its key numbers.
   7. The **Limitations / Future Work paragraph** verbatim. If the PDF has no such section, write literally `PDF 中无 Limitations 章节` in your note.
4. **Skim structure**: title, authors, venue/date, abstract, introduction, method, experiments, limitations, relevant appendix.
5. **Extract the central claim**: write the paper's one-sentence thesis before details.
6. **Build the note around questions**:
   - 这篇论文解决什么问题？为什么重要？
   - 现有方法为什么不够？根本瓶颈是什么？
   - 论文的核心 insight 是什么？
   - 问题如何数学化定义？训练域、目标域、假设、输入输出、风险函数分别是什么？
   - 方法具体怎么做？每个模块输入/输出/优化目标是什么？
   - 算法如何用符号、目标函数、递推/优化步骤严谨描述？每一步的数学含义和直觉是什么？
   - 实验如何证明 claim？哪些表格/消融最关键？
   - 与相关工作的区别是什么？
   - 局限、失败场景、可改进点是什么？
7. **Write with interpretation**: Do not merely translate the abstract. Explain why each design matters and how it connects to the problem.
8. **Flag uncertainty**: If a claim is inferred rather than explicitly stated, say "我的理解是" or "可理解为". If the PDF itself contains a typo (e.g. a subscript that disagrees with another part of the same paper), copy it faithfully but add a `> 笔者注：原文此处 ...，疑为笔误` line.
9. **Run the per-note self-check before `Write`** (mandatory, both modes). Procedure and pass thresholds in §"Per-Note Self-Check"; result file goes to `/tmp/...`, never into the md.

## Mathematical Rigor Requirements

These are mandatory for standard and deep notes:

- **Problem definition must be formula-based**: Define source/target domains, samples, labels, time/domain descriptors, model family, prediction target, and risk/objective using inline or block equations. Do not describe the task only in prose.
- **State assumptions explicitly**: Write the paper's modeling assumptions as equations or quantified statements whenever possible.
- **Algorithm section must be mathematically self-contained**: For each module, specify input, output, learned parameters, update rule/objective, and how it composes with other modules.
- **Explain every central formula**: After each key equation, explain each symbol and the logic connecting it to the paper's claim.
- **Use the paper's own symbols** wherever possible. Do not silently replace `W_l, X_l, H^{-1}` with generic `θ, x, H`. If you must normalize notation across two papers being compared, declare it once at the top of the relevant section.
- **Quantitative hard floors per note**:
  - §3 (方法详解) must contain **≥ 3 formulas that are numbered or recognizable as appearing in the PDF** (not invented). At least 2 of them must be the paper's actual Eq. (with their `Eq. N` label).
  - §4 (实验结果) must contain **≥ 2 specific numbers from real tables**, each annotated with `Table X, column name, model/dataset`.
  - §5 (与相关工作的区别) must name **≥ 2 specific compared methods** and give a quantitative or mechanism-level difference (not vague claims like "更适合该任务" / "performance is better on benchmark X").

## LaTeX & Markdown Hygiene (critical — silently breaks notes if violated)

These bugs have been observed in real outputs and must be guarded against on every write:

- **Backslash commands must survive serialization.** When writing math like `\frac{a}{b}`, `\sum`, `\sqrt{}`, `\alpha`, `\beta`, etc., the leading backslash gets eaten in some shells and JSON tool-call paths. **Before declaring a note done, grep the file for these residues and fix them**:
  ```bash
  grep -nE '[^\\](rac\{|um_|qrt\{|lpha|eta\s|ambda|abla)' "<file>.md"
  ```
  If anything matches, replace `rac{` → `\frac{`, `um_` → `\sum_`, etc. **The note is not done until this grep returns empty.**
- **Block formulas use `$$ ... $$` on their own lines.** Tags use `\tag{N}` only when the paper has an Eq. N you're directly citing.
- **Inline math uses `$...$`, never backticks.** Symbols, formulas, function/set/space names that the reader should see *rendered* (e.g. `$x \in \mathcal{X}$`, `$\theta$`, `$\mathbb{E}[\cdot]$`, `$O(n \log n)$`) must be wrapped in `$...$`. **Backticks are reserved for code, file paths, shell commands, and CLI flags** — wrapping a formula in `` ` `` produces monospace literal text (`x \in \mathcal{X}`) that doesn't render and is unreadable. This applies inside bullet lists too: `- $\theta$：模型参数`, NOT `` - `\theta`：模型参数 ``.
- **Never use `\\sum`, `\\frac`, `\\{`, `\\}` etc.** with double-backslash in Markdown math — Markdown will eat one backslash and you get a literal `\sum`.
- **Math Render Gate is mandatory** before marking any note done:
  - no invisible control characters in the Markdown body; CRLF line endings are OK, but a bare carriage return byte (`\r`) or NUL byte is blocking because it can split commands like `\right` into an unrenderable fragment;
  - display math fences are standalone `$$` lines; standalone `$$` lines are valid and must not be treated as anti-template collisions; do not collapse multi-line formulas into one-line `$$...$$`;
  - every display math block is closed, has balanced braces after ignoring escaped `\{` / `\}`, and has matching `\left` / `\right`;
  - suspicious over-escaped literal braces such as `\\}` or `\\{` are blocking unless the source PDF visibly uses a LaTeX line break followed by a brace, which is extremely rare in these notes.
- **Position Render Gate is mandatory** for embedded crops: every `![...](_figs/...)` line must have a nearby visible red explanation block. If the red block is **before** the image, use `下图解释 / 下表解释 / 下方算法`; if the red block is **after** the image, use `上图解释 / 上表解释 / 上方伪代码`. A block saying `上表解释` before a table, or `下图解释` after a figure, is a render-position error. If Markdown layout is uncertain, use a neutral label like `Table 1 解释`, but keep the block adjacent to the image.
- **Tables must be Markdown-renderable**: every row has the same column count, separator row uses `---` / `---:` consistently, numbers preserve the paper's decimal precision.
- **Hidden HTML for color emphasis**: use `<font color="red">`, `<font color="blue">`, `<font color="green">` sparingly (1-3 per note), each highlighting a distinct insight. Don't sprinkle them throughout.

## Default Note Template

Use this structure unless the user requests another format:

```markdown
# MethodName: Full Paper Title

> **发表信息**: venue/year or arXiv date
> **作者**: 第一作者 (单位) / 共同一作 (单位) / 其他作者 …
> **机构**: ...
> **代码/项目**: ...
> **本地 PDF**: <absolute path>

---

## 一、研究背景与动机

### 1.1 [论文自己关心的具体问题 — 写论文实际针对的瓶颈，不写适用于全领域的通用句]
### 1.2 [论文具体批评的 2-4 个先前方法，必须出现具体方法名]
### 1.3 关键 Insight: "[≤25 字的论文自己的一句话]"

## 二、预备知识与形式化定义

### 2.1 数学化任务定义（用论文符号）
### 2.2 论文用到的关键工具 / 前置算法
### 2.3 符号表（≥ 4 个新符号时显式列出）

## 三、方法详解

### 3.1 总览（一张数据流图 or 100-200 字的 mechanism）
### 3.2 模块 / Stage 1
  #### 3.2.1 输入 / 输出 / 可学习参数
  #### 3.2.2 核心公式（带 Eq. 编号、逐符号解释）
  #### 3.2.3 直觉：这一步解决 §1.2 的哪个具体缺陷
### 3.3 模块 / Stage 2 ...
### 3.x 算法伪代码（与论文 Algorithm 框对齐；若论文没有，自构时标"归一化伪代码"）
### 3.x+1 复杂度 / 实现成本

## 四、实验结果

### 4.1 实验设置：模型族 / 数据集 / 关键超参（论文所在子领域的核心控制变量，如稀疏率、比特数、学生大小、检索深度、上下文长度等）
### 4.2 主结果（≥ 1 张数值表，数字必须来自 PDF）
### 4.3 关键消融（≥ 1 张表/图的关键发现）
### 4.4 失败 / 不利场景（来自 PDF）
### 4.5 与最直接 baseline 的具体数字差

## 五、与相关工作的区别

## 六、核心贡献总结

## 七、讨论与局限

## 八、对后续研究的启发（可选）
```

For short notes, compress sections but keep: 背景动机、方法、实验、区别、贡献局限.

## Style Rules

- Write in Chinese; keep paper-specific technical terms in English when clearer.
- Use numbered Chinese section headers: `## 一、...`, `### 1.1 ...`.
- Start with metadata block if available.
- **Author affiliations**: in the `作者` line, always annotate the **first author** (and any co-first authors marked with `*` / `†` / `equal contribution`) with their affiliation in parentheses, read from the PDF's title-page footnote. Example: `Alice Wang* (MIT) / Bob Chen* (Tsinghua) / Carol Liu (Google)`. Other authors get affiliations only if it materially helps (e.g. cross-institution collab worth highlighting).
- Use bold emphasis for key concepts.
- For formulas, show the equation and then explain each symbol line by line.
- For algorithms, describe stages with inputs/outputs, learned variables, objective functions, update/recurrence rules, inference rules, and intuitive purpose.
- For tables, state what each table proves rather than copying all numbers — but **always** include enough specific numbers to anchor the claim.
- Prefer "根本原因 / 直觉 / 为什么有效 / 为什么失败" explanations.
- Add "与相关工作的区别" even if the original paper only has a related work section.
- Be critical: distinguish author claims, evidence, and your own inference.

## Image-Rich Notes (figure / table / algorithm / equation crops)

A high-quality paper note is often **image-rich**: schematic figures, result tables, and pseudocode are easier to read as crops from the original PDF than as transcribed prose. Use the companion skill **`paper-figure-clipper`** to produce these crops with precise bounding boxes (never percent-of-page heuristics).

**Image-Rich Notes is ON by default** — every note should embed figures/tables unless the paper genuinely has none worth citing. Don't ask the user whether to enable it.

### When to embed an image

Embed a crop in the note when ANY of these is true:
- **§3 has a key schematic** (e.g. an architecture diagram, data-flow chart, or routing pattern) the prose can't fully convey.
- **§3 has algorithm pseudocode** that matters for reproducibility (any boxed `Algorithm N` with non-trivial control flow).
- **§4 reports a multi-column ablation** whose structure (header hierarchy, grouped rows) is more readable as the original table.
- **§4 has a scaling or trend curve** (e.g. metric-vs-control-parameter) whose visual trend is more informative than 3-5 transcribed numbers.
- **A single equation is too complex** for faithful Markdown reproduction (multi-level subscripts, matrix operators) and a tight crop is clearer.

Do NOT embed crops:
- For decorative reasons. Every embedded image must be cited by name and explained in the surrounding prose.
- As a substitute for transcribed numbers. Tables in §4 should be discussed by specific cell values; the crop is supplemental.

### Workflow

1. **Once per paper (MUST, no shortcuts)**: run `clip.py scan` to enumerate all figures/tables. **Do NOT bypass this with self-written `PyMuPDF` / `fitz` / `pdfplumber` bbox guessing** — `clip.py` uses caption-anchored bboxes that are far more reliable than hand-picked coordinates, and it produces the `manifest.json` that downstream steps depend on. Roll-your-own clipping is only allowed if `clip.py scan` itself errors out, and you must say so in the progress remark.
   ```bash
   ~/.codex/skills/paper-figure-clipper/scripts/clip.py scan \
     --pdf "<paper.pdf>" \
     --out-dir "/tmp/paper-figs/<Method>"
   ```
   Read the resulting `manifest.json` to learn which figures/tables exist and their captions. **Sort entries by `body_refs` descending** — figures with `body_refs ≥ 3` are central to the paper's narrative and should be embedded first; `body_refs = 1` is usually supplementary and can be skipped unless it carries a unique ablation insight.

   **🚫 Do NOT call `view_image` on every scan-produced PNG.** That burns enormous token budget for negligible quality gain — scan output is reliable by default. Open **only the top 1~3 PNG by `body_refs`** to visually verify the crop is clean (no caption cut off, no neighboring text bleed, no missing legend). Open the top 2~3 only when they are equally critical to the note. All other crops are accepted as-is from `scan` without inspection. If the top-1~3 crop is broken, fix via `clip bbox` per step 2 — **inspecting more PNGs will not change this decision**.

2. **For algorithm/equation/sub-figure crops** that `scan` doesn't cover, use `clip` mode (also to `/tmp/`). **优先级**：若 step 1 产出的概念图/框架图 bbox 有严重问题（截断、漏标题、含杂内容），优先用 `clip bbox` 微调原图；其它情况（scan 没覆盖的算法/公式/子图）才走 `clip` mode 重裁。

   **Bad-crop salvage (4-candidate recipe)**: when the top-1 (or top-2/3) figure / algorithm has severe truncation (only the title, missing last lines, half a figure cut off), do **NOT** retry with one larger bbox — that usually fails again. Instead generate **4 bbox candidates** at progressively larger margins into `/tmp/paper-figs/<Method>/<artifact>_candidates/`, view the 2×2 contact sheet, `cp` only the winner to the canonical filename, delete the rest. Copy-pasteable commands in `~/.codex/skills/paper-figure-clipper/references/recipe-book.md` §R4.5. **Trigger** — step 2 fixes at most the top-1/top-2 critical figures this way; all other figures keep `scan` output unchanged. Never run the 4-candidate recipe proactively.

   ```bash
   clip.py clip --pdf P.pdf --out /tmp/paper-figs/<Method>/algorithm_1_p5.png algorithm --label "Algorithm 1" --page 5
   clip.py clip --pdf P.pdf --out /tmp/paper-figs/<Method>/equation_3_p3.png equation --label "3" --page 3
   ```

3. **Reference in the note** with relative Markdown image syntax. **The explanation goes in the body as a red-font block**, never in alt text. The example below is from an LLM-compression note (SparseGPT) — the format generalizes to any paper:
   ```markdown
   <font color="red">**下方算法**</font>：第 6–9 行的 Hessian 更新只依赖右下子矩阵，这是 SparseGPT 复杂度优化的来源；第 4 行的 mask reselect 每 $B_s=128$ 列做一次。

   ![Algorithm 1 — SparseGPT 单层剪枝主循环](_figs/SparseGPT/algorithm_1_p5.png)
   ```
   Why a body block instead of a long alt text: Markdown viewers render alt text as a hover tooltip — readers can't see it without mousing over. Putting the explanation as visible body text means it's readable on first scroll. Use one of `上图解释 / 下图解释 / 上表解释 / 下表解释 / 下方算法 / 上方伪代码` depending on position (**IMPORTANT**: image-below content uses `上*`, image-above content uses `下*` !). The alt-text inside `[ ]` must be **minimal** — just `<Label> — <≤ 25 字 topic>`, no explanation, no "why" sentence. See `references/image-embedding-recipes.md` §0 for the full position rule (schematic → image above, results table → image below, etc.).

4. **After the note is finalized**: promote only referenced images from `/tmp/` to `<batch>/_figs/<Method>/`. This keeps the cloud-synced workspace lean — unused crops never leave `/tmp/`.
   ```bash
   grep -oE '!\[[^]]*\]\(([^)]+)\)' <note.md> | sed -E 's/.*\]\(([^)]+)\)/\1/' | while read img; do
     mkdir -p "<batch>/$(dirname "$img")"
     cp "/tmp/paper-figs/<Method>/$(basename $img)" "<batch>/$img"
   done
   ```

### Output naming convention

Use `<batch>/_figs/<Method>/<type>_<label>_p<page>.png` so paths are deterministic. Examples (illustrative, from various domains):
- `_figs/SparseGPT/algorithm_1_p5.png`
- `_figs/OWL/figure_1_p2.png`
- `_figs/SliceGPT/table_3_p7.png`

See `~/.codex/skills/paper-figure-clipper/SKILL.md` for full options (DPI, padding, explicit bbox, page fallback) and `~/.codex/skills/paper-figure-clipper/references/recipe-book.md` for copy-pasteable commands.

**For *where* to place each embedded image in the note** (§1.3 vs §3.x vs §4.5) and the right caption style, see **`references/image-embedding-recipes.md`** — 8 real placement recipes covering motivation hooks, method schematics, algorithm crops, main-result tables, scaling curves, ablation figures, and throughput tables. Use it as a pattern library: find the recipe matching your candidate figure's paper-role, then adapt its caption pattern.

**Before saving any note with embedded images, the four quality gates in `image-embedding-recipes.md` §0.5 apply** — two hard gates and two writing guidelines:

- **G1 (hard)**: screenshot-only by default; Markdown table requires explicit justification (cross-paper merge, re-keyed pivot, or labeled reasoning subset). No "I抄了整张表然后又贴了截图" duplication.
- **G2 (hard)**: no redundancy across alt-text / red-block / prose / multi-image / cross-section.
- **G3 (guideline)**: when writing each red-block, push from "what the image shows" to "why the author put it here" — try to add one §1.3 / §3.x / §6 / §7 back-reference if a natural one exists. Aim for majority Tier A (字面 + 一条 §-reference); allow a minority of Tier B (字面 only) for genuinely contextual figures.
- **G4 (guideline)**: most images should map to a §6 contribution bullet; if MOST images don't, revisit §6 or trim images.

The two hard gates protect against concrete redundancy/duplication failures; the two guidelines push the note from image slideshow toward "图说同时讲方法/动机/贡献". 

**§4 experiment-redundancy self-audit (mandatory at end of every note)**: after drafting, run the redundancy grep (`batch-workflow.md` §2 Step D.6.a) and **walk through the checklist in your own reasoning / reply** to confirm no Markdown table duplicates a screenshot, no number is re-stated across §4 → §6/§7, and no red-block restates the prose's numbers. **The self-audit is a process, not a product — do NOT write the checklist into the `.md` file**; readers care about the cleaned-up note, not the audit trail. Failures get recorded in the progress row (Mode B) or in your reply (Mode A), never in the note itself. Applies to both Mode A and Mode B.

## Anti-Template Red Lines

These phrases / patterns indicate the note is not actually based on the PDF and must be rewritten. Before saving, scan the draft for them.

**Domain-agnostic red lines** (apply to every paper):

- 通用占位句：任何描述"这个领域为什么重要"的句子，如果它不引用 PDF 中具体的数字/方法/瓶颈，就是占位句（每个子领域都有自己的"XX 部署很贵 / XX 模型越来越大 / XX 数据集太小"）。
- 占位符变量名：`EvidenceSpecificScore`、`Compress_method`、`ScorePlaceholder`、`f_θ`、`min E[d(f,f')]`、`重要性分数 s_g`、`目标函数 L` — 必须替换为论文真实符号；论文里若没有就不要发明。
- 元描述实验：`应该查 ablation`、`应该看 <metric>/精度 是否保留`、`关键看消融` — 替换为来自论文表的具体数字。
- 无量化空话：`更适合该任务`、`在某些 benchmark 上优于 baseline`、`显著提升` — 替换为具体方法名 + 具体数字差。
- "我的笔记骨架" 暴露：`待填入`、`TODO`、`见后续`、`[此处插入 XX]` — 落盘前必须清理。

**Domain-specific anti-patterns** (`references/anti-template.md` 中有按子领域分组的硬编码 grep 模式；当前最完整的是 LLM 压缩 batch 总结出来的一组)。读其他子领域（如知识编辑、检索增强、推理引擎）的论文时，按相同原理为该子领域积累自己的占位句清单。

See `references/anti-template.md` for the full pattern list and what to replace each with.

## Per-Note Self-Check (mandatory, runs at note exit)

**Every note (Mode A or Mode B) must pass a self-check before it counts as done.** The check is a process artifact, not part of the deliverable.

- **What to check** — 6 numbers: §2-§3 PDF 公式数 (≥ 3) / §4 PDF 数值数 (≥ 2) / §5 比较方法数 (≥ 2) / PDF 章节-表号引用次数 (≥ 5) / LaTeX residue grep 是否清空 (Y/N) / 自检日期. Mode B additionally runs the 5 Step D checks in `batch-workflow.md` (anti-template, numeric anchor, cross-note collision, image-link sanity, §4 redundancy).
- **Where the result goes** — write to `/tmp/cs-paper-reader-<batch>/_selfcheck/<Method>.txt` (Mode B) or `/tmp/<Method>_selfcheck.txt` (Mode A). **Never** as `<!-- 自检 -->` HTML comments inside the `.md`.
- **When to run** — right before the final `Write` in Mode A, or at Step D in Mode B (`batch-workflow.md` §2 Step D is the authoritative procedure).
- **On failure** — revise the note and re-run once. If still failing, save anyway and record `⚠️ 自检未过: <reason>` in `_progress_<batch>.md` (Mode B) or surface it in your reply (Mode A). Failure metadata never enters the note itself.

## Depth Control

- **Quick summary**: 1-2 pages; skip most equations; focus on insight and takeaways.
- **Standard note**: full template; include key formulas and main experiments. **220–400 行** for a standard note; soft-expand to **400–550 行** when the paper is formula-dense (§2-§3 formula tags ≥ 12) AND has ≥ 3 distinct ablation tables AND covers multiple evaluation axes (zero-shot / scaling / efficiency / downstream). See `references/batch-workflow.md` §2 Step C for the full rule and the inflation check to run before `Write` if the draft exceeds 550 行.
- **Deep read**: include derivations, appendix details, failure modes, and research ideas. Up to ~600 行 if the paper warrants it.

When unspecified, use **standard note**.

## Comparison Tasks

For multiple papers, create:
- A taxonomy table: problem, generated object, architecture, training objective, assumptions, datasets.
- A "same vs different" section.
- A "which paper to read first" recommendation.
- A "possible synthesis/new idea" section.

## File Output

When asked to write files:
- Name notes as `(Venue Year) MethodName-Paper Title.md` unless the user specifies another path, e.g. `(ICML 2025) PropMEND-Hypernetworks for Knowledge Propagation in LLMs.md`.
- Name downloaded source PDFs with the same base name as the note: `(Venue Year) MethodName-Paper Title.pdf`.
- Before using `arXiv` as the venue in a filename, check whether the paper has since been accepted by a conference, journal, workshop, or findings venue. Prefer the accepted venue and publication year from official sources (publisher page, conference proceedings, OpenReview, ACL Anthology, PMLR, IEEE/ACM, or the paper's own metadata). Use `arXiv Year` only when no accepted venue can be verified.
- When the official paper title already begins with the method name or acronym, strip that duplicated leading token in the visible filename so the result stays `MethodName-Paper Title.md` / `MethodName-Paper Title.pdf` with a literal hyphen between the method name and the remaining title; keep natural spaces inside the title itself.
- Preserve natural spaces in paper titles and file names; do not replace spaces with underscores unless the user explicitly asks for machine-safe names.
- `MethodName` should be the paper's method/acronym if clear; otherwise use the shortest distinctive method phrase from the title.
- Preserve existing user note style and Chinese numbering.
- Do not overwrite existing notes without checking or making a clearly named new file.

## Response-Budget Discipline (especially critical in Mode B — Batch reading)

A single model response has a finite `max_output_tokens`. Writing a 300-line note + saving it + updating the progress table + deleting an old file in one response can hit the cap mid-output and truncate the file. To avoid this:

1. **Plan the note offline first**: collect Evidence Seven-Pack, list section bullets — these are cheap thinking, not output tokens.
2. **Write each note in its own dedicated response**. Don't bundle two notes in one turn.
3. **Within a note, prefer one Write call that emits the full Markdown**, rather than streaming many small Edit calls.
4. **Bookkeeping (progress table update, old-file rm, diff self-check) goes in the *next* response after the note is written.** This guarantees the note is on disk before any later step can fail.
5. **If you see your previous response truncated with `max_output_tokens` / "stream disconnected"**: the note text is in your context, the Write call did not complete. Re-issue Write with the same content in a fresh response — do not start the note over from scratch.

For deeper guidance, including the full batch workflow with progress tracking and red-line handling, see **`references/batch-workflow.md`**.


## Field-Tested Batch Additions (2026-05-16)

The following additions originated from a large batch of LLM-compression / pruning notes, but each rule is stated in domain-agnostic form. They are additive guardrails; keep all earlier rules.

- **Use the bundled self-check script when writing files**: after drafting a note, run `python3 ~/.codex/skills/cs-paper-reader/scripts/check_note_quality.py --note <draft.md> --compare-dir <batch-dir> --refs <approved-ref-1.md> ...`. This implements the exact forbidden-pattern, LaTeX-residue, and §1.1/§3.1 collision checks that repeatedly caught real failures. **Pass `--subfield <name>` (e.g. `--subfield llm-compression`) to additionally enforce subfield-specific anti-template phrases from `subfield-patterns/<name>.txt`**; omit it when reading a subfield with no pattern file yet — universal checks alone still apply, with no false positives from another subfield's vocabulary.
- **Read both raw and layout PDF text**: for formula-heavy papers, extract both `pdftotext -raw` and `pdftotext -layout`; use raw text for prose continuity and layout text for tables / formula placement. If a formula contains ambiguous constructs such as nested norms, square roots, or Unicode math, render that PDF page (`pdftoppm`) and visually inspect the equation before writing it.
- **Say the paper-specific mechanism before §3**: in batch mode, before drafting each note, write a ≤30 Chinese-character mechanism sentence for yourself (or in the progress reply when requested). If the sentence could also describe a previous paper, the §3.1 plan is still too generic.
- **Separate note generation from landing**: draft to a temporary file first; only copy to the final note path after forbidden-pattern scan, LaTeX scan, exact-number spot checks, and collision checks pass. Then update progress. This avoids partially landed notes when a response or shell session is interrupted.
- **Treat limitations carefully**: search `Limit`, `Limitation`, `Future Work`, `Discussion`, and `Impact Statement` in the PDF text. Distinguish `PDF 无独立 Limitations 章节` from `含作者 Future Work / Impact Statement` instead of writing a blanket “无局限”.
- **Evidence must be grep-able**: every major number in §4 should be traceable to `/tmp/cs-paper-reader-<batch>/_evidence/<Method>.md` or the raw/layout PDF text. If a table value was read from a screenshot because `pdftotext` mangled it, say so in a local comment or the evidence file (which lives under `/tmp`, never in the output directory).
- **Line count is not quality**: if a note exceeds the requested range because of blank-line inflation, compress blank lines first; do not delete formulas, table numbers, or paper-specific mechanism explanations.

For implementation snippets and resume discipline, see `references/batch-workflow.md`. For the expanded field-tested failure modes, see `references/anti-template.md`.


## Unattended Closed-Loop Autonomy (2026-05-16, added by Claude)

Mode B must run **fully closed-loop without human intervention** once started, until either all papers are done or one of the legitimate stop conditions in `batch-workflow.md` §3 fires. The following four guardrails handle the boundary conditions that previously broke automation:

### 1. Manifest auto-construction (no manifest required from user)

If the user says only "把这个目录里的论文都读了" or similar, do NOT stop and ask for a manifest. Construct one yourself:

1. Scan the user-supplied PDF directory for `*.pdf` files.
2. For each, parse the filename to extract venue/year/method/title. The canonical pattern is `(Venue Year) MethodName-Paper Title.pdf`; if a file doesn't match, still include it with a best-effort method name and add a `⚠️ 文件名不规范` remark in the progress row.
3. Order: by venue year if extractable, otherwise alphabetic on filename.
4. Write the implicit manifest into `<output>/_progress_<batch>.md` at setup time. (The progress file IS a final-output artifact and stays in `<output>/`; only intermediate evidence/manifests/dumps go to `/tmp/cs-paper-reader-<batch>/` per §"Output Hygiene".)

Only stop if the directory itself doesn't exist or contains zero PDFs.

### 2. Bootstrap reference samples when none exists (avoid the cold-start dead-end)

`batch-workflow.md` §2 Step D's cross-note uniqueness check fails when no approved reference exists. Handle this by **bootstrapping the first two notes**:

1. **#1 and #2 use Mode A standards** — write each with full care, but do not run the cross-note collision check (there's nothing to compare against). Run forbidden-pattern, LaTeX, and per-note quantitative checks normally.
2. After #2 lands, **compare §1.1 and §3.1 of #1 vs #2 directly** using the `compare_sections` logic of `scripts/check_note_quality.py`. If they collide (≥5 identical non-empty lines), rewrite #2 with a sharper per-paper angle before continuing.
3. From #3 onward, use #1 and #2 as the in-batch reference set; pass them via `--refs`. Once 5+ notes exist, switch to `--compare-dir <output-dir>` and stop passing explicit `--refs`.
4. Record in `_progress_<batch>.md` that #1 and #2 are self-bootstrap references; flag them as **recommended for the user to spot-check first** in the final report.

The user's recommended flow is: let codex generate the first two notes under Mode A standards, the user verifies them once, then the rest of the batch proceeds. Even without that verification, the bootstrap rule above keeps the loop closed.

### 3. Paper-type-aware quantitative floors

`scripts/check_note_quality.py --strict` defaults assume a "method-heavy" paper. Before running `--strict` on each note, classify the paper into one of three types based on the abstract and method section:

| Paper type | Indicators | Adjusted floors |
|---|---|---|
| **method-heavy** | introduces a new algorithm with formulas, training objective, or proof | default: `--min-formula-tags 3` across §2-§3, `--min-section4-numbers 2`, `--min-section5-methods 2`, `--min-pdf-anchors 5` |
| **empirical-study** | benchmarks, analysis papers, "study of X" titles, no novel algorithm | `--min-formula-tags 1` across §2-§3, `--min-section4-numbers 5 --min-pdf-anchors 8` (more numbers, fewer formulas) |
| **system / engineering** | inference engines, kernels, infrastructure / framework / dataset-pipeline papers | `--min-formula-tags 1` across §2-§3, `--min-section4-numbers 3 --min-pdf-anchors 6` |

If unclear, default to **method-heavy**. Record the chosen type in the progress row remark column (`type=empirical`, `type=system`, etc.).

### 4. Evidence-only-on-demand (don't keep all PDFs in context)

`batch-workflow.md` §1.5 says "optionally extract evidence for all papers up front". For batches of >10 papers, this can saturate the model's working context if you keep all `/tmp/cs-paper-reader-<batch>/_evidence/<Method>.md` content visible. The discipline:

1. Extract evidence files for **all** papers up front (cheap, parallel-safe), under `/tmp/cs-paper-reader-<batch>/_evidence/`.
2. When writing paper #N, only **read `/tmp/cs-paper-reader-<batch>/_evidence/<Method-N>.md` at that moment**. Do not keep evidence #N-1's content in your in-message working set after the note is written.
3. The on-disk evidence file is the durable source; the in-context evidence is ephemeral.
4. If the user asks for cross-paper comparison after the batch, re-read the specific evidence files needed — don't try to remember all of them at once.

### Net effect

With these four guardrails, Mode B becomes **truly closed-loop**: codex can take a sentence like

> 请把 `/path/to/pdfs/` 下的所有论文逐篇阅读，把笔记放到 `/path/to/notes/<topic>/`。

and run to completion, producing `<output>/_progress_<batch>.md`, `<output>/_collision_warnings.md`, all final notes, and `<output>/_final_report_<batch>.md`, plus intermediate `/tmp/cs-paper-reader-<batch>/_evidence/` and `/tmp/paper-figs/<Method>/` scratch trees, without ever blocking on the user.
