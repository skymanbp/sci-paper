# Changelog

All notable changes to the `sci-paper` plugin. Versions follow the
`plugin.json` / `marketplace.json` `version` field.

## v0.12.0 — 2026-05

- **`paper`** adds top-level writing standard
  **"Structural Updates · Forward Narrative"**: every update / correction /
  iteration must rewrite the paper to its current final state; never
  accrete "tried A, found A wrong, switched to B" patch-style residue in
  the body. Ships with:
  - Forward-narrative (final-state only) requirement.
  - Patch-vs-structural comparison table.
  - A single allowed exception (true external-baseline contrast).
  - 4-question per-paragraph self-check.
- The existing `formula derivation > no shooting-arrow-then-drawing-target`
  rule is now framed as a narrow special case with a back-reference.
- Writing-time dual of `paper-review` §2.O (update-not-accumulate).

## v0.11.0

- **`final-review` nested-sub-agent bug fix.** `paper-review` §4.4 isolated
  MPR was unrunnable when launched inside an `isolation=worktree`
  sub-agent. Resolved by promoting MPR to the `final-review` main agent as
  a dedicated 5th isolated sub-agent (§3.6); `paper-review` gains
  `--no-isolated-mpr` so orchestrators can suppress the nested call.
- **`paper-review` dimension R** — Glossary consistency (canonical-term
  alignment against project `FACTS.md` / glossary; alias / conflict /
  missing detection). Borrowed from `mattpocock-skills:grill-with-docs`.
- **`brainstorm` §2.0 glossary grill prelude** — one-question-at-a-time
  term lock against `FACTS.md` before root-node generation.
- 6 skill descriptions rewritten with explicit "Use when …" triggers per
  `mattpocock-skills:write-a-skill` convention.

## v0.10.0

- **NEW `final-review`** — 5-skill orchestrator for pre-submission final
  pass. Runs `paper` / `paper-review` / `figure-review` / `mainline` /
  `paper-attack-tree` each in its own `isolation: worktree` sub-agent
  every round; merges all issues; applies fixes; loops until consecutive
  N rounds (default 2) show 0 issues across all 5 skills. ITER_BUDGET 10
  rounds by default with `BREAK_WITH_USER_DECISION` on cap hit. No silent
  skipping or premature completion.
- **`paper-review` dimensions P and Q.**
  - **P** — internal development / research / draft language sweep:
    4-class grep for placeholders / draft colloquialisms / experiment-log
    style / internal codenames, replaced with general academic language.
  - **Q** — reference completeness + citation precision: missing-key-
    reference detection via WebSearch + per-`\cite{}` WebFetch
    verification that the cited paper actually supports the citing
    sentence (CORRECT / WEAK / MISUSED / UNVERIFIABLE).
- Convergence criteria extended: `P=0` / `Q-MISUSED=0` /
  `Q-missing-key-ref=0` / `Q-UNVERIFIABLE=0`.

## v0.9.0

- **NEW `paper-attack-tree`** — `brainstorm`'s radial phylogenetic-tree
  methodology applied to paper critique. Each node is one critique
  attacked via 12 framing passes (first-principles / inversion /
  cross-disciplinary reviewer / adversarial red-team / constraint
  variation / scale extrapolation / substitution / office-hours /
  contrarian / failure-driven / high-risk-fatal / meta). Every leaf
  resolved to **CONFIRMED** (`file:line` + proposed fix) / **REFUTED**
  (`file:line` of paper's defense) / **MARGINAL** (author judgement).
  Hard ban on `NEEDS-MORE-INFO` defer. Complements `paper-review` by
  covering open-ended adversarial angles a static checklist misses.

## v0.8.0

- **NEW `mainline`** — structural narrative-spine reinforcer. Mandatory
  full-read (no grep-only / no memory / no guessing). Audits along
  7 positive dimensions (spine sharpening / language compression /
  narrative architecture / isolated readability / derivation completeness
  / logical soundness / chaining) and 8 negative dimensions (vague
  definitions / scattered spine / volume-over-precision / disconnected
  sections / unclear structure / missing academic narrative / context
  drift / low-information adjectives). Explicit brainstorm-divergence
  consolidation pass; forbids transitional-phrase suturing of logical
  jumps; mandatory isolated-context cold-read 7-question readability
  check by an `isolation: worktree` sub-agent. Zero-issue convergence
  hard loop.

## v0.7.0

- **`paper-review` dimensions N and O.**
  - **N** — deep stale / wrong / redundant / drift sweep across 6
    content types + residual-markup grep.
  - **O** — process-artifact removal with **update-not-accumulate** hard
    constraint.

## v0.6.0

- **`paper-review` v3 dimensions K, L, M + isolated MPR.**
  - **K** — host-level `modern-physics-review` (M1–M9) merged in-process.
  - **L** — systemic inconsistency / cross-section context discontinuity.
  - **M** — mathematical / physical adversarial 3-pass.
- On zero-issue convergence, mandatory isolated-context final MPR via
  `isolation: worktree` sub-agent.

## v0.5.0

- **`brainstorm` v0.5** — radial 12-framing idea / problem tree with
  phylogenetic-tree width × depth model and no-defer enforcement.

## v0.4.0

- **NEW `brainstorm`** — fully-automated radial research-direction
  explorer (12 framings; recursive on promising leaves until
  convergence).

## v0.3.0

- **`extract_style.py`**: PDF parsing via `pymupdf` blocks-mode +
  ALL-CAPS heuristic for thematic section detection on top of the
  keyword-based detector.
- **`train_ai_ism_classifier.py`**: paragraph-level AI-ism classifier
  (logistic regression on word 1–2 gram TF-IDF). CV F1 ≈ 0.88 on the
  `wgl` corpus with 20 handcrafted negatives.
- **`ai_ism_lint.py --ai-classifier`** opt-in flag.

## v0.2.0

- **Embedding-based exemplar retrieval** in `retrieve_exemplars.py` via
  sentence-transformers + per-corpus `.npy` cache (rebuilt automatically
  when JSONL is newer). Keyword-overlap fallback via `--allow-fallback`.
- **Tier-graded `ai_ism_lint.py`** with `--summary` per-section density.
- **Multi-field profiles** under `style-profile/<field>/` with
  auto-detection in the single-field case.

## v0.1.0

- Initial plugin scaffold. Skills `paper`, `paper-review`, `figure-review`
  ported verbatim from `weak-gravitational-lensing/.claude/skills/`
  (project-specific anchors marked `[WGL]`).
- `paper-style/SKILL.md` spec + initial `tools/` stubs
  (`extract_style.py`, `retrieve_exemplars.py`, `ai_ism_lint.py`).
- Field-aware corpus / profile layout:
  `style-corpus/<field>/tier-{1-top, 2-mentor, 3-reference}/` ↔
  `style-profile/<field>/`.
