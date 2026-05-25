# sci-paper plugin — project working directory instructions

## What this project is

A standalone Claude Code plugin for scientific paper writing + review,
extracted and generalized from the `weak-gravitational-lensing` project's
`.claude/skills/{paper, paper-review, figure-review}` skills, plus a new
`paper-style` skill that adds **corpus-driven style distillation** (RAG-for-
style; not actual model fine-tuning — Anthropic does not offer Claude
fine-tuning, see EVALUATION.md).

## Working principles for THIS project

1. **The three ported skills are v0.** They contain weak-gravitational-lensing
   project specifics (NFW, ACSDM, S/N maps, kappa, escnn library refs).
   Generalization is a separate task — do NOT silently rewrite them while
   working on something else. Mark project-specific anchors with `[WGL]`
   comments when you find them.

2. **`paper-style` is the headline feature.** The corpus is user-supplied and
   copyright-sensitive; never commit PDFs from `style-corpus/` (`.gitignore`
   already excludes them). Treat any contents of `style-corpus/<field>/tier-*`
   as read-only inputs; write only to `style-profile/<field>/`.

   **Field-aware layout.** v0.1 ships only `wgl`. Tools/skills auto-detect a
   single-field corpus; multi-field corpora require explicit `--field <name>`.
   When extending, add subdirs under `style-corpus/<new-field>/{tier-1-top,
   tier-2-mentor,tier-3-reference}/` and run
   `python tools/extract_style.py --field <new-field>`.

3. **Honest about limits.** When asked "can we fine-tune Claude?", answer
   "no, but here's what we can actually do" — see EVALUATION.md for the
   reasoning. Do not pretend the LoRA path works.

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

Required for the full feature build (pinned in `requirements.txt`):
- `pymupdf` — PDF text extraction
- `sentence-transformers` — exemplar retrieval embeddings
- `scikit-learn` — optional sentence classifier
- `regex` (the third-party one, not stdlib `re`) — Unicode-aware sentence segmentation

## Personal / machine-specific notes

Put paths, virtualenv locations, or anything else that shouldn't go to
the public repo in `CLAUDE.local.md` next to this file. That filename
is gitignored on purpose — Claude Code reads both, but only this file
is shared.
