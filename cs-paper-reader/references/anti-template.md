# Anti-Template Patterns

The single biggest failure mode of this skill is producing a "fill-in-the-blank" template note that could plausibly belong to any paper in the same subfield. This reference catalogs the **pattern categories** observed in real failures, abstractly stated so they apply across subfields. Concrete grep strings for **LLM-compression** notes are collected in Appendix I as one worked example — when you start a different subfield (knowledge editing, retrieval, agents, training systems, etc.), accumulate an analogous appendix for that subfield.

Run the greps below before declaring any note done. They are framed as "if you grep this pattern and it matches, you have a problem."

---

## A. Generic placeholder sentences

**Symptom**: opening lines of §1 or §1.1 that could be written without opening the PDF. They restate the field's standard motivation rather than the paper's specific bottleneck.

**Abstract test**: if you can copy-paste the sentence into a different paper's note in the same subfield without modification, it's a placeholder.

**Generic anti-pattern shapes**:

| Shape | Why bad | Fix |
|---|---|---|
| "<X> 部署/训练/推理 很贵" / "面临 ... 瓶颈" | Applies to every paper in the subfield | Specific number from the PDF (e.g. memory footprint, latency, dataset size) |
| "随着 ... 规模/参数量 增长" | Generic scaling-law preamble | Skip it; go straight to this paper's actual problem |
| "<metric> 改善不一定代表 ... 真正提升" | True-but-contentless caveat | Cite a specific evaluation gap in the PDF or drop the line |
| "<A>、<B>、<C>" triplet-of-burdens cliché | Equal-weight list of generic concerns | Pick the one the paper actually optimizes |

When you find one of these, ask: **what number, table, or specific prior method would replace this sentence?** If you can't answer, you haven't read the paper deeply enough yet.

---

## B. Universal-skeleton formulas

**Symptom**: §3.1 has formulas that could be the §3.1 of any paper in the subfield. The writer used an abstract operator instead of extracting the paper's actual symbols.

**Abstract test**: every formula in §3 must use **at least one symbol that appears in the PDF**. Generic letters (θ, x, M, L) are fine if they correspond to the paper's own usage; replacing the paper's `W_ℓ X_ℓ` with generic `θ x` is not.

**Generic anti-pattern shapes**:

- Using `f_θ` (or any single-symbol model abstraction) as the entire §3 description.
- Stating the subfield's generic objective (e.g. "minimize reconstruction loss", "minimize KL", "match teacher logits") as the *only* method formula. This is fine as §2 background; insufficient as §3.
- Introducing an English-named "score" or "method" placeholder (`EvidenceSpecificScore`, `ImportanceMetric`) — see §C.

**Fix**: extract the paper's actual Eq. (N) with their `Eq. N` label. If the paper has 3+ numbered equations, **at least 2 of them must appear in §3** of your note with their original numbering.

---

## C. Variable-name-style placeholders (leaked drafting scaffold)

**Symptom**: CamelCase or `snake_case_placeholder` tokens that look like slots in a template, not real paper notation.

**Abstract test**: if a token in the note doesn't appear anywhere in the PDF and is not a product name (model, dataset, baseline), it's a scaffold leak.

Common leak forms:

- `EvidenceSpecificScore`, `ScorePlaceholder`, `MethodSpecificMetric`, `Compress_method`, `<task>_method`
- Any CamelCase word ending in `Score`, `Metric`, `Method`, `Operator`, `Function`, `Module` that you can't find in the PDF.

Detection grep:

```bash
grep -nE '[A-Z][a-z]+[A-Z][a-z]+|_method\b|_score\b|Placeholder' <file>
```

Inspect every match — most legitimate matches will be product names (model families, dataset names, prior-method acronyms). Anything that looks like an English-named slot is wrong.

---

## D. Meta-description instead of content

**Symptom**: §4 / §5 sentences that say what the reader *should* look at, instead of stating what the result *is*.

**Abstract test**: every sentence in §4 should contain at least one of {a number, a method name, a table/figure reference}. If a sentence has none of those three, rewrite it or delete it.

Generic anti-pattern shapes:

| Bad | Better |
|---|---|
| 应重点检查 <X> 消融是否说明 ... | Table N ablation 显示：去掉 X 后 <metric> 从 a.bc 升到 d.ef |
| <metric> 改善是否保留 <capability>？ | <capability> 平均 62.97 vs <baseline> 63.32 |
| 是否做高 <factor> 实验？ | <factor>=70% 下 <metric>=24.55，比 <prior>=85.77 低 61.22 |
| 这个方法可能在 <case> 上失效 | Appendix C 报告：<setting> 上 <method> 反而比 <baseline> 差 (a vs b) |

---

## E. Quantification-free comparison

**Symptom**: §5 ("与相关工作的区别") uses qualitative comparison language without any number or mechanism difference.

**Abstract test**: every comparison sentence must end in one of:

- A specific number difference (e.g. "<model> <metric>: <A>=4.60, <B>=4.98").
- A specific mechanism difference (e.g. "<A> 删元素后保留矩阵形状；<B> 旋转后切行列得到更窄 dense 矩阵").
- A specific capability difference (e.g. "<A> 不需要 weight update；<B> 需要 <update mechanism>").

Banned shapes (each is a placeholder for "I didn't actually compare"):

- "更适合 <task>"
- "在某些 benchmark 上优于 baseline"
- "保留更多能力"
- "在 <subfield> 中表现良好"

---

## F. LaTeX residues (silent renderer killers)

**Symptom**: math formulas with backslashes eaten by JSON / shell escape rules.

| Residue | Should be | How it happens |
|---|---|---|
| `rac{` | `\frac{` | The leading `\f` gets stripped by JSON escape (`\f` = form feed) |
| `um_` (not followed by a real word) | `\sum_` | Same with `\s` |
| `qrt{` | `\sqrt{` | Same |
| `lpha`, `eta`, `ambda`, `abla` | `\alpha`, `\beta`, `\lambda`, `\nabla` | Same |
| `\\sum`, `\\frac` (double-backslash in Markdown math) | `\sum`, `\frac` | Over-escaping — Markdown eats one `\`, leaving a literal `\sum` |

Detection grep:

```bash
grep -nE '[^\\](rac\{|um_|qrt\{|lpha|eta\s|ambda|abla)|\\\\(sum|frac|sqrt|alpha|beta|lambda)' <file>
```

Fix each match. Rerun until empty.

---

## G. Scaffold leakage

**Symptom**: late-stage drafts still contain planning markers.

Banned markers:

- `### TODO:` or `<!-- TODO -->`
- `待填入`、`见后续`、`此处补充`、`[此处插入 ...]`
- Empty placeholder sections (`### 3.4` with no body)
- Literal phrases like `按 _rewrite_style_spec.md` or `按 cs-paper-reader 骨架`

Detection grep:

```bash
grep -nE 'TODO|待填入|见后续|此处补充|按.*骨架' <file>
```

Empty-section detection:

```bash
awk '/^### /{if(prev_header && !content) print "EMPTY: " prev_header; prev_header=$0; content=0; next} /\S/{content=1}' <file>
```

---

## H. Cross-paper contamination

**Symptom**: two notes in the same batch share ≥ 5 non-empty lines of prose in their §1.1 or §3.1.

Common culprits across all subfields:

- The §3.1 "总览" paragraph
- The §1.2 "现有方法的局限" bullet list
- The §2.x "符号表" header lines
- The §7 "discussion" generic boilerplate

Pairwise check:

```bash
for old in "$dir"/*.md; do
  [ "$old" = "$current" ] && continue
  overlap=$(diff <(sed -n '/^### 1\.1/,/^###/p' "$current") \
                 <(sed -n '/^### 1\.1/,/^###/p' "$old") \
              | grep -c '^[<>] ')
  [ "$overlap" -ge 5 ] && echo "COLLISION $(basename "$old") (${overlap} lines)"
done
```

---

## Master grep template

Every subfield should maintain its own master grep — concatenate (a) the LaTeX residue regex (universal), (b) the scaffold-leak regex (universal), and (c) the subfield-specific placeholders / formulas / phrases.

**Universal portion (works on any subfield)**:

```bash
grep -nE \
  'EvidenceSpecificScore|ScorePlaceholder|_method\b|TODO|待填入|见后续|此处补充|[^\\](rac\{|um_|qrt\{|lpha|eta\s|ambda|abla)|\\\\(sum|frac|sqrt|alpha|beta|lambda)' \
  "<file>"
```

The subfield-specific portion goes in an appendix below (see Appendix I for LLM-compression). When using the automated `check_note_quality.py`, point at the corresponding `subfield-patterns/<name>.txt` via `--subfield <name>`.

If both greps return empty AND the per-paper angle (batch-workflow §2 Step B) is visible in §1.3, the note is shippable.

---

## I. Appendix — LLM-compression subfield placeholders (worked example)

The patterns below were collected during a large LLM-compression / pruning batch. **They are an illustration of how to specialize the categories above for one subfield**; they should NOT be applied verbatim when reading papers in other subfields. When you start a new subfield, build an analogous appendix for it.

### I.1 Subfield-specific generic placeholder sentences (instantiates §A)

| Pattern (regex) | Why bad | What to write instead |
|---|---|---|
| `LLM 部署很贵` / `部署面临.*瓶颈` | Generic to every compression paper | The specific deployment number (e.g. "GPT-175B 在 FP16 下至少需要约 320GB 存储，推理至少需要 5 张 80GB A100") |
| `随参数量.*增长` | Generic scaling preamble | Skip; go to actual problem |
| `小模型从头训练需要大量 token` | Filler intro | Cut |
| `PPL 改善不一定代表.*能力保留` | True but contentless | Either cite a specific zero-shot gap or drop |
| `参数量、计算量、显存` | Triplet-of-burdens cliché | Pick the one the paper actually optimizes |

Grep:
```bash
grep -nE 'LLM 部署很贵|参数量.*增长|小模型从头训练|PPL 改善不一定|参数量、计算量、显存' <file>
```

### I.2 Subfield-specific universal-skeleton formulas (instantiates §B)

| Pattern | Fix |
|---|---|
| `f_θ` / `f_{θ_T}` as the entire model abstraction | Use the paper's own model symbol (e.g. `W_l`, `θ_{l,ℓ}`, `M`) |
| `\min E[d(f, f')]` | Use the actual reconstruction objective with the paper's symbols (e.g. SparseGPT's Eq. 1) |
| `\theta' = C(\theta; D_c, B)` | Describe the paper's actual algorithm, not the abstract operator |
| `min_{M_ℓ, Ŵ_ℓ} ‖W_ℓ X_ℓ - (M_ℓ ⊙ Ŵ_ℓ) X_ℓ‖²` as the *only* method formula | Add the paper's specific score / update / allocation formula |
| `重要性分数 s_g` for some `g ∈ G` | Use the paper's actual score (e.g. Wanda's `|W_ij| · ‖X_j‖_2`, SparseGPT's OBS update) |

Grep:
```bash
grep -nE 'f_θ|f_\{θ|f_\{theta|min E\[d\(f|min_\{M.*Ŵ|重要性分数 s_g|剪枝单元 G' <file>
```

### I.3 Subfield-specific meta-description fixes (instantiates §D)

| Bad | Better |
|---|---|
| 应重点检查 ablation 是否说明 X | Table 4 ablation 显示：去掉 X 后 PPL 从 7.12 升到 9.84 |
| PPL 改善是否保留 zero-shot 能力？ | Zero-shot 平均 62.97 vs Dense 63.32 |
| 是否做高压缩率实验？ | 70% sparsity 下 PPL = 24.55，比 Wanda 的 85.77 低 61.22 |
| 这个方法可能在 X 上失效 | Appendix C 报告：OPT-6.7B 上 OWL w. SparseGPT 反而比 SparseGPT 差 (22.48 vs 20.29) |
| 应该看真实推理速度 | A100-40GB 上 SliceGPT 25% 把 4 GPU 降到 3 GPU |

### I.4 Subfield-specific banned comparison phrases (instantiates §E)

Banned:
- "更适合 LLM"
- "在某些 benchmark 上优于 baseline"
- "保留更多能力"
- "在结构剪枝中表现良好"

Replace with one of:
- A specific number difference: "Llama-2-70B PPL: SliceGPT 25% = 4.60, SparseGPT 2:4 = 4.98"
- A specific mechanism difference: "SparseGPT 删元素后保留矩阵形状；SliceGPT 旋转后切行列得到更窄 dense 矩阵"
- A specific capability difference: "Wanda 不需要 weight update；SparseGPT 需要 OBS 更新"

### I.5 Subfield-specific master grep (combine with universal master grep)

```bash
grep -nE \
  'LLM 部署很贵|参数量、计算量、显存|f_θ|min E\[d\(f|统一目标函数|重要性分数 s_g|剪枝单元 G|更适合 LLM|应重点检查|应该查|应该看' \
  "<file>"
```

### I.6 Subfield-specific failure modes (additive to §A-§H)

These were observed while rewriting pruning / sparsification notes.

**I.6.a False "no limitations" claim**:

Bad pattern: `PDF 无 Limitations 章节`. Acceptable only after searching `Limit / Future Work / Discussion / Impact Statement / constraint / failure / drawback`:

```bash
grep -niE 'limit|future work|discussion|impact statement|constraint|failure|drawback' <raw-or-layout-text>
```

Write the precise remark: `含作者 Limitations` / `PDF 无独立 Limitations 章节；含 Future Work` / `PDF 无独立 Limitations 章节；含 Impact Statement`.

(This rule itself is not subfield-specific; it's a universal reminder, just collected here because the same omission pattern recurred in the compression batch.)

**I.6.b Formula transcription from broken PDF text**:

Red flags: doubled or missing norm bars (`||W| × |W||`), missing square roots, separated superscripts/subscripts over lines, table values attached to unrelated prose, Greek letters as replacement glyphs. Fix: render the page (`pdftoppm`) and inspect visually before writing.

**I.6.c Mechanism drift from the previous paper**:

Bad sign: §3.1 first sentence still describes the previous paper's family (e.g. using "layer replacement" language for a continual-pruning sensitivity paper). Guardrail: before writing §3, state a ≤30-character mechanism sentence. If it doesn't contain the current paper's unique object (e.g. `sensitivity history`, `expression tree`, `redundancy matrix`, `routing mask`), reread the method section.

**I.6.d Blank-line inflation**:

A note hitting 350+ lines just from blank-line separation is not depth. Compress blank lines first, then check whether §3 still has the required formulas and §4 still has the required numbers. Never delete evidence-bearing content to meet a line target.

**I.6.e Table-number hallucination**:

If you cite `Table X`, verify the number / model / dataset triple appears in evidence or raw PDF text:

```bash
grep -nE 'Table X|<model-name>|<exact number>' /tmp/cs-paper-reader-<batch>/_evidence/<Method>.md /tmp/cs-paper-reader-<batch>/<Method>.*.txt
```

### I.7 Automated check

Instead of hand-running every grep, use:

```bash
python3 ~/.codex/skills/cs-paper-reader/scripts/check_note_quality.py \
  --note <draft.md> --compare-dir <batch-dir> --refs <approved-ref.md> ... \
  --subfield llm-compression
```

The script checks forbidden scaffolds, common LaTeX residues, and exact-line collisions for §1.1 / §3.1. Conservative by design; inspect any warning rather than suppressing it.

> **Subfield patterns are opt-in via `--subfield`**: the script's built-in `FORBIDDEN_PATTERNS` are deliberately *subfield-independent* (scaffold leaks, generic-skeleton formulas, meta-description, universal scaffolds). Domain-specific phrases like `LLM 部署很贵` / `更适合 LLM` / `重要性分数 s_g` live in `~/.codex/skills/cs-paper-reader/subfield-patterns/llm-compression.txt`, loaded only when `--subfield llm-compression` is passed. To add another subfield, copy that file to `<subfield>.txt`, edit `[FORBIDDEN]` and `[BLACKLIST]` sections, then call with `--subfield <subfield>`. When reading a paper in a subfield with no pattern file yet, run **without** `--subfield` — you'll get the universal checks and zero false positives from another subfield's vocabulary.

---

## How to specialize this file for a new subfield

When you start a batch in a different subfield (e.g. knowledge editing, retrieval-augmented generation, agents, training systems):

1. Keep all of §A–§H as-is — those categories are universal.
2. Add a new appendix `J. <subfield name> subfield placeholders` mirroring §I's structure: subfield-specific placeholder sentences (§A→§J.1), formulas (§B→§J.2), meta-description (§D→§J.3), banned comparisons (§E→§J.4), master grep (§J.5).
3. Build the master grep by reading 2-3 first notes in the batch and listing the recurring "could-be-any-paper" phrases.
4. **Do NOT delete §I**. It stays as the worked example future readers can imitate.
5. **Create `~/.codex/skills/cs-paper-reader/subfield-patterns/<subfield>.txt`** (copy `llm-compression.txt` as a template). Fill the `[FORBIDDEN]` and `[BLACKLIST]` sections with the regex/tokens from §J's master grep + §5 method-name blacklist. Then run the script with `--subfield <subfield>` so the automated check enforces these alongside the universal patterns.
