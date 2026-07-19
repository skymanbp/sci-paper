# style-corpus/

Private source papers used to build field-specific writing evidence for
`/sci-paper:de-ai` and the de-AI analysis tools. Corpus contents are
copyright-sensitive and gitignored; only the directory scaffold and README
files belong in the repository.

Corpus evidence is descriptive or calibrational input. It cannot redefine the
consequence classes in `docs/SCIPAPER_STANDARD.md`, prove authorship, or create a
universal paper verdict.

## Layout

```text
style-corpus/
└── <field>/
    ├── tier-1-top/         # top-journal exemplars
    ├── tier-2-mentor/      # mentor or target-author exemplars
    └── tier-3-reference/   # other relevant field papers
```

A field is a writing domain such as `wgl`, `cosmology`, or `ml-methods`. Each
field produces an independent `style-profile/<field>/`. Tools auto-detect only
when exactly one field exists; otherwise pass `--field <name>`.

`tools/extract_style.py` currently aggregates the three tiers with fixed weights
`0.5 / 0.3 / 0.2`. These weights describe the current implementation, not a
calibrated consequence rule. Change them only together with an evaluation of how
the resulting profile behaves.

## Accepted sources

**Preferred: LaTeX source** (`.tex` plus any required `.bib`). Section boundaries
and citation removal are more reliable than PDF extraction. A multi-file paper
may live in its own subdirectory:

```text
style-corpus/wgl/tier-1-top/
└── smith-2024-mnras/
    ├── main.tex
    ├── methods.tex
    └── refs.bib
```

**Accepted with inspection: standalone PDF.** Extraction uses pymupdf when
installed. Block segmentation and section detection remain heuristic, so inspect
the generated evidence for missing columns, merged paragraphs, headers, and
misclassified sections.

Do not use screenshots, uncontrolled OCR, slides, theses, reviews, or other
document types when the intended reference population is journal prose. Record
and justify any deliberate expansion of the population in `EVALUATION.md`.

## Corpus size

The following is an editorial starting heuristic, not a measured sufficiency
threshold:

| Tier | Starting point | Broader target |
|---|---:|---:|
| 1 (top) | 5 | 15–25 |
| 2 (mentor) | 3 | 5–10 |
| 3 (reference) | 0 | 5–15 |
| **Total** | **8** | **25–50** |

Small corpora produce uncertain per-section distributions. The extractor does
not currently enforce or guarantee a minimum-paper warning, so downstream
reports must preserve the actual sample count and use `degraded` or
`unmeasured` when the intended inference is unsupported.

Whole-document calibration has a stricter unit rule: each observation must be an
independent complete paper. Do not resample paragraph exemplars as if they were
independent documents. Pass a verified private complete-document directory
explicitly to `tools/deai_docstructure.py --calibrate`.

## Build and inspect

```bash
python tools/extract_style.py --field <name>
```

Inspect `style-profile/<field>/style_dossier.md` and the JSON/JSONL artifacts for
extraction errors. Do **not** hand-edit generated evidence. If a pattern is wrong,
fix the source selection or extractor and regenerate; otherwise the next rebuild
will erase the change and provenance will be lost.

For the full asset map and the boundary between basic profile generation and
calibration, see `style-profile/README.md`.

## Updating

Add or remove authorized papers, rerun `extract_style.py`, and re-evaluate any
calibrated asset that depends on the changed corpus. Missing or stale calibration
must remain visible as `degraded` or `unmeasured`, never as zero findings.
