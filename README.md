# Research Paper Reading Skills / 论文阅读 Skills

[English](#english) | [中文](#中文)

---

## English

Two Codex skills for reading computer-science papers and producing image-rich Chinese Markdown notes.

### Skills

- `cs-paper-reader` — Reads, summarizes, dissects, compares, and writes structured Chinese notes for CS research papers.
  - Supports single-paper deep reading and unattended batch reading from a folder or chapter.
  - Emphasizes PDF-grounded evidence, formulas, algorithms, experiments, limitations, and research ideas.
  - Includes note-quality checks for math rendering, anti-template repetition, quantitative anchors, and final-output hygiene.

- `paper-figure-clipper` — Extracts figures, tables, algorithms, equations, and custom regions from research PDFs.
  - Uses bbox/caption-anchored cropping instead of percent-of-page heuristics.
  - Produces staging crops and metadata for image-rich notes.
  - Works as the companion skill for `cs-paper-reader`.

### Requirements

- Codex CLI with skill support.
- Python 3.10+.
- Python package: `PyMuPDF`.
- System PDF tools: `pdftotext`, `pdftoppm` from Poppler.
- Java 11+ for `pdffigures2`.
- Optional but recommended: `pdffigures2` assembly JAR for automatic figure/table discovery.

### Install Dependencies

macOS:

```bash
brew install python poppler openjdk@17
python3 -m venv ~/.codex/venvs/paper-figure-clipper
~/.codex/venvs/paper-figure-clipper/bin/python -m pip install --upgrade pip pymupdf
```

Ubuntu / Debian:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv poppler-utils openjdk-17-jre
python3 -m venv ~/.codex/venvs/paper-figure-clipper
~/.codex/venvs/paper-figure-clipper/bin/python -m pip install --upgrade pip pymupdf
```

`pdffigures2` is optional but useful for `paper-figure-clipper scan`. Build or download the assembly JAR, then place it here:

```bash
mkdir -p ~/.codex/tools
cp /path/to/pdffigures2-assembly.jar ~/.codex/tools/pdffigures2-assembly.jar
```

### Environment Variables

Usually no environment variable is required. The scripts look for the dedicated Python environment and `pdffigures2` JAR at these default paths:

```bash
export CODEX_SKILLS_DIR="$HOME/.codex/skills"
export PATH="$HOME/.codex/venvs/paper-figure-clipper/bin:$PATH"
export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"   # macOS Apple Silicon, if Java is not found
```

Default paths used by the skills:

```text
~/.codex/skills/cs-paper-reader
~/.codex/skills/paper-figure-clipper
~/.codex/venvs/paper-figure-clipper/bin/python
~/.codex/tools/pdffigures2-assembly.jar
```

### Install Skills

Copy the two skill folders into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R cs-paper-reader ~/.codex/skills/
cp -R paper-figure-clipper ~/.codex/skills/
```

Then restart Codex or reload skills if your environment supports it.

### Usage Template

Single-paper deep read:

```text
Use $cs-paper-reader and $paper-figure-clipper.
Read this PDF carefully and write a Chinese Markdown note.
PDF: /path/to/paper.pdf
Output directory: /path/to/notes
Requirements:
- Use image-rich notes when figures/tables/algorithms are useful.
- Keep temporary evidence and crop metadata under /tmp.
- Put final referenced images under _figs/<Method>/.
- Run the note-quality check before finishing.
```

Batch folder reading:

```text
Use $cs-paper-reader and $paper-figure-clipper.
Read all PDFs under /path/to/pdf_folder and continue until the batch is complete.
Output notes to /path/to/notes.
Work paper by paper, reuse existing temporary evidence when valid, and keep final notes consistent with the skill format.
```

Manual figure extraction:

```bash
python ~/.codex/skills/paper-figure-clipper/scripts/clip.py scan \
  --pdf /path/to/paper.pdf \
  --out-dir /tmp/paper-figs/Method

python ~/.codex/skills/paper-figure-clipper/scripts/clip.py clip \
  --pdf /path/to/paper.pdf \
  --out /tmp/paper-figs/Method/algorithm_1_p5.png \
  algorithm --label "Algorithm 1" --page 5
```

Quality check:

```bash
python ~/.codex/skills/cs-paper-reader/scripts/check_note_quality.py /path/to/note.md
```

### Notes

These skills are optimized for Chinese long-form research notes, but the workflow is domain-agnostic and can be adapted to compression, distillation, retrieval, agents, systems, and other CS areas.

---

## 中文

两个用于计算机论文精读与图文笔记生成的 Codex skills。

### Skills

- `cs-paper-reader` — 阅读、总结、拆解、比较计算机论文，并生成结构化中文 Markdown 笔记。
  - 支持单篇深读，也支持按文件夹、章节或目录批量阅读。
  - 强调基于 PDF 原文的证据、公式、算法、实验、局限和研究想法。
  - 内置数学渲染、反模板重复、定量锚点、最终输出目录卫生等质检规则。

- `paper-figure-clipper` — 从论文 PDF 中精确裁剪图、表、算法、公式或自定义区域。
  - 基于 bbox / caption 定位，不使用页面百分比裁剪。
  - 生成临时裁剪图和元数据，供图文笔记引用。
  - 通常作为 `cs-paper-reader` 的配套 skill 使用。

### 依赖

- 支持 skills 的 Codex CLI。
- Python 3.10+。
- Python 包：`PyMuPDF`。
- 系统 PDF 工具：Poppler 提供的 `pdftotext`、`pdftoppm`。
- Java 11+，用于运行 `pdffigures2`。
- 可选但推荐：`pdffigures2` assembly JAR，用于自动发现论文中的图表。

### 安装依赖

macOS：

```bash
brew install python poppler openjdk@17
python3 -m venv ~/.codex/venvs/paper-figure-clipper
~/.codex/venvs/paper-figure-clipper/bin/python -m pip install --upgrade pip pymupdf
```

Ubuntu / Debian：

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv poppler-utils openjdk-17-jre
python3 -m venv ~/.codex/venvs/paper-figure-clipper
~/.codex/venvs/paper-figure-clipper/bin/python -m pip install --upgrade pip pymupdf
```

`pdffigures2` 是可选依赖，但建议安装，主要用于 `paper-figure-clipper scan`：

```bash
mkdir -p ~/.codex/tools
cp /path/to/pdffigures2-assembly.jar ~/.codex/tools/pdffigures2-assembly.jar
```

### 环境变量

通常不需要额外环境变量。脚本默认会查找专用 Python 环境和 `pdffigures2` JAR：

```bash
export CODEX_SKILLS_DIR="$HOME/.codex/skills"
export PATH="$HOME/.codex/venvs/paper-figure-clipper/bin:$PATH"
export PATH="/opt/homebrew/opt/openjdk@17/bin:$PATH"   # macOS Apple Silicon 下找不到 Java 时使用
```

默认路径：

```text
~/.codex/skills/cs-paper-reader
~/.codex/skills/paper-figure-clipper
~/.codex/venvs/paper-figure-clipper/bin/python
~/.codex/tools/pdffigures2-assembly.jar
```

### 安装 Skills

将两个 skill 目录复制到 Codex skills 目录：

```bash
mkdir -p ~/.codex/skills
cp -R cs-paper-reader ~/.codex/skills/
cp -R paper-figure-clipper ~/.codex/skills/
```

然后重启 Codex，或在支持的环境中重新加载 skills。

### 使用模板

单篇论文精读：

```text
使用 $cs-paper-reader 和 $paper-figure-clipper。
请精读这篇 PDF，并写成中文 Markdown 论文笔记。
PDF: /path/to/paper.pdf
输出目录: /path/to/notes
要求：
- 如果图、表、算法对理解论文有帮助，启用图文笔记。
- 临时证据、OCR、裁剪元数据放在 /tmp。
- 最终引用图片放在 _figs/<Method>/。
- 完成前运行 note-quality check。
```

目录批量阅读：

```text
使用 $cs-paper-reader 和 $paper-figure-clipper。
阅读 /path/to/pdf_folder 下的所有 PDF，直到整批完成。
笔记输出到 /path/to/notes。
注意：逐篇处理，已有临时证据有效时可以复用，并保持最终笔记符合 skill 规范. 不能使用自动化程序撰写文档，每一篇都必须手写，且每篇都必须完成质量检查、图片检查和实验结果冗余检查
```

手动裁剪图表：

```bash
python ~/.codex/skills/paper-figure-clipper/scripts/clip.py scan \
  --pdf /path/to/paper.pdf \
  --out-dir /tmp/paper-figs/Method

python ~/.codex/skills/paper-figure-clipper/scripts/clip.py clip \
  --pdf /path/to/paper.pdf \
  --out /tmp/paper-figs/Method/algorithm_1_p5.png \
  algorithm --label "Algorithm 1" --page 5
```

质量检查：

```bash
python ~/.codex/skills/cs-paper-reader/scripts/check_note_quality.py /path/to/note.md
```

### 说明

这些 skills 主要面向中文长篇论文笔记，但流程本身与具体 CS 子领域无关，可以迁移到压缩、蒸馏、检索、智能体、系统等不同方向。
