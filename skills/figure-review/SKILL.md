---
name: figure-review
description: Review paper figures at print-realistic DPI for readability, consistency, and journal standards. Renders every page of the compiled PDF at 150 DPI (simulating a reader viewing at 100% zoom on a standard monitor) and checks each figure systematically. Use when 用户说 "查图" / "figure-review" / "图能不能读" / "图够不够清楚" / "导出的 PDF 图字号太小" / 投稿前图表 audit / 用 `\includegraphics` 的 paper.tex 编完后 final 检查。
---

> **v0 — ported verbatim from `weak-gravitational-lensing/.claude/skills/figure-review.md`.**
> Project-specific colour/marker conventions (RdBu_r, GNN/Swin colours) are
> marked `[WGL]`; replace with your project's palette before running on a
> different paper.

# Figure Review Skill

## When to invoke

Use after adding or modifying any figure in the paper, or before submission. This skill ensures all figures meet journal print-quality standards **as seen by a human reader**, not just in a zoomed-in vector view.

## Core principle

> **Never review figures from the raw PDF or vector source.**
> Always render the **compiled main.pdf** at **150 DPI** (full page) and review from those rasterised images.
> This simulates what a reader sees at 100% zoom on a standard monitor.
> AI can read tiny text in vectors that humans cannot — this DPI check corrects for that bias.

## Review protocol

### Step 1: Compile and render

```bash
# Compile (2 passes for cross-refs)
pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex

# Render every page at 150 DPI
python -c "
import pymupdf as fitz
doc = fitz.open('main.pdf')
for i in range(len(doc)):
    mat = fitz.Matrix(150/72, 150/72)
    pix = doc[i].get_pixmap(matrix=mat)
    pix.save(f'review_p{i+1:02d}.png')
"
```

### Step 2: Per-figure checklist

For each figure page, read the 150-DPI PNG and check:

| # | Item | Pass criterion |
|---|---|---|
| 1 | **Axis labels** | Readable without zooming; minimum ~8pt at print size |
| 2 | **Tick labels** | Minimum ~7pt at print size |
| 3 | **Legend text** | Minimum ~7pt; legend box doesn't obscure data |
| 4 | **Title / panel labels** | (a)(b)(c) labels bold and ≥9pt |
| 5 | **Annotation text** | Any in-figure text ≥6.5pt at print size |
| 6 | **Line thickness** | Data lines ≥1.0pt; axis lines ≥0.7pt; no "hairline" lines |
| 7 | **Marker size** | Scatter points distinguishable (no sub-pixel markers) |
| 8 | **Colour contrast** | All colours distinguishable in greyscale (for B&W printing) |
| 9 | **Colour bar** | Present if using colour mapping; label + tick labels readable |
| 10 | **Aspect ratio** | Square data shown square; no unintended stretching |
| 11 | **White space** | No large empty regions within the figure boundary |
| 12 | **Caption** | Fully self-contained; all symbols defined; correct cross-refs |
| 13 | **Float placement** | Figure appears near its first text reference, not pages away |
| 14 | **Consistency** | Font family, colour palette, line styles match across all figures |
| 15 | **Single vs double column** | `figure` for ≤3.4" wide; `figure*` for >3.4" wide |

### Step 3: Cross-figure consistency

After reviewing individual figures, check across all figures:

- **Font family**: all serif (Times/CM) or all sans — no mixing
- **Colour palette**: accent colours reused consistently
- **Axis label style**: consistent format throughout
- **Line width / marker size**: similar data density → similar visual weight
- **Colormap**: same physical quantity → same colormap

### Step 4: Float placement scan

```python
# Scan for sparse pages (potential float displacement)
for i in range(len(doc)):
    pix = doc[i].get_pixmap(matrix=fitz.Matrix(1,1))
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, -1)
    ink = np.any(img < 240, axis=2).mean()
    if ink < 0.10:
        print(f'  p{i+1}: coverage={ink:.2f} -- check for displaced float')
```

### Step 5: Report

Output a markdown table:

```
| Fig # | Page | Status | Issues |
|-------|------|--------|--------|
| 1     | 4    | PASS   | --     |
| 2     | 5    | WARN   | cell text 5.5pt, borderline |
| ...   |      |        |        |
```

## Font size reference (at print)

For a two-column article on letter paper (text width ~3.4" per column, ~7" for figure*):

| Element | Minimum pt | Recommended pt |
|---------|-----------|----------------|
| Axis labels | 8 | 10 |
| Tick labels | 7 | 8.5 |
| Legend | 7 | 8 |
| Panel labels (a)(b)(c) | 9 | 10 |
| In-figure annotations | 6.5 | 8 |
| Colorbar label | 8 | 9 |

## Float parameters (recommended for `article` class)

```latex
\renewcommand{\topfraction}{0.95}
\renewcommand{\bottomfraction}{0.95}
\renewcommand{\textfraction}{0.05}
\renewcommand{\floatpagefraction}{0.80}
\renewcommand{\dbltopfraction}{0.95}
\setlength{\textfloatsep}{8pt plus 2pt minus 2pt}
\setlength{\floatsep}{8pt plus 2pt minus 2pt}
\setlength{\dbltextfloatsep}{8pt plus 2pt minus 2pt}
```

Use `[!htb]` instead of `[htbp]` to prevent float-page displacement.

## Style guide for this project [WGL — replace per project]

- **S/N maps**: `RdBu_r` colormap, `vmin=-3.5, vmax=4.5`, with shared colorbar labelled "$S/N$"
- **GT markers**: black `+` for main, green `×` for sub-halo
- **Model accent colours**: GNN = `#1f6f9a` (blue), Swin = `#7e3a8e` (purple), Per-peak = `#c0561f` (orange)
- **Serif font**: Times New Roman / DejaVu Serif, `mathtext.fontset = 'cm'`
- **Figure generation**: project-specific Python scripts, each producing `.pdf` + `.png`
