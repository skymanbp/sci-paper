# Changelog

All notable changes to the `sci-paper` plugin. Versions follow the
`plugin.json` / `marketplace.json` `version` field.

## v0.14.0 — Unreleased

**Unified scientific-writing feedback contract.** This release supersedes the
v0.13 de-AI semantics without erasing their historical record. The sole
normative authority is `docs/SCIPAPER_STANDARD.md`; corpus profiles, structural
baselines, UID measurements, and learned models are evidence, not competing
policy or authorship detectors.

- **Typed consequences and measurement states.** New
  `sci-paper.feedback.v1` findings distinguish `integrity_blocker`, `l0_target`,
  and `advisory`, with `measured`, `degraded`, `unmeasured`, and
  `not_applicable` axis states. Missing calibration is never converted to zero
  findings.
- **Feedback, not a universal prose verdict.** The shared workflow is measure →
  type → rank → edit → re-measure → disposition. Strong advisories require an
  explicit author disposition; ordinary advisories remain visible without
  blocking the paper.
- **Narrow L0 semantics.** Tier A lexical occurrences, prose em-dashes, and only
  Tier B occurrences above one use per section and word are rewrite targets.
  `ai_ism_lint.py` exits `0` with no L0 targets, `1` with L0 targets, and `2`
  for invalid input/configuration/execution; advisories never cause exit `1`.
- **Structured analysis.** Added deterministic sentence-template analysis and
  whole-document rhetorical-shape analysis. Complete papers are the independent
  calibration unit for document structure; paragraph exemplars cannot be
  relabelled as independent documents.
- **Claim-first rewrite eligibility.** Rewrite candidates must preserve protected
  numbers, units, citations, mathematics, acronyms, comparison direction,
  negation, and causal direction before ranking. Ineligible candidates receive
  negative infinity and cannot win on style or learned score.
- **Learned evidence renamed and bounded.** The optional learned model reports
  field similarity/compatibility for triage and eligible-candidate ranking, not
  `P(human)`. A bundle without a calibrated operating point remains degraded;
  source, section, length, jargon, and mathematical-density confounds remain
  explicit evaluation requirements.
- **All writing/review skills aligned.** `paper`, `paper-style`, `paper-review`,
  `figure-review`, `mainline`, `paper-attack-tree`, `rewrite-in-voice`, and
  `final-review` implement the same consequence, ranking, disposition, and
  stopping contract. Evidentiary `CONFIRMED` does not automatically mean
  blocker, and bounded-process `CONVERGED` is not a paper-quality verdict.
- **Profile/build boundary documented.** `build_profile.py` now identifies
  itself as a basic descriptive-profile builder. Sentence structure, UID,
  whole-document shape, learned field similarity, hard-set labels, and policy
  operating points have explicit independent build/calibration paths.
- **Validation strengthened.** The repository validator checks manifests,
  registries, skill frontmatter and standard references, normative/evaluation
  document authority, Python syntax/imports, CLI help, schema fields/enums,
  linter exit semantics, Tier B cap behavior, tests, and CI wiring. It rejects
  an active duplicate `docs/EVALUATION.md`; regression tests cover the shared
  schema, linter CLI, document structure, and rewrite eligibility.
- **Real-paper evaluation added.** `EVALUATION.md` records a source-traced,
  proposal-only the manuscript introduction rewrite that removes an announced-list
  template while preserving L0=0 and all protected scientific invariants. The
  manuscript remains unchanged pending author disposition.
- **Independent-review fixes (16 verified findings).** An adversarially
  verified multi-agent review confirmed and this release fixes: undefined F1 on
  positive-free strata now reports `None` and is excluded from aggregation;
  AUC midrank tie handling is regression-tested; the confound-audit threshold
  threads through every stratum breakdown; the scoring side now refuses model
  bundles whose feature names/schema drift from the installed extractor and
  degrades cleanly on corrupt bundles; the model bundle is written atomically
  and carries fingerprint provenance surfaced in findings; an explicitly
  requested unavailable `--field` exits `2`; detector objects carry real
  version and calibration-asset provenance; `strong_advisory` is derived from
  the strength enum (single source of truth); rewrite eligibility is
  bidirectional (invented negation/causal/comparison markers, numbers, units,
  citations, or acronyms disqualify) and protects semantic LaTeX macros;
  rewrite ranking is led by specificity/fidelity with the learned score gated
  to tie-break weight unless its bundle is measured; an uncalibrated voice
  bundle emits rank-based triage (lowest-scoring paragraphs) instead of a
  forbidden universal 0.5 cutoff; grouped-split validation recomputes
  `corpus_cos` against training-only centroids so held-out papers cannot
  inflate their own similarity feature; and the trainer adds an
  author-labelled hard-set stratum plus preemption-safe featurization
  checkpoints for cloud runs. `docs/EVALUATION.md` is now a pointer stub to
  the canonical root record.

Release gates still required before publication: fresh validator/tests,
confound-aware learned-model status, independent code review, clean-checkout
verification, version bump, tag, push, and GitHub release.

## v0.13.0 — 2026-07-11

**Fundamental (non-keyword) de-AI subsystem** — a four-layer capability that
detects and removes the *structural* AI-ness (smoothed per-token surprisal,
homogeneous sentence length, paragraph signposting) that survives keyword
cleaning. Design + guardrails: [docs/DEAI_SUBSYSTEM.md](docs/DEAI_SUBSYSTEM.md).

- **Layer A — `tools/deai_metrics.py`** (model-free): flags sentence-length
  burstiness / connective-opener signposting outside the human-corpus baseline.
- **Layer B — `tools/deai_oracle.py`** (gpt2-large): per-token surprisal / UID
  oracle; flags below-baseline surprisal variance. Calibrated per section.
- **Layer C — `skills/rewrite-in-voice/` + `tools/rewrite_reward.py`**: new
  `/sci-paper:rewrite-in-voice` skill rebuilds flagged paragraphs from their
  claim-graph (claim → fill-in skeleton → author-voice regeneration) instead of
  word-swapping. Best-of-N over a multi-term reward (learned-voice P(human) ×
  number-specificity, gated by relative claim-fidelity) so genuine voice +
  preserved meaning win, never detector-evasion (the AuthorMist→Pangram DAMAGE
  lesson). Human-in-the-loop; optional self-distillation.
- **Layer D — `tools/deai_voice.py` + `tools/train_voice_model.py`**: a learned
  voice/reward model on the *fundamental* features (distributional + surprisal/
  UID + corpus-embedding), not word-ngram TF-IDF. Held-out AUC 0.953 on `wgl`;
  ships LogisticRegression over gradient-boosting for out-of-distribution
  robustness (a reward that scores arbitrary rewrites must stay monotonic — the
  tree model scored a hand-crafted LLM paragraph P(human)=0.99, LR gave 0.003).
- **Training data** scaled + diversified to ~8.2k paragraphs: curated corpus +
  clean pre-2022 arXiv abstracts (broad astro + weak-lensing + authoritative
  authors, via new `tools/fetch_arxiv_abstracts.py`) as human positives;
  Claude-generated 6-register + multi-model RAID abstracts as LLM negatives. A
  controlled source ablation caught and excluded a poisoning source: our own
  de-AI-reviewed drafts read partly human, so mislabeling them AI dropped
  held-out AUC 0.953→0.920 and crossed an OOD fixture to the wrong side.
- **`ai_ism_lint.py`** gains `--distribution` / `--oracle` / `--voice` advisory
  passes, kept out of the exit-code gate (guardrail 2: diagnostic, not gate).
- **Skill integration**: `paper` gains a fundamental-tier note; `paper-review`
  gains dimension **D4** (structural AI-ness → rewrite-in-voice); `mainline` B8
  gains the structural complement; `final-review` inherits D4 via `paper-review`.
- **`paper/SKILL.md` drift fix**: anti-AI-ism corpus provenance re-derived from
  the current 31-paper dossier (was N=16 / 203,251 tokens → N=31 / 230,006;
  em-dash 0.098→0.213 per 1k words, Tier-B frequency table refreshed).
- **`.gitignore`**: trained model artifacts + feature caches (`*.joblib` /
  `*.npz`) ignored per-field (regenerate via `train_*.py`); the
  copyright/privacy-sensitive corpus jsonl stays local, so voice models built on
  unpublished drafts never leak.

## v0.12.1 — 2026-05-25

Structural cleanup release; **no skill behavior changes**.

- **`CHANGELOG.md`** extracted: per-version history pulled out of the
  `plugin.json` / `marketplace.json` `description` fields (which had
  bloated to ~1.4 KB of inline changelog text); both manifests now carry
  a one-line description pointing here.
- **`README.md`** drift fixes: skills table now lists all 8 skills (was 5;
  `mainline` / `paper-attack-tree` / `final-review` were only mentioned in
  prose); new Tools (7) table replaces hand-counted "Tools (6)" (was missing
  `build_profile.py` + `extract_md_negatives.py` + the negatives data file);
  hard-coded `D:/Projects/sci-paper` paths replaced with
  `<path-to-this-repo>` placeholders.
- **`CLAUDE.md`** sanitization: dropped three personal Windows absolute
  paths (`D:/Projects/weak-gravitational-lensing/`, two
  `C:/Users/skyma/...`) in favour of portable descriptions; documented
  the new `CLAUDE.local.md` convention.
- **`CLAUDE.local.md`** added to `.gitignore` (per-machine paths / virtualenvs
  go there; Claude Code reads both, only `CLAUDE.md` is shared).
- **`memory/`** added to `.gitignore`: cc-memory plugin local sqlite +
  private conversation notes. Regenerable; never commit.
- **`style-profile/README.md`** added: documents the generated-artifact
  layout, why per-field subdirs appear empty in git, how to rebuild,
  and the privacy / copyright reason exemplar JSONL is gitignored.
- **`tools/README.md`** table extended from 4 to 7 rows so it matches
  what actually lives in `tools/`; new entry for `validate_plugin.py`.
- **NEW `tools/validate_plugin.py`**: repo-shape sanity checks
  (manifests parse + versions match, every `skills/<name>/SKILL.md` has
  YAML frontmatter with matching `name`, every `tools/*.py` parses).
  stdlib-only; runs in ~50 ms.
- **NEW `.github/workflows/ci.yml`**: invokes the validator on push to
  main and on every PR so the README drift / mismatched-version class
  of bug can't silently reappear.
- **`requirements.txt`**: drop "v0.3 pipeline" anchor so the comment
  doesn't need bumping each release.

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
