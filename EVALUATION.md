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
| L3 learned field similarity | degraded (confound-audited) | Confound-aware audit complete (§7): repeated grouped-split AUC 0.932, matched-stratum AUC 0.924, but 32–41% false-positive rate on field-topic AI text and author-hard-set AUC 0.354 (below random). | None for calibration: the audit and hard set show the score measures field register, not AI-ness, so no operating point is justified. |
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

The current pre-release working tree passes the validator and all 36 unit/CLI tests.
These commands must be rerun after every subsequent code or release-metadata change; the
final release record must quote the fresh output rather than this intermediate result.

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
was retrained on an expanded corpus and evaluated with the confound-aware audit on
2026-07-12 (cloud run on an RTX PRO 6000 Blackwell GPU; artifacts SHA-256 verified on
retrieval). The full machine-readable audit is
[`style-profile/wgl/voice_model_evaluation.json`](style-profile/wgl/voice_model_evaluation.json)
(schema `sci-paper.voice-model-evaluation.v1`).

| Metadata | Value |
|---|---:|
| classifier | logistic regression |
| positive-class records (curated field + dated arXiv + public human) | 16,394 |
| negative-class records (generated field + generated public) | 2,265 |
| total records | 18,659 |
| primary grouped-split held-out AUC | 0.9414 |
| primary grouped-split F1 (positive class) | 0.9266 |
| primary grouped-split balanced accuracy | 0.8580 |
| feature count | 14 |
| operating point in bundle | absent |
| `measurement_status` | degraded |

The labels represent curated field prose versus generated negative examples. The
resulting probability is exposed as `field_similarity`, not a probability that a human
wrote the paragraph.

### 7.1 Repeated source-grouped audit (20 splits)

Every split holds out complete source papers, retrains logistic regression, and
recomputes `corpus_cos` against a training-only curated centroid so held-out papers
cannot inflate their own similarity feature. Intervals summarize split-to-split
variation; they are not independent-sample confidence intervals.

| Metric | mean | 2.5% | 97.5% |
|---|---:|---:|---:|
| overall AUC (raw UID) | 0.9324 | 0.9220 | 0.9424 |
| overall balanced accuracy | 0.8515 | 0.8378 | 0.8641 |
| matched-stratum AUC (section × length × math × field-term) | 0.9242 | 0.9085 | 0.9416 |
| overall AUC (section-normalized UID) | 0.9366 | 0.9288 | 0.9445 |

The matched-stratum AUC stays within ~0.01 of the overall AUC, so the separation is not
merely a topic, length, or mathematical-density artifact. Section-normalizing the UID
features changes overall AUC by only +0.004 on average, so raw UID is not the dominant
lever.

### 7.2 Negative controls — the confound the audit exposes

The false-positive rate is the fraction of generated negatives the model wrongly scores
as curated-field-like (mean across 20 splits):

| Generated-negative control | false-positive rate |
|---|---:|
| public-generic AI text | 0.086 |
| field-topic AI text | 0.316 |
| field-jargon-dense AI text | 0.412 |

Generic public AI prose is easy (8.6% FPR), but AI text written in the field's topic and
jargon fools the model 32–41% of the time. The learned score partly measures field
register, so it is unreliable on the exact distribution — field-topic AI prose — that a
manuscript de-AI pass must catch.

### 7.3 Author-labelled hard-set calibration — decisive

The 75-paragraph author hard set (§10, now fully labelled) is the only stratum whose
negatives are human-perceived AI-feel judgements rather than generated text, so it is
the calibration path the generated-negative audits structurally cannot provide. Scoring
the shipped model against it:

| Author `ai_feel_1to5` | n | mean compatibility score |
|---|---:|---:|
| 1 (no AI feel) | 20 | 0.624 |
| 2 | 28 | 0.701 |
| 3 | 19 | 0.681 |
| 4 (strong AI feel) | 8 | 0.796 |

AUC for "low compatibility predicts strong author AI-feel" is **0.354** — below random.
The model assigns its *highest* compatibility to the paragraphs the author rated most
AI-feeling. On the deployment task (flagging AI-feel prose inside a human manuscript) the
learned score is anti-correlated with human perception.

### 7.4 Release consequence

L3 stays `degraded` with **no operating point**. The confound audit and the author hard
set together show the learned score tracks curated-field register, not AI-ness, so no
threshold on it is justified as policy. The model remains useful only as rank-based
triage evidence that an author reads alongside the deterministic L0 and the descriptive
L1/L2 axes. [`tools/deai_voice.py`](tools/deai_voice.py) enforces this: an uncalibrated
bundle emits only rank-ordered triage, never a universal cutoff.

### 7.5 Known limitations

- Grouping by source paper reduces same-paper leakage; the matched-stratum result adds
  section/length/math/jargon control, but observational separation is not causal proof.
- The bundle was trained on the cloud with scikit-learn 1.4.2; loading it under a newer
  local scikit-learn emits an unpickle-version warning. The model is gitignored and
  rebuilt per field, so a local rebuild removes the mismatch.
- Held-out classification performance alone is insufficient for rewrite ranking outside
  the training distribution; §8 gates ranking on measured calibration.

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
contains 75 difficult paragraphs. On 2026-07-12 the author supplied all 75
`ai_feel_1to5` labels (distribution: 20×1, 28×2, 19×3, 8×4; no 5s). The labelled hard
set is now the calibration path, evaluated in §7.3.

The result is decisive and negative: the learned score is anti-correlated with the
author's AI-feel judgement (AUC 0.354), so:

- no isotonic or other label-based calibration is claimed;
- no measured author-specific operating point exists or is justified;
- L3 remains `degraded`, and the hard set continues to serve as the reference that any
  future calibration attempt must beat before an operating point is proposed.

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

v0.14.0 release gates and their status on 2026-07-12:

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
