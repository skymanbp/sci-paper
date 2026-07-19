---
name: figure-review
description: Review every paper figure from the compiled document at print-realistic 150 DPI. Verify figure/caption/data consistency, required labels, units, references, readability, accessibility, float placement, and cross-figure visual coherence. Report SCIPAPER_STANDARD typed findings: objective figure/build contradictions as integrity blockers and aesthetic or borderline readability concerns as advisories, never a universal PASS/WARN paper verdict. Use after figure changes or before submission.
---

# figure-review — compiled-page evidence and typed feedback

> **Normative authority:** `docs/SCIPAPER_STANDARD.md`.
> This skill reviews rendered evidence. Project palettes and journal conventions are
> contextual references, not independent blocker policy.

## 0. Core rules

1. **Review the compiled document, not only raw vectors.** Render every page containing a
   figure at 150 DPI and inspect the rasterized page at normal size. Vector extraction may
   assist diagnosis but cannot replace the human-scale view.
2. **Read every actual figure.** A caption alone cannot verify curves, points, error bars,
   panels, labels or visual hierarchy.
3. **Trace scientific content.** Figure values, sample definitions, symbols and caption
   claims must agree with the generating data/script and manuscript.
4. **Type consequences correctly.**
   - missing/broken required figure, unreadable required scientific label, wrong unit,
     caption/figure contradiction, data mismatch, missing panel, broken reference or failed
     required build → `integrity_blocker`;
   - borderline font size, whitespace, palette preference, visual balance or nonessential
     polish → `advisory`;
   - any textual L0 occurrence follows the shared L0 policy.
5. **No figure PASS verdict.** Report what was measured, what was not, and the disposition
   of each finding.
6. **Do not invent visual thresholds.** Journal rules and intended print size determine
   applicability. Reference sizes below are review aids, not automatic blocker boundaries.

## 1. Compile and render

Use the paper's authoritative build command. A simple LaTeX fallback is:

```bash
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

Render every page at 150 DPI:

```python
import pymupdf as fitz

doc = fitz.open("main.pdf")
for index in range(len(doc)):
    pix = doc[index].get_pixmap(matrix=fitz.Matrix(150 / 72, 150 / 72))
    pix.save(f"review_p{index + 1:02d}.png")
```

Record:

- build command and result;
- compiled PDF path and timestamp/hash when available;
- page-to-figure mapping;
- pages or assets that could not be rendered;
- measurement state for rendering and source tracing.

A build or render failure is an execution failure; if it prevents a required figure from
appearing, also emit an `integrity_blocker`.

## 2. Per-figure scientific checks

For each figure, inspect the 150-DPI page and the source asset where useful.

### 2.1 Required content

- all referenced panels exist and panel labels match the caption;
- axes, units, legends, color bars and symbol definitions needed to interpret the result
  are present;
- figure numbering and `\ref{}` target the correct object;
- caption describes the plotted quantity, sample, statistic and uncertainty correctly;
- stated scales, cuts, normalization, sign convention and color mapping match the data;
- no clipping, accidental crop, overlap or rendering corruption hides scientific content.

Failures that change or prevent scientific interpretation are `integrity_blocker`.

### 2.2 Readability at intended size

Inspect without zooming:

- axis and tick labels;
- legend and annotation text;
- panel labels;
- line and contour separation;
- marker visibility;
- error bars;
- color-bar ticks and labels;
- dense table-like cells inside figures.

Reference ranges for a conventional two-column paper are approximately 8 pt for axis labels,
7 pt for ticks/legend, 9 pt for panel labels and 6.5 pt for nonessential annotations. Use the
journal template and actual final width where available. A slightly smaller but clearly
readable annotation is an advisory, not an automatic blocker. An unreadable label required to
identify a quantity, sample or panel is a blocker.

### 2.3 Accessibility and encoding

- important distinctions survive grayscale when the venue requires print accessibility;
- color is not the sole carrier of class, sign or model identity when readers need the
  distinction;
- palettes are perceptually appropriate for sequential/diverging/categorical data;
- identical physical quantities use consistent range and mapping unless the difference is
  explicitly signaled;
- line styles, markers or labels provide redundant encoding where needed.

Accessibility that blocks interpretation is a blocker; stronger redundancy or palette polish
is advisory.

### 2.4 Geometry and placement

- aspect ratio does not distort coordinates or images;
- square physical maps remain square when required;
- subpanels align and use consistent margins;
- whitespace does not bury the data or create accidental emphasis;
- the float appears near its first substantive reference;
- single/double-column choice matches the information density.

Wrong geometry that changes scientific interpretation is a blocker. Placement, whitespace and
balance are normally advisories.

### 2.4.1 Canvas balance (pixel-measured)

When placement or balance is in question, measure it rather than eyeballing it. On the 150-DPI
render, quantify the rendered whitespace: the left/right and top/bottom outer margins, the
panel-centre offset from the canvas centre, and, for faceted or multi-panel layouts, the strip
and gutter widths that should match across panels. A canvas is balanced when opposing outer
margins agree within **max(2 px at 150 DPI, 1% of the canvas width)** and every repeated
structural element (facet strip, inter-panel gap, colour-bar gutter) is equal across panels.
The usual root cause is a tight save that keeps the left axis-title + tick-label column but
crops the right edge flush, shifting the panel left of centre. Correct the asymmetry at the
generator, setting the right outer pad to the measured width of the opposing left column
rather than nudging with an absolute offset, then re-render and re-measure. Imbalance within
tolerance needs no action; beyond it, an advisory — unless it crops or misaligns scientific
content, which is the Section 2.4 blocker.

## 3. Source and manuscript cross-check

For every figure:

1. identify the live generator and upstream data;
2. verify the figure asset was produced from the current source rather than a stale copy;
3. compare caption and manuscript numerical claims with plotted data/output;
4. verify all samples, cuts, units, uncertainty definitions and color conventions;
5. inspect any figure-derived values quoted in abstract, results or conclusion;
6. record file/line or data-cell provenance.

Do not rerun a heavy multi-minute pipeline locally when project rules require cloud execution.
Use current verified artifacts or the authorized compute environment.

## 4. Cross-figure consistency

Compare all figures for:

- font family and math typography;
- notation and terminology;
- palette semantics;
- line/marker identity for recurring methods or samples;
- axis-label grammar and unit formatting;
- panel-label sequence;
- color-bar placement and scale behavior;
- relative visual weight for comparable data density.

Inconsistency that maps the same visual encoding to conflicting scientific meanings is a
blocker. Pure styling variation is advisory.

Project-specific conventions may be loaded from the manuscript repository, figure scripts or
style guide. Verify them from current files rather than relying on values copied into this skill.

## 5. Fix and re-review

For authorized edits:

1. rank findings by the unified standard;
2. repair scientific blockers at the generating source when possible, not by covering them in
   LaTeX or caption text;
3. apply the minimum visual change for readability/advisory findings;
4. regenerate the asset using the live script;
5. rebuild the paper;
6. re-render the affected full page at 150 DPI;
7. re-inspect the figure, caption, references and dependent manuscript claims;
8. report residual advisories and unavailable measurements.

Do not upscale a raster to simulate real resolution, edit a stale exported asset while leaving
the generator wrong, or change data limits solely to make the plot look cleaner.

## 6. Report contract

```markdown
# Figure Review — Typed Feedback Report
Target: <main file> | Compiled PDF: <path>
Workflow state: DISPOSITION_COMPLETE | REVIEW_ONLY | EXECUTION_FAILURE

## Measurement state
| axis | status | provenance / limitation |

## Figure inventory
| figure | page | asset | generator/data provenance | rendered |

## Ranked findings
| id | kind | rule | figure/page | evidence | source trace | action | disposition |

## Per-figure observations
### Figure N
- scientific content and caption agreement
- readability at 150 DPI
- accessibility and geometry
- residual advisories

## Cross-figure observations
<typed findings and evidence>

## Author decisions required
<strong advisories or unavailable evidence>
```

Do not use a `PASS`/`WARN` status column. A figure with no current findings is recorded as
“no findings under measured axes”, not as proof that every unmeasured property is correct.

## 7. Stopping rule

Figure review is disposition-complete when:

- all figure-related integrity blockers are resolved or verified false positives;
- applicable textual L0 targets are zero;
- every strong figure advisory is acted, accepted, rejected as false positive, or pending with
  a stated reason;
- ordinary aesthetic advisories and unmeasured axes are reported;
- affected pages have been rebuilt and re-rendered at 150 DPI.

## 8. Anti-patterns

- Reviewing only the raw PDF/vector source.
- Reading captions without viewing the actual figure.
- Treating every font-size recommendation as a blocker.
- Treating palette preference as scientific failure.
- Calling a figure PASS because no issue was noticed.
- Fixing a data mismatch in the caption instead of the generator/data.
- Ignoring a broken or missing figure because the prose describes it.
- Relying on color alone for a required distinction without checking accessibility.
