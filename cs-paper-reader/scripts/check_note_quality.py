#!/usr/bin/env python3
"""Field-tested quality checks for cs-paper-reader Markdown notes.

This script is intentionally conservative: it reports suspicious patterns,
section collisions, and quantitative-floor violations. It does not rewrite
notes; callers decide whether to fix or override.

Two modes:
  default — print counters and warnings, exit 1 only on forbidden patterns
            or LaTeX residues or collisions (the "blocking" checks).
  --strict — additionally enforce the per-note quantitative floors from
            SKILL.md (§2-§3 formulas, §4 numbers, §5 methods, line range).
            Recommended in Mode B (batch reading).

Paper-type presets:
  --paper-type method-heavy     default floors for algorithmic papers
  --paper-type empirical-study  fewer formulas, more experimental anchors
  --paper-type system           fewer formulas, system-oriented anchors

Explicit --min-* flags always override the preset they correspond to.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


PAPER_TYPE_PRESETS = {
    "method-heavy": {
        "min_formula_tags": 3,
        "min_section4_numbers": 2,
        "min_section5_methods": 2,
        "min_pdf_anchors": 5,
    },
    "empirical-study": {
        "min_formula_tags": 1,
        "min_section4_numbers": 5,
        "min_section5_methods": 2,
        "min_pdf_anchors": 8,
    },
    "system": {
        "min_formula_tags": 1,
        "min_section4_numbers": 3,
        "min_section5_methods": 2,
        "min_pdf_anchors": 6,
    },
}

# Universal forbidden patterns — apply to every subfield.
# Subfield-specific patterns live in subfield-patterns/<name>.txt and are
# appended at runtime via --subfield <name>.
# Keep this list in sync with references/anti-template.md §A–§H ("universal").
FORBIDDEN_PATTERNS = [
    # B. Universal-skeleton formulas (truly generic — every subfield uses these)
    r"f_θ",
    r"f_\{θ",
    r"f_\{theta",
    r"min E\[d\(f",
    r"统一目标函数",
    # C. Variable-name-style placeholders (scaffold leak, subfield-independent)
    r"EvidenceSpecificScore",
    r"Compress_method",
    r"ScorePlaceholder",
    r"MethodSpecificMetric",
    # D. Meta-description instead of content (subfield-independent)
    r"应重点检查",
    r"应该查",
    r"应该看",
    # E. Quantification-free comparison (subfield-independent shapes)
    r"在某些 benchmark 上优于 baseline",
    r"保留更多能力",
    # G. Scaffold leakage (subfield-independent)
    r"TODO",
    r"待填入",
    r"见后续",
    r"此处补充",
    r"按.*骨架",
]

# Universal §5 method-name blacklist — tokens that look like ALL-CAPS or
# CamelCase but are NOT compared methods (file formats, hardware, generic
# acronyms, markdown labels). Subfield blacklists are appended at runtime.
UNIVERSAL_BLACKLIST = {
    "PDF", "GPU", "CPU", "FP", "INT", "BF",
    "Table", "Fig", "Figure", "Equation", "Algorithm", "Appendix",
    "I", "II", "III", "IV", "V", "VI", "VII", "VIII",
    # Common cross-subfield acronyms that are NOT compared methods
    "LLM",
}


def load_subfield_file(path: Path) -> tuple[list[str], set[str]]:
    """Parse a subfield patterns file (see subfield-patterns/llm-compression.txt
    for the format). Returns (forbidden_regexes, blacklist_tokens)."""
    forbidden: list[str] = []
    blacklist: set[str] = set()
    section: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].upper()
            continue
        if section == "FORBIDDEN":
            forbidden.append(line)
        elif section == "BLACKLIST":
            blacklist.add(line)
    return forbidden, blacklist


def resolve_subfield_path(name: str) -> Path:
    """Resolve a subfield name to a patterns file path.
    Accepts either a bare name (looks in <skill>/subfield-patterns/<name>.txt)
    or an absolute / relative path to a custom file."""
    candidate = Path(name)
    if candidate.exists():
        return candidate
    skill_root = Path(__file__).resolve().parent.parent
    return skill_root / "subfield-patterns" / f"{name}.txt"

# LaTeX residues from backslash-eating during JSON / shell serialization.
#
# We need to flag the BARE residue (`rac{`) without matching the correct
# command (`\frac{`). A single-char lookbehind `(?<!\\)rac\{` is NOT enough,
# because in `\frac{` the char before `rac` is `f`, not `\` — so the
# lookbehind would still match.
#
# Correct rule: flag the residue only when the residue is NOT preceded by
# the corresponding LaTeX command prefix. Use a multi-char lookbehind that
# checks for the full prefix (`\f` for `rac`, `\s` for `um_`, etc.). Also
# require non-letter boundaries around alphabetic residues so ordinary words
# such as `ablation` are not flagged as broken `\nabla`.
LATEX_RESIDUES = [
    # `rac{` not preceded by `\f` (so `\frac{` is OK, but bare `rac{` is not).
    r"(?<!\\f)(?<![A-Za-z])rac\{",
    # `um_` not preceded by `\s` (so `\sum_` is OK).
    r"(?<!\\s)(?<![A-Za-z])um_",
    # `qrt{` not preceded by `\s` (so `\sqrt{` is OK).
    r"(?<!\\s)(?<![A-Za-z])qrt\{",
    # `lpha` not preceded by `\a` (so `\alpha` is OK).
    r"(?<!\\a)(?<![A-Za-z])lpha(?![A-Za-z])",
    # `ambda` not preceded by `\l` (so `\lambda` is OK).
    r"(?<!\\l)(?<![A-Za-z])ambda(?![A-Za-z])",
    # `abla` not preceded by `\n` (so `\nabla` is OK).
    r"(?<!\\n)(?<![A-Za-z])abla(?![A-Za-z])",
    # Double-backslash over-escaping in Markdown math. `\\` is a line break,
    # not a safe way to serialize LaTeX commands such as `\right`.
    r"\\\\(sum|frac|sqrt|alpha|beta|lambda|nabla|left|right)\b",
]

# Limitations-claim sanity: if a note states "PDF 无 Limitations 章节",
# the caller should have already verified by grep on the PDF text.
LIMITATIONS_CLAIM_RE = re.compile(r"PDF\s*[中无]?\s*无\s*Limitations\s*章节")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text()


def control_character_failures(path: Path) -> list[str]:
    """Catch invisible characters that break Markdown/LaTeX rendering.

    CRLF line endings are tolerated, but bare carriage returns are not: a
    serialized LaTeX command such as `\right` can become an actual CR byte
    followed by `ight`, making the rendered formula fail without an obvious
    textual clue.
    """
    data = path.read_bytes()
    failures: list[str] = []
    line = 1
    col = 1
    for idx, byte in enumerate(data):
        if byte == 0:
            failures.append(f"CONTROL line {line}: NUL byte is forbidden")
        elif byte == 13:
            if idx + 1 < len(data) and data[idx + 1] == 10:
                continue
            failures.append(
                f"CONTROL line {line}: bare carriage return byte (possible broken `\\right`/`\\r...`)"
            )
            line += 1
            col = 1
            continue
        elif byte == 10:
            line += 1
            col = 1
            continue
        col += 1
    return failures


def display_math_failures(text: str) -> list[str]:
    """Conservative renderability checks for Markdown display math blocks."""
    failures: list[str] = []
    lines = text.splitlines()
    in_block = False
    start_line = 0
    block_lines: list[str] = []

    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if "$$" in line and stripped != "$$":
            failures.append(
                f"MATH line {lineno}: display math fence must be a standalone `$$` line"
            )
            continue
        if stripped == "$$":
            if in_block:
                content = "\n".join(block_lines)
                failures.extend(check_math_block(content, start_line, lineno))
                in_block = False
                block_lines = []
            else:
                in_block = True
                start_line = lineno
                block_lines = []
            continue
        if in_block:
            block_lines.append(line)

    if in_block:
        failures.append(f"MATH line {start_line}: unclosed display math block")
    return failures


def check_math_block(block: str, start_line: int, end_line: int) -> list[str]:
    failures: list[str] = []
    if re.search(r"\\\\[{}]", block):
        failures.append(
            f"MATH lines {start_line}-{end_line}: suspicious `\\\\}}`/`\\\\{{`; "
            "use `\\}` or `\\{` for literal braces"
        )
    left_count = len(re.findall(r"(?<!\\)\\left\b", block))
    right_count = len(re.findall(r"(?<!\\)\\right\b", block))
    if left_count != right_count:
        failures.append(
            f"MATH lines {start_line}-{end_line}: unmatched `\\left`/`\\right` "
            f"({left_count} vs {right_count})"
        )
    unescaped_braces = re.sub(r"\\[{}]", "", block)
    if unescaped_braces.count("{") != unescaped_braces.count("}"):
        failures.append(
            f"MATH lines {start_line}-{end_line}: unbalanced LaTeX braces "
            f"({unescaped_braces.count('{')} vs {unescaped_braces.count('}')})"
        )
    return failures



def grep_patterns(text: str, patterns: list[str]) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    lines = text.splitlines()
    for pattern in patterns:
        rx = re.compile(pattern)
        for lineno, line in enumerate(lines, 1):
            if rx.search(line):
                hits.append((lineno, pattern, line.strip()))
    return hits


def extract_subsection(text: str, heading_prefix: str) -> list[str]:
    """Return non-empty content lines under `### X.Y` until next `### `."""
    lines = text.splitlines()
    out: list[str] = []
    capture = False
    for line in lines:
        if line.startswith(heading_prefix):
            capture = True
            continue
        if capture and line.startswith("### "):
            break
        if capture and line.strip():
            out.append(line.strip())
    return out


def extract_top_section(text: str, start_prefix: str, end_prefix: str) -> str:
    """Return raw text between `## start_prefix...` and `## end_prefix...`."""
    lines = text.splitlines()
    out: list[str] = []
    capture = False
    for line in lines:
        if line.startswith(start_prefix):
            capture = True
        elif capture and line.startswith(end_prefix):
            break
        if capture:
            out.append(line)
    return "\n".join(out)


COLLISION_IGNORED_EXACT_LINES = {"$$"}


def collision_relevant_lines(lines: list[str]) -> list[str]:
    """Filter formatting-only lines from anti-template collision checks.

    Standalone Markdown math fences (``$$``) naturally repeat in notes with
    display equations and should not force authors to collapse formulas into
    less readable one-line math blocks.
    """
    return [line for line in lines if line.strip() not in COLLISION_IGNORED_EXACT_LINES]


def compare_sections(note: Path, compare_paths: list[Path], threshold: int) -> list[str]:
    note_text = read_text(note)
    warnings: list[str] = []
    for section in ("### 1.1", "### 3.1"):
        current = collision_relevant_lines(extract_subsection(note_text, section))
        current_set = set(current)
        for other in compare_paths:
            if other.resolve() == note.resolve() or not other.exists() or other.suffix != ".md":
                continue
            other_lines = collision_relevant_lines(extract_subsection(read_text(other), section))
            common = [line for line in other_lines if line in current_set]
            if len(common) >= threshold:
                warnings.append(
                    f"COLLISION {section}: {note.name} vs {other.name} "
                    f"({len(common)} identical non-empty lines)"
                )
    return warnings


def count_table_refs(text: str) -> int:
    """Count references to Table N / Fig. N / Figure N / 表 N / 图 N."""
    return len(re.findall(r"(?:Table|Fig\.|Figure|表|图)\s*\d+", text))


def count_pdf_anchors(text: str) -> int:
    """Count references to specific PDF anchors: Eq. N, Algorithm N, Appendix X, §X.Y."""
    patterns = [
        r"Eq\.\s*\d+",
        r"Equation\s*\d+",
        r"Algorithm\s*\d+",
        r"Appendix\s+[A-Z]",
        r"§\s*\d+(\.\d+)?",
    ]
    total = 0
    for p in patterns:
        total += len(re.findall(p, text))
    return total + count_table_refs(text)


def count_section4_numbers(text: str) -> int:
    """Count §4 tokens that look like data-anchored numbers."""
    section4 = extract_top_section(text, "## 四", "## 五")
    if not section4:
        section4 = extract_top_section(text, "## 四、", "## 五、")
    return len(re.findall(r"\d+\.\d+|\d+%|\d+\.\d+e[+-]?\d+", section4))


def count_section5_methods(text: str, extra_blacklist: set[str] | None = None) -> int:
    """Count distinct method-acronym-like tokens in §5.
    `extra_blacklist` is the subfield-specific blacklist appended at runtime."""
    section5 = extract_top_section(text, "## 五", "## 六")
    if not section5:
        section5 = extract_top_section(text, "## 五、", "## 六、")
    tokens = re.findall(r"\b[A-Z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)*\b", section5)
    blacklist = set(UNIVERSAL_BLACKLIST)
    if extra_blacklist:
        blacklist |= extra_blacklist
    return len({t for t in tokens if t not in blacklist and len(t) >= 2})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--note", required=True, type=Path)
    parser.add_argument("--compare-dir", type=Path,
                        help="Directory of existing notes to compare §1.1/§3.1 against")
    parser.add_argument("--refs", nargs="*", type=Path, default=[],
                        help="Specific reference notes to compare against")
    parser.add_argument("--collision-threshold", type=int, default=5)
    parser.add_argument("--strict", action="store_true",
                        help="Enforce per-note quantitative floors (SKILL.md). "
                        "Recommended in Mode B (batch reading).")
    parser.add_argument("--paper-type", choices=sorted(PAPER_TYPE_PRESETS),
                        default="method-heavy",
                        help="Strict-mode quantitative floor preset. Explicit --min-* "
                        "flags override the selected preset.")
    parser.add_argument("--subfield", default=None,
                        help="Subfield name (e.g. `llm-compression`) OR a path to "
                        "a subfield patterns file. Loads additional forbidden "
                        "patterns and §5 blacklist from "
                        "subfield-patterns/<name>.txt. Omit when reading a "
                        "subfield without a pattern file — only universal "
                        "patterns will be checked.")
    parser.add_argument("--min-lines", type=int, default=220)
    parser.add_argument("--max-lines", type=int, default=400)
    parser.add_argument("--min-formula-tags", type=int)
    parser.add_argument("--min-section4-numbers", type=int)
    parser.add_argument("--min-section5-methods", type=int)
    parser.add_argument("--min-pdf-anchors", type=int)
    args = parser.parse_args()

    preset = PAPER_TYPE_PRESETS[args.paper_type]
    for key, value in preset.items():
        if getattr(args, key) is None:
            setattr(args, key, value)

    # Load subfield-specific forbidden patterns + §5 blacklist if requested.
    subfield_forbidden: list[str] = []
    subfield_blacklist: set[str] = set()
    if args.subfield:
        subfield_path = resolve_subfield_path(args.subfield)
        if not subfield_path.exists():
            print(f"WARNING: --subfield {args.subfield} → {subfield_path} not found; "
                  "running with universal patterns only.", file=sys.stderr)
        else:
            subfield_forbidden, subfield_blacklist = load_subfield_file(subfield_path)
    effective_forbidden = FORBIDDEN_PATTERNS + subfield_forbidden

    note = args.note
    text = read_text(note)
    failures: list[str] = []
    soft_notes: list[str] = []

    # --- Blocking checks ---
    failures.extend(control_character_failures(note))
    failures.extend(display_math_failures(text))
    for lineno, pattern, line in grep_patterns(text, effective_forbidden):
        failures.append(f"FORBIDDEN line {lineno}: /{pattern}/ :: {line}")
    for lineno, pattern, line in grep_patterns(text, LATEX_RESIDUES):
        failures.append(f"LATEX line {lineno}: /{pattern}/ :: {line}")

    compare_paths: list[Path] = list(args.refs)
    if args.compare_dir and args.compare_dir.exists():
        compare_paths.extend(sorted(args.compare_dir.glob("*.md")))
    failures.extend(compare_sections(note, compare_paths, args.collision_threshold))

    # --- Counters ---
    formal_method_section = extract_top_section(text, "## 二", "## 四")
    if not formal_method_section:
        formal_method_section = extract_top_section(text, "## 二、", "## 四、")
    method_section = extract_top_section(text, "## 三", "## 四")
    if not method_section:
        method_section = extract_top_section(text, "## 三、", "## 四、")
    formula_tags = re.findall(r"\\tag\{[^}]+\}", formal_method_section)
    method_formula_tags = re.findall(r"\\tag\{[^}]+\}", method_section)
    display_math_blocks = formal_method_section.count("$$") // 2
    method_display_math_blocks = method_section.count("$$") // 2
    table_refs = count_table_refs(text)
    pdf_anchors = count_pdf_anchors(text)
    s4_numbers = count_section4_numbers(text)
    s5_methods = count_section5_methods(text, subfield_blacklist)
    line_count = len(text.splitlines())

    # --- Soft sanity ---
    if LIMITATIONS_CLAIM_RE.search(text):
        soft_notes.append(
            "LIMITATIONS: note claims `PDF 无 Limitations 章节`. "
            "Verify by grepping the PDF for `limit|future work|discussion|"
            "impact statement|drawback` before trusting this claim."
        )

    print(f"note={note}")
    print(f"paper_type={args.paper_type}")
    print(f"lines={line_count}")
    print(f"section2_3_formula_tags={len(formula_tags)}")
    print(f"section2_3_display_math_blocks={display_math_blocks}")
    print(f"section3_formula_tags={len(method_formula_tags)}")
    print(f"section3_display_math_blocks={method_display_math_blocks}")
    print(f"section4_numeric_anchors={s4_numbers}")
    print(f"section5_distinct_method_names={s5_methods}")
    print(f"table_or_figure_refs={table_refs}")
    print(f"pdf_anchor_refs={pdf_anchors}")

    # --- Strict-mode floors ---
    if args.strict:
        if len(formula_tags) < args.min_formula_tags:
            failures.append(
                f"STRICT §2-§3 formula tags: {len(formula_tags)} < {args.min_formula_tags} "
                f"(need ≥ {args.min_formula_tags} `\\tag{{N}}` formulas across §2-§3)"
            )
        if s4_numbers < args.min_section4_numbers:
            failures.append(
                f"STRICT §4 numeric anchors: {s4_numbers} < {args.min_section4_numbers}"
            )
        if s5_methods < args.min_section5_methods:
            failures.append(
                f"STRICT §5 distinct method names: {s5_methods} < {args.min_section5_methods}"
            )
        if pdf_anchors < args.min_pdf_anchors:
            failures.append(
                f"STRICT PDF anchor refs: {pdf_anchors} < {args.min_pdf_anchors} "
                f"(Eq./Table/Figure/Algorithm/Appendix/§X.Y)"
            )
        if line_count < args.min_lines:
            failures.append(
                f"STRICT lines: {line_count} < {args.min_lines} (note too short)"
            )
        if line_count > args.max_lines:
            soft_notes.append(
                f"LENGTH: lines={line_count} > {args.max_lines}; "
                "compress blank-line inflation before adding more content."
            )

    if soft_notes:
        print("NOTES:")
        for item in soft_notes:
            print(f"- {item}")

    if failures:
        print("FAILURES:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
