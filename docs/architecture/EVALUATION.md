# EVALUATION: de-AI subsystem for `sci-paper` v0.36.1

First recorded 2026-07-12; every section-keyed measurement re-derived against the
rebuilt `wgl` profile on 2026-08-17.

## 0. Section map

This record is split across nine files so no single one grows past the
point of being readable. **This file is the hub**: it carries the
evaluation contract, the current per-axis status table, repository
verification, and the release evidence boundary. Everything else lives in
`evaluation/`, and section numbers stay global — §9.5 is §9.5 wherever it
is cited from.

| Section | Evidence | Where |
|---|---|---|
| **1** | 1. Evaluation contract | this file |
| **2** | 2. Current axis status | this file |
| **3** | 3. Repository verification | this file |
| **4** | 4. L0 behavior | [`lexical-structure-uid.md`](evaluation/lexical-structure-uid.md) |
| **5** | 5. Sentence-structure reference evidence | [`lexical-structure-uid.md`](evaluation/lexical-structure-uid.md) |
| **6** | 6. UID reference evidence | [`lexical-structure-uid.md`](evaluation/lexical-structure-uid.md) |
| **7** | 7. Learned field-similarity model | [`learned-model.md`](evaluation/learned-model.md) |
| **8** | 8. Rewrite eligibility | [`learned-model.md`](evaluation/learned-model.md) |
| **9** | 9. Whole-document cross-paragraph dispersion (the keystone axis) | [`document-scale.md`](evaluation/document-scale.md) |
| **10** | 10. Hard-set human input | [`learned-model.md`](evaluation/learned-model.md) |
| **11** | 11. Real introduction rewrite evaluation | [`narrative-salience-register.md`](evaluation/narrative-salience-register.md) |
| **12** | 12. Release evidence boundary | this file |
| **13** | 13. Blind A/B perceptual panel and the layer-2 tell taxonomy (v0.18.0) | [`narrative-salience-register.md`](evaluation/narrative-salience-register.md) |
| **14** | 14. Salience hierarchy and domain register (v0.26.0) | [`narrative-salience-register.md`](evaluation/narrative-salience-register.md) |
| **15** | 15. Narrative salience: two more refuted features, and two reference nulls (v0.26.1) | [`narrative-salience-register.md`](evaluation/narrative-salience-register.md) |
| **16** | 16. `L1.distribution`: the operating point is refuted, not merely absent (v0.28.0) | [`lexical-structure-uid.md`](evaluation/lexical-structure-uid.md) |
| **17** | 17. Held-out refereed papers as labels: register and salience measured (v0.30.0, corrected v0.31.0, superseded by 18) | [`held-out-labels.md`](evaluation/held-out-labels.md) |
| **18** | 18. Projection symmetry, the register operating point, and citation placement (v0.32.0) | [`projection-and-operating-point.md`](evaluation/projection-and-operating-point.md) |
| **19** | 19. Discourse texture: cohesion and hedging (v0.33.0) | [`discourse-and-citation.md`](evaluation/discourse-and-citation.md) |
| **20** | 20. Citation placement refuted by the second bank (v0.33.0) | [`discourse-and-citation.md`](evaluation/discourse-and-citation.md) |
| **21** | 21. A second held-out population, and the leak that had reopened (2026-08-27) | [`held-out-labels.md`](evaluation/held-out-labels.md) |
| **22** | 22. Numbers held in macros were invisible to the axis that counts numbers (2026-08-27) | [`projection-and-operating-point.md`](evaluation/projection-and-operating-point.md) |
| **23** | 23. Vocabulary the field never wrote, sentence families from a mentor's comments, the removal map, and the residue an edit leaves (v0.36.0) | [`vocabulary-and-residue.md`](evaluation/vocabulary-and-residue.md) |

## 1. Evaluation contract

This file records current measurements, unavailable evidence, and known confounds.
It is not normative policy. The policy authority is
[`SCIPAPER_STANDARD.md`](../SCIPAPER_STANDARD.md), and the implementation
architecture is [`DEAI_SUBSYSTEM.md`](DEAI_SUBSYSTEM.md).

All machine-readable findings use the `sci-paper.feedback.v1` contract. The learned
task and structural detectors provide scientific-writing similarity and triage
evidence. They do not identify an author and do not produce a universal paper PASS/FAIL
result.

## 2. Current axis status

> ### ⚠️ Every section-keyed figure below is post-2026-08-25. Rebuild before reading them.
>
> Two rounds of corpus-layer defects were fixed on 2026-08-25 and the profile
> was rebuilt against both. **A machine still holding an older profile must
> treat every section-keyed axis below as `degraded`, whatever this table
> says**, until it reruns the rebuild. The repository ships no baseline (all
> are gitignored), so a fresh clone is `unmeasured` and unaffected.
>
> **Round 1 — section labels.** `classify_section` matched titles in the
> singular only, so `Results`/`Conclusions`/`Systematics` fell to `method`;
> `method` was itself the default bucket and absorbed every unnamed heading;
> PDF table cells were accepted as headings and PDF "paragraphs" were line
> fragments. An unrecognised heading is now `unknown` and is dropped rather
> than guessed.
>
> **Round 2 — what counts as a paper.** The corpus layer treated a *file* as a
> paper and could only see the three curated tiers. Four consequences, each
> measured: `\include` fragments counted as separate papers (one review entered
> every distribution twelve times); selecting the root instead lost the body it
> includes (72 words in place of 64,657); the root-selector and the reader
> resolved `\input` targets differently, costing four arXiv bundles most of
> their prose; and a `\subsection` did not inherit its `\section`, sending
> 54.8% of all section words to `unknown`. Separately, the 500-paper
> `fulltext-arxiv/` breadth corpus — already on disk for §9 — was invisible to
> every paragraph-level baseline.
>
> | bucket | v0.27.1 (31 files) | v0.28.0 | v0.29.0 (heading coverage) | v0.32.0 (citation fix) |
> |---|---:|---:|---:|---:|
> | abstract | 15 | 433 | 433 | 433 |
> | intro | 109 | 3,753 | 3,844 | 3,840 |
> | data | 112 | 3,929 | 3,915 | 3,908 |
> | method | 163 | 8,144 | 9,522 | 9,512 |
> | discussion | 118 | 3,088 | 3,653 | 3,647 |
> | conclusion | 48 | 2,533 | 2,610 | 2,609 |
> | results | 26 | **3,118** | **3,964** | **3,958** |
> | **total** | **593** | **25,005** | **27,951** | **27,907** |
>
> Consequences, stated rather than smoothed over:
>
> - **Every bucket now clears the 30-passage floor**, `results` by 104×. No
>   bucket is rank-only, and the `results` limitation recorded since v0.27.0 is
>   cleared — the binding constraint was never corpus availability but a
>   corpus layer that could not see it.
> - The curated tiers and the breadth corpus are **distinct roles**. The tiers
>   carry every weighted aggregate and the dossier; the breadth corpus is
>   unweighted and feeds the reference distributions only, so it cannot restyle
>   the imitation target. `retrieve_exemplars` reads the curated tiers by
>   default.
> - Register composition changes materially and for the better: abstracts fall
>   from 96% of the reference to 35%.
> - One arXiv bundle in 500 still loses 35% of its prose — it ships chapter
>   files with no root that assembles them.
>
> Rebuild: `python tools/build_profile.py --field <field>` then the
> `--calibrate` commands listed in `style-profile/README.md`, including a full
> `train_voice_model.py` retrain (§7).

| Axis | Status | Current evidence | Required next evidence |
|---|---|---|---|
| L0 lexical/punctuation | measured | Deterministic Tier A, em-dash, and Tier B cap implementation with CLI regression tests. | Continue regression coverage when policy changes. |
| L1 distribution | degraded (refuted) | §16: measured on 500 human papers against 173 `docval` AI documents, one observation per document. Burstiness reverses sign — adversarial prose is *more* bursty than the human median (1.036 vs 0.775, AUC 0.181) and long-form sits inside the human band (AUC 0.441) — while flagging 7.2% of humans. Signposting has an AUC of 0.247, below chance, and flags 0 of 173 AI documents at the shipped default. | None. `deai_policy.json` is withdrawn as a roadmap item: the statistics do not support an operating point, so the axis stays advisory by measurement rather than by absence. |
| L1 UID | degraded | `style-profile/wgl/uid_baseline.json` records paragraph-level GPT-2-large summaries. | A documented operating point and human false-flag behavior; audit sensitivity to mathematics and jargon. |
| L2 salience hierarchy | measured | §14: per-bucket passage reference from the field's own banks (abstract 13,971; method 6,959; data 3,016; intro 3,264; discussion 2,958; results 3,206; conclusion 1,994 after the 2026-08-26 author-query sweep); P(X ≤ x) on a 0.01 quantile grid; abstains where the reference cannot resolve above the gate. | Whether an individual advisory is good advice; recall. §17.5: the p90 gate **transfers to unseen refereed papers essentially exactly** — 0.2775 measured per passage on 203 held-out ApJ/ApJL/A&A papers against the 1 − 0.9³ = 0.2710 three-feature union bound — and machine text separates at AUC 0.772. §18.2: 7.00% of the digits this axis read on LaTeX were citation years, now removed; 0 of its 2,759 findings on those papers start on a bibliography line. §22: the same class in the other direction — a quantity written as `\newcommand{\Nfields}{63}` was unreadable at its use site and mis-attributed to the preamble at its definition site; expansion now runs once on the assembled root. 88.2% of 390 corpus documents never use the construction, and both rebuilt baselines move by **zero to four decimals** at the p90 and p95 gates in all seven buckets, so no figure here changes. Every bucket clears the 30-passage floor by two orders of magnitude. |
| L0 register | measured | §14: document frequency over 41,710 corpus passages, 53,414 terms; compound-by-rarest-part and macro-subscript handling; native-term controls pass. Since v0.32.0 a `<field>-<variant>` profile whose own bank cannot resolve the 1e-4 gate judges against `<field>` and names the borrowed bank in every finding: on 36 letter-format documents the 706-passage `wgl-letter` bank produced 262 findings the field bank did not (`sne`, `bao`, `pantheon`, and `letter` itself) against 2 the other way (§18.5). | Recall below the 15-use floor, and a **measured** false-positive rate: §18.4 put it at 0.0858 findings per 1,000 words on 203 held-out refereed papers (44.83% of documents), rank AUC 0.2856 against machine text — it still fires more on human prose than on AI drafts — and §23.1 re-measures the same papers at 0.0351 (30.05%, AUC 0.352) after the heading projection fix and at 0.0247 (22.2%, AUC 0.392) after v0.36.1's float projection fix, same direction. §17.3, re-measured: 94.44% of the 198 remaining flags would be suppressed by the paper's own bank membership (98.2% of the 57 under v0.36.1). The operating point is no longer an open item: swept 5→50 uses, rank AUC stays below 0.5 everywhere, so no setting makes this a detector and the knob buys advisory volume only. It was cut at 15, the first point where a referee-grade paper is not flagged more often than not (§18.4). §21 replicates that refutation on a second population — 22 papers by one author, 1996–2015, sampled by author rather than by journal and spanning a different two decades — where rank AUC is **0.328**, again below 0.5. |
| L2 sentence structure | measured for deterministic matches; degraded for strength | `style-profile/wgl/structure_baseline.json` provides section-level reference fractions over 27,907 paragraphs — method 9,512; results 3,958; data 3,908; intro 3,840; discussion 3,647; conclusion 2,609; abstract 433. §23.3 adds the per-bucket human fractions of the three auxiliary families taken from a mentor's comments (paper-as-agent 0.13–1.00%, wh-cleft 0.00–0.23%, modifier stacks 2.5–15.9%). | Author-labelled difficult cases. A calibrated strong-advisory threshold is no longer expected from `deai_policy.json` (§16). |
| L2 collocation | measured | §23.2: per-sentence fraction of adjacent common-word pairs unattested in 41,710 passages, leave-one-out reference per bucket at sentence unit (abstract 90,202; method 27,575; intro 14,478; results 12,602; data 12,339; discussion 12,336; conclusion 8,653); p90 gates 0.44–0.60, p95 0.50–0.67. Flags five of the six mentor-marked phrases present in the private Letter; the document novel-pair fraction separates machine documents from held-out refereed papers. | Whether an individual advisory is good advice; a second generation process (§20's lesson). |
| L4 residue | measured | §23.4: three static rules and one diff rule, deterministic, strengths set on 203 held-out refereed papers (85,324 prose sentences): strong self-history fires in 20 papers, strong edit-meta in 15 (all `\textcolor{red}` in tables), any strong in 34 (16.7%); the static negative-label rule is ordinary at 29% of papers. Three passes to get there, the first a projection asymmetry. | Recall against a labelled edit history; only the author's own drafts can supply it. |
| L0 register zero-hit audit | measured, not a detector | §23.1: every body word with corpus df 0, on both sides of one projection (headings now excluded on both). All 203 held-out refereed papers carry zero-hit words, 2.21 per 1,000 words under v0.36.1's float projection (2.66 before it), against 0.98 for the 173 machine documents — rank AUC 0.246, the audit fires more on human prose — so it ships as exhaustive advice with author dispositions, never as a gate. The two projection fixes moved the thresholded rule from 0.0858 to 0.0247 findings per 1,000 words on the same papers. | None as a detector. Whether the mechanical exemptions (attested stem, defined term) are the right three. |
| L2 document structure | measured | §9: cross-paragraph dispersion calibrated one-observation-per-paper over 493 complete human `wgl` papers; human false-flag at the shipped conformal operating point 0.0325 (manifold) and 0.0426 (role) against nominal α = 0.05. The `docstructure_baseline.json` artifact is gitignored and rebuilt per field. | Continue recalibration when the corpus changes. |
| L3 learned field similarity | degraded (confound-audited) | Confound-aware audit complete (§7): repeated grouped-split AUC 0.932, matched-stratum AUC 0.924, hard-set true-provenance AUC 0.937, but 32–41% false-positive rate on field-topic AI text. Document-level now measured (§9.8): surprisal dispersion (0.757) is weaker than the model-free manifold (0.881) and adds nothing to it, so L3 stays degraded for a measured reason. | A field-topic-robust operating point with provenance and uncertainty; the surprisal path is measured not to provide one. |
| L2 cohesion | measured | §19: given/new linkage per paragraph against the field's own bank (abstract 13,967; method 6,903; intro 3,252; results 3,183; data 2,992; discussion 2,932; conclusion 1,975), flagged on the LOW tail at p10. The gate transfers to 203 held-out refereed papers at 10.87% against a 10% design point, in every bucket (6.58%–14.63%), and separates all six machine regimes in `intro` at worst-of-six 0.676 against a 0.515 human-vs-human null. | Whether an individual advisory is good advice; recall. Whether the `intro` separation holds for a second generation process — §20 is what happens when that question is not asked. |
| L2 hedging | measured, restricted to `intro` | §19: epistemic markers per 1,000 words per SECTION (abstract 10,404; intro 502; method 438; conclusion 382; discussion 327; results 316; data 299). It has no paragraph-scale lower tail — p10 is 0.000 in all seven buckets — so calibration and detection both run at section unit, and each artifact records its own. Restricted to `intro` by two independent measurements that agree: held-out transfer is 7.89% there against 15.48–26.77% elsewhere, and worst-of-six AUC is 0.613 (null 0.460) there while `conclusion` runs below chance at 0.376. | Whether the restriction generalizes beyond `wgl`. On `wgl-letter` the axis is `degraded`: no bucket clears the 30-unit floor after the restriction. |
| Citation placement | **refuted, not shipped** | §20: the v0.32.0 candidate (section-matched AUC 0.866 in `method`) does not hold its sign across generation processes. A second bank from a different model scores 0.053 with no citation instruction and 0.734 with one — one prompt line, a 12.5× density swing, and the two machine extremes bracket the human distribution rather than sitting on one side of it. | None. Reopening requires a statistic that holds its sign across independently produced banks. |
| Rewrite scientific fidelity | measured for protected invariants | Unit tests cover preserved invariants, dropped number, dropped citation, reversed comparison, display-math values and exponents (v0.27.0), and the punctuation/adjacent-word tokenizer boundaries (§8). | Real manuscript before/after demonstration, including scope and stance review; the plain-ASCII-space unit boundary in §8 remains open. |

A missing baseline is not interpreted as zero findings.

## 3. Repository verification

The repository validator checks manifest/version agreement, skill contract references,
product registries, Python syntax, runtime imports, CLI entry points, feedback schema,
linter exit semantics, Tier B cap behavior, tests, and CI wiring:

```bash
python tools/validate_plugin.py
python -m unittest discover -s tests -v
```

The working tree passes the validator and all 465 unit/CLI tests (23 test files, collected
2026-09-04). These commands must be rerun after every subsequent code or release-metadata
change; the release record must quote the fresh output rather than a past result.

Figures quoted from a generated profile are pinned the same way, by
`tests/test_published_figures.py`: each one is rendered *from* the artifact it
came from and then looked for, so a document that quotes a number the artifact
no longer holds fails. Those artifacts are gitignored and no CI runner can see
them, so on a clean clone the cases **skip** rather than pass — absence is
reported as absence, which is the same rule this record applies to every axis.
The three drift events it exists to stop are recorded in §18.8.

## 12. Release evidence boundary

Current release gates (as of 2026-09-04; last tagged release v0.36.0):
`validate_plugin.py` all 10 checks pass and the full unit/CLI suite
(465 tests, 23 files) passes on a clean tree; both are rerun before every tag,
and as of v0.25.1 the hosted CI run on the release commit must also be green
(first green runs: 31133202443 push, 31133215203 manual dispatch).

A v0.28.0-specific gate applies because this release changes what the corpus
layer reads: no figure may be carried forward on assertion. Every section-keyed
number here was re-read from the rebuilt artifact in the pass that wrote it, and
§9 — which was not regenerated by the rebuild — was re-scored through the
shipped path so its reproduction is a per-value comparison across eight AUCs
rather than a matching total. Where a figure moved, both values are printed.

Historical record — v0.14.0 release gates and their status on 2026-07-12:

- validator and 36 unit/CLI tests after final edits — met (rerun before tag);
- independent multi-agent review and fixes — met: an adversarially verified Opus review
  (4 dimensions × 2 verifiers per finding) confirmed 16 findings, all fixed this cycle;
- real introduction rewrite evidence — met (§11, proposal-only, author disposition
  pending);
- confound-aware learned-model status with an explicit degraded result — met (§7): the
  audit and author hard set keep L3 degraded with no operating point;
- documentation and release metadata — updated for this release;
- clean-checkout verification — performed before tag;
- commit, tag, push, and GitHub release — performed after the gates above are re-run
  green.

Author decisions that remain open and do not block the plugin release: accepting or
rejecting the §11 rewrite proposal, and whether to ever propose an L3 operating
point (the hard set says not yet).
