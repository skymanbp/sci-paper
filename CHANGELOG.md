# Changelog

All notable changes to the `sci-paper` plugin. Versions follow the
`plugin.json` / `marketplace.json` `version` field.

## v0.25.0 — 2026-08-06

Hardening patch on the v0.24.0 consistency release.

- **Validator: versioned doc headers are now gated.** `check_manifests`
  additionally requires the header lines of `docs/DEAI_SUBSYSTEM.md` and
  `docs/EVALUATION.md` to carry the current release version — the one
  surface the v0.24.0 sweep missed (two stale `v0.23.0` headers shipped
  and were fixed post-tag in `475f632`). The class of miss is now a
  release blocker instead of a review catch.
- **Full-repo debug round (all green, recorded here as the release
  gate):** validator 8/8; 115 unit/CLI tests; 33/33 tracked `.py`
  compile; 22/22 tool `--help` entry points exit 0; zero TODO/FIXME and
  zero bare `except:`; all tracked JSON parses; 20 markdown files with
  zero broken relative links; linter exit semantics re-verified on true
  process exit codes (Tier A fixture exits 1 with the `tier-a:delve`
  target present).

## v0.24.0 — 2026-08-06

Documentation-consistency release: two audit rounds (2026-08-06) drove
every finding to closed; no behavior change to the L0 linter or the
measurement axes.

- **Docs single-sourcing.** The validator check list is now authoritative
  in `validate_plugin.py` with descriptive mirrors marked as such
  (`README.md`, `docs/DEAI_SUBSYSTEM.md`); the de-ai/condense boundary
  block has one canonical home (`de-ai` SKILL.md §0); the product-tool
  registry ownership is stated (`README.md` machine-checked,
  `tools/README.md` adds calibration/failure detail).
- **Contradictions closed.** `brainstorm` is now explicitly the one
  non-normative skill in both `SCIPAPER_STANDARD.md` §7 and
  `docs/DEAI_SUBSYSTEM.md` §7 (matching `NORMATIVE_SKILLS`);
  `extract_style.py` no longer invites hand-editing generated evidence;
  stale v0.14.0 anchors in `DEAI_SUBSYSTEM.md` §11 and `EVALUATION.md`
  §12 are dated or superseded by the current release-gate record;
  perceptual AUC unified at 0.444 (EVALUATION §7).
- **Command fixes.** The whole-document calibration command in
  `tools/README.md` now matches the real CLI (`--field` + `--calibrate`
  `--corpus-dir`); the dead cross-repo link in `EVALUATION.md` §11 is a
  commit-pinned citation.
- **Registry completeness.** `style-profile/README.md` layout now lists
  `voice_model_evaluation.json`, `anchoring_baseline.json`, negative/extra
  banks, and `docval/`, and documents the second populated field
  (`wgl-letter`, 11-paper Letter-register corpus, built 2026-07); the
  `figure-review` frontmatter carries `disable-model-invocation` and an
  `argument-hint` like every other skill.
- **Tool hygiene.** The validator's exit-2 fixture no longer leaks a
  spurious stderr line above the first `[ok]`; `deai_metrics._bucket_for`
  narrows its exception guard with a stated reason.

## v0.23.0 — 2026-07-18

Skill consolidation: 11 skills become 8 mutually orthogonal directions.
The three de-AI surfaces merge into one `de-ai` skill, the two review
augmenters fold into paper-review dimensions, and a new `condense` skill
becomes the §5.3 action surface.

- **New skill `de-ai`.** Merges `academic-humanizer` (the Layer 1--5
  structural-tell catalog with patterns 2.12--2.16 and the Pass-2
  self-interrogation, both MIT upstreams credited), `rewrite-in-voice`
  (the claim-first rewrite engine with hard fidelity eligibility and the
  §5.3 length gate), and `paper-style` (field-corpus calibration, dossier
  freshness, exemplar retrieval) into one three-pass pipeline:
  measure (L0--L4) -> humanizer audit -> claim-first rewrite.
  `--audit-only` runs passes 1--2 for review integration; `--no-apply`
  proposes without writing.
- **New skill `condense` (精简).** Whole-document elimination of all
  unnecessary and cross-document duplicated content, executing the
  standard's §5.3 policy: delete > condense-in-place > same-length
  rewrite, growth only with recorded justification;
  one-canonical-home-per-fact deduplication with a genre carve-out for
  abstract/conclusion restatement; loop-until-dry convergence; the length
  gate closes every pass. Redundancy detection stays in paper-review
  dimension I; condense executes the fixes.
- **paper-review absorbs `mainline` and `paper-attack-tree`.** Dimension E
  gains the narrative-spine protocol (purpose record, contribution graph,
  cold-read questionnaire, multi-contribution legitimacy); dimension M is
  sub-structured into M.1 (the existing three-pass derivation
  verification) and M.2 (the 12-framing radial escalation with S/P/R/F/B
  scoring and CONFIRMED/REFUTED/MARGINAL verdicts, no deferred leaves,
  in-process by design); dimension D's structural-tell audit now invokes
  `de-ai --audit-only`. A--R lettering unchanged.
- **final-review re-orchestrates to four isolated reviewers.**
  paper-review, figure-review, the `de-ai --audit-only` audit, and the
  parent-level modern-physics review. `condense` is positioned as an
  action skill on dimension-I findings, not a fifth review lane.
- **figure-review gains pixel-measured canvas balance (§2.4.1).**
  Opposing outer margins must agree within max(2 px at 150 DPI, 1% of the
  canvas width); fixes go to the generator (right pad = measured left
  axis-title + tick column), never to an absolute nudge.
- **SCIPAPER_STANDARD v3.4.** Records the consolidation and rebuilds the
  §7 responsibility table as a complete 8-row registry; no policy in
  §§0--6 or §§8--11 changes. Docs, tool strings, and directory READMEs
  re-point to the surviving skills; both MIT attributions survive in the
  README Acknowledgments and the `de-ai` provenance block.

## v0.22.0 — 2026-07-18

`academic-humanizer` absorbs the academically-relevant structural tells
from blader/humanizer (MIT), a second upstream after the AIScientists-Dev
port in v0.21.0.

- **Five new Layer-2 structural patterns (2.12--2.16).** False ranges
  (categorical "from X to Y"), aphorism formulas ("X is the Y of Z"
  epigrams), persuasive-authority tropes ("at its core", "fundamentally"
  as empty emphasis), manufactured staccato drama (runs of terse fragments),
  and hyphenated-pair predicate overuse ("the result is model-dependent").
  Each is framed as structural, not lexical, and carries a corpus caveat so
  genuine quantitative ranges, formal definitions, real physical
  distinctions, single emphatic sentences, and attributive compound
  modifiers are never flagged.
- **Pass-2 self-interrogation step (Process §3.5).** After the first
  rewrite of a span, ask "what still reads as machine-written here?",
  answer in 2--4 concrete bullets, and apply one further targeted rewrite
  that re-clears the fidelity and length gates. Neutral-and-precise stays
  the target; the pass strips tells, it does not manufacture voice.
- **False-positive guards added to Layer 3.** Formal vocabulary alone, a
  single mixed register, isolated curly quotes, a lone emphatic short
  sentence, and text inside quotations / caption labels / worked examples
  are explicitly not tells.
- **What was NOT adopted.** blader/humanizer's blog/chat-specific patterns
  (emoji, title-case headings, chatbot artifacts, curly-quote flags) and
  its `landscape`-flagging word list are deliberately excluded; they
  conflict with the plugin's corpus evidence (`landscape` is a measured
  legitimate astro term). Attribution added to the SKILL provenance header
  and README Acknowledgments.

## v0.21.0 — 2026-07-17

The academic-humanizer becomes a standalone skill, paper-review gains a
per-round structural audit step, and the documentation tree is consolidated.

- **New skill `academic-humanizer` (11th skill).** Whole-repo port of
  AIScientists-Dev/academic-humanizer v0.3.3 (MIT; attribution retained):
  Layers 1--5 as a standalone audit-then-rewrite pass. Adaptations over
  upstream: corpus overrides are normative (landscape never flagged;
  demonstrate/significantly evidence-conditional only), rewrites must pass
  the fidelity and length gates, Layer 6 routes to the existing
  `proposal-polish` skill instead of being duplicated, and lexical tells
  defer to `ai_ism_lint.py` Tier A/B rather than re-deriving a word list.
  Field-validated before porting: a standalone audit run on a live
  manuscript found seven true positives (two colon-elaborations that the
  per-line linter regex misses at line breaks, three comma-splice
  run-ons, one Layer-1 lexical hit, one dense results sentence).
- **paper-review §D structural-tell audit step.** Every review round now
  runs the humanizer Layers 1--2 checklist (clause-stacking, negative
  parallelism, elegant variation, rule-of-three, formulaic openers,
  connective runs) in audit-only mode; structural hits are advisories,
  Layer-4 claim-evidence hits join §C as `integrity_blocker`.
- **Docs consolidated.** The canonical `EVALUATION.md` moved from the
  repository root into `docs/` (replacing the redirect stub that pointed
  the other way); all path references updated (README, standard,
  subsystem, roadmap links). `docs/` is now the single home for all five
  documentation files.

## v0.20.1 — 2026-07-16

Post-release independent audit of the v0.20.0 length gate (7 findings, all
dispositioned; the two High items were real defects in orchestration use).

- **JSON report is now self-describing.** `length_gate.py --format json`
  embeds a `length_budget` block (totals, justified growth,
  `net_unjustified_growth`, `tolerance_words`, `gate_exit`), so a downstream
  orchestrator derives the gate result from the report alone instead of
  parsing stdout or trusting the process exit.
- **Allowance accounting matches the documented net formula.** Every allowed
  positive section delta is credited to `justified_growth`, including growth
  below the per-section flagging tolerance; previously an allowed
  sub-tolerance growth was not credited and could flip a compliant edit to
  exit 1.
- **Ambiguous `--allow` keys are a configuration error (exit 2)** instead of
  silently authorizing every matching section.
- **Heading stripper covers `\\section[short]{long}` and one level of nested
  braces**, keeping renames of those forms budget-neutral.
- Registry/skill wording aligned with shipped behavior (net-exit semantics in
  the top-level README; rewrite-in-voice ranking terms name L0 advisory
  reduction, fidelity, voice, condensation, with specificity
  transparency-only).
- New tests: allowance-tolerance interaction, ambiguous key, optional-argument
  heading rename, self-describing JSON, empty-original budget, and three
  mocked `rank()` integration cases (-inf over budget, `allow_growth` lift,
  fidelity-floored condensation bonus). Suite: 115 tests green.

## v0.20.0 — 2026-07-16

§5.3 (condense, do not accumulate) gets mechanical enforcement. Standard bumped
to **v3.3**. Design: prevent at candidate time, detect at loop close, and make
recorded justification the only path for growth — three layers, all auditable.

- **New tool `length_gate.py` (tools: 21 → 22), the loop-close delta gate.**
  Compares per-section rendered-prose word counts (comments and math excluded
  via `latex_to_plain`) between the pre-edit baseline (`--before <snapshot>` or
  `--git-ref <ref>`) and the edited file. Each unjustified growing section
  emits a strong advisory `length-growth:<section>` (strong advisories already
  require an explicit disposition before a loop may close); `--allow
  "<section>=<reason>"` (case-insensitive, substring-tolerant) /
  `--allow-total <reason>` convert it to an ordinary
  `length-growth-justified` advisory that carries the recorded reason into the
  report. The exit code gates the NET budget: 0 when total growth minus
  justified growth is within `--tolerance-words`, 1 beyond it, 2 for invalid
  input (negative tolerance, empty reason, missing baseline) or execution
  failure; a pure section rename nets to zero. Registered in standard §0.1.
- **`rewrite_reward.py` length-budget hard gate (candidate time).** New
  `--original <paragraph>` input: a candidate longer than the original scores
  `-inf` regardless of style evidence (`length_eligible` joins fidelity in the
  eligibility conjunction); `--allow-growth <reason>` lifts the gate for one
  run and prints the reason; within budget a `CONDENSATION_WEIGHT` bonus
  prefers the shorter of otherwise-equal candidates. CLI prints a
  `words(o/c)` column and the over-budget diagnosis.
- **Contract wiring.** Standard §5.3 enforcement paragraph + §0.1 exit
  exception + §8 tool row; `paper-review` §1 snapshot step (6b), §4 step 8
  (gate must exit 0 before the loop closes), §6 report length-budget row, §7
  stopping condition; `rewrite-in-voice` §2.1 saves `original.txt`, §2.4
  passes `--original`; `paper` mirror notes the two mechanical gates.
- Section headings are stripped before counting, so a section rename cannot
  register as prose growth; independent review (2 accepted defects, net-exit
  redesign, substring `--allow`, UTF-8-lossy git baseline, input validation)
  is folded in.
- New tests: `tests/test_length_gate.py` (10 CLI cases: shrink, unjustified
  growth, justified growth, comment/math exclusion, shared JSON schema,
  missing-baseline / negative-tolerance / empty-reason failures, rename
  netting, substring allowance) and 3 `length_budget` unit cases. Suite: 107
  tests green.

## v0.19.0 — 2026-07-16

Academic-humanizer integration (github.com/AIScientists-Dev/academic-humanizer,
MIT; acknowledged in README) plus the condense-not-accumulate rule. Standard
bumped to **v3.2**.

- **New normative rule §5.3 — condense, do not accumulate（改写、删减、精简，
  而不是堆叠）.** The default direction of every edit is shorter: delete >
  condense in place > same-length rewrite > growth; growth is legitimate only
  for author-requested content or source-verified scientific necessity. The
  explanatory patch (appending a clarification to flagged text instead of
  rewriting it) is the canonical violation. Fix loops report a per-passage
  length delta; clearing a detector signal by inflating prose is a defect.
  Mirrored in `paper` (writing), `paper-review` §4 (fix loop), and
  `rewrite-in-voice` §2.3/§2.5 (candidate constraint + re-measure check).
- **Proposal routing note in `paper-review`:** funding proposals are reviewed
  under the `proposal-polish` register; the L0 policy and §6 invariants carry
  over, paper-mode significance trimming does not.

- **Lexicon extensions, corpus-verified.** `LLM_TYPICAL_WORDS` gains
  `underscore*`, `intricate`, `tapestry`, `testament`, `pivotal`, `foster*`,
  `realm*`; profiles regenerated for both fields. Zero-in-both-corpora words
  (`underscore*`, `tapestry`, `testament`, `pivotal`, `realm*`) enter Tier A
  (linter `TIER_A_PATTERN` + `skills/paper/SKILL.md` canonical table);
  `intricate` (1 hit per corpus) and `foster*` (1 hit in wgl) enter Tier B.
  `landscape` deliberately NOT adopted (legitimate domain term, 192 hits in the
  combined corpus); blanket `demonstrate`/`significantly` bans NOT adopted
  (0.147/1k and 0.274/1k in astro corpora — evidence-conditional rules instead).
- **New linter rules** (all advisory): `ing-tail` (curated participial-tail verb
  set, L2), `colon-elaboration` (appositive-elaboration prose colon, L2; user
  style rule 2026-07-16 — caption tags and list specifications stay legitimate),
  and `serves as` added to the `style-substitution` set (L0 advisory).
- **Claim–Evidence Discipline** section in `skills/paper/SKILL.md` (QD;
  operationalizes the existing claim-evidence `integrity_blocker` class):
  unbacked claim → evidence pointer or soften; verb strength ≤ evidence
  strength; vague magnitude → attributed number or range; compare against the
  strongest baseline; `significantly` requires an accompanying test or number.
  Mirrored as a review-side item in `paper-review` §2.C.
- **Preserve List** (anti-over-correction guard) in `skills/paper/SKILL.md`:
  evidence-tied hedging, actor-irrelevant passives, first-person plural,
  definitions/symbols/citations stay; strengthening a hedged verb is itself a
  claim-evidence defect. Mirrored in `paper-review` §2.D.
- **New skill `proposal-polish` (skills: 9 → 10).** Funding-proposal editing
  mode adapted from academic-humanizer Layer 6: NSF/NIH structural anatomy,
  first-pages primacy, proposal-specific weak moves (vague importance,
  method-as-aim, dominoed aims, ambition-without-feasibility, boilerplate
  broader impacts, hedged central hypothesis), preserve-and-deploy craft list,
  claim ↔ feasibility discipline, and hard anti-fabrication rules.
- New tests: 5 CLI cases (`tier-a:pivotal`, `ing-tail`, `colon-elaboration`
  with `\ref{fig:...}` exemption, `style-substitution:serves as`, Tier B
  `intricate` cap). Suite: 93 tests green.

## v0.18.0 — 2026-07-14

Panel-validated release: a blind A/B perceptual panel on a real 31-page ApJ
draft (three versions of the same document under a mechanical fidelity gate)
surfaced a second stratum of machine-writing tells and validated the reading
protocol for perceptual scores. Standard bumped to **v3.1**.

- **New auxiliary L2 template families in `deai_structure`** (panel-derived,
  corpus-calibrated): `antithesis-cluster` (2+ contrastive "X rather than Y" /
  "not X but Y" frames in one paragraph; human base rate 0.2% of 1,957 wgl
  paragraphs vs 5.6% in the audited drafts, a 28x separation) and
  `short-reversal` (a reversal sentence of 5 words or fewer, e.g. "It would
  not."; human base rate 0/1,957). Both emit ordinary advisories under the new
  `structure-auxiliary:<bucket>` rule and are **excluded from `template_score`**,
  so the calibrated document-dispersion manifold consumed by
  `deai_docstructure` is unchanged. `structure_baseline.json` recalibrated with
  the new per-bucket fractions (`auxiliary_frac`, `antithesis_cluster_frac`,
  `reversal_frac`).
- **Blind perceptual panel recognized as an L2 validation instrument**
  (standard §2 L2): independent cold-read judges score `ai_feel_1to5` and must
  name tells with verbatim quotes. The normative reading is **tell-inventory
  turnover, not the mean score** — judges saturate on the most visible tell
  family, so removing it exposes the next stratum at a similar score.
- **EVALUATION §13: the case study.** Three versions paneled at mean scores
  2.0 / 2.0 / 2.25 while the top tell named turned over completely (announced
  enumeration 4/4 judges → 0/4 after the de-scaffold rewrite). The upgraded
  detector cross-validates the panel: template findings 8→0→0, auxiliary
  findings 4→6→1 across pristine / Phase A / targeted-revision versions.
- **Aphoristic "perform rigor" closers** documented as a panel-advisory class
  (no reliable lexical pattern; handled by rewrite instruction, not a
  detector).
- New test module `tests/test_deai_structure.py` (6 tests: cluster detection,
  reversal detection, clean-prose negative, sub-threshold negative,
  `template_score` isolation, finding-rule emission). Suite: 88 tests green.

## v0.17.0 — 2026-07-13

Normative-standard release: `docs/SCIPAPER_STANDARD.md` is updated to **v3** and
is now the complete de-AI standard. There is no separate de-AI standard document
— the sci-paper standard includes it.

- **The de-AI subsystem is fully specified in the single authority.** v2 predated
  the v0.13–0.16 buildout; v3 adds the document-scale detection core (per-stratum
  dispersion manifold, role-coupled dispersion, split-conformal operating points),
  the L2 claim-anchoring writing-quality band, the offline-audit-instrument status
  of the L3 learned classifier, and the cooperative L4 repair layer
  (`deai_partition`, `deai_provenance`, `deai_personal`) — each with its axis,
  measurement state, and confound status.
- **`calibration_unit` is now in the finding contract (§3).** The paragraph
  confidence cap is stated normatively: a single paragraph is near-unjudgeable, so
  paragraph-unit findings are structurally capped at 0.5; `null` is uncapped.
- **New: the de-AI-ization procedure (§5.2, 去AI化步骤).** An ordered,
  layer-by-layer normative procedure for removing machine-writing regularity —
  L0 to zero, L1 distribution, L2 sentence and document structure (via
  fidelity-free partition), L4 anchoring and voice, the confound-free
  provenance/personal self-checks, then invariant-protected re-measurement — with
  the concrete move and tool named at each step. The target is faithful writing
  quality, never detector evasion.
- **Length is stratified, never normalized (guardrail 9).** Dividing a
  document-scale distance by a function of paragraph count is prohibited as a
  length-confound exploit (measured in EVALUATION.md §9.8).
- **Every open item is dispositioned (§11).** The ranked frontier is complete; the
  remaining roadmap ranks (2/3/4/6), the degraded L1 (distribution and UID) and
  L3.voice operating points, and the `ai_long` standing target each carry a decided
  disposition, so the standard rests on no undecided obstacle.

No product code changed; the tool and test registries are unchanged (21 tools, 9
skills). Validator and the 82-test suite pass.

## v0.16.0 — 2026-07-13

Closes the ranked de-AI frontier and the last recorded measurement debt. Two new
cooperative-layer tools finish the frontier queue (17 → 19 → 21 tools), two
roadmap ranks land, and the document-level L3 surprisal question is resolved on a
cloud pass. Every result is measured in EVALUATION.md §9.8–9.9; three findings
came back negative and are recorded, not deleted.

- **Editing-provenance ledger (`deai_provenance.py`, new tool — frontier idea 4).**
  Inverts the question from "is this AI?" to "have my edits made it mine?" Matches
  each current paragraph to its nearest paragraph in a designated AI-draft ancestor
  (an earlier file or a git ref from the author's own history) and labels the span
  `ai_untouched` / `lightly_edited` / `rewritten` / `author_original` by a
  deterministic token edit ratio (difflib, no model). Reads only the author's own
  history; `unmeasured` without an ancestor (EVALUATION.md §9.9).
- **Personal dispersion baseline (`deai_personal.py`, new tool — frontier idea 6).**
  Uses the author's own prior papers as the confound-free dispersion reference:
  same author, same field, same jargon, so it sidesteps the field-topic
  false-positive rate (32–41%) entirely. Flags a draft that varies paragraph shape
  far less than the author usually does; `unmeasured` below three prior papers
  (EVALUATION.md §9.9).
- **Document-level L3 surprisal — measured and refuted (the last cloud debt).** A
  gpt2-large pass over 38,319 paragraphs (507 human + 154 AI docs) shows
  document-scale surprisal dispersion (pooled AUC 0.757) is weaker than the
  model-free manifold (0.881) and adds nothing to it (0.878). The detector stays
  model-free by measurement at document scale too; L3 stays `degraded` for a
  measured reason (EVALUATION.md §9.8).
- **Rank 5 (enriched surprisal) — confirmed but inert.** Five enriched surprisal
  descriptors (skew, kurtosis, filler rate, burstiness, low-frequency spectral
  energy) beat the three shipped scalars (0.803 vs 0.757), but since surprisal is
  not in the shipped model-free detector they would be dead weight — recorded, not
  added (EVALUATION.md §9.8).
- **Length-normalization refinement — measured as a confound trap.** Dividing
  manifold distance by √(paragraph count) appears to lift AUC to 0.929, but that is
  a length confound (human papers median 60 paragraphs vs 11–15 for AI tiers); a
  human-null-calibrated normalization gives 0.752 and a length-matched band shows no
  gain. The per-stratum manifold plus length-Mondrian conformal remains the
  confound-safe length handling (EVALUATION.md §9.8).
- **Rank 7 — dead specificity term replaced (`rewrite_reward.py`).** The retired
  `specificity` term was identically 1.0 for every eligible candidate (the
  eligibility gate already forces the reference numbers in), so it did no ranking
  work. Replaced with a signed L0-advisory-reduction delta (reusing `ai_ism_lint`)
  gated by a semantic-fidelity floor, so ranking now rewards the actual writing
  improvement a rewrite makes.
- **Rank 8 — `calibration_unit` honesty cap (`deai_feedback.make_finding`).** A new
  `calibration_unit` field (paragraph|section|document) structurally caps
  paragraph-unit findings at 0.5 confidence (a single paragraph is near-unjudgeable,
  perceptual AUC 0.44). Wired through every detector at its true granularity; the
  learned per-paragraph classifier (`deai_voice`) is now capped by construction.
  Backward-compatible: `None` (every prior caller) is uncapped.

## v0.15.0 — 2026-07-13

The document-scale de-AI release: a validated detection core (dispersion band →
joint manifold → role coupling → split-conformal operating points), the first
repair path for document-scale findings, a claim-anchoring quality band, and a
corpus grown 14 → 507 human papers plus five AI validation tiers. Every claim in
this release is measured in EVALUATION.md §9; refuted hypotheses (surprisal
recovery, perceptual hard-set labels, the under-anchoring AI tell) are recorded
rather than deleted.

- **Partition operators (`deai_partition.py`, new tool).** Merge/split suggestions
  that move a document toward the human dispersion band; zero-token operations, so
  the rewrite fidelity gate holds by construction. Suggest-only with a
  self-normalized cohesion floor; reordering deliberately excluded. Efficacy: 4 of 8
  conformally flagged AI docs brought inside the band (median 1 op); 116/116
  unflagged docs untouched (EVALUATION.md §9.7). Wired into `rewrite-in-voice` as
  the sanctioned lever when document-dispersion findings persist.
- **Claim-anchoring band (`deai_anchoring.py`, new tool).** Section-class
  conditional anchored-sentence rates (number/citation/\ref/math/comparison) against
  517 corpus documents, low-tail conformal with a Bonferroni share per class
  (document-level human false-flag 0.037 ≤ α). Shipped explicitly as a
  writing-quality axis: the "under-anchoring is the AI tell" hypothesis is
  **refuted** for strong-model full-paper generations, which anchor above the human
  level (EVALUATION.md §9.6). Wired into `paper-review`.
- **Per-stratum (length-aware) manifolds.** Each length stratum with enough
  training/calibration papers gets its own manifold; `manifold_operating_point` is
  the single scoring entry for findings, partition, and evaluations. Structure
  clones caught at twice the rate (0.125 → 0.292); adversarial 0.026 → 0.053
  (EVALUATION.md §9.7).
- **The `ai_long` validation tier (29 long-form generations).** The measured
  frontier: manifold flags 0/29, role 4/29 at α = 0.05, while ranking signal
  survives (stratum-matched AUC 0.716/0.639). Long-form natural generation is
  recorded as the standing falsification target (EVALUATION.md §9.7).

### Document-scale dispersion detector + hard-set correction

**Document-scale cross-paragraph dispersion detector (architecture keystone).** A
five-lens architecture reflection ([`docs/DEAI_ARCHITECTURE_ROADMAP.md`](docs/DEAI_ARCHITECTURE_ROADMAP.md))
identified that AI-ness in scientific writing concentrates at the document scale, which
the paragraph-level detectors structurally cannot see.

- `deai_features.cross_paragraph_dispersion` / `feature_dispersion`: per-feature spread
  (std/cv/iqr/lag1-autocorrelation/min-gap) of the per-paragraph features across a
  complete document. Stdlib, no GPU.
- `deai_docstructure` now attaches a model-free dispersion profile and calibrates a
  human dispersion **band** at two levels: a joint Mahalanobis dispersion manifold
  (`fit_dispersion_manifold` / `manifold_distance`, pure stdlib, primary finding at the
  95th-percentile distance) and per-feature two-sided band flags (5th/95th percentile
  low/high tails, demoted to ordinary context when the manifold is present). `calibrate`
  takes `(name, text)` or `Path`; multi-file papers are concatenated into one
  observation.
- **Calibrated over 507 complete human `wgl` papers** (new bulk arXiv full-text channel
  in `fetch_arxiv_abstracts.py --fulltext`: 475 papers fetched politely from local-ID
  candidates); manifold leave-one-paper-out false-flag rate 0.063, per-feature tails
  0.051 median. `L2.document_structure` is `measured`; every finding states only the
  measured deviation from the human corpus, not an AI verdict.
- **Role-coupled dispersion (`document-role-decoupling`).** Humans vary paragraph shape
  where the argument demands it; both AI failure modes (uniform and forced-ragged) vary
  it at random with respect to rhetorical role. Per-document permutation-normalized
  eta-squared over two role factors (which-section, has-math × has-cite; split-half
  selection rejected in-section position as chance). Held-out confirmation AUC: natural
  0.846, de-AI'd 0.833, adversarial 0.850, skeleton 0.715 (full-set adversarial 0.888,
  CI 0.847–0.926, with residual selection optimism) — the shape adversary that narrows
  the manifold's margin is this axis's strongest tier, because random variety cannot
  fake role-coupling. The manifold+role union flags 0.68–0.80 of AI tiers at ~0.10
  human in-sample cost, and the two 5% flag sets are exactly disjoint on the 507 humans
  (EVALUATION.md §9.4). Structure cloning evades role-coupling (0.658) but is caught by
  the manifold (§9.3): the axes cover each other. Known quantified bias: flagged human
  papers skew short (median 38 vs 60 paragraphs).
- **Split-conformal + Mondrian operating points (`baseline["conformal"]`).** The two
  strong document findings now flag on conformal p-values: the manifold is fit on a
  304-paper proper-training split and calibrated on 203 held-out human papers; the
  role z (no fit needed) calibrates on all 507. P(false flag) ≤ α = 0.05 finite-sample
  and distribution-free for exchangeable human papers, stratified by document-length
  terciles (the measured confound). Legacy baselines without the block fall back to
  the percentile thresholds. Independent three-way replication: human test rates
  0.029 (manifold) / 0.069 (role) at α = 0.05.
- **Corrected: earlier flag rates were length-confounded.** Stratification exposed
  that short human papers score systematically higher manifold distances (stratum-0
  95th percentile 5.23 vs 4.16/4.36) and all AI validation docs are short, so the
  unstratified thresholds had overstated tail power (e.g. natural 0.607 → honest
  0.071 at length-fair α = 0.05). The discrimination itself survives length matching:
  manifold length-fair AUC 0.82–0.90 across all four tiers (consistent with the
  paired skeleton test), role 0.70–0.82 with the skeleton tier at chance (its earlier
  0.658 was length artifact). Full corrected picture in EVALUATION.md §9.5.
- **Post-review hardening of the role axis** (multi-agent adversarial review; the
  verifier stage hit session limits, so every finding was manually re-verified against
  the code): NaN/inf feature columns no longer bypass the eta-squared guard via
  `min(1.0, NaN) == 1.0`; unequal-length paragraph vectors raise instead of silently
  truncating under `zip`; a baseline whose `scoring_factors` differ from the current
  code disables the role finding instead of comparing against mismatched thresholds;
  the math marker regex no longer counts escaped dollars (`\$`) or row breaks
  (`\\[5pt]`) as math. Baseline regenerated; all discrimination numbers re-measured
  (unchanged within rounding).
- **Fixed: baseline quantile CIs were zero-width.** The "deterministic balanced"
  resampler indexed `(iter*17 + idx*31) % n`, a full permutation whenever
  gcd(31, n) = 1 — every bootstrap CI in the document baseline was degenerate and
  overstated certainty. Replaced with a seeded with-replacement bootstrap; baseline
  regenerated.
- **Held-out validation** (242 reference / 242 never-touched humans): natural AI AUC
  0.917 (CI 0.874–0.951), de-AI-rewritten 0.931 (CI 0.888–0.965) — a 22%-of-text
  paragraph-level de-AI rewrite barely moves the document signal — and a deliberate
  paragraph-shape adversary 0.895 (CI 0.855–0.930). The adversarial number is the honest
  arc's endpoint: one-sided low-tail scoring collapsed to chance at realistic reference
  breadth, the adversary's overshoot motivated the two-sided band (0.801), and the joint
  covariance geometry recovered the rest (EVALUATION.md §9).
- **Skeleton-matched falsification (format artifact ruled out).** 24 AI papers generated
  to the exact structural skeleton of 24 human papers (sections, paragraph counts,
  sentence counts); on the 17 compliant pairs, with the manifold refit excluding all
  sources, the AI clone still separates from its own identically-structured human source
  at paired AUC 0.934 (CI 0.830–1.000) — 0.920 (CI 0.810–1.000) after dropping the two
  count features the skeleton pins. The signal is intra-format prose texture, not paper
  format (EVALUATION.md §9.3).
- **Full-feature cloud pass refuted the surprisal-recovery hypothesis.** Against the
  adversarial tier, surprisal-only dispersion scores AUC 0.677 (CI spans chance) and the
  GPU model features add nothing to the robust punctuation/clause-rhythm core (0.921 with
  vs 0.914 without), while including gamed features dilutes the detector (full-14 0.673).
  The shipped document detector is model-free and GPU-free by measurement (EVALUATION.md
  §9). Honest limits (small n per tier, single field and generator) are recorded.

### Hard-set evaluation correction

Corrects a statistically wrong claim in the v0.14.0 evaluation record and reframes the
author hard set around true provenance instead of perception.

- **Provenance is the hard-set yardstick, not perception.** `hardset_evaluation` now
  reads `deai_hardset_key.csv` and reports, as the primary metric, the model's AUC for
  separating true generated-vs-human paragraphs (0.937, bootstrap CI 0.860–0.990). The
  author's perceptual `ai_feel` rating is demoted to a task-difficulty baseline: it
  separates the same true provenance only at chance (AUC 0.444, CI 0.304–0.582), showing
  that single decontextualized paragraphs carry too little signal for reliable human
  AI-judgement.
- **Withdrawn claim.** v0.14.0's EVALUATION.md called an AUC of 0.354 (model vs
  `ai_feel≥4`) "decisive" proof that the model measures field register, not AI-ness. That
  metric scored the model against the near-chance perceptual axis and, with only 8
  strong-feel labels, has a bootstrap interval of 0.141–0.588 that straddles 0.5. It is
  not distinguishable from random and is retained only as a low-power secondary line.
- **Every hard-set AUC now carries a seeded bootstrap 95% interval** (`_bootstrap_auc_ci`)
  so small strata cannot be over-read again.
- L3 remains `degraded`, now on the well-powered field-topic negative-control
  false-positive rates (§7.4) and the absence of a document-level calibration set, not on
  the withdrawn perceptual metric.

## v0.14.0 — 2026-07-12

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

- **Confound-aware learned-model audit run (cloud, RTX PRO 6000).** The learned model
  was retrained on an expanded corpus (16,394 positive / 2,265 negative; dated arXiv
  positives grown 3,197 → 13,642) and audited with the new pipeline. Repeated
  source-grouped AUC 0.932 and matched-stratum AUC 0.924 show the separation is not a
  pure topic/length/math artifact, but 32–41% false-positive rates on field-topic and
  field-jargon-dense AI text keep L3 `degraded` with no operating point. The full result
  is in `EVALUATION.md` §7 and the machine-readable `voice_model_evaluation.json`. The
  75-paragraph author hard set is now fully labelled. **[Correction — see Unreleased
  above:** this entry originally cited an author-hard-set AUC of 0.354 as decisive proof
  the model measures field register, not AI-ness; that metric was underpowered
  (n_pos=8, CI 0.141–0.588) and scored against a near-chance perceptual axis. Against
  true provenance the model separates AI-vs-human at AUC 0.937.**]**

Published after fresh validator/tests, the 16-finding independent review and fixes, the
confound-aware learned-model status above, EVALUATION.md update, and clean-checkout
verification.

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
