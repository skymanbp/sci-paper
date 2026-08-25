# EVALUATION: de-AI subsystem for `sci-paper` v0.27.1

First recorded 2026-07-12; every section-keyed measurement re-derived against the
rebuilt `wgl` profile on 2026-08-17.

## 0. Section map

This record is split across five files so no single one grows past the
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

> ### ⚠️ Section buckets were mis-assigned before v0.27.0 — profile rebuilt 2026-08-17
>
> `extract_style.classify_section` matched section titles in the singular only,
> so `Results`, `Conclusions` and `Systematics` were bucketed as `method`, and
> `Acknowledgements`/`Bibliography` were ingested as prose rather than skipped.
> v0.27.0 fixes both. **Every section-keyed number in §5, §6, §7 and §14 has
> been re-measured against a profile rebuilt with the fixed classifier and now
> reports post-rebuild values.** §15 is unaffected and was left alone: its
> figures come from the abstract and generated banks, which are not section-
> bucketed — verified by comparing the rebuilt artifacts against the pre-rebuild
> snapshot key by key.
>
> The impact is measured, not estimated. Rebuilding the same 31-paper `wgl`
> corpus with the fixed classifier, into a scratch profile root so the shipped
> assets were untouched:
>
> | bucket | pre-fix | post-fix | change |
> |---|---:|---:|---:|
> | abstract | 15 | 15 | 0 |
> | intro | 99 | 99 | 0 |
> | method | 1770 | 1671 | −99 |
> | discussion | 43 | 97 | **+126%** |
> | conclusion | 30 | 50 | **+67%** |
> | results | 0 | 10 | **0 → 10** |
> | **total** | **1957** | **1942** | −15 (back matter now skipped) |
>
> Consequences, stated rather than smoothed over:
>
> - `discussion` and `conclusion` reference distributions change materially;
>   `method` loses 5.6% of its passages, all of them Results/Conclusions prose.
> - `results` exists for the first time but at **n = 10**, below the documented
>   30-passage floor, so that bucket is honestly omitted until the corpus grows.
> - The register corpus loses 15 of 15,599 passages (0.096%) — the back matter
>   that is now skipped, plus the ligature expansion below. Document frequency
>   shifts by less than the 1e-4 threshold's resolution, but it is not zero.
> - **A machine still holding a pre-v0.27.0 profile must treat every
>   section-keyed axis below as `degraded`, whatever this table says**, until it
>   reruns the rebuild. The repository ships no baseline (all are gitignored), so
>   a fresh clone is `unmeasured` and unaffected; this notice is for machines that
>   already hold a pre-v0.27.0 profile.
>
> Rebuild: `python tools/build_profile.py --field <field>` then the
> `--calibrate` commands listed in `style-profile/README.md`. The reference
> profile these measurements are read from was rebuilt that way on 2026-08-17,
> including a full `train_voice_model.py` retrain (§7).

| Axis | Status | Current evidence | Required next evidence |
|---|---|---|---|
| L0 lexical/punctuation | measured | Deterministic Tier A, em-dash, and Tier B cap implementation with CLI regression tests. | Continue regression coverage when policy changes. |
| L1 distribution | degraded | Field sentence/connective summaries exist; compatibility thresholds are not a documented policy operating point. | `deai_policy.json` with corpus unit, uncertainty, applicability, and validation behavior. |
| L1 UID | degraded | `style-profile/wgl/uid_baseline.json` records paragraph-level GPT-2-large summaries. | A documented operating point and human false-flag behavior; audit sensitivity to mathematics and jargon. |
| L2 salience hierarchy | measured | §14: per-bucket passage reference from the field's own banks (abstract n=13,438; method n=1,303); P(X ≤ x) on a 0.01 quantile grid; abstains where the reference cannot resolve above the gate. | Buckets below the 30-passage floor (`results`, n=10); a human-judgement validation set. |
| L0 register | measured | §14: document frequency over 15,584 corpus passages, 41,714 terms; compound-by-rarest-part and macro-subscript handling; native-term controls pass. | Corpus composition bias toward abstract vocabulary; recall below the 5-use floor. |
| L2 sentence structure | measured for deterministic matches; degraded for strength | `style-profile/wgl/structure_baseline.json` provides section-level reference fractions. | Calibrated strong-advisory thresholds and author-labelled difficult cases. |
| L2 document structure | measured | §9: cross-paragraph dispersion calibrated one-observation-per-paper over 14 complete human `wgl` papers; leave-one-paper-out false-flag rate ~0.07 at n=14. The `docstructure_baseline.json` artifact is gitignored and rebuilt per field. | Continue recalibration when the corpus changes. |
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

The working tree passes the validator and all 213 unit/CLI tests (15 test files, collected
2026-08-17). These commands must be rerun after every subsequent code or release-metadata
change; the release record must quote the fresh output rather than a past result.

## 12. Release evidence boundary

Current release gates (v0.27.1, 2026-08-17): `validate_plugin.py` all 9 checks
pass and the full unit/CLI suite (213 tests, 15 files) passes on a clean tree;
both are rerun before every tag, and as of v0.25.1 the hosted CI run on the
release commit must also be green (first green runs: 31133202443 push,
31133215203 manual dispatch).

A v0.27.1-specific gate applies because this release is a measurement write-back
rather than a code change: every section-keyed figure in this document is
re-read from the rebuilt artifact in the same pass that writes it, and the
pre-rebuild snapshot under `.backups/` is compared key by key so a figure that
moved cannot be reported as unchanged.

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
