# De-AI subsystem architecture (current as of v0.27.1)

## 1. Purpose

The subsystem improves scientific prose without treating authorship detection as
the objective. It analyzes how information is distributed, how sentences and
paragraphs are built, how sections relate across a document, and whether a rewrite
preserves the scientific claim.

The normative authority is [`SCIPAPER_STANDARD.md`](../SCIPAPER_STANDARD.md). This
document explains the implementation. Corpus dossiers, learned models, thresholds,
and evaluation results are evidence. They cannot redefine the standard.

## 2. Design constraints

1. **Scientific integrity outranks style.** A rewrite that changes a number, unit,
   citation, equation, comparison direction, negation, causal direction, or other
   protected claim content is ineligible.
2. **Feedback drives action.** Prose does not receive a universal PASS/FAIL or
   human/AI verdict. The workflow measures, types, ranks, edits, re-measures, and
   records a disposition.
3. **Unavailable evidence remains visible.** Missing calibration or model assets
   produce `unmeasured` or `degraded`, never an implicit zero.
4. **Calibration uses the right independent unit.** Paragraph evidence calibrates
   paragraph axes. Complete papers calibrate document axes. Paragraphs from one
   paper must not be represented as independent papers.
5. **Learned scores are field-similarity evidence.** They may prioritize inspection,
   but they do not prove authorship and do not determine L0 status.
6. **The implementation is shared.** Writing, review, rewriting, final review, and
   adversarial review consume the same feedback vocabulary and consequence rules.

## 3. Consequence model

Every finding uses one of three consequence classes.

### `integrity_blocker`

A scientific contradiction, unsupported value, source mismatch, invalid statistic,
broken required build, leakage, or missing required artifact. These are mandatory
repairs or explicit user decisions. They are never waived as style preferences.

### `l0_target`

A narrow deterministic rewrite target:

- Tier A lexical occurrence;
- em-dash occurrence;
- Tier B occurrence above the cap of one occurrence per section and word.

The target count is reduced to zero during editing, but an L0 target does not imply
that the manuscript is scientifically invalid.

### `advisory`

Evidence about information distribution, sentence construction, document shape,
field similarity, clarity, rhetoric, or aesthetics. Strong advisories require an
author disposition. Ordinary advisories remain visible and may be acted on,
accepted, or rejected as false positives.

## 4. Shared data contract

[`../tools/deai_feedback.py`](../../tools/deai_feedback.py) implements
`sci-paper.feedback.v1`. A finding carries:

- a stable content-derived `finding_id`;
- consequence `kind` and analysis `layer`;
- `rule`, `scope`, and source `location`;
- observed and reference evidence;
- normalized distance and confidence where applicable;
- `measurement_status`;
- strength and strong-advisory state;
- deterministic priority;
- recommended action and detector provenance;
- source trace, disposition, and before/after evidence.

Allowed measurement states are:

- `measured`;
- `degraded`;
- `unmeasured`;
- `not_applicable`.

Allowed author dispositions are:

- `pending`;
- `acted`;
- `accepted`;
- `rejected_as_false_positive`.

Findings are ranked lexicographically by consequence, strength, layer, reader
exposure, calibrated distance, confidence, and a stable source tie-break. The same
ranked report drives both text and JSON output.

## 5. Measurement layers

### L0: lexical and punctuation targets

[`../tools/ai_ism_lint.py`](../../tools/ai_ism_lint.py) implements the canonical
Tier A, em-dash, and Tier B cap rules. Corpus-zero vocabulary is advisory because a
field corpus can be incomplete.

The command-line exit contract is deliberately narrow:

- `0`: no L0 target, regardless of remaining advisories;
- `1`: one or more L0 targets;
- `2`: invalid input, configuration failure, or execution failure.

[`../tools/deai_register.py`](../../tools/deai_register.py) adds a second lexical
axis at this layer that never joins the to-zero set. It asks whether the draft
speaks its own field's vocabulary, by comparing terms the manuscript leans on
(≥ 5 uses) against document frequency in the field's own corpus. The evidence is
frequency, never a curated list of a neighbouring discipline's words, because a
list cannot separate `AUC` (1 corpus passage) from `epoch` (402) and `accuracy`
(774). Three constructions are handled rather than thresholded: hyphenated
compounds are judged by their rarest part, `\mathrm{}` preceded by `_` or `^` in
a macro body is a subscript decoration rather than a term, and possessives fold
onto the bare term. Macro bodies are read because the shared reduction erases
macro-bound vocabulary entirely. Findings are always advisories.

### L1: information distribution

[`../tools/deai_metrics.py`](../../tools/deai_metrics.py) measures section-aware
sentence-length variation and paragraph-opening connective density. A compatibility
heuristic may produce degraded evidence. A strong advisory requires an applicable
calibrated policy and sufficient reference support.

[`../tools/deai_oracle.py`](../../tools/deai_oracle.py) optionally measures token
surprisal and Uniform Information Density features. Missing model assets leave the
axis unmeasured. The compatibility `FLAG_Z` remains degraded until field calibration
provides an operating point with provenance and uncertainty.

### L2: sentence and paragraph construction

[`../tools/deai_structure.py`](../../tools/deai_structure.py) detects deterministic
structural patterns that keyword replacement cannot repair:

- announced enumeration and ordinal runs;
- repeated modal frames;
- parallel or anaphoric runs;
- setup, list, and wrap-up symmetry;
- balanced closers;
- repeated paragraph templates.

These are advisories. A detector match identifies a construction to inspect; it does
not establish that the construction is wrong or machine-generated.

### L2: salience hierarchy

[`../tools/deai_salience.py`](../../tools/deai_salience.py) measures whether a
passage ranks the quantities it reports or recites them. Sentence templates and
document shape are both silent here: prose can vary its sentence lengths, sit
inside the human dispersion band, and still hand the reader an undifferentiated
inventory of results.

The measured quantity is deliberately not numeric density, since a quantitative
abstract is supposed to carry numbers. It is how far the numerals run without an
interpreting sentence between them, alongside density and per-sentence numeral
count as supporting features. Calibration is per section bucket from the field's
own passage banks, at one shared unit, and the reading is P(X ≤ x) against a 0.01
quantile grid taken at the top of any tie plateau — two of the three features are
ratios of small integers, so their reference distributions are tie-heavy and a
coarse grid or a lower-edge reading swallows exactly the passages the axis exists
to find. Where a reference has no spread above the advisory gate the feature
abstains rather than reporting an ordinary passage as the 100th percentile.

This detector is the sole consumer of
[`extract_style.latex_to_numeral_text`](../../tools/extract_style.py), the second
LaTeX projection. `latex_to_plain` replaces every math span with `[math]`, which
is right for lexical and shape statistics and zeroes every numeral signal on
`.tex` input; the numeral-preserving projection shares the same pattern set and
differs only in what happens inside an inline math span. Displayed equations are
dropped by both.

### L2: whole-document rhetorical shape

[`../tools/deai_docstructure.py`](../../tools/deai_docstructure.py) measures shape similarity:

- `within_section_similarity`;
- `cross_section_similarity`;
- `section_arc_similarity`.

Since the 2026-07-13 keystone it also carries the detection core that the axis actually
scores on: cross-paragraph dispersion as a joint Mahalanobis manifold fit pooled and per
length stratum (`fit_dispersion_manifold`, `manifold_distance`), role-coupled dispersion
(`document_role_coupling`), and split-conformal (Mondrian) operating points.

Document calibration records one observation per verified complete paper, bootstrap
uncertainty, leave-one-document-out human flag behavior, and empirical percentiles.
If the corpus does not contain enough complete and measurable papers, the axis is
`unmeasured`; for `wgl` it is `measured` on a 14-paper calibration (EVALUATION §9). The
implementation must not synthesize a document baseline from paragraph exemplars.

### L3: learned field similarity

[`../tools/deai_features.py`](../../tools/deai_features.py) exposes reusable
model-free, UID, and embedding features.
[`../tools/train_voice_model.py`](../../tools/train_voice_model.py) trains the optional
model, and [`../tools/deai_voice.py`](../../tools/deai_voice.py) reports its result as
field-similarity triage.

A bundle without a documented calibrated operating point is degraded. Evaluation
must separate source-paper groups and audit mathematical-placeholder density,
jargon density, section type, and paragraph length. The mathematical-density
confound is unresolved until the evidence in `EVALUATION.md` demonstrates otherwise.

The per-paragraph learned classifier is an **offline audit instrument, not a
product detector one calibration away from an operating point**: the paragraph
unit is near-unjudgeable for AI-ness (perceptual AUC 0.444, EVALUATION.md §7), and the document-level
surprisal path is now measured (EVALUATION.md §9.8) to be weaker than the
model-free manifold and to add nothing to it. Accordingly, `make_finding` carries
a `calibration_unit` (paragraph|section|document) that structurally caps
paragraph-unit findings at 0.5 confidence; `deai_voice` emits at paragraph unit
and is capped by construction, so a per-paragraph score can never present as a
high-confidence AI verdict.

## 6. Claim-first rewriting

The `/sci-paper:de-ai` skill (Pass 3) does not polish the original sentence in
place by default. It reconstructs prose from the scientific argument:

1. extract claims, evidence, scope, stance, and logical relations;
2. build a prose-independent skeleton;
3. generate candidates using field exemplars as descriptive anchors;
4. reject candidates that fail scientific-fidelity eligibility;
5. rank eligible candidates with L0 advisory reduction (signed, fidelity-floored),
   structural, distributional, and optional learned evidence;
6. re-measure the selected rewrite and record before/after findings;
7. disposition every strong advisory and retain ordinary residual advisories.

[`../tools/rewrite_reward.py`](../../tools/rewrite_reward.py) protects numbers, units,
citations, inline mathematics, uppercase acronyms, comparison direction, negation,
and causal direction. An ineligible candidate receives a combined score of negative
infinity and cannot win. If no candidate is eligible, rewriting stops instead of
selecting a scientifically altered sentence.

## 7. Skill integration

All active writing and review skills implement the same standard:

- `paper` writes against the consequence and measurement vocabulary;
- `de-ai` chains subsystem measurement (Pass 1), the vendored humanizer
  structural-tell audit (Pass 2), and claim-first reconstruction with hard
  fidelity eligibility (Pass 3); it treats corpus profiles as descriptive
  evidence, never competing policy;
- `condense` executes the standard's §5.3 condensation policy with
  one-canonical-home deduplication, closed by the length gate;
- `paper-review` emits typed, source-traced findings across its review
  dimensions, including the narrative-spine protocol (dimension E, which never
  requires exactly one narrative spine) and adversarial escalation
  (dimension M);
- `figure-review` separates scientific/build contradictions from readability and
  aesthetic advisories;
- `final-review` merges stable findings from isolated reviewers and verifies a
  disposition-complete state rather than demanding zero advisories;
- `proposal-polish` applies the same fidelity-first rewrite contract to
  proposal and application prose.

`brainstorm` is pre-draft ideation; it loads the field dossier but is not a
normative implementer of this standard (see `validate_plugin.py`
`NORMATIVE_SKILLS`).

`CONFIRMED`, `REFUTED`, and `MARGINAL` in the escalation record describe whether a
critique survived evidentiary verification. They do not select its consequence class.
`CONVERGED` may describe the completion of a bounded search or review process. It is
not a claim of perfect prose, human authorship, scientific infallibility, or journal
acceptance.

## 8. Isolation architecture

`final-review` owns isolated child execution. Nested agents are unsupported, so the
parent passes explicit interface flags:

- `paper-review --no-isolated-mpr` (its dimension-M escalation is in-process by
  design and never spawns);
- `de-ai --audit-only` (measurement + audit, no rewrite, no spawning).

The parent launches the modern-physics reviewer as a sibling isolated agent. Child
review coverage is preserved in the current isolated process rather than silently
reduced.

## 9. Calibration artifacts

A field profile may contain:

- descriptive corpus statistics and exemplars;
- L1/L2 calibrated reference distributions;
- a complete-document structure baseline;
- learned-model bundles and operating points;
- `deai_policy.json` with provenance, sample unit, uncertainty, and applicability.

A policy asset must state what was measured, the independent unit, the corpus
selection rule, sample size, uncertainty method, and validation behavior. If any
required provenance is absent, the consumer reports degraded or unmeasured evidence.

Current effect sizes, model scores, corpus counts, and threshold performance belong
in [`EVALUATION.md`](EVALUATION.md), not this architecture or the normative
standard.

## 10. Validation and release boundary

[`../tools/validate_plugin.py`](../../tools/validate_plugin.py) checks:

- manifest, README, and CHANGELOG version agreement;
- skill frontmatter and standard references;
- stale review-contract markers;
- README and manifest skill/tool counts;
- exact README product-tool registry;
- Python syntax and core imports;
- core command-line entry points;
- shared schema fields and allowed enums;
- linter exit and Tier B cap semantics;
- normative/evaluation document authority boundaries;
- required tests and CI wiring.

The authoritative check list is `validate_plugin.py` itself (`tools/README.md`
mirrors it); this summary is descriptive.

CI also runs the unit and CLI test suite. A release additionally requires an
independent code review, a clean-checkout verification, release metadata updates,
and successful tag/push/release operations.

## 11. Evidence still required (open items; heading written at v0.14.0)

The implementation can ship with explicit unavailable axes, but it must not imply
that missing evidence exists. Before release, the evaluation record must state the
status of:

1. a real introduction rewrite with before/after structural findings and protected
   invariant verification;
2. learned-model audits for mathematics, jargon, section, length, and source-paper
   confounds;
3. complete-document calibration, or an explicit `unmeasured` document axis if a
   verified corpus is unavailable;
4. UID and learned-model operating points, including degraded status when not
   calibrated;
5. author labels and editorial dispositions that remain external human inputs.
