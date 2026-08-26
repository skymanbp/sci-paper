# EVALUATION: de-AI subsystem for `sci-paper` v0.31.0

First recorded 2026-07-12; every section-keyed measurement re-derived against the
rebuilt `wgl` profile on 2026-08-17.

## 0. Section map

This record is split across six files so no single one grows past the
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
| **17** | 17. Held-out refereed papers as labels: register and salience measured (v0.30.0, corrected v0.31.0) | [`held-out-labels.md`](evaluation/held-out-labels.md) |

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
> | bucket | v0.27.1 (31 files) | v0.28.0 | v0.29.0 (heading coverage) |
> |---|---:|---:|---:|
> | abstract | 15 | 433 | 433 |
> | intro | 109 | 3,753 | 3,844 |
> | data | 112 | 3,929 | 3,915 |
> | method | 163 | 8,144 | 9,522 |
> | discussion | 118 | 3,088 | 3,653 |
> | conclusion | 48 | 2,533 | 2,610 |
> | results | 26 | **3,118** | **3,964** |
> | **total** | **593** | **25,005** | **27,951** |
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
| L2 salience hierarchy | measured | §14: per-bucket passage reference from the field's own banks (abstract 13,823; method 5,957; data 3,025; intro 3,189; discussion 2,506; results 2,541; conclusion 1,924 after the 2026-08-25 corpus rebuild); P(X ≤ x) on a 0.01 quantile grid; abstains where the reference cannot resolve above the gate. | Whether an individual advisory is good advice; recall. §17.5: the p90 gate **transfers to unseen refereed papers essentially exactly** — 0.2705 measured per passage on 203 held-out ApJ/ApJL/A&A papers against the 1 − 0.9³ = 0.2710 three-feature union bound — and machine text separates at AUC 0.770. Every bucket clears the 30-passage floor by two orders of magnitude. |
| L0 register | measured | §14: document frequency over 41,593 corpus passages, 55,133 terms; compound-by-rarest-part and macro-subscript handling; native-term controls pass. | Recall below the 5-use floor, and now a **measured** false-positive rate: §17.4 puts it at 0.384 findings per 1,000 words on 203 held-out refereed papers (87.2% of documents), with rank AUC 0.148 against machine text — it fires more on human prose than on AI drafts. §17.3: 86.3% of those flags would be suppressed by the paper's own bank membership. The v0.30.0 figures (0.991, 93.6%, AUC 0.080) were 58.7% projection defect: detection read whole files while the corpus df excluded front matter and bibliographies. The operating point needs re-deriving against a held-out target rate. Since v0.30.1 a bank whose resolution (1/n) cannot express the 1e-4 gate reports `degraded` naming the coarseness rather than `measured`: `wgl-letter` at 706 passages was 14.2x coarser and had been running 'df == 0' as its rule. |
| L2 sentence structure | measured for deterministic matches; degraded for strength | `style-profile/wgl/structure_baseline.json` provides section-level reference fractions over 27,951 paragraphs — method 9,522; results 3,964; data 3,915; intro 3,844; discussion 3,653; conclusion 2,610; abstract 433. | Author-labelled difficult cases. A calibrated strong-advisory threshold is no longer expected from `deai_policy.json` (§16). |
| L2 document structure | measured | §9: cross-paragraph dispersion calibrated one-observation-per-paper over 493 complete human `wgl` papers; human false-flag at the shipped conformal operating point 0.0325 (manifold) and 0.0426 (role) against nominal α = 0.05. The `docstructure_baseline.json` artifact is gitignored and rebuilt per field. | Continue recalibration when the corpus changes. |
| L3 learned field similarity | degraded (confound-audited) | Confound-aware audit complete (§7): repeated grouped-split AUC 0.932, matched-stratum AUC 0.924, hard-set true-provenance AUC 0.937, but 32–41% false-positive rate on field-topic AI text. Document-level now measured (§9.8): surprisal dispersion (0.757) is weaker than the model-free manifold (0.881) and adds nothing to it, so L3 stays degraded for a measured reason. | A field-topic-robust operating point with provenance and uncertainty; the surprisal path is measured not to provide one. |
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

The working tree passes the validator and all 315 unit/CLI tests (17 test files, collected
2026-08-27). These commands must be rerun after every subsequent code or release-metadata
change; the release record must quote the fresh output rather than a past result.

## 12. Release evidence boundary

Current release gates (v0.31.0, 2026-08-27): `validate_plugin.py` all 9 checks
pass and the full unit/CLI suite (315 tests, 17 files) passes on a clean tree;
both are rerun before every tag, and as of v0.25.1 the hosted CI run on the
release commit must also be green (first green runs: 31133202443 push,
31133215203 manual dispatch).

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
rejecting the §11 the manuscript rewrite proposal, and whether to ever propose an L3 operating
point (the hard set says not yet).
