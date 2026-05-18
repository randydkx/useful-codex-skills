# Image-Embedding Recipes — when, where, why, and how to embed a crop

> **Domain note**: every concrete example in this file (SliceGPT, SparseGPT, OWL, FLAP, Wanda, etc.) comes from a single LLM-compression batch. **The recipes themselves — position rule, alt-text discipline, four gates, R1–R8 patterns — are domain-agnostic.** When you read papers in a different subfield (knowledge editing, retrieval, agents, training systems, alignment, etc.), reuse the recipe structure but instantiate it with figures from that subfield. The examples are kept to show what a fully-filled recipe looks like; do not copy the domain vocabulary (`sparse kernel`, `PPL`, `2:4`) into a different subfield's note.

This reference catalogs **8 real placement decisions** plus a unified embedding format. Use it as a pattern library: when drafting a new note, find the recipe whose paper-role matches yours and reuse its placement + explanation pattern.

These recipes encode four things that abstract rules can't:

1. **Where in the note structure** a particular figure type belongs (§1.3 vs §3.x vs §4.5).
2. **Which side of the image** the textual explanation should go (schematic-like → above, results-like → below).
3. **What the explanation should emphasize** (most caption failures are "what" instead of "why").
4. **When to skip a figure** even though `body_refs` is high — and when a Markdown table and a screenshot are redundant duplicates.

---

## 0. Embedding format — caption goes in BODY, not in alt text

**The single most important rule.** Every Markdown viewer renders alt text as a hover tooltip — it is invisible by default. If you put the explanation inside the `![...]()` brackets, readers must hover to see it, which defeats the whole purpose of embedding the image.

**Required format** for every embedded image:

When the explanation comes **before** the crop, it must point downward:

```markdown
<font color="red">**下表解释**</font>：<one-to-three sentences explaining what the
image proves and which detail the reader should look at>.

![Table 1 — <minimal label + one-line topic, ≤ 25 字>](_figs/Method/table_1_p6.png)
```

When the explanation comes **after** the crop, it must point upward:

```markdown
![Figure 3 — <minimal label + one-line topic, ≤ 25 字>](_figs/Method/figure_3_p4.png)

<font color="red">**上图解释**</font>：<one-to-three sentences>.
```

A block saying `上表解释` before the table, or `下图解释` after the figure, is a position-rendering bug.

### Position decision (above vs below)

| Image kind | Default position | Marker phrase | Reason |
|---|---|---|---|
| Schematic / architecture / data-flow diagram | **Above** (prep the reader) | `下图解释` | Reader needs the framing before parsing the visual. |
| Algorithm pseudocode crop | **Above** | `下方算法` or `下方伪代码` | Reader needs to know what they're about to walk through. |
| Unit-cell / single-block diagram | **Above** | `下图解释` | Same as schematic: framing first. |
| Motivation hook (comparison figure) | **Either**, prefer **below** | `上图解释` | Reader already has §1's prose framing; the image is the punchline. |
| Main results table screenshot | **Below** (numbers first) | `上表解释` | Reader should read the numbers themselves before being told what to see. |
| Scaling / trend curve | **Below** | `上图解释` | Same as result table. |
| Ablation / explainer figure | **Below** | `上图解释` | The note's prose has already set up the puzzle; the image resolves it. |
| Throughput / efficiency table | **Below** | `上表解释` | Same as main results table. |

When in doubt, prefer **below** with `上图解释 / 上表解释` — most paper figures are evidence, and evidence reads better after the claim.

**Direction semantics are relative to the image, not to the paragraph topic**:

- red block **above** image/table/algorithm → `下图解释 / 下表解释 / 下方算法`;
- red block **below** image/table/algorithm → `上图解释 / 上表解释 / 上方伪代码`;
- if a renderer or exported Markdown may reorder the block, use a neutral label such as `Figure 3 解释` / `Table 1 解释`, but do not use a contradictory directional label.

### Alt-text discipline

The alt-text inside `![ ]` must be **极简**:

- Pattern: `<Label> — <≤ 25 字 主题>`
- Examples:
  - `Figure 1 — OPT-175B sparsity-vs-PPL 曲线`
  - `Table 3 — 70% sparsity 主结果`
  - `Algorithm 1 — SparseGPT 单层剪枝主循环`
- **Do NOT** put the explanation, the per-paper insight, or the comparison vocabulary in alt text. Those go in the red-font body block.

The alt-text is fallback content for accessibility tools and broken-image renders, **not** the main caption.

---

## 0.5 Quality discipline — two hard gates + two writing guidelines

Before you embed any image, AND once more before saving the note, run through these four. **G1 and G2 are hard gates** (concrete failure modes that need to be prevented). **G3 and G4 are writing guidelines** (they push the note from literal-caption mode toward "图说同时讲方法/动机/贡献" — strive for them, but they are not enforced as pass/fail).

### Gate G1 — Screenshot-only by default; Markdown table requires justification

**Default state**: when the paper provides a table or figure that can be cleanly cropped, embed **only the screenshot**, not a Markdown reproduction. The red-font 上表解释 / 下图解释 block carries the analytical 2-3 numbers that need to be inlined.

**Add a Markdown table only when ONE of these is true**:

- **G1.a — Cross-paper comparison**: the Markdown table merges numbers from this paper's table AND a different paper's table that the note already covers (e.g. "本论文 Table 3 + Wanda Table 1 合并对照"). The screenshot cannot do this because it shows only this paper's table.
- **G1.b — Re-keyed pivot**: the Markdown table has different rows/columns than the screenshot, e.g. transposes the table or re-sorts by a different metric. The screenshot's row/column ordering is the original; your Markdown view is a different angle.
- **G1.c — Subset for reasoning anchor**: you need to quote 2-4 specific cells inline in subsequent prose, and a Markdown table makes those cells `grep`-able. In this case **mark the table explicitly** with a prose line above it: `仅摘 N 行 / N 列作为推理锚点；完整 X 行 × Y 列见下方截图`.

**If NONE of the three justifications apply → delete the Markdown table, keep only the screenshot.** Default to less.

**Failure mode this gate prevents**: the "I抄了整张表然后又贴了截图" pattern (observed in the SparseGPT note in the compression batch), where Markdown and screenshot carry identical information. Reading both teaches the reader nothing new from the second one.

### Gate G2 — Anti-redundancy across alt / red-block / prose / multi-image

Once you have the image + red-block + surrounding prose, audit the **four redundancy axes**:

1. **alt text ↔ red-block**: alt is `<Label> — <≤25字 topic>` only. The red-block must NOT restate the topic — it must start from the explanation. ❌ Bad: alt=`Table 1 — 主结果`, red-block 开头="主结果表显示..."; ✅ Good: red-block 开头 = "三个值得读者从完整截图里确认的发现——".
2. **red-block ↔ prose immediately above/below the image**: the prose introduces the claim; the red-block points at evidence in the image. If the prose already lists three numbers and the red-block lists the same three numbers, **delete one set**. Prefer keeping numbers in the red-block (anchored to the image) and making the prose more abstract.
3. **multi-image redundancy within a section**: if §4 has two screenshots that carry the same load-bearing claim (e.g. both saying "method beats baseline under setting X"), they compete for the same role. Pick the one with higher `body_refs` or stronger visual hook; demote the other to a one-line mention or skip it.
4. **cross-section data repeat**: §4 numbers should NOT be re-quoted verbatim in §6 (核心贡献) or §7 (讨论). §6 should say "the §4.2 main result demonstrates contribution C2", not re-quote the numbers. The image lives in §4; later sections reference it by section number.

### Guideline G3 — Push the explanation from "what" to "why" (closed-loop preference)

This is the **single biggest lever** for raising note quality, but it is a **写作准则**, not a hard gate. The aim:

- 图说不仅要解释字面看到了什么，还要尽可能把它**和方法/动机/贡献串起来**——读图的同时加深对算法或动机的理解。
- 同时，**图说必须和当前 crop 的真实对象一致**：先核对 `manifest.json` 中的 label/caption、PNG 文件名、alt text、以及图片中可见的标题/表头/图形内容，再解释它。不要把另一个 Figure/Table/Algorithm 的结论套到当前图片上；如果 manifest、文件名、可见内容和图说之间有不一致，先回到 PDF 或重新裁剪，而不是强行解释。

Concretely, when you write the red-block, after stating the literal observation, ask yourself: **"can I add one more clause that links this image back to §1.3 / §3.x / §6 / §7?"** If yes, add it. If no (the image is genuinely just context, e.g. a dataset histogram), it's fine to stay literal — don't fabricate a connection.

Useful back-reference patterns (use any that fit naturally; don't force):

- **Method anchor**: `这张图是 §3.x 中 <机制名> 的直接证据` / `这解释了 §3.x 末为什么 <设计选择>`
- **§1.3 insight echo**: `这是 §1.3 insight "<≤25字>" 在 <实验/消融> 维度上的二次确认`
- **§7 limitation echo**: `这也是 §7 中 <作者承认的边界> 的视觉证据`
- **§6 contribution echo**: `这支撑了 §6 贡献第 N 条 "<贡献短语>"`

**Two-tier rubric** (use it to self-grade each red-block):

| Tier | Red-block content | When acceptable |
|---|---|---|
| **A — Deep** | 字面观察 + 一条 §-reference 把它接回方法/动机/贡献 | Default target. Strive for this on every load-bearing image. |
| **B — Literal-only** | 仅字面观察（"这张表显示 X% sparsity 下 A 比 B 高 0.3 PPL"） | OK for genuinely contextual figures (datasets, hardware specs, paper roadmap diagrams). |

**Failure case to avoid**: a note where **every** red-block is Tier B. That means the agent stayed at "what the image shows" and never asked "why the author put it here". Aim for the majority to be Tier A; allow a minority of Tier B for genuinely contextual images.

**Optional self-check grep** (informational, not blocking):
```bash
# Surface images whose ±5-line neighborhood has no § reference.
# These are CANDIDATES to deepen — review case by case, don't auto-delete.
awk '/!\[/{img_ln=NR; img_seen=1; loop=0}
     img_seen && NR > img_ln-6 && NR < img_ln+6 && /§[0-9]/{loop=1}
     img_seen && NR == img_ln+5 {if(!loop) print "LITERAL_ONLY candidate near line " img_ln; img_seen=0}' <note.md>
```
Treat hits as "can I deepen this one?" prompts, not as errors.

### Guideline G4 — Contribution alignment (soft)

Before finalizing, do a quick mental pass: **does each image have a story for why it's in the note?** Most should map to a §6 contribution bullet ("Figure 1 → C1 motivation", "Algorithm 1 → C2 method", "Table 1 → C3 main result"). When the mapping is direct, mention it in the red-block (Tier A from G3).

When an image is genuinely auxiliary (dataset stats, related-work positioning, a calibration detail), that's fine — but if you notice **most** of the embedded images don't map to any §6 bullet, that's a signal to either:

- (a) trim a few images that don't carry their weight, or
- (b) revisit §6 — perhaps the contributions are under-stated and the figures are surfacing things you didn't yet list as contributions.

**Not enforced as a count**. Use judgment.

### Putting it together — two hard gates, two writing guidelines

For each candidate image, the decision flow is:

```
Candidate image from manifest.json (sorted by body_refs desc)
│
├── G1 (HARD) — Will I add a Markdown table alongside?
│       ├── Justified by G1.a/b/c? → keep both (mark Markdown as subset/pivot/cross-paper)
│       └── Not justified?         → screenshot only
│
├── G2 (HARD) — Run redundancy audit (4 axes):
│       alt vs red-block, red-block vs prose, multi-image, cross-section
│       Any axis fails? → fix or remove
│
├── G3 (SOFT) — When writing the red-block, try to push from "what" to "why":
│       Add one § back-reference (Tier A) if a natural one exists.
│       If the image is genuinely contextual, Tier B (literal-only) is acceptable.
│       Aim for majority Tier A across the note.
│
└── G4 (SOFT) — Does this image have a story tied to a §6 bullet?
        If yes → mention it in the red-block (this also satisfies G3).
        If genuinely auxiliary → keep but don't over-explain.
        If MOST images lack §6 mapping → revisit §6 or trim images.
```

**G1 and G2 are hard** — they protect against concrete redundancy/duplication failures that erode reader trust.

**G3 and G4 are soft writing guidelines** — they push the note from "image slideshow" toward "图说同时讲方法/动机/贡献"，but they should not become bureaucratic checklists. Use judgment.

---

## R1. Motivation visual hook → §1.3 关键 Insight

**Paper-role**: a single figure in §1 or §2 that visually states the paper's core problem-vs-solution. Often appears in the abstract preview or §1's last paragraph.

**Signal**: caption starts with comparison vocabulary ("comparison of", "overview of", "vs"); the figure is referenced ≥2 times including in §1 itself.

**Where**: end of §1.3 (right after the Insight sentence), image **below** with `上图解释`.

**Example** (SliceGPT Figure 1, `body_refs=2`):

```markdown
### 1.3 关键 Insight: <font color="blue">"..."</font>

[1-paragraph mechanism description]

> **直觉对照**: ...

![Figure 1 — 四种稀疏方式下 $XW$ 的对比](_figs/SliceGPT/figure_1_p2.png)

<font color="red">**上图解释**</font>：最右栏 SliceGPT 把 $X$ 的列与 $W$ 的行同步删去，产物仍是 dense 小矩阵；其他三种方案都保留矩阵形状，因此都需要稀疏 kernel 才能加速。这张图把 §1.3 insight "换基底后整列扔掉" 与现有"打洞式稀疏" 的差异在视觉上一刀切开。
```

**Explanation pattern**: `<视觉差异的一句话>；<本论文方案>的关键特征：<这个特征是 §1.3 insight 的直接视觉证据>。`

**Anti-pattern**: don't put motivation figures in §3 — by §3 the reader has already accepted the framing; the image will feel like recap.

---

## R2. Method schematic → §3.x first paragraph

**Paper-role**: an architecture / data-flow diagram that shows how the pieces fit together. Usually `Figure 2` or `Figure 3` in the typical CS paper layout (after the motivation hook, before the experiments).

**Signal**: caption contains "architecture", "framework", "overview", "pipeline"; `body_refs ≥ 3`.

**Where**: at the end of §3.2 or §3.4. Image **above** the explanation with `下图解释`, because the reader needs framing before parsing the visual.

**Example** (SliceGPT Figure 3, `body_refs=3`):

```markdown
### 3.2 Stage 1: LayerNorm → RMSNorm 等价改写

[Prose introducing 均值消去 M, 缩放 diag(α), 吸收策略]

这一步**严格不改变输出**...

<font color="red">**下图解释**</font>：$M$ 吸收进下游、$\text{diag}(\alpha)$ 吸收进上游后，块内只剩 RMSNorm；这恰好满足 Eq. (2) 中正交不变性的前置条件——所以 Stage 2 才能在每个 RMSNorm 前后插入 $Q_\ell$ 与 $Q_\ell^\top$ 而不改变输出。

![Figure 3 — LayerNorm→RMSNorm 改写示意](_figs/SliceGPT/figure_3_p6.png)
```

**Explanation pattern**: `<这张图展示的操作名>。<操作的关键步骤：什么吸收进什么>，结果是<§3.x 想达成的状态>。`

The explanation restates the **invariant the figure proves**, not the figure's components.

---

## R3. Single-layer / unit-cell diagram → §3.x mid-section

**Paper-role**: a diagram showing one repeated unit (one transformer block, one routing layer, one expert) plus the adapters/connections around it.

**Signal**: caption mentions "single layer", "one block", "a layer of"; `body_refs ≥ 3`.

**Where**: in the §3 subsection that introduces the cross-block / cross-unit modification. Image **above** the red-font explanation with `下图解释`.

**Example** (SliceGPT Figure 2, `body_refs=4`):

```markdown
### 3.4 Stage 3: 跨块 $Q_\ell \ne Q_{\ell-1}$ 的修补

[Prose on 块内吸收 + 残差路径插入新线性层]

唯一的"运行时新增开销"是残差里那个 $D \times D$ 的 $Q_{\ell-1}^\top Q_\ell$（不能预先吸收）。

<font color="red">**下图解释**</font>：注意残差路径上那个新增的 $Q_{\ell-1}^\top Q_\ell$ 适配层——这是 SliceGPT 唯一不可消除的运行时开销。块内的 $Q_\ell^\top, Q_\ell$ 可以被吸收进相邻线性层，但跨块基底不一致时只能在残差里补一次旋转。

![Figure 2 — 单层 Transformer 结构示意](_figs/SliceGPT/figure_2_p4.png)
```

**Explanation pattern**: `<单元名> 结构示意。注意 <反直觉的细节>——<这个细节为什么是本论文最重要的工程取舍>。`

Emphasis: point the reader at the **one detail in the figure that costs / saves the most**. Not a description of all the boxes.

---

## R4. Algorithm pseudocode → §3.x end (or its own subsection)

**Paper-role**: a numbered `Algorithm N` box. Critical for reproducibility, often referenced 2-5 times.

**Signal**: anything with "Algorithm" in the caption.

**Where**: either (a) at the end of §3 as a complete-procedure summary, or (b) inside the §3.x subsection that describes the algorithm's main loop. Use (a) when the algorithm has multiple stages already covered in subsections; use (b) when it's a single tight loop. Image **above** the explanation with `下方算法`.

**Two ways to embed**:

- **As a crop** (preferred when the paper's typography uses non-Markdown symbols like ⊙, ⟵, ⊤):
  ```markdown
  <font color="red">**下方算法**</font>：第 6–9 行的 Hessian 更新只依赖右下子矩阵，这是 $O(d_\text{col}^3) \to O(d_\text{col})$ 复杂度优化的来源；第 4 行的 mask reselect 每 $B_s=128$ 列做一次，让 OBS update 的副作用能被后续 mask 看到。

  ![Algorithm 1 — SparseGPT 单层剪枝主循环](_figs/SparseGPT/algorithm_1_p5.png)
  ```

- **As a Markdown code block** (preferred when the algorithm uses ASCII-friendly symbols):
  ```markdown
  ```text
  Input: ...
  for ℓ = 1 .. L:
      ...
  ```

  <font color="red">**上方伪代码解释**</font>：...
  ```

If unsure, prefer the crop — `clip.py clip algorithm --label "Algorithm N" --page <p>` produces a clean rule-bounded image.

**Explanation pattern**: `<一句话过程概述>：<指出读者应该重点看的那 2-3 行 / 那个公式>。`

---

## R5. Main results table → §4.2

**Paper-role**: the single "headline" table that the abstract teases — usually `Table 1` in CS papers.

**Signal**: caption contains "main results", "perplexity results", or the headline metric; `body_refs ≥ 3`.

**Where**: §4.2 (主结果). Image **below** with `上表解释`. **Default: screenshot only.** If you also include a Markdown table, it must pass Gate G1 above — i.e., serve as a cross-paper merge, a re-keyed pivot, or an explicitly-labeled subset-for-reasoning. Plain duplication of the screenshot's rows is forbidden (Case B / G1 violation).

**Example** (SliceGPT Table 1, `body_refs=3`):

```markdown
### 4.2 主结果：WikiText-2 perplexity（论文 Table 1）

| 模型 | Dense | SparseGPT 2:4 | SliceGPT 25% | SliceGPT 30% |
|---|---:|---:|---:|---:|
| OPT-66B | 9.33 | 10.22 | **9.68** | 9.85 |
| Llama-2-70B | 3.32 | 4.98 | **4.60** | 5.05 |

（仅摘 2 行展示趋势；完整 8 行 4 列见下表截图。）

![Table 1 — 完整 WikiText-2 PPL 结果](_figs/SliceGPT/table_1_p8.png)

<font color="red">**上表解释**</font>：OPT 系列在 25% 切片下全面优于 SparseGPT 2:4，Llama-2 大模型同样；上方 Markdown 表只摘了两行作为趋势锚点，完整 8 行 4 列结果在截图里——值得读者注意的是 30% 切片在 Llama-2-70B 上 PPL 反超 SparseGPT 2:4（5.05 vs 4.98），是切片率上界的早期信号。
```

**Explanation pattern**: `<完整结果范围>。<从全表中能看到但 4-6 行抽样看不到的二阶趋势>。`

---

## R6. Scaling / trend curve → §4.3 zero-shot 或 §4 后段

**Paper-role**: a line chart showing how some metric varies with a control parameter (sparsity, model size, compute).

**Signal**: caption contains "vs", "across", "as a function of"; the X axis is the control parameter.

**Where**: in the §4 subsection that discusses the trend's meaning. Image **below** with `上图解释`. Pair with **one explicit number from the curve** (the inflection point or chosen operating point).

**Example** (SliceGPT Figure 5, `body_refs=2`):

```markdown
### 4.3 Zero-shot 任务 + RFT

5 任务平均（PIQA / WinoGrande / HellaSwag / ARC-e / ARC-c）：
- **Llama-2-70B 25% 切片 + Alpaca RFT**：99% dense 性能保留；
- ...

![Figure 5 — 切片率 vs zero-shot 平均准确率](_figs/SliceGPT/figure_5_p9.png)

<font color="red">**上图解释**</font>：25% 切片是精度-效率的甜点——曲线在此前几乎平直，30% 后所有规模都开始陡降；大模型（70B）曲线最平缓，小模型（125M）最陡，这是 §4.2 中 "大模型更可切" 在 zero-shot 维度上的二次确认。
```

**Explanation pattern**: `<inflection 点> 是 <trade-off 名称> 的甜点，<阈值后的退化方向>；<不同分组的曲线斜率差异>。`

Emphasis: name the **inflection** and the **slope differences** — these are what the reader will remember in 6 months.

---

## R7. Ablation / explanatory figure → §4.5 关键消融

**Paper-role**: a figure that **explains why** the main result varies across a factor — often a frequency / distribution / spectrum plot. Usually low `body_refs` (1-2) because it's referenced once but matters a lot.

**Signal**: the figure is in an Appendix or the very last §4 subsection; the caption mentions "spectrum", "distribution", "histogram", or "frequency".

**Where**: §4.5 (关键消融). Image **below** the prose with `上图解释`.

**Example** (SliceGPT Figure 8, `body_refs=1` but **critical**):

```markdown
### 4.5 关键消融

**(a) 逐层非均匀切片**：
按每层 PCA 频谱衰减自适应切片，OPT 系列 PPL 改善 0.12–0.28；**但 Llama-2 系列反而退化 0.17–0.79**。论文坦承这与频谱分析一致——Llama-2 没有显著主导主成分。

![Figure 8 — OPT vs Llama-2 各层 MLP 输入归一化频谱（log scale）](_figs/SliceGPT/figure_8_p16.png)

<font color="red">**上图解释**</font>：OPT 的频谱衰减陡峭——前几个主成分占主导，切尾部损失小；Llama-2 的频谱接近水平，无明显主导方向，因此切片代价更高。这一张图直接解释了 §4.2 主表中 OPT 系列比 Llama-2 系列 "更可切" 的反直觉差异，也是 (a) 中 Llama-2 非均匀切片反而退化的根本原因。
```

**Explanation pattern**: `<分组 A 的特征>，<推论 A>；<分组 B 的特征>，<推论 B>。这解释了 §4.x 中 <反直觉现象> 的现象。`

**Key insight**: low `body_refs` figures can be the most valuable — they're often the **causal explanation** for a headline number. Don't auto-skip them just because the count is low.

---

## R8. Throughput / efficiency table → §4.4

**Paper-role**: end-to-end speedup numbers — the "this method actually works in production" evidence.

**Signal**: caption mentions "inference time", "throughput", "latency", "GPU"; `body_refs ≥ 2`.

**Where**: §4.4 推理吞吐与延迟. Image **below** with `上表解释`. **Default: screenshot only.** Quote the dense baseline number(s) inline in the surrounding prose (not in a parallel Markdown table) so the reader can compute the speedup ratio without re-reading the screenshot — this satisfies G1.c (reasoning anchor) without triggering G1's duplication rule.

**Example** (SliceGPT Table 2, `body_refs=2`):

```markdown
### 4.4 推理吞吐与延迟

H100 上 25% 切片可达 **1.55× 吞吐**；A100-40GB 上 Llama-2-70B 的 dense latency 是 125 ms / 4 GPU，25% 切片后是 110 ms / 3 GPU——延迟降 12%，GPU 数量降 25%。50% 切片大模型只需 1 GPU（从 2 GPU），等效吞吐 **6.26× 与 3.75×**。

![Table 2 — DeepSparse 上 OPT-66B / Llama-2-70B 推理延迟与 GPU 数量](_figs/SliceGPT/table_2_p10.png)

<font color="red">**上表解释**</font>：SliceGPT 25% 切片让 70B 模型从 4 GPU 降到 3 GPU 同时延迟降 12%——这是 unstructured/2:4 稀疏做不到的真实端到端加速，因为它们仍需稀疏 kernel；SliceGPT 切完是更窄的 dense 矩阵，standard GEMM kernel 直接受益。
```

**Explanation pattern**: `<本方法在某配置下的关键数字>——<对比 baseline 不能达成的相同维度的事实>。`

Emphasis: state what the baseline **fails** to do at the same metric — this is the table's load-bearing claim.

---

## Redundancy rule — Markdown table vs screenshot must be COMPLEMENTARY, not duplicate

This section is the longer reference for **Gate G1** in §0.5. G1 states the default ("screenshot only") and the three allowed justifications for adding a Markdown table; the three cases below are those justifications restated with examples and a detection grep. If G1 already gave you a clear answer, you don't need to read this section.

### Case A — Markdown table is a strict subset, screenshot is the complete original
Acceptable. Use this when the original has 8+ rows / 5+ columns and you want to quote 2–4 rows in Markdown for inline reasoning, but want readers to see the full table for confirmation.

Required signal: the prose explicitly says "仅摘 N 行展示趋势；完整结果见下表截图" (or equivalent). Without this signal, the reader doesn't know the Markdown is a partial extract.

### Case B — Markdown extract == screenshot content (FORBIDDEN)
If your Markdown table reproduces every row and column of the screenshot, **delete one of them**. Default: delete the Markdown, keep the screenshot, and put the analytical 2–3 numbers in the red-font explanation block. Reason: the screenshot already shows the exact original layout and decimal alignment; the Markdown duplicate only inflates note length without adding information.

Detection grep (before saving the note):
```bash
# For each screenshot of a table, check if a Markdown table within ±15 lines has
# the same row count and similar column count.
awk '/!\[Table/{img_line=NR} /^\|.*\|/ && img_line && NR-img_line < 15 {print "POTENTIAL DUP at line " NR " near image line " img_line}' <note.md>
```

### Case C — Markdown table covers different columns/rows than screenshot (BEST)
Acceptable and recommended for §4 main results. Use Markdown to show the **comparison with the most relevant 2 baselines**; use the screenshot to show **all 6+ baselines and additional columns** (e.g. memory, FLOPs, multiple datasets). This way Markdown is the load-bearing evidence for quotes; screenshot is for "is this consistent across the rest of the table" verification.

**Rule of thumb**: if you can read both the Markdown table and the screenshot and learn nothing new from the second one, you have Case B — delete it.

---

## When NOT to embed (3 negative cases)

### N1. Equations that render fine in Markdown
If the equation is `$L = \sum_i (y_i - \hat y_i)^2$`, do not crop it. Crop only when:
- The equation has matrix operators that Markdown math can't typeset (`\mathbf{R}^{N \times D \times K}` with annotations).
- The equation has multi-level subscripts / hats / tildes that visually align in the PDF but break in Markdown.
- The equation is part of a derivation chain (3+ lines) where the PDF's vertical alignment carries meaning.

### N2. Tables with ≤ 3 columns and ≤ 5 rows
These should be Markdown tables, not crops. Crops are for tables where:
- Header has 2+ row levels.
- There are grouped rows (separator lines between groups).
- The original numbers have decimal alignment that matters.

### N3. Architecture diagrams of standard components
Do not crop a Transformer block diagram from a paper just because the paper has one. Crop only when the diagram shows **what this paper modifies** (e.g. SliceGPT's `Q_{ℓ-1}^⊤ Q_ℓ` adapter on the residual path). A generic block diagram is decorative.

---

## Decision tree (use when in doubt)

```
Got a figure / table candidate from manifest.json?
├── body_refs ≥ 3?
│   ├── Yes → likely worth embedding. Pick recipe + position:
│   │   ├── "overview/architecture/framework"   → R2 schematic     → §3.x, image ABOVE
│   │   ├── "single layer/one block"            → R3 unit cell     → §3.x mid, image ABOVE
│   │   ├── label is "Algorithm N"              → R4 algorithm     → §3.x end, image ABOVE
│   │   ├── "main results / headline metric"     → R5 main table    → §4.2, image BELOW
│   │   ├── "throughput/latency/inference"        → R8 throughput    → §4.4, image BELOW
│   │   ├── X-axis is control parameter           → R6 trend curve   → §4.3+, image BELOW
│   │   └── "comparison of / overview of / vs"    → R1 motivation    → §1.3, image BELOW
│   └── No (body_refs ≤ 2) → consider these:
│       ├── In Appendix and explains a §4.2 finding?  → R7 ablation → §4.5, BELOW
│       ├── Spectrum / histogram / distribution plot? → R7 ablation → §4.5, BELOW
│       ├── Cited only in passing?                    → SKIP
│       └── Cited in abstract or §1?                  → R1 motivation → §1.3, BELOW
└── No candidates with body_refs ≥ 2 at all?
    └── Figure-light paper. Embed 0-1 crops max.
```

After picking a recipe, verify:
1. Alt text is ≤ 25 字 and contains only `<Label> — <topic>`. No "why" sentence inside `[ ]`.
2. A red-font `上图解释 / 下图解释 / 上表解释 / 下表解释 / 下方算法` block sits on the opposite side of the image.
3. If a Markdown table is also present, run the redundancy grep (Case A/B/C above).

---

## How to use this file

1. After running `clip.py scan`, sort `manifest.json` entries by `body_refs` desc.
2. For each top-K entry (K = ceil(note_length / 80)), find the matching recipe above.
3. Place the image at the recipe's specified `§<section>` location AND with the recipe's position (above/below).
4. Write a red-font `<上下><图表>解释：...` block on the opposite side of the image. **Keep alt text minimal** — `<Label> — <≤25字 topic>` only.
5. If you also include a Markdown table near the screenshot, ensure it's Case A or Case C from the Redundancy rule, never Case B.
6. Total image count should land in 4-8 for a 300-line note (≈ 1 per 50-80 lines).
