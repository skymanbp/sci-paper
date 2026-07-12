# sci-paper plugin — project working directory instructions

## What this project is

A standalone Claude Code plugin for scientific paper writing, rewriting,
review, figure review, adversarial critique, narrative analysis, and research
ideation. `docs/SCIPAPER_STANDARD.md` is the single normative writing standard.
Corpus profiles, structural measurements, UID evidence, and learned
field-similarity models are descriptive or calibrational evidence; they do not
create an authorship verdict or a separate paper gate.

## Working principles for THIS project

1. **One normative contract.** Writing and review skills must implement
   `docs/SCIPAPER_STANDARD.md` and `sci-paper.feedback.v1`. Do not introduce a
   competing consequence vocabulary, universal prose PASS/FAIL gate, or
   authorship claim. Field-specific scientific guidance may remain explicitly
   marked `[WGL]`; do not silently generalize domain facts while changing the
   shared writing contract.

2. **Corpus evidence is read-only input.** The corpus is user-supplied and
   copyright-sensitive; never commit PDFs from `style-corpus/` (`.gitignore`
   excludes them). Treat `style-corpus/<field>/tier-*` as read-only inputs;
   generated evidence belongs under `style-profile/<field>/`. Corpus statistics
   cannot redefine consequence classes or prove authorship.

   **Field-aware layout.** Never assume a specific field exists. Tools/skills
   auto-detect only when exactly one field is present; multi-field corpora
   require explicit `--field <name>`. Add new sources under
   `style-corpus/<new-field>/{tier-1-top,tier-2-mentor,tier-3-reference}/` and
   run `python tools/extract_style.py --field <new-field>`.

3. **Honest measurement states.** Missing calibration, optional dependencies,
   complete-document corpora, or human labels remain `unmeasured` or
   `degraded`. Never convert unavailable evidence into zero findings. Current
   metrics and limitations belong in `EVALUATION.md`, not the normative standard.

4. **Plugin manifest format is verified.** `.claude-plugin/plugin.json` per
   the official Claude Code plugins reference; skills live at
   `skills/<name>/SKILL.md` (NOT inside `.claude-plugin/`). When invoked
   from another project via `--plugin-dir`, skills are namespaced as
   `/sci-paper:paper`, etc.

## Cross-project references

- **Source project:** the sibling `weak-gravitational-lensing` project
  (sci-paper was extracted from its `.claude/skills/{paper, paper-review,
  figure-review}`). Those existing skills are the v0 inputs to this plugin.
  Record your local clone path in `CLAUDE.local.md` (gitignored) if you
  want an absolute reference handy.
- **User's global writing-quality memory** lives in the user-level
  `~/.claude/CLAUDE.md` (Linux/macOS) or `%USERPROFILE%\.claude\CLAUDE.md`
  (Windows). The rule that matters here, verbatim:
  > **Paper writing: never quote from memory.** Every number, date,
  > coefficient, figure caption, and citation in a manuscript edit must
  > be re-read from its source in the same turn it's pasted.

## Toolchain

Python ≥ 3.11 on PATH (developed against 3.13; nothing in `tools/` uses
3.12-only syntax).

Optional capabilities are listed in `requirements.txt`:
- `pymupdf` — PDF corpus extraction and compiled-page inspection
- `sentence-transformers` — exemplar retrieval and embedding features
- `scikit-learn` + `joblib` — legacy and learned field-similarity models
- `transformers` + `torch` — optional token-surprisal / UID measurement
- `numpy` — learned feature, cache, and rewrite-score utilities

The shared schema, deterministic L0 linter, model-free L1/L2 axes, and validator
remain standard-library paths. Missing optional dependencies must stay visible as
`unmeasured` or `degraded`.

## Personal / machine-specific notes

Put paths, virtualenv locations, or anything else that shouldn't go to
the public repo in `CLAUDE.local.md` next to this file. That filename
is gitignored on purpose — Claude Code reads both, but only this file
is shared.
