# EVALUATION: de-AI subsystem for `sci-paper` v0.23.0

First recorded 2026-07-12; axis table and repository-verification counts current as of
2026-08-06.

## 1. Evaluation contract

This file records current measurements, unavailable evidence, and known confounds.
It is not normative policy. The policy authority is
[`SCIPAPER_STANDARD.md`](SCIPAPER_STANDARD.md), and the implementation
architecture is [`DEAI_SUBSYSTEM.md`](DEAI_SUBSYSTEM.md).

All machine-readable findings use the `sci-paper.feedback.v1` contract. The learned
task and structural detectors provide scientific-writing similarity and triage
evidence. They do not identify an author and do not produce a universal paper PASS/FAIL
result.

## 2. Current axis status

| Axis | Status | Current evidence | Required next evidence |
|---|---|---|---|
| L0 lexical/punctuation | measured | Deterministic Tier A, em-dash, and Tier B cap implementation with CLI regression tests. | Continue regression coverage when policy changes. |
| L1 distribution | degraded | Field sentence/connective summaries exist; compatibility thresholds are not a documented policy operating point. | `deai_policy.json` with corpus unit, uncertainty, applicability, and validation behavior. |
| L1 UID | degraded | [`style-profile/wgl/uid_baseline.json`](../style-profile/wgl/uid_baseline.json) records paragraph-level GPT-2-large summaries. | A documented operating point and human false-flag behavior; audit sensitivity to mathematics and jargon. |
| L2 sentence structure | measured for deterministic matches; degraded for strength | [`style-profile/wgl/structure_baseline.json`](../style-profile/wgl/structure_baseline.json) provides section-level reference fractions. | Calibrated strong-advisory thresholds and author-labelled difficult cases. |
| L2 document structure | measured | §9: cross-paragraph dispersion calibrated one-observation-per-paper over 14 complete human `wgl` papers; leave-one-paper-out false-flag rate ~0.07 at n=14. The `docstructure_baseline.json` artifact is gitignored and rebuilt per field. | Continue recalibration when the corpus changes. |
| L3 learned field similarity | degraded (confound-audited) | Confound-aware audit complete (§7): repeated grouped-split AUC 0.932, matched-stratum AUC 0.924, hard-set true-provenance AUC 0.937, but 32–41% false-positive rate on field-topic AI text. Document-level now measured (§9.8): surprisal dispersion (0.757) is weaker than the model-free manifold (0.881) and adds nothing to it, so L3 stays degraded for a measured reason. | A field-topic-robust operating point with provenance and uncertainty; the surprisal path is measured not to provide one. |
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

The working tree passes the validator and all 115 unit/CLI tests (11 test files, collected
2026-08-06). These commands must be rerun after every subsequent code or release-metadata
change; the release record must quote the fresh output rather than a past result.

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
[`tests/test_ai_ism_lint_cli.py`](../tests/test_ai_ism_lint_cli.py).

## 5. Sentence-structure reference evidence

[`style-profile/wgl/structure_baseline.json`](../style-profile/wgl/structure_baseline.json)
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

[`style-profile/wgl/uid_baseline.json`](../style-profile/wgl/uid_baseline.json) records
1,957 paragraphs that met its token requirement. It stores pooled and section-level
means, standard deviations, and counts for global UID, local UID, and mean surprisal
under GPT-2-large.

This supports comparative evidence, but the current subsystem reports degraded status
because the profile does not document an operating point, uncertainty-to-action rule,
or leave-source-out human flag behavior. The values must not be turned into a universal
threshold.

## 7. Learned field-similarity model

The current
[`style-profile/wgl/voice_model.joblib`](../style-profile/wgl/voice_model.joblib) bundle
was retrained on an expanded corpus and evaluated with the confound-aware audit on
2026-07-12 (cloud run on an RTX PRO 6000 Blackwell GPU; artifacts SHA-256 verified on
retrieval). The full machine-readable audit is
[`style-profile/wgl/voice_model_evaluation.json`](../style-profile/wgl/voice_model_evaluation.json)
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

### 7.3 Author hard set — true provenance is the yardstick, perception is not

The 75-paragraph hard set carries recorded **true provenance** in its key file: 21
generated (14 RAID, 7 Claude) and 54 human (28 author drafts, 26 published papers). The
author also supplied a perceptual `ai_feel_1to5` rating. These are different signals, and
the provenance is the meaningful one. Every AUC below is reported with a seeded bootstrap
95% interval because the generated subset is small (n=21).

| Question | AUC | 95% CI |
|---|---:|---:|
| Does the **model** score separate true generated from human? (low compatibility = generated) | 0.937 | 0.860–0.990 |
| Can the **author's `ai_feel`** separate the same true provenance? | 0.444 | 0.304–0.582 |

The model separates true AI-vs-human prose well (0.94). The author's single-paragraph
`ai_feel` rating is at chance (0.44, interval spanning 0.5): a decontextualized paragraph
does not carry enough signal for reliable human AI-judgement. Mean `ai_feel` by true
source confirms this — author drafts were rated *most* AI-feeling (2.68) and actual
generated text less so (~2.0), so the perceptual axis does not track provenance.

An earlier version of this section reported an AUC of 0.354 for "low compatibility
predicts strong `ai_feel`" and called it decisive proof that the model measures field
register, not AI-ness. That was wrong: it scored the model against the near-chance
perceptual axis, and with only 8 strong-feel labels its interval is 0.141–0.588, which
straddles 0.5 and is not distinguishable from random. It is retained only as a low-power
secondary line in `voice_model_evaluation.json`, not as evidence about the model.

### 7.4 Release consequence

L3 stays `degraded` with **no operating point** — but for the well-powered reasons, not
the hard-set perception metric:

1. the field-topic and field-jargon-dense negative controls (§7.2, n=167/81) show a
   32–41% false-positive rate on exactly the AI prose a manuscript pass must catch;
2. AI-ness in scientific writing is substantially a document- and cross-paragraph
   property, and no document-level calibration set exists yet (§9).

The provenance result (0.94) shows the model is a useful field-similarity triage signal,
not that it is a calibrated AI detector. [`tools/deai_voice.py`](../tools/deai_voice.py)
enforces the degraded posture: an uncalibrated bundle emits only rank-ordered triage,
never a universal cutoff.

### 7.5 Known limitations

- Grouping by source paper reduces same-paper leakage; the matched-stratum result adds
  section/length/math/jargon control, but observational separation is not causal proof.
- The bundle was trained on the cloud with scikit-learn 1.4.2; loading it under a newer
  local scikit-learn emits an unpickle-version warning. The model is gitignored and
  rebuilt per field, so a local rebuild removes the mismatch.
- Held-out classification performance alone is insufficient for rewrite ranking outside
  the training distribution; §8 gates ranking on measured calibration.

## 8. Rewrite eligibility

[`tools/rewrite_reward.py`](../tools/rewrite_reward.py) checks protected invariants before
ranking. The protected set includes numbers, units, citations, inline mathematics,
uppercase acronyms, comparison direction, negation, and causal direction.

An ineligible candidate receives a combined score of negative infinity. This replaces
the former relative semantic-similarity band, under which a fluent but scientifically
altered candidate could remain competitive.

Current tests in
[`tests/test_rewrite_reward.py`](../tests/test_rewrite_reward.py) verify:

- a candidate preserving protected invariants remains eligible;
- dropping a number makes it ineligible;
- dropping a citation makes it ineligible;
- reversing a comparison makes it ineligible.

Section 11 records a source-traced, proposal-only real-manuscript validation. Its
manual review covers entities, scope, stance, logical dependency, and citation support,
which cannot all be reduced to the deterministic token sets. Author disposition and any
application to the manuscript remain pending.

## 9. Whole-document cross-paragraph dispersion (the keystone axis)

The architecture reflection ([`DEAI_ARCHITECTURE_ROADMAP.md`](DEAI_ARCHITECTURE_ROADMAP.md))
identified the document scale as the confound-orthogonal signal: field register shifts the
*level* of per-paragraph features, while AI-uniformity compresses their *spread* across a
document, which no per-paragraph score can see (the 32–41% field-topic FPR of §7.2).

[`tools/deai_docstructure.py`](../tools/deai_docstructure.py) now measures, per model-free
per-paragraph feature, the cross-paragraph dispersion of a complete document
(`deai_features.cross_paragraph_dispersion`), and flags a document that varies a feature
below the human low tail. Calibrated one-observation-per-paper over 14 complete human
`wgl` papers (multi-file papers concatenated to avoid pseudoreplication), the
`L2.document_structure` axis is now `measured`. Leave-one-paper-out false-flag rates sit
near the nominal low percentile (~0.07 at n=14). The `docstructure_baseline.json` artifact
is gitignored and rebuilt per field.

### 9.1 Validation against AI documents, including an adversarial de-AI tier

A held-out document-level validation set was built with the same generation pipeline used
for the paragraph negatives: 20 natural AI-drafted `wgl` documents (no length or structure
constraint) and their de-AI-rewritten versions (the sci-paper de-AI standard applied as an
adversarial attack: em-dashes removed, Tier-A/B words stripped, paragraph shapes explicitly
told to vary). Scoring the model-free dispersion aggregate (low dispersion → AI), with
seeded bootstrap 95% intervals:

| Contrast (7 length-independent features) | AUC | 95% CI |
|---|---:|---:|
| human vs natural AI | 0.990 | 0.954–1.000 |
| human vs de-AI'd AI (paragraph-level de-AI attack) | 1.000 | 1.000–1.000 |
| human vs **adversarial-varied** AI (deliberate raggedness) | 0.846 | 0.662–0.992 |
| human vs adversarial-varied AI, all 11 features (incl. length) | 0.643 | 0.425–0.842 |

Two attacks, two outcomes. The de-AI rewrite changed 22% of the text and removed all 14
em-dashes, yet the document-level dispersion barely moved (mean score 0.47 → 0.49 versus
human 1.08): **paragraph-level de-AI does not fix a document-level signal**, because
rewriting each paragraph toward a "more human" target still leaves the paragraphs uniform
relative to each other.

The shape adversary's story required the corpus scale-up to resolve, and it resolved in
two stages:

1. **Against the 14 curated papers** the adversary looked only partially effective
   (length-independent AUC 0.846). **Against 195 heterogeneous held-out human papers**
   (the honest protocol: reference median fit on half the humans, AUC computed on the
   never-touched other half) the one-sided low-tail score collapses to **chance**
   (all-features 0.436, CI 0.344–0.534; length-independent 0.512, CI 0.412–0.610),
   while natural AI stays separable (0.928, CI 0.880–0.968) and de-AI'd AI likewise
   (0.946, CI 0.901–0.982). The earlier "bounded power" was an artifact of the narrow
   curated reference. Marginal dispersion *magnitude* is fully gameable.
2. The collapse itself carried the tell: the all-features AUC fell *below* 0.5 — the
   adversary **overshoots**, varying paragraph length more than real humans do. Humans
   occupy a **band** of dispersion; natural AI leaves it on the uniform side, the forced
   adversary leaves it on the over-dispersed side. A two-sided statistic (mean robust z
   of per-feature log dispersion ratios from the human center) **recovers the
   adversarial contrast to AUC 0.801 (CI 0.733–0.867)** while keeping natural at 0.894
   and de-AI'd at 0.932 — on the same held-out protocol.

The shipped detector implements the band view at three levels, calibrated over **507
complete human papers** (the bulk full-text fetch; the reference grew 14 → 507 within
two days):

1. **Joint manifold statistic (primary).** The per-document vector of log dispersion
   ratios is scored by Mahalanobis distance against the human center and covariance
   (pure-stdlib 11-D implementation, ridge-stabilized, clipped log ratios). One
   calibrated aggregate finding (`document-dispersion-manifold`) replaces the
   correlated per-feature "strong" flag spray; per-feature band findings demote to
   ordinary context when the manifold is present. Mixed-length held-out validation
   (242 reference / 242 never-touched test humans): natural AI AUC 0.917 (CI
   0.874–0.951), de-AI'd 0.931 (CI 0.888–0.965), shape-adversarial 0.895 (CI
   0.855–0.930) — part of which section 9.5 later attributes to a document-length
   confound; the length-fair numbers below supersede these as the discrimination
   claims. The joint geometry catches what independent marginals cannot: the adversary
   lands plausible per-feature spreads with the wrong covariance.
2. **Role-coupling statistic (orthogonal axis).** Section 9.4: shape variance
   explained by rhetorical role, permutation-normalized per document
   (`document-role-decoupling`).
3. **Per-feature band flags (context).** Low/high tails at the 5th/95th percentile
   (`document-uniformity` / `document-overdispersion`), median LOO false-flag
   0.051/0.051.

Corpus quantile CIs in the baseline come from a seeded with-replacement bootstrap; an
earlier "deterministic balanced" resampler was a full permutation whenever
gcd(31, n) = 1, so every CI it produced was zero-width — that overstatement is fixed
and the baseline regenerated. The operating points of the two strong document
findings are split-conformal and Mondrian-stratified by document length (section
9.5), which corrected the flag-rate table that previously appeared here: the
unstratified thresholds compared short AI documents against a reference dominated by
longer human papers, overstating power. Current honest operating characteristics are
tabulated in 9.5. On the human corpus the two flag sets at the pre-conformal 5%
tails were exactly disjoint (0 of 507 papers flagged by both; independence would
predict ~1.3), so the axes are complementary rather than redundant. Below
`MIN_MANIFOLD_DOCUMENTS` reference papers the manifold is honestly omitted and the
per-feature flags remain the primary (strong) findings.

### 9.2 Honest limits of this validation

- n is small (14 human, ~14–15 AI per tier); the intervals are wide even where the point
  AUC is 1.0.
- The human corpus is heterogeneous real papers (a review through short letters) and the AI
  set is one generator (Claude) in a narrow format, so some separation reflects
  diverse-corpus-versus-synthetic-batch, not only human-versus-AI. The de-AI'd tier
  surviving is the stronger evidence that the signal is uniformity, not source.
- One field (`wgl`), one generator, one de-AI rewriter. Transfer to other fields,
  generators, and human-AI hybrids is unmeasured.
- The detector reports the *measured* deviation from the human corpus; the AI
  interpretation, though now supported by 9.1, is not asserted in the per-finding message.
- The surprisal + embedding dispersion features were measured in a cloud GPU pass
  (GPT-2-large + MiniLM over 14 human + 48 measurable AI documents; results SHA-256
  verified). The hypothesis that surprisal dispersion would recover the adversarially
  evaded signal — because an author cannot consciously control token predictability —
  was **refuted**: against the adversarial tier, surprisal-only dispersion scores AUC
  0.677 (CI 0.489–0.853, interval spanning chance) and the four model features together
  0.594 (CI 0.395–0.789). Deliberately varying sentence and paragraph shape evidently
  varies the surprisal profile with it. The robust core stays the model-free
  punctuation/clause-rhythm dispersion: excluding length, AUC 0.921 (CI 0.789–1.000)
  with the model features adding nothing (0.914 without them). Including gamed features
  *dilutes* the detector (full 14-feature AUC 0.673). Consequence: the shipped detector
  remains model-free and GPU-free by evidence, not merely by convenience, and feature
  subset choice matters more than model capacity — consistent with the roadmap's
  "the ceiling is unit and distribution, not model capacity."

Paragraph exemplars must not be resampled or relabelled as independent papers to enlarge
the reference; only genuine complete papers are used, and the axis stays `unmeasured` for
documents below the section/paragraph minimums.

### 9.3 Skeleton-matched falsification: the signal is texture, not format

§9.2 conceded that part of the separation could be "diverse real library versus
synthetic batch" — a format artifact rather than an authorship property. The direct
test (frontier idea 7): for 24 human papers from the full-text corpus, extract the
exact structural skeleton (section count, per-section paragraph counts, per-paragraph
sentence counts) and generate one AI paper per skeleton (Claude Sonnet, structure
forced, no style instructions). Compliance gate: identical `document_shape` section
count and total paragraph count within 25% — 17/24 clones pass; 7 excluded (exclusion
only costs power, it cannot inflate the AUC). The manifold is refit on 483 human
papers with all 24 skeleton sources held out, so neither side of each pair is
in-reference.

Result (`skeleton_eval.py`, seeded bootstrap): **paired AUC 0.934 (CI 0.830–1.000)**
for the AI clone versus its own human source under an identical skeleton (AI median
Mahalanobis distance 4.09 versus human 2.67), and 0.921 (CI 0.860–0.968) versus 100
other humans. Decisively, dropping the two count-coupled features the skeleton itself
pins (`n_sentences`, `word_count`) leaves a **texture-only paired AUC of 0.920 (CI
0.810–1.000)** on the remaining 9 features (sentence-length spread, connectives,
hedging, punctuation rhythm, template score). The dispersion-manifold signal therefore
survives exact format matching: it measures how prose texture varies across paragraphs
within a fixed structure, not the structure itself. Limits: 17 pairs is a wide-CI
sample; one generator; sentence counts were requested per paragraph but compliance was
enforced only at the section/paragraph level.

### 9.4 Role-coupled dispersion (frontier idea 1): variation must be explained

The adversarial arc in 9.1 proved dispersion *magnitude* is gameable: forced variety
lands inside (or past) the human band. What forced variety cannot do without actually
reasoning about the content is couple the variation to the argument. Humans vary
paragraph shape *where the argument demands it* — across sections, and between
citing/derivation/prose paragraphs — so part of each paper's shape variance is
explained by rhetorical role. Both AI failure modes (uniform AND forced-ragged) vary
shape at random with respect to role.

Statistic (`deai_features.role_coupling_z` + `deai_docstructure.
document_role_coupling`): per paragraph, the existing 11 model-free shape features;
per role factor, a one-way eta-squared per feature, normalized as a z-score against a
seeded within-document permutation null (200 label shuffles) — raw eta-squared
inflates with group count and shrinks with paragraph count, and the permutation null
removes both biases *under the null*. Under the alternative the z of a fixed true
coupling still grows with paragraph count (the null spread shrinks), so scores are
comparable for testing "no coupling" but not magnitude-calibrated across lengths:
measured on the 507 humans, r(score, paragraphs) = 0.353 and the low-tail-flagged
papers have median 38 paragraphs versus 60 corpus-wide. Short human papers are
over-represented among false flags; this is a known, quantified bias of the operating
point, not of the AUC. No reference fit is needed per document, so score validation
has no train/test leakage. Three factors are measured: which section (`section`),
first/middle/last in section (`position`), has-math × has-cite (`content`).

Factor selection was split-half to avoid post-hoc optimism: on one seeded human half
(253 papers) plus AI-tier halves, `section+content` maximizes mean AUC (0.786) and
beats the 3-factor composite (0.766) because `position` is at chance. The unbiased
headline is therefore the held-out confirmation half: **natural 0.846, de-AI'd 0.833,
adversarial 0.850, skeleton 0.715** (n_ai = 14/8/19/12). Full-set AUC of the shipped
composite is reported for narrower intervals but includes the selection half, so it
carries residual selection optimism:

| tier | full-set AUC | CI95 | n |
|---|---|---|---|
| natural | 0.811 | 0.751–0.864 | 28 |
| de-AI'd | 0.842 | 0.762–0.913 | 15 |
| adversarial | **0.888** | 0.847–0.926 | 38 |
| skeleton | 0.658 | 0.561–0.748 | 24 |

The adversarial tier — the manifold's hardest — is role-coupling's strongest, as the
frontier note predicted: random variety cannot fake role-coupling. The shipped finding
(`document-role-decoupling`, strong advisory) fires on the low tail of the 507-paper
human reference (threshold −0.039, CI [−0.073, 0.006], LOO false-flag 0.053); flag
rates and the disjoint union with the manifold are tabulated in 9.1.

Detection is deliberately one-sided (low tail only). The high side is a constructible
evasion: rigidly repeating one shape within each section while varying it across
sections drives coupling z far above the human range — but that construction walks
directly into the pre-existing `within_section_similarity` strong finding (95th
percentile of the same baseline), which flags exactly repeated within-section shape.
No measured AI tier sits high (adversarial median z = −0.02), so a high threshold
would add human false flags with no demonstrated power; the high tail stays
unthresholded until an adversary tier actually lands there.

Honest limits: (a) skeleton clones transfer part of the coupling — forcing a real
paper's per-section shape skeleton onto AI text reproduces some section-coupled
variance (0.658 AUC, flag rate 0.083), so role-coupling is partially fakeable by
structure cloning, which the manifold catches instead (paired 0.934, 9.3) — the two
axes cover each other's evasion; (b) one field, one generator family; (c) the
`content` factor keys on surface markers (math/cite presence), not semantic roles;
(d) AI-tier n per cell is modest (15–38), so tier CIs are wide; (e) the flagged-paper
length bias quantified above; (f) 1 of 507 reference papers has only one defined
scoring factor (its score pools a different null spread) — measured and negligible.

Length-fair correction (section 9.5): against same-length-stratum humans only, the
role AUCs above shrink to natural 0.703, de-AI'd 0.752, adversarial 0.819, and the
skeleton tier collapses to 0.516 — the skeleton clones' apparent role signal was a
length artifact, while the adversarial complementarity survives length matching.

### 9.5 Split-conformal operating points (frontier idea 8) and the length confound

The percentile thresholds above were in-sample: the same 507 papers fit the manifold
and set its threshold (LOO 0.063 vs nominal 0.05), and the confidence constants were
ungrounded. The shipped operating points are now split-conformal: the manifold is fit
on a proper-training split (304 papers) and its nonconformity scores calibrated on
203 held-out human papers; the role z needs no fit, so all 507 are calibration.
Conformal p = (1 + #{calibration ≥ score}) / (n_cal + 1), flag at p ≤ α = 0.05,
giving P(false flag) ≤ α finite-sample and distribution-free for exchangeable human
papers. Calibration is Mondrian-stratified by document-length terciles (edges 46 and
76 paragraphs) — length is the measured confound (9.4); a thin stratum falls back to
the pooled calibration set, keeping marginal validity. Legacy baselines without the
conformal block fall back to the percentile thresholds.

Stratification exposed a second, larger instance of the same confound: **short human
papers score systematically higher manifold distances** (stratum-0 95th percentile
5.23 versus 4.16/4.36 for longer strata — fewer paragraphs make the dispersion vector
noisier), and every AI validation document is short (all ≤ 46 paragraphs). The
unstratified thresholds therefore compared short AI documents against a mostly-long
human reference, and the flag rates previously reported (manifold 0.607/0.600/0.447/
0.292 across tiers) overstated tail power. At the honest, length-stratified conformal
operating point (α = 0.05) the measured rates are:

| conformal flag | natural | de-AI'd | adversarial | skeleton |
|---|---|---|---|---|
| manifold | 0.071 | 0.133 | 0.026 | 0.125 |
| role-decoupling | 0.107 | 0.333 | 0.316 | 0.042 |
| union | 0.179 | 0.467 | 0.342 | 0.167 |

A three-way replication on an independent split (train 253 / calibration 152 / test
102 humans, seed distinct from the shipped one) gives human test rates manifold 0.029
and role 0.069 — both within binomial noise of α; per-stratum rates on ~33 test
papers wobble (one stratum hit 7/33 on the role axis), which is the expected
conditional-coverage fluctuation at ~50 calibration papers per stratum plus residual
within-bin length correlation, both of which shrink at the shipped calibration sizes
(manifold 60–78, role 167–171 per stratum).

The discrimination signal itself survives length matching — the ranking is real even
where the 5% tail is weak. Length-fair AUC against the 171 same-stratum (short)
humans: manifold natural 0.873 (CI 0.81–0.93), de-AI'd 0.901 (0.83–0.96),
adversarial 0.836 (0.78–0.89), skeleton 0.822 (0.75–0.89) — consistent with the
length-matched-by-construction paired skeleton test (0.934, 9.3); role natural 0.703,
de-AI'd 0.752, adversarial 0.819, skeleton 0.516. The corrected picture: the manifold
carries robust length-fair discrimination against every tier including structure
clones; the role axis's genuine power concentrates on the shape adversary (0.819),
exactly the tier that narrows the manifold's margin (0.836); the skeleton tier's
earlier role signal (0.658) was length, not coupling. Short documents have honestly
weak 5%-tail power on the manifold axis (natural 0.071) because the short-human
distance distribution is heavy-tailed — a length-aware manifold (normalizing
estimator noise by paragraph count) is the natural next refinement and is recorded in
the frontier queue rather than improvised here.

### 9.6 Claim anchoring: hypothesis refuted for strong-model generations

The frontier note predicted unfalsifiable hedged generality ("demonstrates strong
performance" with no number, citation, reference, equation, or comparison) as AI's
durable tell. Measured on the section-class conditional anchored-sentence rates
(`deai_anchoring.py`, calibrated on 517 corpus documents, all six section classes
above the 30-document minimum), the prediction is **refuted for full-paper
generations from a strong model**: every AI tier anchors at or above the human
level, with AUC(human high) far below chance where it matters (methods 0.09–0.20,
results 0.14–0.40 across tiers) — generated papers are dense with (invented)
numbers, citations, and mathematics. The axis therefore ships as a
**writing-quality band, explicitly not an AI-discrimination axis**, and its docstring
and finding text say so.

Two operating-point facts. First, testing each of a document's ~5 measured classes
at α = 0.05 gave a document-level union false-flag rate of 0.170; each class now
tests at the Bonferroni share α/k, and the measured document-level human rate is
**0.037 ≤ α**. Second, the conformal resolution 1/(n+1) must beat α/k — the
production classes (n = 315–512) resolve p ≈ 0.002–0.003, comfortably below the
0.008–0.017 shares. A fully unanchored Results section still flags (functional
test); AI tiers flag at 0.000 under the corrected operating point, consistent with
the refutation.

### 9.7 Partition operators and per-stratum manifolds

`deai_partition.py` closes the detection-repair asymmetry: merge (delete one blank
line) and split (insert one at a low-cohesion sentence boundary) change zero tokens,
so the fidelity invariants hold byte-identically. The greedy band-seeking plan is
suggest-only with a self-normalized cohesion floor (the document's median
adjacent-pair overlap). Efficacy on the docval tiers: of 124 measurable AI
documents, 8 flag at the conformal manifold operating point; the default plan brings
**4 of 8 inside the band (median 1 operation)**, while all 116 unflagged documents
receive zero suggestions (no-harm check). The 4 unfixed documents sit at distance
10.5–11.8: partition operations move count and length dispersion but not punctuation
or clause-rhythm texture, which is the stated limit.

The recorded length-aware refinement is implemented as per-stratum manifolds:
each length stratum that supports its own fit (93–107 training papers) and
calibration (60–78 papers) gets a stratum-local metric, with pooled fallback
(`manifold_operating_point` is the single scoring entry for findings, partition,
and evaluations). Measured effect at α = 0.05: skeleton clones 0.125 → **0.292**,
adversarial 0.026 → 0.053, natural/de-AI'd unchanged (0.071/0.133) — the short-human
distance distribution's heavy tail is intrinsic to an 11-D covariance fit at ~100
documents, so the honest summary stays: strong length-fair AUC (0.82–0.90),
modest 5%-tail power on short documents, structure clones now caught at twice the
rate.

**The `ai_long` tier: the detector's measured frontier.** 29 long-form papers
(9,000–17,000 words requested, paragraph shape left free) were generated to make
strata 1/2 power measurable. The generator's own paragraphing density placed 20 of
29 in stratum 0 regardless (its natural paragraphs are large — 100k+ characters
still yield ~40 measured paragraphs, itself a departure from human density that the
current features do not exploit). Results: manifold flags 0/29, role flags 4/29 —
at the strict 5% operating point the document detectors have almost no tail power
on natural long-form generation. Ranking signal survives: stratum-matched AUC 0.716
(manifold) and 0.639 (role), mixed 0.729 (CI 0.67–0.78) and 0.720 (CI 0.64–0.80).
Honest characterization: for long-form strong-model output, the document axes are
informative as ranked percentile feedback but rarely cross the calibrated flag
threshold; this tier is the standing falsification target for future detector work.

The last recorded measurement debt — a document-level L3 surprisal evaluation —
was run and is resolved in §9.8.

### 9.8 Document-level L3 surprisal, rank-5 enrichment, and the length confound

A bounded cloud pass on 2026-07-13 computed gpt2-large surprisal over 38,319
paragraphs from all 507 human papers and 154 qualifying AI-tier documents
(SHA-verified `l3_surprisal.json`, `d1dd1b7e…`; one NVIDIA B200, ~12 min). For
each feature group the human dispersion manifold was fit on a 60% human split and
scored on the 40% held-out human papers versus each AI tier (pooled held-out
AUC, AI = higher manifold distance):

| feature group | pooled AUC |
|---|---:|
| model-free (11, shipped) | 0.881 |
| surprisal only (3 shipped scalars) | 0.757 |
| enriched surprisal (5, rank 5) | 0.803 |
| model-free + surprisal (14) | 0.878 |
| model-free + surprisal + enriched (19) | 0.871 |

The model-free row reproduces the shipped 0.82–0.90 range (§9.5), validating the
pass. **The L3 document-level debt is measured and refuted**: document-scale
surprisal dispersion (0.757) is weaker than the model-free manifold (0.881), and
adding surprisal to the manifold does not help (0.878, a slight dilution). The
shipped detector stays model-free and GPU-free by measurement at document scale,
as it already was at the paragraph and dispersion scales (§7, §9.2). L3 remains
`degraded`, now for a measured document-level reason rather than an unmeasured
one. **Rank 5 (enriched surprisal) is confirmed but inert**: the five enriched
descriptors (skew, excess kurtosis, predictable-filler rate, Goh–Barabási
burstiness, low-frequency spectral energy) improve the surprisal representation
(0.803 vs 0.757 pooled; +0.09 adversarial, +0.11 skeleton, +0.04 long), but
because surprisal is not in the shipped model-free detector, shipping them would
be dead weight — they are recorded, not added.

**The length-normalization refinement is a measured confound trap.** The frontier
note (§9.5) recorded a follow-up "length-aware manifold that normalizes estimator
noise by paragraph count." Within human papers, manifold distance does fall with
paragraph count (corr −0.30; corr with 1/√n +0.42, the estimator-noise
signature), and naively dividing distance by √(n_paragraphs) lifts the pooled AUC
to 0.929. That gain is a length confound, not a noise correction: human papers
have a median of 60 measured paragraphs while the AI tiers have 11–15 (ai_long
40), so dividing by √n merely amplifies the shorter class. A normalization
calibrated on the human null alone (distance ÷ its human-null trend a + b/√n)
gives 0.752, *below* plain, and a length-matched band of 36–95 paragraphs shows
no gain (0.812 plain vs 0.789 normalized). The shipped per-stratum manifold plus
length-Mondrian conformal (§9.5) is the confound-safe length handling; the naive
refinement is not adopted.

### 9.9 Cooperative-layer tools: provenance and personal baseline (frontier 4, 6)

Two cooperative-layer tools complete the ranked frontier. Neither is an AI
detector; both read only the author's own material and are honestly `unmeasured`
without it.

`deai_provenance.py` (frontier idea 4) matches each current paragraph to its
nearest paragraph in a designated AI-draft ancestor — an earlier file or a git
ref from the author's own history — and labels the span `ai_untouched`,
`lightly_edited`, `rewritten`, or `author_original` by a deterministic token edit
ratio (difflib, no model). It answers "have my edits made this mine?" and flags
spans still essentially the AI draft. With no ancestor it is `unmeasured`, never
a guess.

`deai_personal.py` (frontier idea 6) uses the author's own prior papers as the
dispersion reference: for each shape feature it places the draft's within-document
dispersion in the distribution of the author's own papers. Because that reference
is same-author, same-field, same-jargon, it sidesteps the field-topic confound
behind the classifier's 32–41% false-positive rate entirely — the comparison is
you-versus-you. It flags a draft that varies paragraph shape far less than the
author usually does, and is `unmeasured` below three prior papers.

## 10. Hard-set human input

[`style-profile/wgl/hardset/deai_hardset_LABEL_ME.csv`](../style-profile/wgl/hardset/deai_hardset_LABEL_ME.csv)
contains 75 difficult paragraphs with recorded true provenance in
`deai_hardset_key.csv` (21 generated, 54 human). On 2026-07-12 the author supplied all 75
perceptual `ai_feel_1to5` labels (distribution: 20×1, 28×2, 19×3, 8×4; no 5s), evaluated
in §7.3.

The methodological finding is that single-paragraph perceptual labelling has low
resolution: the author's `ai_feel` separates true provenance only at chance (AUC 0.44),
so it cannot serve as the model's yardstick. Therefore:

- provenance, not perception, is the hard-set label of record;
- no isotonic or other label-based operating point is claimed from this set;
- L3 remains `degraded` on the well-powered field-topic negative controls (§7.4), not on
  the perceptual metric;
- the next calibration effort should build a document-level or multi-paragraph set, where
  AI-ness signal actually lives, rather than adding more single-paragraph perceptual
  labels.

## 11. Real introduction rewrite evaluation

A proposal-only run was completed on 2026-07-12 against the manuscript commit
`[removed]`,
`sec_1_intro.tex` lines 54--76 (paths as of that commit; the draft tree
was dissolved into `papers/manuscripts/the manuscript/` + git history on 2026-08-06). The manuscript was not modified. The target was the announced
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

Current release gates (v0.24.0, 2026-08-06): `validate_plugin.py` all 8 checks
pass and the full unit/CLI suite (115 tests, 11 files) passes on a clean tree;
both are rerun before every tag.

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

## 13. Blind A/B perceptual panel and the layer-2 tell taxonomy (v0.18.0)

Date: 2026-07-14. Subject: the full de-scaffold rewrite of a real 31-page ApJ
draft (the manuscript, weak-lensing pipeline; 71 substantial paragraphs) executed under
a mechanical fidelity gate (8 protected token multiset classes: cites, refs,
labels, byte-frozen floats, byte-frozen display math, inline math, macro
invocations, numeric literals, all multiset-identical before/after).

### 13.1 Protocol

Independent cold-read judge agents, blind to version identity and to each other,
each read the complete assembled main text and return: an `ai_feel_1to5` score
(1 = confidently human, 5 = confidently machine), a tell inventory with verbatim
quotes, and the single strongest machine-feeling passage. Four judges per
version. The panel is a perceptual validation instrument for L2: it measures
what a hostile expert reader actually notices, which the deterministic detectors
can then be tested against.

### 13.2 Case study: tell substitution under score invariance

Three versions of the same document were paneled:

| Version | Mean score | Judge scores | Top tell named |
|---|---|---|---|
| pristine v18 | 2.0 | [2,2,2,2] | announced enumeration scaffolds (4/4 judges; 3x strongest passage) |
| Phase A (de-scaffold) | 2.0 | [2,2,2,2] | antithesis density, aphoristic closers (0/4 mention enumeration) |
| Phase A2 (tell-targeted) | 2.25 | [2,3,2,2] | residual antithesis habit, intro requirement cadence |

The headline result: **the mean score is invariant while the tell inventory
turns over completely.** Removing the dominant tell family (announced
enumeration, 8 instrument findings to 0) did not move the score; judges
saturated on the next stratum (antithesis clusters, aphoristic closers) at the
same perceived intensity. Reading the mean score as "no improvement" is
therefore wrong: the correct diagnostic is which tells the judges name and
whether the previous stratum is gone. Score movement is expected only when the
tell hierarchy is exhausted.

### 13.3 Layer-2 tell taxonomy (panel-derived)

Tells the panel surfaced that the v0.17.0 detectors did not capture:

1. **Antithesis clusters**: "X rather than Y" / "not X but Y" / "X instead of
   Y" as a default sentence engine. Corpus calibration (1,957 human paragraphs,
   wgl field): at least one antithesis in 3.3% of paragraphs, two or more in
   **0.2%**. The the manuscript drafts: two or more in 5.6% of paragraphs (28x the
   human base rate). Captured in `deai_structure` as auxiliary family
   `antithesis-cluster` (threshold: 2 per paragraph).
2. **Short reversal beats**: a setup followed by a reversal sentence of five
   words or fewer ("It would not." / "It does the opposite."). Human base rate:
   **0 of 1,957 paragraphs**. Two instances in the Phase A draft, both
   rewrite-introduced. Captured as auxiliary family `short-reversal`.
3. **Aphoristic "perform rigor" closers**: sentences engineered to sound
   quotable about the method's honesty ("has to earn every claim it makes",
   "runs conservative in the null direction it could cheat in"). No reliable
   lexical pattern exists; this class is documented here as a panel-advisory
   target and handled by targeted rewrite instruction, not a detector.

Auxiliary families emit ordinary advisories under `structure-auxiliary` and are
excluded from `template_score`, so the calibrated document-dispersion manifold
(which consumes `template_score` as a dispersion feature) is unchanged.

### 13.4 Detector-vs-panel cross-validation

The upgraded detector, re-run on all three versions (field profile wgl):

| Version | `structure-template` findings | `structure-auxiliary` findings |
|---|---|---|
| pristine v18 | 8 | 4 |
| Phase A | 0 | 6 (incl. 2 reversal beats) |
| Phase A2 | 0 | 1 |

The auxiliary axis now tracks exactly what the panel reported: Phase A traded
template findings for auxiliary density (including the two rewrite-introduced
reversal beats the panel quoted verbatim), and the A2 targeted revision cut
auxiliary findings 6 to 1 while the fidelity gate stayed PASS on all 8
protected token classes and the document stayed inside the human manifold band
(distance 4.392, conformal p 0.082). Antithesis instances counted by grep fell
23 to 12.

### 13.5 Limits

One document, one field, four judges per version, and judge agents share a
model family: the panel measures a strong-reader perception proxy, not human
referee behavior. The score scale is compressed at the low end (all versions
scored near 2), so the tell-turnover reading, not the score, carries the
signal. The aphoristic-closer class has no detector and relies on
rewrite-instruction coverage; residual instances survive in A2 (the intro
requirement cadence one judge still names).
