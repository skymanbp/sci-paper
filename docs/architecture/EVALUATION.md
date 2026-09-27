# EVALUATION: de-AI subsystem for `sci-paper` v0.39.0

First recorded 2026-07-12. The profile-dependent figures in §2 were re-taken on the
`wgl` profile rebuilt on 2026-09-27; a row that was not re-taken names the build it
was measured on.

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
| **17** | 17. Held-out refereed papers as labels: register and salience measured (v0.30.0; every re-measurement since is tabled in §17.4) | [`held-out-labels.md`](evaluation/held-out-labels.md) |
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

> **Every section-keyed figure below reads the profile rebuilt on 2026-09-27.** A
> machine holding an older profile must treat every section-keyed axis as
> `degraded`, whatever this table says, until it reruns the rebuild:
> `python tools/build_profile.py --field <field>`, then the `--calibrate`
> commands in `style-profile/README.md`, including a full `train_voice_model.py`
> retrain (§7). The repository ships no baseline (all are gitignored), so a
> fresh clone is `unmeasured` and unaffected. How the paragraph bank reached its
> present shape, and why no count before v0.28.0 compares with one after, is
> recorded once, in [§5](evaluation/lexical-structure-uid.md).

| Axis | Status | Current evidence | Required next evidence |
|---|---|---|---|
| L0 lexical/punctuation | measured | Deterministic Tier A, em-dash, and Tier B cap implementation with CLI regression tests. | Continue regression coverage when policy changes. |
| L1 distribution | degraded (refuted) | §16 (v0.28.0; not re-taken on later builds): measured on 500 human papers against 173 `docval` AI documents, one observation per document. Burstiness reverses sign — adversarial prose is *more* bursty than the human median (1.036 vs 0.775, AUC 0.181) and long-form sits inside the human band (AUC 0.441) — while flagging 7.2% of humans. Signposting has an AUC of 0.247, below chance, and flags 0 of 173 AI documents at the shipped default. | None. `deai_policy.json` is withdrawn as a roadmap item: the statistics do not support an operating point, so the axis stays advisory by measurement rather than by absence. |
| L1 UID | degraded | `style-profile/wgl/uid_baseline.json` records paragraph-level GPT-2-large summaries. | A documented operating point and human false-flag behavior; audit sensitivity to mathematics and jargon. |
| L2 salience hierarchy | measured | §14: per-bucket passage reference from the field's own banks, calibrated on the numeral projection of each passage (abstract 13,970; method 7,209; data 3,098; intro 3,280; discussion 3,051; results 3,337; conclusion 2,018 on the 2026-09-27 rebuild); P(X ≤ x) on a 0.01 quantile grid at nearest rank; abstains where the reference cannot resolve above the gate. The smallest bucket clears the 30-passage floor 67-fold. The p90 gate transfers to 203 held-out refereed papers at 0.2007 per passage (1,975 findings over 9,840 scorable paragraphs) against the 1 − 0.9³ = 0.2710 three-feature union bound, under it as three correlated gates must be, and machine text separates at rank AUC 0.666 on body-word density. §17.5 is the record of the two projection seams that moved this rate; §18.2 of the citation years removed from its numerals; §22 of the numbers held in macros. | Whether an individual advisory is good advice; recall. |
| L0 register | measured | §14: document frequency over 42,237 corpus passages, 53,668 terms (2026-09-27 rebuild); compound-by-rarest-part and macro-subscript handling; native-term controls pass. A `<field>-<variant>` profile whose own bank cannot resolve the 1e-4 gate judges against `<field>` and names the borrowed bank in every finding (§18.5). The false-positive rate is measured: on 203 held-out refereed papers the rule fires 0.0364 times per 1,000 body prose words (56 findings, 22.17% of documents) at rank AUC 0.391 against machine text — more on human prose than on AI drafts — and 87.5% of those flags would be suppressed by the paper's own bank membership. The table closing §17.4 is the one account of how the rate reached this value. Swept 5 → 50 uses, rank AUC stays below 0.5 at every setting (§18.4), and a second population, 22 papers by one author, agrees at 0.411 (§21). | Recall below the 15-use floor. There is no operating point to find: no setting makes this a detector, so the floor buys advisory volume only, and it is cut at 15, the first point where a referee-grade paper is not flagged more often than not. |
| L2 sentence structure | measured for deterministic matches; degraded for strength | `style-profile/wgl/structure_baseline.json` provides section-level reference fractions over 28,439 paragraphs — method 9,654; results 4,065; data 3,953; intro 3,848; discussion 3,739; conclusion 2,747; abstract 433. §23.3 adds the per-bucket human fractions of the three auxiliary families taken from a mentor's comments (paper-as-agent 0.11–0.95%, wh-cleft 0.00–0.22%, modifier stacks 2.6–15.9%). | Author-labelled difficult cases. A calibrated strong-advisory threshold is no longer expected from `deai_policy.json` (§16). |
| L2 collocation | measured | §23.2: per-sentence fraction of adjacent common-word pairs unattested in 42,237 passages (535,517 pairs over 11,368 partner words), leave-one-out reference per bucket at sentence unit (abstract 89,377; method 28,114; intro 14,529; results 12,911; data 12,346; discussion 12,584; conclusion 8,741 on the 2026-09-27 rebuild); p90 gates 0.44–0.58, p95 0.50–0.67. On the first measured draft of a manuscript under review it flagged five of the six mentor-marked phrases present; the document novel-pair fraction separates machine documents from held-out refereed papers at rank AUC 0.703 (7,172 findings on the 203 papers). The document-scope glossary reading (v0.38.0) on the same manuscript: 252 distinct unattested pairs, 42 used twice or more, 16 with a definition cue at first use; the default run's finding set is unchanged (86 before and after, set difference 0). | Whether an individual advisory is good advice; a second generation process (§20's lesson). |
| L4 residue | measured | §23.4: four static rules (self-history, edit-meta, negative-label, and since v0.37.0 the absence rule, §23.4a) and one diff rule, deterministic, strengths set on 203 held-out refereed papers and re-measured on 2026-09-27 on the source as both CLIs read it, comments blanked: strong self-history fires in 20 papers, strong edit-meta in 5 (53 of its 54 hits are `\textcolor{red}`), strong absence in 16; any strong in 38 (18.7%), 24 (11.8%) without the absence rule. The static negative-label rule is ordinary at 26% of papers. | Recall against a labelled edit history; only the author's own drafts can supply it. |
| L0 register zero-hit audit | measured, not a detector | §23.1: every body word with corpus df 0, on both sides of one projection (headings excluded on both). All 203 held-out refereed papers carry zero-hit words, 3.34 per 1,000 body prose words, against 1.05 for the 173 machine documents — rank AUC 0.177, the audit fires more on human prose — so it ships as exhaustive advice with author dispositions, never as a gate. | None as a detector. Whether the mechanical exemptions (attested stem, defined term, proper name) are the right three. |
| L2 document structure | measured | §9: cross-paragraph dispersion calibrated one-observation-per-paper over 504 complete human `wgl` papers and re-scored through the shipped path on 2026-09-27 — human false-flag at the shipped conformal operating point 0.020 (manifold) and 0.042 (role) against nominal α = 0.05, in-sample; length-fair manifold AUC 0.840–0.953 across the natural, adversarial, skeleton and long-form tiers, long-form tail power 0.000. The `docstructure_baseline.json` artifact is gitignored and rebuilt per field. | Continue recalibration when the corpus changes. |
| L3 learned field similarity | degraded (confound-audited) | Confound-aware audit complete (§7): repeated grouped-split AUC 0.9487, matched-stratum AUC 0.9250, hard-set true-provenance AUC 0.937 (2026-09-27 retrain), but a 29–42% false-positive rate on field-topic AI text. Document-level now measured (§9.8): surprisal dispersion (0.757) is weaker than the model-free manifold (0.881) and adds nothing to it, so L3 stays degraded for a measured reason. | None from this feature set: five retrains agree the confound is in the features (§7.0a), so reopening needs a different feature set; the surprisal path is measured not to provide one. |
| L2 cohesion | measured | §19: given/new linkage per paragraph against the field's own bank (abstract 13,966; method 7,138; intro 3,269; results 3,309; data 3,069; discussion 3,022; conclusion 1,988 on the 2026-09-27 rebuild), flagged on the LOW tail at p10. The gate transfers to 203 held-out refereed papers at 11.15% against a 10% design point, in every bucket (6.76%–14.88%), and separates all six machine regimes in `intro` at worst-of-six 0.677 against a 0.489 human-vs-human null. | Whether an individual advisory is good advice; recall. Whether the `intro` separation holds for a second generation process — §20 is what happens when that question is not asked. |
| L2 hedging | measured, restricted to `intro` and `method` | §19: epistemic markers per 1,000 words per SECTION (abstract 10,400; intro 503; method 438; conclusion 384; discussion 329; results 317; data 303 on the 2026-09-27 rebuild). It has no paragraph-scale lower tail — p10 is 0.000 in all seven buckets — so calibration and detection both run at section unit, and each artifact records its own. Restricted to `intro` and `method` by two independent measurements that agree: held-out transfer is 9.09% and 9.62% there against 12.23–14.17% in `data`, `conclusion` and `results`, and worst-of-six AUC is 0.605 (null 0.487) and 0.731 (null 0.442) there, while `discussion`, which transfers at 8.23%, has a regime below chance at 0.421. | Whether the restriction generalizes beyond `wgl`. On `wgl-letter` it is inherited, and the `method` reference sits exactly at the 30-unit floor. |
| Citation placement | **refuted, not shipped** | §20: the v0.32.0 candidate (section-matched AUC 0.866 in `method`) does not hold its sign across generation processes. A second bank from a different model scores 0.053 with no citation instruction and 0.734 with one — one prompt line, a 12.5× density swing, and the two machine extremes bracket the human distribution rather than sitting on one side of it. | None. Reopening requires a statistic that holds its sign across independently produced banks. |
| Rewrite scientific fidelity | measured for protected invariants | Unit tests cover preserved invariants, dropped number, dropped citation, reversed comparison, display-math values and exponents (v0.27.0), and the punctuation/adjacent-word tokenizer boundaries (§8). | Real manuscript before/after demonstration, including scope and stance review. The plain-ASCII-space unit boundary in §8 is an accepted limit ([DISPOSITIONS](DISPOSITIONS.md)): the number stays protected, the unit does not. |

A missing baseline is not interpreted as zero findings.

## 3. Repository verification

The repository validator runs the release checks listed once, in
[`tools/README.md`](../../tools/README.md); the unit and CLI suite covers the rest:

```bash
python tools/validate_plugin.py
python -m unittest discover -s tests -v
```

The working tree passes the validator and all 801 unit/CLI tests (32 test files, collected
2026-09-27). These commands must be rerun after every subsequent code or release-metadata
change; the release record must quote the fresh output rather than a past result.

Figures quoted from a generated profile are pinned by
`tests/test_published_figures.py`, which renders each one from its artifact and
skips, rather than passes, on a clean clone that has none; §18.8 records how it
works and the drift it exists to stop.

## 12. Release evidence boundary

Current release gates (as of 2026-09-27; last tagged release v0.38.0, this release v0.39.0):
`validate_plugin.py` all 11 checks pass and the full unit/CLI suite
(801 tests, 32 files) passes on a clean tree; both are rerun before every tag,
and as of v0.25.1 the hosted CI run on the release commit must also be green
(first green runs: 31133202443 push, 31133215203 manual dispatch).

Earlier releases' gates are recorded with each release in the CHANGELOG and its
archives (v0.14.0's, the first set, in
[`CHANGELOG-ARCHIVE-EARLY.md`](../../CHANGELOG-ARCHIVE-EARLY.md)).

Author decisions outside this record, which do not block a release: accepting or
rejecting the §11 rewrite proposal ([DISPOSITIONS](DISPOSITIONS.md)). The L3
operating point is decided, not open: not obtainable from this feature set (§7.0a).
