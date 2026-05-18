# User Note Style Reference

> **Domain note**: the style observations and calibration samples listed below come from this user's existing notes, which to date concentrate on LLM compression. The **style discipline** (long-form Chinese, causal explanation, formula + symbol-by-symbol explanation, quantitative §5) is domain-agnostic. **Specific calibration samples** (`_SAMPLE_SliceGPT.md`, the SparseGPT note) and **specific mechanism-noun examples** (`OBS update`, `routing mask`) are illustrative — when reading a paper outside compression, you may need to find a more representative calibration sample, and the mechanism-noun you look for in §3.1 will be drawn from that subfield's vocabulary.

Observed style from the user's existing paper notes:

- Long-form Chinese Markdown, title as `# Paper Title` (or `# MethodName: Full Paper Title`).
- Metadata block with `发表信息`、`作者`、`机构`、optional `代码/项目`、optional `本地 PDF` (absolute path).
- Sections commonly include:
  - `## 一、研究背景与动机`
  - `## 二、预备知识与形式化定义`
  - `## 三、方法详解`
  - `## 四、实验结果`
  - `## 五、与相关工作的区别`
  - `## 六、核心贡献总结`
  - `## 七、讨论与局限`
  - optional `## 八、对后续研究的启发`
- Strong preference for causal explanation: "现有方法失败的根本原因"、"核心 Insight"、"为什么有效"。
- Formulas are followed by symbol-by-symbol explanations.
- Method sections are decomposed into stages/modules with intuitive summaries.
- Experiment sections explain what each table validates **and include enough numbers to anchor the claim**; not just numeric transcription, but also not pure prose.
- Add `与相关工作的区别` even if the paper only has a brief related-work section, and always name specific compared methods with quantitative differences.
- Use `<font color="red">`、`<font color="blue">`、`<font color="green">` to highlight 1–3 core insights per note; do not sprinkle.
- File naming: prefer `(Venue Year) MethodName-Paper Title.md`, e.g. `(ICLR 2024) SliceGPT-Compress Large Language Models by Deleting Rows and Columns.md`. Use `arXiv Year` only when no accepted venue can be verified.

## Calibration samples already approved

When the user provides a sample note that has been human-approved, treat it as the authoritative style + density reference for the current batch. Examples seen in this user's workspace:

- `_SAMPLE_SliceGPT.md` — purpose-written sample (~280 lines, 9 formulas, ≥10 table values).
- `(ICML 2023) SparseGPT-Massive Language Models Can Be Accurately Pruned in One-Shot.md` — codex-generated, human-approved (~390 lines, 6 formulas, 30+ table values).

If asked to "match the style of X", read X end-to-end first and replicate its density, section depth, and table-citation discipline.

## Related references in this skill

- `batch-workflow.md` — full Mode B (batch reading) workflow including progress tracking, bootstrap protocol, paper-type-aware floors, resume, and stop conditions.
- `anti-template.md` — exhaustive list of bad patterns + grep commands to catch them.


## Field-tested style refinements (2026-05-16)

- In batch notes, the first 5 non-empty lines of `### 1.1` should reveal the paper's specific problem, not the chapter's general topic.
- `### 3.1` should name the paper's unique computational object — a noun specific to this paper, not a noun that fits every paper in the subfield. Examples from various subfields (illustrative): `OBS update` (pruning), `hidden-state pair` (editing), `sensitivity history` (continual pruning), `symbolic tree` (NAS), `redundancy matrix` (low-rank), `routing mask` (MoE), `retrieval-augmented prompt` (RAG), `policy advantage` (RL). If the noun you wrote could fit every paper in the subfield, rewrite it.
- Tables in §4 should be selective but multi-anchor: include at least one main-table row, one ablation/failure number, and one direct baseline delta whenever the PDF provides them.
- When a paper has strong appendix evidence, use appendix tables sparingly but explicitly label them as `Appendix Table X`; do not blend appendix numbers into main-result claims.
- Limitation writing should distinguish three sources: `作者自承`, `Impact/Future Work`, and `我的判断`. Do not collapse all three into generic “可能不适用”.
- If line count exceeds the user's requested range, first remove redundant blank lines and repeated prose. Keep formulas, table values, and paper-specific mechanism explanations intact.
