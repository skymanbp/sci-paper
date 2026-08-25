# EVALUATION — Learned field similarity, rewrite eligibility, and the author hard set · `sci-paper` v0.27.1

Part of the evaluation record. The hub — evaluation contract, current
axis status, repository verification, release evidence boundary, and the
map of every section — is [`EVALUATION.md`](../EVALUATION.md); read it
first. Section numbers are global across the whole record, so a reference
like "§9.5" means the same thing in every file.

Normative policy lives in [`SCIPAPER_STANDARD.md`](../../SCIPAPER_STANDARD.md);
nothing here can redefine it. All machine-readable findings use the
`sci-paper.feedback.v1` contract.

---

## 7. Learned field-similarity model

The current
`style-profile/wgl/voice_model.joblib` bundle
was **retrained locally on 2026-08-17** (RTX 4060 Ti) after the §2 section-classification
fix changed the curated-field bank, and re-evaluated with the same confound-aware audit.
It supersedes the 2026-07-12 cloud run (RTX PRO 6000 Blackwell; artifacts SHA-256 verified
on retrieval) whose figures this section previously carried. The full machine-readable
audit is
`style-profile/wgl/voice_model_evaluation.json`
(schema `sci-paper.voice-model-evaluation.v1`, `generated_utc` `2026-08-17T05:18:20Z`).

| Metadata | Value |
|---|---:|
| classifier | logistic regression |
| positive-class records (curated field + dated arXiv + public human) | 16,382 |
| negative-class records (generated field + generated public) | 2,265 |
| total records | 18,647 |
| primary grouped-split held-out AUC | 0.9399 |
| primary grouped-split F1 (positive class) | 0.9246 |
| primary grouped-split balanced accuracy | 0.8571 |
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
| overall AUC (raw UID) | 0.9320 | 0.9218 | 0.9416 |
| overall balanced accuracy | 0.8509 | 0.8382 | 0.8642 |
| matched-stratum AUC (section × length × math × field-term) | 0.9236 | 0.9044 | 0.9414 |
| overall AUC (section-normalized UID) | 0.9358 | 0.9280 | 0.9438 |

The matched-stratum AUC stays within ~0.01 of the overall AUC, so the separation is not
merely a topic, length, or mathematical-density artifact. Section-normalizing the UID
features changes overall AUC by only +0.004 on average, so raw UID is not the dominant
lever.

**What the section fix did and did not move.** Comparing this audit against the
pre-rebuild record key by key, every headline figure moved by at most 0.002 in AUC
(primary split 0.9414 → 0.9399; 20-split mean 0.9324 → 0.9320) — the fix does not change
what the model measures or its `degraded` posture. The change is in the per-section audit
strata, which were degenerate before: the `discussion` stratum held a median of 5 positive
rows and some splits contained none at all, so its minimum F1 and recall were both 0.000.
Post-rebuild it holds a median of 19, and those minima are 0.857 and 0.850. The
`conclusion` stratum's smallest split rose from 3 rows to 9. Before the fix the
by-section breakdown of this audit was not measuring section behavior; it was measuring
an empty cell.

### 7.2 Negative controls — the confound the audit exposes

The false-positive rate is the fraction of generated negatives the model wrongly scores
as curated-field-like (mean across 20 splits):

| Generated-negative control | false-positive rate |
|---|---:|
| public-generic AI text | 0.086 |
| field-topic AI text | 0.318 |
| field-jargon-dense AI text | 0.417 |

Generic public AI prose is easy (8.6% FPR), but AI text written in the field's topic and
jargon fools the model 32–42% of the time. The learned score partly measures field
register, so it is unreliable on the exact distribution — field-topic AI prose — that a
manuscript de-AI pass must catch. The retrain moved these rates by at most +0.005, so the
confound is a property of the feature set rather than of one training bank.

### 7.3 Author hard set — true provenance is the yardstick, perception is not

The 75-paragraph hard set carries recorded **true provenance** in its key file: 21
generated (14 RAID, 7 Claude) and 54 human (28 author drafts, 26 published papers). The
author also supplied a perceptual `ai_feel_1to5` rating. These are different signals, and
the provenance is the meaningful one. Every AUC below is reported with a seeded bootstrap
95% interval because the generated subset is small (n=21).

| Question | AUC | 95% CI |
|---|---:|---:|
| Does the **model** score separate true generated from human? (low compatibility = generated) | 0.937 | 0.861–0.990 |
| Can the **author's `ai_feel`** separate the same true provenance? | 0.444 | 0.304–0.582 |

The model separates true AI-vs-human prose well (0.94). The author's single-paragraph
`ai_feel` rating is at chance (0.44, interval spanning 0.5): a decontextualized paragraph
does not carry enough signal for reliable human AI-judgement. Mean `ai_feel` by true
source confirms this — author drafts were rated *most* AI-feeling (2.68) and actual
generated text less so (~2.0), so the perceptual axis does not track provenance.

An earlier version of this section reported an AUC of 0.353 for "low compatibility
predicts strong `ai_feel`" and called it decisive proof that the model measures field
register, not AI-ness. That was wrong: it scored the model against the near-chance
perceptual axis, and with only 8 strong-feel labels its interval is 0.140–0.585, which
straddles 0.5 and is not distinguishable from random. It is retained only as a low-power
secondary line in `voice_model_evaluation.json`, not as evidence about the model.

### 7.4 Release consequence

L3 stays `degraded` with **no operating point** — but for the well-powered reasons, not
the hard-set perception metric:

1. the field-topic and field-jargon-dense negative controls (§7.2, n=167/81 in the
   primary split) show a 32–42% false-positive rate on exactly the AI prose a manuscript
   pass must catch;
2. AI-ness in scientific writing is substantially a document- and cross-paragraph
   property, and no document-level calibration set exists yet (§9).

The provenance result (0.94) shows the model is a useful field-similarity triage signal,
not that it is a calibrated AI detector. [`tools/deai_voice.py`](../../../tools/deai_voice.py)
enforces the degraded posture: an uncalibrated bundle emits only rank-ordered triage,
never a universal cutoff.

### 7.5 Known limitations

- Grouping by source paper reduces same-paper leakage; the matched-stratum result adds
  section/length/math/jargon control, but observational separation is not causal proof.
- The `results` audit stratum exists for the first time but holds n=10, so its per-section
  figures are reported and not interpreted.
- Held-out classification performance alone is insufficient for rewrite ranking outside
  the training distribution; §8 gates ranking on measured calibration.

The earlier cloud bundle was trained with scikit-learn 1.4.2 and emitted an
unpickle-version warning when loaded under a newer local scikit-learn. The 2026-08-17
local retrain resolves it by the mechanism this section predicted: the rebuilt bundle
loads under local scikit-learn 1.8.0 with no warnings.

## 8. Rewrite eligibility

[`tools/rewrite_reward.py`](../../../tools/rewrite_reward.py) checks protected invariants before
ranking. The protected set includes numbers, units, citations, inline mathematics,
uppercase acronyms, comparison direction, negation, and causal direction.

**Three properties of the protected set, recorded rather than implied:**

- **Display math is protected as of v0.27.0.** Both LaTeX projections drop
  `\begin{equation}`/`align`/`gather` bodies by design, so until v0.27.0 every
  category computed from them was blind to displayed equations and a value
  silently changed *inside* one passed as fully faithful. `rewrite_reward` now
  reads those bodies from the raw text, through the same reductions the
  projections apply — comments, the environment wrapper and `\label{}` are
  stripped first, so deleting a commented-out dead equation, renaming a label,
  or switching `equation` to `equation*` are all non-changes. Whitespace is
  normalized, so re-wrapping or re-indenting is not a change. The math category
  is compared **case-sensitively**, because LaTeX control words are: a
  `\Delta\Sigma` → `\delta\Sigma` substitution is a different physical quantity
  and is rejected.
- **A unit is recognised in two forms** (v0.27.0). Bound to its number —
  adjacent, LaTeX-spaced, or `\mathrm{}`/`\text{}`/`%`/`°` — any token counts.
  Separated by a plain ASCII space, the token must be in a closed unit
  vocabulary, because an unrestricted pattern made every word after a numeral a
  protected invariant (`in 2020 we found` yielded unit `we`). **The remaining
  boundary is that vocabulary**: a spaced unit outside it loses unit-level
  protection, though its number stays protected. It gates eligibility only and
  never produces a finding, so a missing entry costs protection on one unit and
  cannot create a false positive.
- **Every candidate being ineligible is exit 1, not exit 2** (v0.27.0). It is a
  measured outcome the caller acts on — preserve the original and regenerate
  tighter — so reporting it as an execution failure made a correct run
  indistinguishable from a crash. Registered in `SCIPAPER_STANDARD` §0.1.

An ineligible candidate receives a combined score of negative infinity. This replaces
the former relative semantic-similarity band, under which a fluent but scientifically
altered candidate could remain competitive.

Current tests in
[`tests/test_rewrite_reward.py`](../../../tests/test_rewrite_reward.py) verify:

- a candidate preserving protected invariants remains eligible;
- dropping a number makes it ineligible;
- dropping a citation makes it ineligible;
- reversing a comparison makes it ineligible.

Section 11 records a source-traced, proposal-only real-manuscript validation. Its
manual review covers entities, scope, stance, logical dependency, and citation support,
which cannot all be reduced to the deterministic token sets. Author disposition and any
application to the manuscript remain pending.

## 10. Hard-set human input

`style-profile/wgl/hardset/deai_hardset_LABEL_ME.csv`
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
