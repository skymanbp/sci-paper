# EVALUATION: de-AI subsystem for `sci-paper` v0.14.0

Date: 2026-07-12

## 1. Evaluation contract

This file records current measurements, unavailable evidence, and known confounds.
It is not normative policy. The policy authority is
[`docs/SCIPAPER_STANDARD.md`](docs/SCIPAPER_STANDARD.md), and the implementation
architecture is [`docs/DEAI_SUBSYSTEM.md`](docs/DEAI_SUBSYSTEM.md).

All machine-readable findings use the `sci-paper.feedback.v1` contract. The learned
task and structural detectors provide scientific-writing similarity and triage
evidence. They do not identify an author and do not produce a universal paper PASS/FAIL
result.

## 2. Current axis status

| Axis | Status | Current evidence | Required next evidence |
|---|---|---|---|
| L0 lexical/punctuation | measured | Deterministic Tier A, em-dash, and Tier B cap implementation with CLI regression tests. | Continue regression coverage when policy changes. |
| L1 distribution | degraded | Field sentence/connective summaries exist; compatibility thresholds are not a documented policy operating point. | `deai_policy.json` with corpus unit, uncertainty, applicability, and validation behavior. |
| L1 UID | degraded | [`style-profile/wgl/uid_baseline.json`](style-profile/wgl/uid_baseline.json) records paragraph-level GPT-2-large summaries. | A documented operating point and human false-flag behavior; audit sensitivity to mathematics and jargon. |
| L2 sentence structure | measured for deterministic matches; degraded for strength | [`style-profile/wgl/structure_baseline.json`](style-profile/wgl/structure_baseline.json) provides section-level reference fractions. | Calibrated strong-advisory thresholds and author-labelled difficult cases. |
| L2 document structure | unmeasured for `wgl` | The implementation and complete-document calibration tests exist, but no verified `docstructure_baseline.json` exists. | At least three measurable complete papers, with one observation per paper and leave-one-document-out behavior. |
| L3 learned field similarity | degraded | A trained logistic-regression bundle and grouped validation metadata exist. The bundle has no calibrated operating point. | Confound-aware evaluation and an operating point with provenance and uncertainty. |
| Rewrite scientific fidelity | measured for protected invariants | Unit tests cover preserved invariants, dropped number, dropped citation, and reversed comparison. | Real manuscript before/after demonstration, including scope and stance review. |

A missing baseline is not interpreted as zero findings.

## 3. Repository verification

The repository validator checks manifest/version agreement, skill contract references,
product registries, Python syntax, runtime imports, CLI entry points, feedback schema,
linter exit semantics, Tier B cap behavior, tests, and CI wiring:

```bash
python tools/validate_plugin.py
python -m unittest discover -s tests -v
```

The current pre-release working tree passed the validator and all 20 tests before the
documentation and stale-language sweep. These commands must be rerun after every
subsequent code or release-metadata change; the final release record must quote the
fresh output rather than this intermediate result.

## 4. L0 behavior

The linter contract is:

- exit `0`: no L0 targets; advisories may remain;
- exit `1`: one or more L0 targets;
- exit `2`: invalid input, configuration failure, or execution failure.

Current regression cases include:

- advisory-only prose returns `0`;
- Tier A plus em-dash returns `1` without the former `NameError`;
- one Tier B occurrence per section and word returns `0`;
- the second Tier B occurrence in the same section and word returns `1`;
- paragraph-initial `Furthermore,` remains Tier B and is allowed within the cap;
- paragraph-initial `Importantly,` remains a Tier A target;
- `--output` writes JSON without duplicating it to stdout;
- `--top` truncates emitted details without changing full-report totals.

These tests are in
[`tests/test_ai_ism_lint_cli.py`](tests/test_ai_ism_lint_cli.py).

## 5. Sentence-structure reference evidence

[`style-profile/wgl/structure_baseline.json`](style-profile/wgl/structure_baseline.json)
contains 1,952 paragraph observations across its recorded section buckets. The file
records reference fractions for announced enumeration, ordinal runs, tricolon-like
setup/list patterns, anaphora, balanced closers, and aggregate templating.

Interpretation limits:

1. The observations are paragraph-level and cannot calibrate whole-paper shape.
2. A deterministic pattern match is evidence for inspection, not proof of poor prose
   or machine generation.
3. The current baseline does not by itself define a strong-advisory operating point.
4. Author labels for the difficult hard set are absent, so label-based calibration
   has not been performed.

## 6. UID reference evidence

[`style-profile/wgl/uid_baseline.json`](style-profile/wgl/uid_baseline.json) records
1,957 paragraphs that met its token requirement. It stores pooled and section-level
means, standard deviations, and counts for global UID, local UID, and mean surprisal
under GPT-2-large.

This supports comparative evidence, but the current subsystem reports degraded status
because the profile does not document an operating point, uncertainty-to-action rule,
or leave-source-out human flag behavior. The values must not be turned into a universal
threshold.

## 7. Learned field-similarity model

The current
[`style-profile/wgl/voice_model.joblib`](style-profile/wgl/voice_model.joblib) bundle
contains:

| Metadata | Value |
|---|---:|
| classifier | logistic regression |
| positive-class records | 5,949 |
| negative-class records | 2,265 |
| total records | 8,214 |
| grouped validation AUC | 0.9530938210 |
| grouped validation F1 for the positive class | 0.9291497976 |
| grouped validation balanced accuracy | 0.8802943008 |
| feature count | 14 |
| operating point in bundle | absent |

The metadata were read directly from the current bundle on 2026-07-12. The labels
represent curated field prose versus generated negative examples. The resulting
probability is therefore exposed as `field_similarity`, not as a probability that a
human wrote the paragraph.

### Known limitations

- The bundle has no `operating_point`, so [`tools/deai_voice.py`](tools/deai_voice.py)
  reports the axis as `degraded`.
- Grouping by source paper reduces same-paper leakage but does not establish causal
  separation from source, section, length, jargon, or mathematical density.
- The existing feature set includes `word_count`, UID terms, punctuation rates, and
  corpus cosine. Their independent contribution under matched confound strata has not
  been evaluated in the current release cycle.
- Older evaluation text described the output as `P(human)`. That name is retained only
  in legacy class semantics inside the serialized classifier; user-facing output now
  calls it field similarity.
- Held-out classification performance alone is insufficient evidence for rewrite
  ranking outside the training distribution.

### Required confound-aware evaluation

The next evaluation must report performance and score distributions stratified by:

1. source paper;
2. section type;
3. paragraph length;
4. mathematical-placeholder density;
5. jargon density.

It must add math-dense and jargon-dense negative controls, compare the current raw UID
features with a domain-normalized alternative, and state whether the result changes the
operating point or leaves the axis degraded. Any multi-minute retraining belongs on
cloud compute; local runs are limited to smoke tests and metadata inspection.

## 8. Rewrite eligibility

[`tools/rewrite_reward.py`](tools/rewrite_reward.py) checks protected invariants before
ranking. The protected set includes numbers, units, citations, inline mathematics,
uppercase acronyms, comparison direction, negation, and causal direction.

An ineligible candidate receives a combined score of negative infinity. This replaces
the former relative semantic-similarity band, under which a fluent but scientifically
altered candidate could remain competitive.

Current tests in
[`tests/test_rewrite_reward.py`](tests/test_rewrite_reward.py) verify:

- a candidate preserving protected invariants remains eligible;
- dropping a number makes it ineligible;
- dropping a citation makes it ineligible;
- reversing a comparison makes it ineligible.

Section 11 records a source-traced, proposal-only real-manuscript validation. Its
manual review covers entities, scope, stance, logical dependency, and citation support,
which cannot all be reduced to the deterministic token sets. Author disposition and any
application to the manuscript remain pending.

## 9. Whole-document calibration gap

[`tools/deai_docstructure.py`](tools/deai_docstructure.py) and
[`tests/test_deai_docstructure.py`](tests/test_deai_docstructure.py) implement and test
complete-document calibration. The `wgl` profile currently has no
`docstructure_baseline.json` and no verified complete-document calibration corpus has
been designated for this release.

Therefore whole-document findings remain `unmeasured` for `wgl`. Paragraph exemplars
must not be resampled or relabelled as independent papers to fill this gap.

## 10. Hard-set human input

[`style-profile/wgl/hardset/deai_hardset_LABEL_ME.csv`](style-profile/wgl/hardset/deai_hardset_LABEL_ME.csv)
contains 75 difficult paragraphs. On 2026-07-12, all 75 `ai_feel_1to5` cells were
blank. Until the user supplies those labels:

- no isotonic or other label-based calibration is claimed;
- no measured author-specific operating point exists;
- the hard set may be used only as an unlabeled inspection set.

## 11. Real introduction rewrite evaluation

A proposal-only run was completed on 2026-07-12 against the manuscript commit
`[removed]`,
[`sec_1_intro.tex`](../wgl-suite/papers/P-pipeline/drafts/sec_1_intro.tex)
lines 54--76. The manuscript was not modified. The target was the announced
"five elements / First ... Fifth" sequence.

### 11.1 Source and fidelity verification

The original paragraph, the current method description, and its current numerical and
citation sources were read in the same run. In particular:

- [removed]
  `notes/REDACTEDNOTE.md` section T2;
- [unpublished manuscript content removed 2026-08-27]

The selected candidate preserved every deterministic protected invariant from the
source paragraph: numbers, units, citations, inline mathematics/macros, uppercase
acronyms, comparison direction, negation, and causal-direction markers. Manual review
also found no change to named entities, scope, stance, stage order, or claim/evidence
relations. No new fact, number, citation, entity, mechanism, or quantitative qualifier
was added.

### 11.2 Proposed rewrite

> [unpublished manuscript content removed 2026-08-27]

### 11.3 Before/after feedback

Both reports used the same field profile and the deterministic L0, distribution,
sentence-structure, and document-structure axes.

| Measurement | Before | Proposed rewrite |
|---|---:|---:|
| L0 targets | 0 | 0 |
| integrity blockers | 0 | 0 |
| total advisories | 3 | 2 |
| target-paragraph structure finding | announced enumeration | none |
| L1 distribution | degraded | degraded |
| L2 sentence structure | degraded | degraded |
| L2 document structure | unmeasured | unmeasured |

The target finding was removed without forcing unrelated advisories to zero. The two
residual advisories occur in unchanged paragraphs at source lines 10--25 and 27--39;
their disposition remains `pending`. Whole-document shape remains unmeasured because a
single introduction does not contain the required independent section structure. L3
field similarity was not rerun locally because arbitrary-candidate featurization may
cross the project's cloud-only compute boundary; its release status remains `degraded`
for the independent calibration reasons in section 7.

The rewrite remains a proposal until the author accepts or rejects it. It must not enter
the exemplar bank or the the manuscript manuscript before that decision.

## 12. Release evidence boundary

v0.14.0 is not ready to publish until all of the following are current:

- validator and unit/CLI tests after final edits;
- independent `code-reviewer` results and fixes;
- real introduction rewrite evidence;
- confound-aware learned-model status, including an explicit degraded result if the
  audit does not support calibration;
- documentation and release metadata;
- clean-checkout verification;
- commit, tag, push, and GitHub release.
