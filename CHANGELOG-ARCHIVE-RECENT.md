# Changelog archive — v0.27.1 through v0.29.0

Entries moved out of [CHANGELOG.md](CHANGELOG.md) on 2026-08-26, when the live
changelog passed the repository's 750-line budget. Nothing here is edited; the
history is verbatim.

- Current releases: [CHANGELOG.md](CHANGELOG.md)
- **v0.22.0 through v0.27.0**: [CHANGELOG-ARCHIVE.md](CHANGELOG-ARCHIVE.md)
- **v0.21.0 and earlier**: [CHANGELOG-ARCHIVE-EARLY.md](CHANGELOG-ARCHIVE-EARLY.md)

---

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

### The last L3 question, answered by a third replication

The roadmap carried "a field-topic-robust L3 operating point, **or a recorded
decision that one is not obtainable from this feature set**". Retraining on the
rebuilt 44,576-record bank is the third independent answer, and the three agree:

| negative control | 44,576 | 41,641 | 17,299 |
|---|---:|---:|---:|
| public-generic generated | **0.052** | 0.053 | 0.086 |
| field-topic generated | **0.280** | 0.285 | 0.318 |
| field-jargon-dense generated | **0.393** | 0.410 | 0.417 |

Every movement across a 2.6× bank increase sits inside a single retrain's own
20-split range (field-topic 0.208–0.344), while headline AUC moves the *other*
way, 0.9320 → 0.9518. More data buys the easy contrast and nothing on the one
that matters — a feature-set confound, not a sampling limit. **Decision recorded:
not obtainable from this feature set.** Reopening it needs different features.

That leaves exactly one open item, and it is blocked on labels rather than on
work: human-labelled validation for salience and register.

### Added

- **`tools/eval_docscale.py`** — reproduces the §9 table (human false-flag rate,
  per-tier tail power, rank AUC) through `manifold_operating_point`.
- **`tools/label_findings.py`** — the labelling harness for that last item, built
  to the scheme chosen on 2026-08-26: finding-level labels, one labeller plus a
  blind re-label subset for intra-rater agreement, drafts and published papers
  sampled and reported separately. It calibrates nothing. A stratum under 20
  labels reports `unmeasured` rather than a rate — the instrument that judges
  these axes must not be where 2-of-3 becomes "precision 0.667" — and the
  intra-rater kappa prints as the ceiling no axis can be held above.
- **`tests/_toolpath.py`** — the test suite's own duplicated preamble, collapsed
  the same way the CLI one was; 13 of 16 test files retrofitted, the other three
  refused because they invoke tools as subprocesses and never touch `sys.path`.
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
