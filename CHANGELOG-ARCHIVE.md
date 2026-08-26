# Changelog archive — v0.19.0 through v0.26.2

Entries moved out of [CHANGELOG.md](CHANGELOG.md) on 2026-08-25 so the live
changelog stays readable, and split in two on 2026-08-26 when this file passed
the repository's 750-line budget. Nothing here is edited; the history is
verbatim.

- Current release and the one before it: [CHANGELOG.md](CHANGELOG.md)
- **v0.18.0 and earlier**: [CHANGELOG-ARCHIVE-EARLY.md](CHANGELOG-ARCHIVE-EARLY.md)

---

## v0.26.2 — 2026-08-16

Evidence only. The validation v0.26.1 said was designed but not executed was
executed, and it **refuted** the statistic v0.26.1 recorded as a lead. No
skill, tool, threshold, or exit code changed.

- **Spine fraction is refuted as a discriminator, on its own pre-registered
  condition** (`EVALUATION` §15.2b). Every clause the first annotator called
  unbound went to a second annotator, blind to the class and to every other
  file in the study, whose task was to *find* an antecedent. The protocol
  pre-registered failure above a 30% overturn rate. **The measured rate was
  45%** (9 of 20). The domain-matched AUC fell from 0.756 to **exactly
  0.500** (p = 1.000): after correction all five Claude-generated astronomy
  passages score 1.000, identical to all nine human arXiv passages. Every
  unbound verdict that survived refutation lies in the cross-domain bank, so
  the residual class-level separation (0.750) is the genre confound alone.
- **The overturns diagnose the contamination they were built to measure.** Six
  of nine fell on the generated astronomy passages, and the refuter's
  antecedents were exact: clauses were marked unbound because they *read* as
  machine prose while their demonstratives pointed at named earlier
  propositions. Authorship instinct produced those verdicts, not the binding
  rule.
- **This vindicates the v0.26.1 shipping decision rather than undermining it.**
  §5.4 shipped as a writing rule that forbids building a threshold on this
  signal; the evidence now says that restraint was correct. The §11
  disposition table records `Spine fraction as a discriminator` as
  **Rejected**.
- What survives is a **writing** distinction, not a detection one: a
  demonstrative pointing at a single earlier proposition is a real antecedent;
  a generic self-reference predicated on an unfalsifiable relevance claim is
  not. That is already how §5.4 and the de-ai binding ledger are written.
- Limits recorded with the result: 20 passages and one annotator pair, and a
  second annotator from the same model family, so the overturn rate bounds
  contamination from below rather than from above.

## v0.26.1 — 2026-08-16

One new normative section and the evidence for why it ships without a
detector, plus the corpus tooling that produced that evidence. No axis,
threshold, or exit code changed.

### The thesis spine (`SCIPAPER_STANDARD` §5.4)

Reader complaint: a draft lists everything its authors did and everything
they measured, and never says which result is *the* result. §5.3 cannot
reach this, because condense removes what is **repeated** and an inventory
repeats nothing — what it lacks is rank.

- **`SCIPAPER_STANDARD` §5.4** states one rule at three nested scales. The
  **document** has exactly one central result, statable in one sentence,
  and every section earns its place by serving it; the reader must finish
  able to say what was done, what the result is, and what it changes. A
  **paragraph** carries one claim, and every other sentence answers "on
  what grounds" or "therefore what". A **clause** either introduces a
  checkable new fact or binds two propositions already in play; one that
  does neither is evaluation, purpose attribution, or restatement. The
  diagnostic is a pointer to the antecedent, not a search for a
  connective.
- **The qualifier class is what this section most endangers**, so the
  protection is stated inside it: a clause that narrows a claim — a
  condition, range, uncertainty, scope limit, negation, or conceded
  limitation — is load-bearing by definition and is never padding. §6
  eligibility outranks the whole section.
- **`skills/paper`** gains the operational form: write the thesis line
  before drafting or revising, then fill the **inventory test** table
  (section → the one sentence it contributes → where it is carried). A
  section with no such sentence is inventory; two sections with the same
  sentence are one section.
- **`skills/de-ai`** Pass 3 gains step 1b and §4.3, the **binding
  ledger**: every clause of a rewritten paragraph is labelled `fact`,
  `link`, or `none` with its antecedent named, and no candidate may carry
  a clause the ledger marked `none`. A paragraph that is all `none` rows
  is handed to `condense` rather than rewritten.
- **It is deliberately not a measured axis**, and §5.4 forbids building a
  threshold on it without new evidence.

### Why there is no detector (`EVALUATION` §15)

- **Two more surface features refuted.** Inert-clause runs do not separate
  human from AI once genre is matched (human span 0.500–0.778, AI span
  0.667–0.889, overlapping, with one AI bank *below* one human bank), and
  the inference-connective rate reverses sign between two AI banks
  (Claude generations median 0.200 against human abstracts' 0.000; RAID
  generations 0.000 with p90 0.125 against the human p90 of 0.222). A
  connective is therefore not evidence of an inference. With claim
  anchoring (§9.6) and the hypotaxis ratio (§14.5), that is three
  independent surface statistics and one outcome.
- **The replacement statistic is a lead, not a result.** A blinded pilot
  (20 passages, 152 clauses, key read only after annotation, blind-file
  SHA-256 matched across a replay) put the domain-matched AUC at 0.756
  with an exact permutation p of 0.032 — but the Hanley–McNeil interval
  at n = 9 vs 5 is [0.441, 1.071], which covers chance. Ten of twenty
  passages scored 1.000, two of them AI, so it cannot be a detector;
  every passage below 0.833 was AI and no human fell below it, so the
  usable form is a one-sided low-tail band. Annotator contamination is
  unquantified and the AUC is an upper bound.
- **Null: a subfield reference does not move the salience gate.** A
  254-abstract weak-lensing top-tier bank reproduces the broad bank's p90
  gates (0.500/0.500, 0.667/0.667, 2.000/2.200) and the case document
  reads p = 0.91 against either. `salience_baseline.json` needs no
  rebuild. Genre separates at the discipline level, not between astro-ph
  subfields.
- **The same bank must not become the register reference.** 254 documents
  cannot express a rate below 1/254 = 3.9e-3, 39.4× coarser than the 1e-4
  threshold, so `saddle`, `classifier`, `recall`, and `ablation` flip to
  foreign on zero counts. A register reference needs of order 10,000
  documents. The bank is stored and wired to nothing.

### Corpus tooling

The measurements above needed a weak-lensing top-tier reference to exist,
and building one exposed three gaps in the fetcher and one in the existing
banks. The human bank is astro-ph at large rather than the weak-lensing
subfield. The two
`ai_ism_negatives_generated*` banks carry no per-record generator, date, or
prompt, only the asset-level description in this file's v0.13 entry. And
the pre-2022 date filter turns out to bound less than it appears to.

- **The "pre-LLM human reference" guarantee was weaker than stated.**
  `--date-hi` filters `submittedDate`, which dates arXiv v1; the API's
  `summary` is always the *latest* version's abstract. 6,552 of the
  13,642 records in `human_abstracts_extra` (48.0%) are non-v1, and a live
  probe of twelve 2021 weak-lensing submissions found eleven with
  `updated > published`, two of them revised after 2022-11 — after the
  text could have been touched by a public LLM. `fetch_page` now records
  `published` and `updated`, and `--updated-before YYYY-MM-DD` drops every
  record whose latest version is dated on or after the cutoff. A record
  with no `updated` is dropped rather than assumed clean. The existing
  bank predates this field and is unaffected; re-deriving its text vintage
  needs a refetch.

- **`fetch_arxiv_abstracts.py` captures `journal_ref` and `doi`**, and
  gains `--journals apj,apjl,aa` to keep only those refereed venues.
  Selection is client-side against the literal `journal_ref` shapes seen
  live, because the API's own `jr:` prefix is a loose token match: a
  `jr:"Astronomy and Astrophysics"` probe returned *Research in Astronomy
  and Astrophysics*, a different journal. The Letters pattern is ordered
  before the main-journal pattern it is a substring of, and ApJS, A&A
  Review, and RAA are pinned as explicit negatives.
- **`--query-set wl`** adds a weak-lensing-only sweep, for a reference
  matched to the subfield rather than to astro-ph at large. The `broad`
  default is byte-identical to the previous query list.
- **Fixed: a rate-limited sweep was indistinguishable from a complete
  one.** The abstract path had no 429 handling at all — it caught the
  error, emptied the page, hit `if not page: break`, and abandoned that
  query, then walked into the same wall on every remaining query. A live
  run lost 11 of 16 queries this way, wrote 195 records, and exited 0.
  The full-text path *did* have a 60 s backoff, so this was one root
  cause at two sites: both now share `urlopen_backoff`, which escalates
  through a backoff schedule and then raises `Throttled`. A throttled
  abstract sweep stops, prints a TRUNCATED report naming the query it
  stopped at, and **exits 2**.
- **`--resume`** seeds from the existing output file, so a run cut short
  by throttling is extended rather than replaced. Without it the writer
  truncates its target, which is also why a journal or subfield run now
  must pass `--out-name`: reusing the default would have destroyed the
  broad corpus the calibration baselines are built from.
- **Measured, and it is a null: the subfield reference does not move the
  salience gate.** A 254-abstract weak-lensing top-tier bank (ApJ 75,
  ApJL 8, A&A 171; submitted 2010-01 to 2021-12, every latest version
  dated before 2022-11) reproduces the broad bank's p90 gates —
  `max_recital_run_frac` 0.500 vs 0.500, `recital_frac` 0.667 vs 0.667,
  `numerals_per_sentence` 2.000 vs 2.200 — and the same manuscript reads
  p=0.91 against either. `salience_baseline.json` therefore needs no
  rebuild, and an earlier p91 finding is not an artefact of the reference
  population. This does not contradict the discipline-level genre effect
  seen against cross-domain banks: genre separates at the discipline
  level, not between astro-ph subfields.
- **The same bank must NOT become the register reference.** `deai_register`
  calls a term foreign below a document-frequency rate of 1e-4, but 254
  documents cannot express a non-zero rate below 1/254 = 3.9e-3, 39x
  coarser than the threshold. Under that reference `saddle` — the central
  concept of one of this suite's manuscripts — flips from native to
  foreign purely on zero counts, as do `classifier`, `recall`, and
  `ablation`. A register reference needs of order 10,000 documents for a
  single occurrence to land at the threshold, so the broad bank stays.
  The new bank is stored but wired to nothing.
- **`tests/test_fetch_arxiv_abstracts.py`** (new, 25 tests): journal
  classification including the four near-miss venues, `fetch_page` over a
  canned feed (namespace-scoped `journal_ref`, whitespace-wrapped values,
  `published` vs `updated`), the backoff schedule under mocked 429s, the
  text-vintage filter, and the resume/truncate contract.

## v0.26.0 — 2026-08-16

Two new corpus-referenced axes, and the reduction fix that made the first
of them measurable at all. Both answer one reader complaint from
different directions: a draft can pass every existing axis and still read
as a machine inventory written for a neighbouring discipline.

- **Fixed: every numeral in a LaTeX manuscript was invisible to the
  subsystem.** `extract_style.latex_to_plain` replaces each math span
  with the token `[math]`, which is right for lexical and sentence-shape
  statistics and destroys the digits. Any signal about how a passage
  distributes its measured quantities therefore read identically zero on
  real `.tex` input — a recital-dense abstract measured 0.0 numeric
  density. The new `latex_to_numeral_text` is a second named projection
  sharing the same pattern set and differing in one decision: it keeps
  the numerals inside *inline* math. Displayed equations are dropped by
  both, because their digits are the constants of a definition rather
  than quantities the prose reports. `latex_to_plain` is unchanged, so
  every existing calibration asset stays valid.

- **New axis `L2.salience_hierarchy` (`deai_salience.py`).** Measures
  whether a passage ranks what it reports or recites it. The
  discriminating quantity is not numeric density — a quantitative
  abstract is supposed to carry numbers — but how far the numerals run
  without an interpreting sentence between them. Calibrated per section
  bucket on the field's own passage banks (13,438 abstracts for the
  `wgl` abstract reference) and read as P(X ≤ x) against a 0.01 quantile
  grid, because two of the three features are ratios of small integers
  and a coarse grid swallows a passage that lands on a tie plateau. One
  finding per over-recital passage, led by its most extreme feature;
  emitting one per feature tripled the count of a single defect.

- **New axis `L0.register` (`deai_register.py`).** Flags terms the
  manuscript leans on that the field's own corpus does not carry — the
  tell of a paper written in a neighbouring discipline's register. The
  judgement is corpus document frequency, never a curated "foreign word"
  list, and the corpus says why: in the 15,599-passage astronomy
  reference `AUC` appears in 1 passage while `epoch` appears in 402 and
  `accuracy` in 774, so any hand-written cross-discipline blacklist
  flags all three. Three constructions that defeat a naive frequency
  test are handled rather than thresholded away: hyphenated compounds
  are judged by their rarest part (`aperture-mass` is native via
  `aperture`), subscript decorations in macro bodies are not terms
  (`\Kraw` renders `S_sad`, not the word "sad"), and possessives fold
  onto the bare term. Advisories only — field register is the author's
  judgement, and a corpus-rare term may be the concept the paper
  introduces.

- **Guard: a reference with no spread above the advisory gate abstains.**
  When every reference passage above p90 shares one value, P(X ≤ x)
  reaches 1.0 there and an ordinary passage reads as the 100th
  percentile. The affected feature declines to rank rather than
  inventing a finding.

- **Recorded negative result.** A subordination-versus-coordination
  ratio was prototyped as the formalisation of "flat prose" and refuted
  against the same human reference: the manuscript under review sits at
  the 77th percentile of hypotaxis, above the human median, so flatness
  is not a deficit of subordinate structure. Not shipped; recorded in
  `docs/EVALUATION.md` §14 so it is not re-proposed.

- Both axes are wired into `ai_ism_lint` (`--register` / `--salience`,
  default on) and emit advisories only, so the 0/1/2 exit contract is
  unchanged. 32 new tests (147 total); standard updated to v3.5.

## v0.25.1 — 2026-08-06

CI-repair patch; no behavior change to any tool or skill.

- **CI green for the first time since v0.20.0.** The numpy-backed
  bootstrap-AUC test lacked the optional-dependency guard the two
  joblib-gated tests already had, so every hosted run since 2026-07-17
  failed with `ModuleNotFoundError` (the workflow installs no optional
  dependencies by design). Guard added in `67a6b55`, verified both ways
  locally (115 discover tests with numpy; skip-not-error with numpy
  import-blocked); first green runs are 31133202443 (push) and
  31133215203 (manual dispatch).
- **`workflow_dispatch` trigger added** (`6886679`) so CI can be
  retried without an empty commit — during the 2026-08-06 GitHub
  Actions outage, pushes produced no runs and there was no manual
  lever.
- Release gate: validator 8/8, 115 unit/CLI tests, and a green hosted
  CI run on the release tree (the CI-green condition is recorded in
  EVALUATION §12 as part of the standing gate).

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

