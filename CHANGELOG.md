# Changelog

All notable changes to the `sci-paper` plugin. Versions follow the
`plugin.json` / `marketplace.json` `version` field.

## v0.29.0 — 2026-08-26

Three roadmap items were closed by building the thing and measuring it, one
published number was found wrong and corrected, and the evidence behind
EVALUATION §9 became a tool instead of a memory.

### The roadmap emptied by refutation

- **The length-aware manifold is built, measured, and refuted.** Each manifold
  coordinate is a log-ratio of a sample standard deviation over *n* paragraphs,
  and `Var(log s) ≈ 1/(2(n-1))` for that statistic — so the roadmap entry had an
  exact form: subtract the fit set's mean noise from the covariance diagonal,
  add each scored document's own back. Over **12 paired seeds** the human
  out-of-fit rate is unchanged (0.030 → 0.030) and two AI tiers move the wrong
  way (`ai` 0.792 → 0.754, natural 0.170 → 0.140). The correction is
  length-*symmetric*, and the AI documents at issue are short exactly like the
  human papers they are compared against, so it cannot separate them.
- **Enlarging the conformal calibration set is refuted.** At n_cal = 78 the
  smallest achievable p is 1/79 = 0.0127, so α = 0.05 flags only a document
  beating all but two calibration points. Moving documents from training to
  calibration (0.6 → 0.3) leaves tail power flat and raises the human
  false-flag rate monotonically 0.030 → 0.038. The shipped split is at the
  better end of that trade.
- **Long-form detection holds at 0.000** across 2 metrics × 4 splits × 12 seeds.
  Rank AUC is 0.729, so the signal is present and the operating point cannot
  reach it. No longer a single-configuration result.

Only one roadmap item remains, and it is blocked on an input rather than on
effort: a human-labelled validation set for salience and register.

### The §9 point estimates are seed draws

Averaged over 12 seeds, manifold tail power is **0.170 ± 0.110** (natural),
0.261 ± 0.114 (de-AI'd), 0.237 ± 0.184 (adversarial), 0.274 ± 0.043 (skeleton).
Several differences the record read as improvements — including v0.28.0's
`0.214 → 0.250` from the bundle-ordering fix — are smaller than that spread.
The ordering fix stands on the grounds that reading a paper in its own order is
correct, and on the human-side rate it lowered; not on those deltas. §9 now
carries the spread, and **`tools/eval_docscale.py`** reproduces the whole table
from the shipped operating point so no figure has to be quoted from memory.

### Section coverage: a wrong number, then a real fix

**Correction.** v0.28.1 published the coverage gap as "1,804 of 5,074 headings
(35.6%)". Those counts were wrong — the probe used a re-typed regex including
`\subsubsection`, which `RE_SECTION` does not split on, swept files
`select_document_roots` rejects, and ran under a `timeout` that may have cut it
short. The correct pre-fix figures are **3,026 of 9,222 (32.8%)** in `wgl` and
52 of 148 (35.1%) in `wgl-letter`. The rate was about right; the counts were not.

Then the unambiguous part was closed, taking `wgl` to **2,334 of 9,178 (25.4%)**:

- `RE_SECTION` captured `[^}]+` and stopped at the first inner brace, so
  `\section{Results\label{sec:res}}` classified `Results\label{sec:res` and
  `\section{\hspace*{+0.0mm}Foo}` classified a spacing command. The title group
  now spans one level of nesting and `clean_heading` strips what survives.
- A `\section{}` whose title is empty once markup is stripped no longer resets
  the enclosing bucket — 12 such headings were turning every following
  subsection `unknown`.
- "Affiliations" is front matter (`skip`); "Covariance matrix", "Likelihood",
  "Blinding", "Cosmological constraints", "Validation" and "Forecasts" name
  section roles the vocabulary did not carry.
- **"Measurements" and "Background" were refused.** In weak lensing "Shear
  measurement" is method while "Mass measurements" is results, and "Background"
  spans intro, method and data. Guessing either is how `method` became the
  residue. The remaining ~25% is mostly topic headings and is a floor, not a
  backlog.

Every profile asset was rebuilt on both fields: the exemplar bank goes
25,005 → **27,951** paragraphs, `results` 3,118 → **3,964**, register 38,647 →
**41,593** passages, and the UID baseline re-reads at 3.321 ± 0.439 pooled with
the section-identity null intact (3.23–3.38 across seven buckets).

### Two files split, and the guard that was missing

`train_voice_model.py` (1,174 lines against a 750-line budget) split into
`voice_dataset.py` (record loading, grouping, the fingerprinted feature cache)
and `voice_audit.py` (held-out metrics, hard set, confound audits), with a
one-way dependency a test asserts. `CHANGELOG-ARCHIVE.md` (1,125) split at its
v0.19.0 seam into `CHANGELOG-ARCHIVE-EARLY.md`; the history is byte-identical
across the split.

The first split shipped four unbound names — `time`, `CHECKPOINT_EVERY`, `df`,
and the two HARDSET category sets — and **the suite stayed green**, because no
test reached `build_features`. A real retrain found it. `test_train_voice_model`
now walks the AST of every file in `tools/` for names that are neither defined
nor imported, so the next split cannot fail that way.

### Added

- **`tools/eval_docscale.py`** — reproduces the §9 table (human false-flag rate,
  per-tier tail power, rank AUC) through `manifold_operating_point`.
- **`tools/cli_common.py`** — the shared CLI preamble and field resolution. The
  argparse opener was duplicated across the suite and `list_fields` /
  `resolve_field` existed in five byte-equivalent copies; the duplicate-content
  guard refused a 27th. **21 of 30 tools retrofitted**, with the allowlist and
  the refusals recorded rather than left implicit: nine are library modules with
  no CLI or are the module itself, `ai_ism_lint` keeps its own resolver because
  it warns and returns `None` so the L0 pass still runs with no profile, and
  `extract_style` resolves against the corpus root — expressed as
  `exclude_prefixes=("tier-",)` rather than as a second implementation.

  The sweep was attempted twice with a regex and reverted both times. The first
  pass inserted the replacement before deleting the original, so the deletion
  consumed the replacement; the second ate four constants and a function out of
  `extract_style.py`, because a `\n\n[A-Z_]` lookahead skips every intervening
  `def` to reach the next module constant. The AST knows where a function ends.
  Both reverts were caught by the suite — the second by the unbound-name guard
  added in this same release.

## v0.28.1 — 2026-08-26

v0.28.0 fixed the corpus layer but only rebuilt the assets on the `wgl` path it
was measuring. Two derived assets were left holding the pre-fix view of the
corpus, and the audit that found them also measured how much corpus the fixed
layer still discards.

### The rebuild v0.28.0 did not finish

- **`wgl-letter` was still entirely pre-fix.** Every asset in that field dated
  from 2026-08-16 and was built by the defective code path, so `--field
  wgl-letter` served baselines nobody had re-derived. Rebuilt through
  `extract_style` plus the `deai_register` / `deai_salience` / `deai_structure`
  calibrations. The old profile read 775 `method` passages against a single
  `results` passage; it now reads `method` 232, `data` 125, `intro` 85,
  `results` 84, `discussion` 83, `conclusion` 22, `abstract` 10. The bank shrank
  from 955 passages to 641 because unattributable prose is now dropped instead of
  absorbed into `method` — the correct direction, and the reason the old numbers
  should not be compared to the new ones.
- **`ai_ism_classifier.joblib` was fit on the 593-paragraph bank.**
  `build_profile.py` runs extraction and classifier training as one chain; the
  v0.28.0 work invoked `extract_style.py` directly, so step 2 never re-ran and
  the legacy L3 advisory kept a model that disagreed with its own corpus.
  Retrained on both fields.

### Section coverage is now measured, not assumed

Sweeping every heading in both corpora through `classify_section`, **35.6% in
`wgl` (1,804 of 5,074)** and **35.8% in `wgl-letter` (63 of 176)** resolve to
`unknown` and reach no baseline. Two independent corpora agreeing to within 0.2
points points at the bucket vocabulary, not at either corpus: review-article
headings such as "Magnification bias" name no standard section. Recorded as a
limitation in both READMEs and
[`lexical-structure-uid.md`](docs/architecture/evaluation/lexical-structure-uid.md)
§5, with the explicit constraint that widening the rules must not reintroduce
the pre-v0.28.0 absorption into `method`.

### Fixed

- `train_ai_ism_classifier` printed `5-fold CV accuracy: 1.000 ± 0.000` at a
  1250:1 class ratio, where always-predict-corpus already scores 0.999. The
  ratio and that baseline now print beside it, so the headline number cannot be
  read as skill; minority-class F1 (0.796 on `wgl`, 0.905 on `wgl-letter`) is
  the signal.
- The README roadmap quoted **−0.418** for the short-stratum length correlation,
  the value superseded by the assembly-order fix. Both READMEs now read
  **−0.414**, matching
  [`document-scale.md`](docs/architecture/evaluation/document-scale.md) §9.4b.
- **Five in-page anchors pointed at headings that no longer existed.**
  `validate_plugin.py` checked relative *file* links but never `#fragments`, so
  the v0.28.0 README restructure left the Chinese README's navigation pointing
  at `#tools25-个` after the count became 26, and four demo cross-references
  pointing one demo off — "demo 3" linked to demo 4. All five fixed, and the
  validator now resolves every in-page anchor across 14 pages against the
  headings actually present, CJK included. Verified by negative control: an
  anchor broken on purpose fails the check.

## v0.28.0 — 2026-08-25

The corpus layer treated a *file* as a paper and could only see the three
curated tiers. Fixing that took the reference banks from 593 paragraphs to
25,005, cleared the `results` limitation carried since v0.27.0, and let two
roadmap items be settled by measurement rather than left open.

### The corpus layer: four defects, one shape

Each was measured before it was fixed, and the profile rebuilt against all four.

- **Every `.tex` counted as its own paper.** Bartelmann & Schneider (2001) ships
  `WeakLens.tex` plus `WeakLens_1..10` and `WeakLens_D`, so that one review
  entered every downstream distribution twelve times at tier-1 weight — the
  pseudoreplication this project refuses everywhere else. `tier-1-top` held 20
  `.tex` files and 8 papers. `select_document_roots` now drops `\include` /
  `\input` fragments and unmarked siblings (`bib.tex`), while keeping plain-TeX
  papers that predate LaTeX2e and carry no document marker at all.
- **Selecting the root is only half the fix.** `WeakLens.tex` is 72 words; its
  ~40,000-word body is in the eleven chapters it includes. `read_tex_document`
  splices them, once — 64,657 words — skipping commented-out `% \includeonly`
  builds and breaking cycles.
- **The selector and the reader disagreed on `\input` targets.** arXiv flattens
  submissions, so `\input{sections/intro}` names a sibling; the selector matched
  by stem and dropped it as a fragment while the reader resolved by literal path
  and never spliced it back. Four bundles lost most of their prose, one keeping
  2 of 9,743 words.
- **A `\subsection` did not inherit its `\section`.** "Covariance matrix",
  "Likelihood" and "Blinding" are method prose; classified alone they are
  `unknown` and discarded — **54.8% of all section words** in the 561-document
  corpus. The PDF path got this fix earlier the same day; the LaTeX path had
  not. An inherited `skip` now also stays skipped, so appendix subsections no
  longer escape into the distributions.

### The breadth corpus was on disk and invisible

500 arXiv full-text papers — fetched for §9, gitignored, present since v0.26 —
were unreachable by every paragraph-level baseline, because the curated tiers
and the reference distributions shared one file list. They are now distinct
roles: `REFERENCE_DIR` is gathered, **unweighted**, and excluded from every
aggregate, so breadth cannot restyle the dossier's imitation target.
`retrieve_exemplars` reads the curated tiers by default (`--include-reference`
widens) and learns about the `data` bucket, which reached the bank on
2026-08-25 but never reached `VALID_SECTIONS`.

| bucket | v0.27.1 | v0.28.0 |
|---|---:|---:|
| method | 163 | 8,144 |
| data | 112 | 3,929 |
| intro | 109 | 3,753 |
| **results** | **26** | **3,118** |
| discussion | 118 | 3,088 |
| conclusion | 48 | 2,533 |
| abstract | 15 | 433 |
| **total** | **593** | **25,005** |

**Every bucket now clears the 30-passage floor**, `results` by 104×, so no
bucket is rank-only. Register goes 14,235 → 38,647 passages and 41,154 → 54,233
terms, with abstracts falling from 96% of the reference to 35%. The `results`
limitation and the "corpus growth for thin buckets" roadmap item are closed —
and the diagnosis they rested on was wrong: the constraint was never corpus
availability.

### Two roadmap items settled by measurement

- **`deai_policy.json` is withdrawn, not deferred** (EVALUATION §16). It would
  have moved `L1.distribution` and `L2.sentence_structure` off `degraded`.
  Measured on 500 human papers against 173 `docval` AI documents, one
  observation per document: burstiness **reverses sign** — adversarial prose is
  more bursty than the human median (1.036 vs 0.775, AUC 0.181) and long-form
  sits inside the human band (AUC 0.441) — while flagging 7.2% of humans; and
  signposting has AUC **0.247**, below chance, flagging **0 of 173** AI
  documents at the shipped default. That is the pattern the standard already
  used to reject the inference-connective rate. Both axes stay `degraded` for a
  measured reason rather than a missing asset.
- **The length-aware manifold has its mechanism measured** (§9.4b) and both
  cheap routes refuted. Inside the short stratum, human manifold distance still
  correlates **−0.414** with paragraph count, unchanged by the assembly-order
  fix above — an estimator-noise effect, not a corpus defect. Normalizing the
  distance stays
  rejected (guardrail 9). Finer Mondrian stratification, tested at 3/4/5/6
  strata, reduces the residual to about −0.27 and buys **no power at all** — the
  conformal test simply becomes more conservative, and skeleton power drops
  0.208 → 0.125. What remains is an explicit estimator-noise model, not shipped.

### Fidelity gate: a hyphen between numerals is a range

Third occurrence of one root cause in `rewrite_reward`'s tokenizer, after the
Oxford comma and the spaced unit: a separator absorbed into the token. `[-+]?`
accepted a sign directly after a digit, so `0.5-1.2 arcsec` tokenized as
`{0.5, -1.2}` and a faithful rewrite saying "from 0.5 to 1.2" was reported as
MISSING `-1.2` while INVENTING `1.2`, then hard-rejected at `-inf`. Every
hyphenated range did this, which is most of them. Measured on the README's own
demo: 12 phantom missing numbers across three candidates, all three rejected;
after the fix the two faithful candidates pass and the one that genuinely drops
seven numbers is the only rejection.

### Re-measured, not carried forward

- **§9 document scale reproduces, then improves.** Every tier re-scored through
  the shipped path with the length-fair protocol restored: all eight published
  AUCs within **0.012** (manifold 0.933 / 0.943 / 0.927 / 0.914; role 0.690 /
  0.742 / 0.810 / 0.507). The 42× *paragraph-bank* growth did not move
  document-scale discrimination, which is expected — §9 always calibrated
  against `fulltext-arxiv`. What did move it is below. A fifth tier is
  recorded: long-form AI, manifold AUC 0.740 with **0.000** tail power.
- **The keystone axis was reading its own corpus out of order.**
  `_paper_documents` assembled each bundle by sorted FILENAME, so
  `Conclusion.tex` preceded `Introduction.tex` — and this axis measures section
  arc and paragraph sequence. 122 of the 500 bundles hold more than one `.tex`,
  12 provably out of order, and all 122 also folded appendices,
  acknowledgements, author lists and the journal's own class documentation in
  as body prose. Rebuilt in include order, manifold tail power rises on natural
  AI **0.214 → 0.250** and on adversarial **0.158 → 0.184** while the human
  false-flag rate *falls* 0.0346 → 0.0325. The role axis trades the other way
  (natural 0.107 → 0.036), so the union is 0.286 / 0.600 / 0.447 / 0.333.
  Fixing this required splitting `deai_docstructure.py` (1,092 lines against a
  750-line budget) into a measurement layer, `deai_docshape.py`, which it
  re-exports in full under a contract test.
- **L3 retrained** on 41,641 records (2.6× the previous bank): grouped-split AUC
  0.9320 → **0.9502**, balanced accuracy 0.8509 → **0.8736**, matched-stratum
  0.9236 → **0.9303**. The confound did not move — field-jargon-dense false
  positives 0.417 → 0.410, inside the split range — so two retrains on very
  differently sized banks now agree it belongs to the feature set, and L3 stays
  `degraded`.
- **Retraining is not behaviour-preserving, and is not claimed to be** (§7.0).
  Checked at the production unit: 1,845 paragraphs scored by both bundles, same
  feature pipeline. Rank correlation holds at Spearman **ρ = 0.846**; the three
  paragraphs surfaced for review overlap **0.654**; 11 of 54 documents get an
  identical set. Same schema, same features, same `degraded` posture, no
  invented threshold — but an old triage list will not reproduce exactly.
- **UID** now spans 25,005 paragraphs, pooled global UID 3.322 ± 0.446. Section
  means span only 3.23–3.38 against within-bucket σ of 0.26–0.57, recorded as a
  null: a per-section UID operating point would calibrate on less than its own
  noise.
- **Latency** re-measured on a real 5,084-word corpus paper: all model-free axes
  390 ms, `--oracle` 23.1 s, `--voice` 26.6 s, validator 359 ms, suite 43.1 s.

### Three files split, because they could no longer be edited

The repository enforces a 750-line budget per file. Three files had passed it,
and the hook refuses *any* write to an over-budget file — including a one-line
factual correction. Each split follows an existing seam rather than inventing
one, and each is verified by a re-export or incorporation contract.

- **`deai_docstructure.py`** (1,092 → 443) splits at measurement versus
  feedback. `deai_docshape.py` (708) holds the per-paragraph feature vector,
  cross-paragraph dispersion, the joint manifold, role coupling, the conformal
  operating points and the baseline builder; `deai_docstructure` turns them
  into findings and a CLI, and re-exports every public name under a contract
  test modelled on the one `extract_style` already has.
- **`SCIPAPER_STANDARD.md`** (823 → 736) at contract versus register. §§7-8
  become [`architecture/RESPONSIBILITIES.md`](docs/architecture/RESPONSIBILITIES.md),
  **incorporated by reference and still normative** with no independent
  authority; §11 becomes
  [`architecture/DISPOSITIONS.md`](docs/architecture/DISPOSITIONS.md), a record
  of decisions rather than policy; and a 49-line embedded version history moves
  to this changelog, where it belonged. §§0-10 of the contract are unchanged.
  The standard is now v3.7.
- **`CHANGELOG.md`** (1,463 → 484) at v0.26.2, with the remainder verbatim in
  [`CHANGELOG-ARCHIVE.md`](CHANGELOG-ARCHIVE.md).

### Documentation

Both READMEs restructured around a **three-way comparison** — as-generated
versus a word-list humanizer versus this pipeline, on one paragraph — which is
the demo that shows the difference: the humanizer clears the L0 target and the
corpus-zero advisory while the `ing-tail` advisory simply follows the
substitution, and across 20 documents it moves strong advisories by exactly
zero. A full-review section documents the A–R dimensions and the merge rule.
EVALUATION gains §16 and §9.4b, and both tool tables collapse from eight
subsections into one table with a `layer` column.

33 new tests (222 → 255); 25 → 26 tools. No consequence class, exit code,
schema, ranking rule, or normative policy changed.

## v0.27.1 — 2026-08-17

v0.27.0 fixed the section classifier and measured what it would change. This
release carries out the rebuild that fix required and writes the resulting
numbers back into the evaluation record. No code, consequence class, exit code,
or normative policy changed; every edit here is a measurement or a document.

### The rebuild, and what it moved

The full `wgl` profile was rebuilt with the fixed classifier — extraction, then
each `--calibrate` stage, then a complete `train_voice_model.py` retrain
(18,647 rows, 20/20 audit splits completed). `wgl-letter` was rebuilt alongside
it. Every figure below is read from the rebuilt artifact, not from the v0.27.0
projection.

- **Reference banks.** `structure_baseline` and `uid_baseline` now hold 1,942
  paragraph observations across six buckets rather than 1,957 across five;
  `results` gains a surprisal reference for the first time. Salience buckets
  move `method` 1,377 → 1,303, `discussion` 35 → 78, `conclusion` 26 → 41, and
  gain `results` at n=10. `conclusion` crosses the 30-passage floor, so it is
  `measured` rather than rank-only for the first time. The register reference
  goes 15,599 → 15,584 passages and 41,933 → 41,714 terms.
- **The learned model barely moved, and that is the result.** Comparing the new
  audit against the pre-rebuild record key by key, every headline figure changed
  by at most 0.002 in AUC (primary split 0.9414 → 0.9399; 20-split mean 0.9324 →
  0.9320) and the negative-control false-positive rates by at most 0.005. L3
  stays `degraded` with no operating point, for the same measured reasons.
- **What did move is the per-section audit strata, which were degenerate.** The
  `discussion` stratum held a median of 5 positive rows and some splits held
  none, so its minimum F1 and recall were both 0.000; post-rebuild the median is
  19 and those minima are 0.857 and 0.850. The `conclusion` stratum's smallest
  split rose from 3 rows to 9. Before the fix that breakdown was not measuring
  section behaviour — it was measuring an empty cell.
- **§15 was checked and left alone.** Its figures come from the abstract and
  generated banks, which are not section-bucketed; the rebuilt abstract
  percentile grids are byte-identical to the pre-rebuild ones. The v0.27.0
  notice that named §15 as affected was over-broad and is corrected.

### A stale artifact the rebuild exposed

The local `voice_model_evaluation.json` predated the hard-set restructure: it
carried only the retired `auc_low_score_predicts_strong_ai_feel` key, while
`EVALUATION.md` §7.3 already documented `primary_provenance` and
`perception_baseline`. The document was ahead of the artifact on disk, which no
gate checked because nothing compared documented figures against the file they
describe. The retrain regenerates the record in the current schema, and §7.3's
0.937 / 0.444 now reproduce from it.

### Resolved limitation

`EVALUATION.md` §7.5 recorded that the cloud bundle was built with scikit-learn
1.4.2 and emitted an unpickle-version warning under a newer local install, and
predicted a local rebuild would clear it. Verified: the retrained bundle loads
under local scikit-learn 1.8.0 with no warnings. The limitation is removed
rather than restated.

### Corrections

- `style-profile/README.md` quoted the pre-ligature-fix projection (`method`
  1672, `conclusion` 51, total 1944) where `CHANGELOG.md` and `EVALUATION.md`
  carried the re-measured 1671 / 50 / 1942. It was missed in the v0.27.0
  re-measurement sweep and now agrees with the artifact it describes.
- Profile snapshots taken before a rebuild now live in the gitignored
  `.backups/` inside the repository. A snapshot placed beside the repository
  reads as a project of its own in the parent directory and escapes the ignore
  rules that cover the same corpus-derived files.

## v0.27.0 — 2026-08-16

A repository audit, the defects it confirmed, and the structure that stops them
recurring. An adversarially verified multi-agent sweep (7 dimensions, every
finding re-derived by an independent refuter) produced 59 candidates; 12 were
refuted and the rest are fixed here. No consequence class, exit code, or
normative policy in `SCIPAPER_STANDARD` §§0-6 changed.

### The section-bucket defect, and what it invalidates

`extract_style.classify_section` matched section titles **in the singular
only**. `\bresult\b` does not match "Results", `\bconclusion\b` does not match
"Conclusions", and `\bsystematic\b` does not match "Systematics" — the standard
ApJ/MNRAS/PRD headings. All of them fell through to `DEFAULT_SECTION_BUCKET` and
were measured against the **methods** reference. The symptom was visible in the
shipped bank all along and had not been read as one: 31 weak-lensing papers
produced 1770 `method` paragraphs and **zero** `results`.

The same defect had a second form. `\b(acknowledg|bibliograph)\b` was written as
if those were stems, but the closing `\b` means each can only ever match that
exact string, so "Acknowledgements" and "Bibliography" were never skipped and
were ingested as prose.

- Every noun in `SECTION_PATTERNS` now carries its plural, and the two stems
  carry `\w*` in place of a closing word boundary.
- **Every per-section asset built before this release carries the
  mis-bucketing, and the impact is measured rather than estimated.** Rebuilding
  the same 31-paper `wgl` corpus with the fixed classifier, into a scratch
  profile root so the shipped assets were untouched:

  | bucket | pre-fix | post-fix | change |
  |---|---:|---:|---:|
  | abstract | 15 | 15 | 0 |
  | intro | 99 | 99 | 0 |
  | method | 1770 | 1671 | −99 |
  | discussion | 43 | 97 | **+126%** |
  | conclusion | 30 | 50 | **+67%** |
  | results | 0 | 10 | **0 → 10** |
  | **total** | **1957** | **1942** | −15 (back matter now skipped) |

  `discussion` and `conclusion` change materially; `results` exists for the
  first time but at n = 10, below the documented 30-passage floor, so that
  bucket stays honestly omitted until the corpus grows. `EVALUATION.md` §2
  carries this table as a standing notice, and `style-profile/README.md` says
  to treat every section-keyed axis as `degraded` until the profile is rebuilt
  and each `--calibrate` re-run. The repository ships no baseline, so a fresh
  clone is `unmeasured` and unaffected.
- `tests/test_extract_style.py` is new. `extract_style` is imported by eight
  sibling tools and owns both LaTeX projections, yet had no test file — which is
  how a singular-only vocabulary survived. The back-matter form above was found
  *by that new test*, not by the audit.

### Fidelity gate: two regexes that rejected faithful rewrites

`rewrite_reward` reported honest rewrites as unfaithful — in the over-strict
direction (`combined = -inf`) — for reasons with nothing to do with science.

- **Numbers absorbed the following comma.** `\d[\d,]*` tokenized "1200, 2400,
  and 4800" as `{"1200,", "2400,", "4800"}`, so dropping an Oxford comma was
  reported as simultaneously *missing* `2400,` and *inventing* `2400`. A numeral
  token must now end in a digit; thousands separators still parse.
- **Units absorbed the following word.** The `\s*` separator let any word after
  a numeral become a "unit": "in 2020 we found" yielded unit `we`. A unit must
  now bind to its number the way the corpus writes it — adjacent, or separated
  only by LaTeX spacing (`\,` `\;` `\!` `\ ` `~`). This deliberately narrows the
  category: a plain-ASCII-space "5 km" no longer registers a unit, though its
  number stays protected.
- Changed numbers and changed units remain ineligible, now under test.

### Display math was invisible to the fidelity gate

Both named LaTeX projections drop `\begin{equation}`/`align`/`gather` bodies by
design, and every protected category was computed from them — so a value
silently changed *inside* a displayed equation passed as fully faithful. That is
the one defect in this release that let an unfaithful candidate through rather
than rejecting a faithful one.

- `rewrite_reward` now reads displayed bodies from the raw text, adding their
  numerals to the number category and the whole body to the math category.
  Whitespace normalizes before comparison, so re-indenting an equation is not a
  change while altering a coefficient or an exponent is.
- **Exit 1, not 2, when no candidate is eligible.** Every candidate failing
  eligibility is a measured outcome the caller acts on (preserve the original,
  regenerate tighter), so reporting it as an execution failure made a correct
  run indistinguishable from a crash. `SCIPAPER_STANDARD` §0.1 now registers
  `rewrite_reward` alongside `length_gate` as carrying a narrow actionable
  contract in which `1` means a measured outcome.

### Reference rates are computed over the set they are compared against

The signposting finding printed a "reference corpus rate" derived from
`blacklist_present_in_corpus`, which `extract_style` keys to its own 12-entry
`PARAGRAPH_INITIAL_LLM_OPENERS` — several of them multi-word phrases that can
never match a single paragraph-initial word. The draft, meanwhile, is measured
against `deai_metrics.CONNECTIVE_OPENERS`, 22 single words. The two numbers were
printed side by side and were never comparable; the reference read roughly seven
times too low.

- `extract_style` now stores the complete `paragraph_initial_counts` counter as
  evidence, and `deai_metrics` computes its reference rate over its own opener
  set. The extractor supplies observations; the detector owns its policy.
- A profile predating that key cannot yield a comparable rate, so the finding
  omits the reference clause and says why, instead of quoting a wrong number.

### Grouped cross-validation, and a cache that notices its own dependency

- `train_ai_ism_classifier` splits with `StratifiedGroupKFold` grouped by source
  paper. Paragraphs from one paper are not independent, and the ungrouped split
  reported F1 0.876 where the grouped split gives 0.823. `cv_grouped` travels
  with the metrics and the CLI prints which split ran, so the two can never be
  read for each other.
- `train_voice_model`'s feature-cache fingerprint includes embedder
  availability. Rows computed without `sentence-transformers` carry
  `corpus_cos = 0.0`; a fingerprint blind to that kept serving them unchanged
  after the dependency was installed, so a degraded value persisted while
  looking measured.

### Other confirmed findings closed

- `deai_oracle` declares `calibration_unit="paragraph"`. It was the one
  paragraph-scope detector that never did, so its findings shipped at confidence
  1.0 and outranked their capped siblings.
- `fetch_arxiv_abstracts` no longer lets a transient page error masquerade as an
  exhausted query. A failed page and an empty page both arrived as `page = []`,
  which silently ended that query's pagination while the run still exited 0.
  Affected queries are now named in an `INCOMPLETE` report and the run exits 2.
- `extract_style` expands typographic ligatures on the PDF path. A PDF text
  layer emits `ﬁ`/`ﬂ`/`ﬀ` as single codepoints, so the tokenizer split
  "significant" into fragments that entered the lexicon and the exemplar bank as
  words.
- `extract_style` and `validate_plugin` gained the stdout re-encoding guard the
  other CLIs already had; both print non-ASCII and both die on a redirected
  stdout under a non-UTF-8 locale. `deai_feedback` was checked and needs none —
  it has no `main()` and no non-ASCII.
- `aggregate_sentence_stats` and `train_and_save` docstrings now describe what
  the code does: tier weights are carried but not applied, the analyzer is
  word-level rather than character-level, and the returned keys are the ones
  actually returned.
- `gather_corpus_files`'s docstring describes the implemented **depth** rule
  rather than a co-location rule it never had.
- `TestShippedReference` is renamed `TestLocalReference`. The plugin ships no
  baseline — every `style-profile/**` artifact is gitignored on purpose — so its
  claim to test "the reference the plugin actually ships" read as CI coverage
  that does not exist.
- The `fetch` tests capture the CLI's progress log, which was the suite's only
  stdout noise and printed an absolute temp path.

### Linter contract

- **Exit 1 no longer reports a crash.** `lint()` caught only
  `(OSError, ValueError, JSONDecodeError)`, so any other exception — a
  `lexicon.json` holding a JSON list raises `AttributeError` — escaped and the
  interpreter exited 1, the status the contract reserves for "an L0 target is
  present". Every execution failure now returns 2.
- **A paragraph-initial connector counts once.** `Crucially` sits in both
  `TIER_A_PATTERN` and the connector list and produced two L0 targets for one
  word, while `Notably`/`Importantly`/`Interestingly` produced one. The Tier A
  scan now applies the same span guard the Tier B scan already used.

### Optional dependencies degrade instead of crashing

- `deai_oracle` probes `transformers`/`torch` before use. Their absence now
  reports `L1.uid` as `unmeasured` with the reason instead of raising
  `ModuleNotFoundError` mid-run; an explicit `--calibrate` that cannot run exits
  2 rather than dying part-way through the corpus.
- `deai_voice` imports `joblib` inside its existing guard, so a present bundle
  with the optional dependency uninstalled degrades the L3 axis instead of
  raising through the caller.
- `deai_provenance` passes `encoding="utf-8"` to its git subprocesses. With
  `text=True` alone they decoded with the locale codepage, so on a non-UTF-8
  Windows locale a tracked file containing an em-dash made the ancestor read as
  "unreadable or untracked" — an axis unmeasured for a decoding reason.
- `retrieve_exemplars` rejects `--k < 1` (exit 2). `--k 0` returned an empty
  list that surfaced as "No paragraphs in section=…", a false claim about the
  bank; a small negative `k` silently returned all-but-the-last exemplar.

### Documentation is categorized, indexed, and mechanically checked

`docs/` now separates what decides from what describes from what is frozen:

```
docs/README.md                          index + authority order
docs/SCIPAPER_STANDARD.md               normative
docs/architecture/DEAI_SUBSYSTEM.md     implementation
docs/architecture/EVALUATION.md         evidence
docs/design-notes/                      frozen, dated reasoning records
```

`validate_plugin.py` gained a ninth check and three new invariants, so this
class of drift fails CI instead of accumulating:

- **recorded suite sizes are validated against real test discovery.**
  `EVALUATION.md` had quoted two different sizes for the same release — 147/13
  in §3 and 172/14 in §12 — because nothing compared either with the repository;
- every document under `docs/` must be linked from the index (no orphans);
- each `design-notes/` file must declare itself a design note in its header;
- no document may reappear at a location it was moved away from.

Corrected in the same pass: the `EVALUATION` §5 baseline total (1,952 → 1,957,
the value the same file already used in §6 and §14.4); the roadmap's disposition
parenthetical, which listed ranks 3 and 6 in the opposite order from
`SCIPAPER_STANDARD` §11, the file it names as the single status home; the
frontier note's "ranks 2-8", which contradicted its own header; the README's
stale tool count; the hard-set filename case in `style-profile/README.md`; and
seven `EVALUATION` links that pointed at deliberately gitignored artifacts and
so resolved on no clone. `style-profile/README.md` now documents
`salience_baseline.json` and `register_lexicon.json` with the `--calibrate`
commands that build them.

### README and discoverability

- `README.md` is rebuilt around what the plugin does, how the loop works, and
  what it refuses to do, with skills grouped by job (write / revise / review /
  explore) and tools grouped by measurement layer. `README.zh-CN.md` is the
  full Chinese counterpart.
- Manifest keywords expanded from 8 to 23 and marketplace tags from 4 to 8;
  five skill descriptions are English-first with their Chinese trigger phrases
  retained, so trigger behaviour is unchanged while the plugin is findable in
  English.

### Skills

- `condense`'s `rewrite_reward.py` example was missing the tool's required
  `--field`, so the documented command exited 2 without doing any work.
- `brainstorm` resolved three internal contradictions: a `--min-frameworks`
  floor of 5 that contradicted the flag table, the §3 completion criterion and
  the anti-pattern list (all 12); two headings both numbered `## 0.`; and a
  §0.6 stopping list that omitted the glossary grill's own hard stop.

### The independent review of this release, and what it caught

Before tagging, the diff itself went through an adversarially verified review
(5 dimensions, every finding re-derived by an independent refuter): 29
candidates, 18 refuted, 11 confirmed — **most of them regressions introduced by
this release**, which is the reason the round happened at all.

- **`rewrite_reward` exit 1 had no execution-failure guard.** Promoting 1 to a
  measured outcome without one meant an uncaught exception also exited 1, so a
  crash was indistinguishable from "no candidate was eligible" — the very bug
  this release fixed in `ai_ism_lint`, reintroduced one file over. `main()` now
  wraps its body and returns 2, matching `length_gate` and `ai_ism_lint`.
- **Reading raw text without the projections' reductions.** Scanning displayed
  equations from the raw source skipped the comment stripping both projections
  do first, so a commented-out dead equation became a hard invariant and
  deleting it scored `-inf`. The fix is one shared `_uncommented()` applied to
  **all five** raw-text categories — citations, inline math, display math,
  macros, units — not to the one site the review happened to name. Display
  bodies additionally drop the `\begin{}`/`\end{}` wrapper and `\label{}`, so
  renaming `eq:mass` or starring an environment is no longer a violation and a
  label's digits (`eq:m200`) no longer enter the number set as `00`.
- **The unit narrowing went too far.** Requiring adjacency or LaTeX spacing
  removed the false positives but also stopped catching `1.5 Mpc` → `1.5 kpc`,
  a factor-1000 physics error, in the gate whose whole job is to catch it. A
  space-separated token is protected again when it is in a closed unit
  vocabulary — keeping `in 2020 we found` unprotected and `1.5 Mpc` protected.
- **The math category is now case-sensitive.** `_normalized` lowercases, so a
  `\Delta\Sigma` → `\delta\Sigma` substitution — a different physical
  quantity — passed as fully faithful.
- **The headline evidence table did not reproduce.** The bucket counts were
  measured before the ligature fix landed in this same release, so three of
  seven numbers were stale. Re-measured against the tagged code: `method` 1770 →
  1671, `discussion` 43 → 97, `conclusion` 30 → 50, `results` 0 → 10, total
  1957 → 1942.
- Documentation overstatements corrected: §12's release gate was half-updated
  (v0.27.0's suite size beside v0.26.2's check count), and the rewritten README
  generalised a true statement about *findings* into a false one about *tools*
  (10 of the 24 entries emit none).

### Verification

`validate_plugin.py` 9/9 checks pass; the suite is **208 tests in 15 files**
(was 172 in 14), all green, with every new test written to fail against the
pre-fix code — including one regression test per confirmed review finding.

Older entries: [CHANGELOG-ARCHIVE.md](CHANGELOG-ARCHIVE.md) (v0.19.0-v0.26.2)
and [CHANGELOG-ARCHIVE-EARLY.md](CHANGELOG-ARCHIVE-EARLY.md) (v0.1.0-v0.18.0).
