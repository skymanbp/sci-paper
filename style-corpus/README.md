# style-corpus/

This is where you place the source papers used to build the writing-style
profile consumed by `/sci-paper:paper-style`. **Contents are NOT committed**
(see `.gitignore`) — the corpus is private and copyright-sensitive.

## Layout

```
style-corpus/
└── <field>/                # one field per subdir; v0.1 ships only `wgl/`
    ├── tier-1-top/         # Top-journal exemplars. Default weight 0.5.
    ├── tier-2-mentor/      # Mentor's high-quality papers. Default weight 0.3.
    └── tier-3-reference/   # Other high-value field references. Default weight 0.2.
```

A "field" is a writing-style domain — `wgl` for weak-gravitational-lensing
papers, and you can add `cosmology/`, `ml-methods/`, etc. alongside it. The
extraction tool builds one independent profile per field. Single-field
corpora are auto-detected; multi-field corpora require `--field <name>`
on every tool invocation.

Tier weights are applied in `tools/extract_style.py` when aggregating
statistics. v0.1 uses fixed defaults (0.5 / 0.3 / 0.2); a `--weights`
override is on the v0.2 roadmap.

## What to put here

**Preferred: LaTeX source** (`.tex` + `.bib`). Parsing is exact, sections are
labelled, citations are clean. If a paper has multiple `.tex` files, put them
in a subdirectory:

```
wgl/tier-1-top/
└── smith-2024-mnras/
    ├── main.tex
    ├── methods.tex
    └── refs.bib
```

**Acceptable: PDF.** Parsed via `pymupdf` text extraction. Section detection
is heuristic (regex on heading-like lines + font-size jumps) and may
misclassify boundaries. Inspect the resulting `style-profile/` artifacts
manually to catch parse errors.

**Do NOT put here:** screenshots, OCR output of unknown quality,
non-paper documents (slides, theses, reviews are out-of-distribution for the
journal style).

## Recommended corpus size

| Tier | Min | Recommended |
|---|---|---|
| 1 (top) | 5 | 15–25 |
| 2 (mentor) | 3 | 5–10 |
| 3 (reference) | 0 | 5–15 |
| **Total** | **8** | **25–50** |

Below 8 total papers, the per-section sentence-length distributions and
transition inventories will be too noisy to be useful — `extract_style.py`
will warn but proceed.

## After populating

```bash
python tools/extract_style.py --field wgl
# (or just `python tools/extract_style.py` while wgl is the only field —
# tools auto-detect single-field corpora.)
```

then inspect `style-profile/wgl/style_dossier.md`. Hand-edit if any extracted
pattern looks wrong; the dossier is the file the skill actually loads
into Claude's context, so a manual pass is worth it.

## Updating

Add new papers to the appropriate tier and re-run `extract_style.py`.
The skill checks dossier mtime vs corpus mtime; stale dossiers cause
the skill to refuse to run.
