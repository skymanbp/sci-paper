# De-AI subsystem — architecture reflection and roadmap

Status: design note written 2026-07-12, retained as the reasoning record for why the
document scale is the keystone. It is **not** a status document: the keystone shipped on
2026-07-13, and the current disposition of every ranked item lives in
[`SCIPAPER_STANDARD.md`](../SCIPAPER_STANDARD.md) §11. Complements
[`DEAI_SUBSYSTEM.md`](../architecture/DEAI_SUBSYSTEM.md) (current architecture) and
[`SCIPAPER_STANDARD.md`](../SCIPAPER_STANDARD.md) (normative policy).

The diagnosis below is stated in the present tense of 2026-07-12. Where it says the
document-scale detector is off or uncalibrated, read that as the condition this note was
written to fix, not as the state of the repository.

This note records a multi-lens reflection prompted by a decisive session finding:
the author's own perceptual rating of AI-ness on single paragraphs is at chance
(AUC 0.444 against true provenance), while the learned model separates true
generated-vs-human prose at AUC 0.937 yet mis-flags field-topic AI text 32–41% of
the time. Five independent analyses (granularity, ML/calibration, linguistics,
engineering elegance, adversarial gap) converged on one structural diagnosis.

## 1. Verdict

The architecture is unusually honest, and its center of gravity is one granularity
level below where its own evidence says the signal lives. The load-bearing strengths
are real and must be preserved. The one structural fault: L1 (UID/burstiness),
L2-sentence (templates), and L3 (learned) are three aggregations of a single 14-dim
**per-paragraph** descriptor, all permanently `degraded`, while the one
document-scale detector (`deai_docstructure`) is the highest-value axis and is turned
**off** (no `docstructure_baseline.json`; verified absent) and built on a weak
primitive (cosine over a non-negative 9-vector dominated by two length terms).

## 2. The keystone insight: level vs spread

The deployment-critical failure is field-topic AI at 32–41% false-positive rate,
while overall AUC is 0.937 and the AUC *within the worst jargon stratum stays 0.912*.
That combination is diagnostic: the confound (field register) shifts the **level**
(mean) of features like `corpus_cos`, `mean_surprisal`, and jargon density, whereas
AI-uniformity compresses their **variance across a document**. A per-paragraph model
sees only levels; it cannot see that a whole AI section is unnaturally uniform where a
human section carries a list paragraph, a long-argument paragraph, and a terse-result
paragraph.

The confound-orthogonal signal is **cross-paragraph dispersion**. A single on-topic AI
paragraph looks field-like (so a paragraph score is fooled), but the *spread* of
per-paragraph features across a real human paper is much larger than across an
AI-drafted one. This is exactly the axis no per-paragraph score can express, and it is
why the human `ai_feel` AUC of 0.444 is not a labeling failure but a statement about
the resolution of the paragraph unit itself.

Verified on disk at the time of writing: the whole-document human corpus already exists
(`style-corpus/wgl/`, dozens of `.tex` sources across tiers), and no
`docstructure_baseline.json` was present. The keystone is a wiring-and-calibration
gap, not a data-collection project. (Closed 2026-07-13: the baseline is now calibrated
over 14 complete papers and rebuilt per field — EVALUATION §9.)

## 3. What to keep (do not touch)

1. The `sci-paper.feedback.v1` typed contract: `make_finding` as one object,
   `render_text` and `dump_report` both projecting from one ranked `build_report`
   list (text and JSON cannot diverge), `strong_advisory` derived from the strength
   enum with raise-on-conflict. Structural enforcement, not discipline.
2. The four-state measurement machine (`measured`/`degraded`/`unmeasured`/
   `not_applicable`) with per-detector `axis_status` always printed, so silence is
   never read as clean; and `deai_voice` refusing to invent a 0.5 cutoff when
   degraded (rank-only triage).
3. The deterministic L0 spine and the model-free L2 sentence-template family. The
   only honestly `measured` signals; un-confoundable.
4. The confound audit: per-split training-only centroid (`split_corpus_cos`),
   whole-paper `GroupShuffleSplit`, per-stratum negative controls, seeded bootstrap
   AUC CIs, and correct demotion of the near-chance perceptual axis. This is what
   makes every proposal below testable.
5. The rewrite fidelity gate (`fidelity_eligibility`): the hard bidirectional
   invariant check returning `-inf`. The part a demanding researcher actually trusts.
6. Shipping logistic regression over the higher-AUC-but-OOD-unstable HGB, and keeping
   the learned voice term subordinate behind the hard gate.

## 4. Roadmap (ranked by leverage)

Every step must survive the existing confound audit before earning a `measured`
status, and must keep the ~38 tests green.

**Rank 1 (keystone) — Document-scale detector via cross-paragraph dispersion.**
Reuse the existing per-paragraph 14-dim descriptor unchanged. For each complete
document, compute the dispersion statistics (std, IQR, coefficient of variation,
lag-1 autocorrelation along document order, over-uniformity min-gap) of each feature
within and across sections, plus cross-paragraph template co-occurrence. Emit one
observation per document. Replace `deai_docstructure._shape_vector`'s magic constants
with z-scoring against a human-document reference so the geometry is empirically
defined. Calibrate one-observation-per-paper with the bootstrap-CI + leave-one-
document-out machinery `deai_docstructure.calibrate` already implements, over the
human corpus. Keep the axis honestly `unmeasured` for short papers/Letters below
`MIN_SECTIONS`/`MIN_PARAGRAPHS`. *Improves performance + honesty; effort medium.
Risk:* validation needs AI-written **full sections** (only paragraph negatives exist
today); the document axis must itself pass the matched-stratum confound audit before
an operating point.

**Rank 2 — Unify the six bespoke baselines into one `(feature, unit)` calibration
object.** One descriptor producer (`deai_features`) emitting a typed
`paragraph_descriptor` and `document_descriptor`; the other tools become thin
calibrators that ask "does a reference exist for this `(feature, unit)`?" — which
*becomes* the measured/degraded/unmeasured decision. Compute the one expensive
GPT-2-large surprisal pass once and fan out (today it runs twice, in `deai_oracle`
and `deai_features`). Make the L0–L4 tag a derived `(granularity, method)` sort key,
presentational rather than a module boundary. *Improves elegance + performance; makes
rank 1 nearly free. Effort medium-large; do it as staged mechanical consolidation
with the suite green, never a rewrite.*

**Rank 3 — Jargon/section-conditional operating point.** The audit's own numbers: as
jargon rises, AUC is flat (0.933/0.922/0.912) while FPR quadruples
(0.094/0.216/0.412). The model still separates within the worst stratum; negatives
merely pile above a single global cutoff the architecture cannot condition. Fit the
human-class score shift as a monotone function of jargon density and residualize to a
jargon-invariant score carrying one global threshold, selected from the upper
bootstrap-CI bound of the per-stratum generated-negative FPR the audit already
computes. `bundle_measured()` flips to `measured` only for strata with sufficient
grouped-split support. *Improves performance + honesty; effort medium. Complementary
to rank 1, not a substitute.*

**Rank 4 — Ablate `corpus_cos` from the shipped classifier.** It is the sole
embedding feature, cosine to the human-corpus centroid, i.e. field-register
similarity by construction, and it votes HUMAN for exactly the on-topic AI negatives.
It is inconsistent to hold `lexicon_density` out as audit-only while shipping its
continuous embedding twin inside the classifier. Cheap A/B via the existing
negative controls; if a within-topic signal is still wanted, replace with a
contrastive margin `cos(p, human_field_centroid) − cos(p, ai_field_centroid)` or
distance to the document's own centroid. *Improves performance + honesty; effort
small-to-medium; self-limiting.*

**Rank 5 — Enrich the surprisal representation.** `global_uid` is the single dominant
feature (+2.76 weight), yet `deai_oracle.uid_features` collapses the whole per-token
surprisal sequence to three scalars. Add skewness, kurtosis, predictable-filler rate,
a burstiness index, and low-frequency spectral energy; bump `FEATURE_SCHEMA_VERSION`
so the provenance guard forces a retrain. *Improves performance + elegance; effort
small; keep only features that raise grouped-split AUC.*

**Rank 6 — Topic-orthogonal deterministic axes.** Three new model-free axes, each
calibratable to `measured`: cross-sentence cohesion (given-new / theme-rheme
overlap), hedging-uniformity (low cross-section hedge dispersion is the tell), and
citation placement (fix the root cause first: `extract_style.py` flattens `\cite` to
a positionless `[CITE]` before analysis, destroying integral-vs-terminal signal).
*Improves performance + honesty; effort small-medium; all confound-orthogonal.*

**Rank 7 — Fix `rewrite_reward`'s dead specificity term.** For every eligible
candidate, eligibility already forces the required numbers in, so `specificity` is
identically 1.0 and its 0.6 weight does zero ranking work. Replace it with the
before/after ranked-advisory-reduction delta the re-measure step already computes,
capped, with skeleton-cosine as a meaning-preservation floor. *Improves honesty +
performance; effort small; eligibility stays the untouched hard gate.*

**Rank 8 — Honesty reframings.** Score the deliberately-excluded 262 `ourdrafts`
paragraphs as a held-out hybrid stratum (they ARE the deployment distribution: neither
pristine-published nor raw-generated); add a `calibration_unit`
(paragraph|section|document) field to `make_finding` that caps paragraph-scope
AI-ness findings at reduced confidence by construction; and reclassify the
per-paragraph learned classifier in the docs as an offline audit instrument, not a
product detector one calibration away from an operating point. *Improves honesty;
effort small; mostly bookkeeping + doc language.*

## 5. What NOT to do

- Do **not** chase a per-paragraph L3 operating point via hard-set calibration. The
  unit is wrong (single paragraph near-unjudgeable, `ai_feel` AUC 0.444).
- Do **not** collect more single-paragraph perceptual labels; that axis is near-chance.
- Do **not** harvest more clean/public-generic AI negatives; that case is already easy
  (8.6% FPR). The failure is the field-topic and lightly-edited-hybrid middle.
- Do **not** swap in a bigger embedding or a transformer classifier. The ceiling is
  unit + distribution, not model capacity (HGB has higher in-distribution AUC and is
  OOD-unstable, which is why logreg ships).
- Do **not** merely section-normalize `corpus_cos` the way UID was normalized; on-topic
  AI is still on-topic. Ablate it, do not launder it.
- Do **not** build an opaque aggregate PASS/FAIL or single blended probability;
  `SCIPAPER_STANDARD` forbids it and it would destroy the policy/evidence separation.
- Do **not** synthesize a document baseline by concatenating paragraph exemplars; that
  is the pseudoreplication trap. Use only genuine one-observation-per-paper
  calibration, and keep the axis `unmeasured` where the corpus is too thin.

## 6. Sequencing

Rank 2 (the `(feature, unit)` object) makes "document" just another unit and makes the
rank-1 keystone nearly free, so the natural order is a thin slice of rank 2 (promote
`deai_features` to a document descriptor + single surprisal pass) then rank 1
(dispersion features + document calibration over the existing human corpus + an
AI-full-section validation set) then rank 3/4 in parallel (both attack the same
field-topic FPR from the calibration and feature sides). Ranks 5–8 are independent
polish. Nothing ships a `measured` status until it passes the existing matched-stratum
confound audit.

## 7. Implementation status

Rank 1 (keystone): **implemented and validated, including the full-feature cloud pass**
(2026-07-12/13). `deai_features.cross_paragraph_dispersion` + `deai_docstructure`
dispersion path, calibrated over 14 complete human `wgl` papers, `L2.document_structure`
axis now `measured`. Three-tier validation: human vs natural AI AUC 0.99; vs
paragraph-level de-AI'd AI 1.00 (the old de-AI flow cannot evade it); vs a deliberate
paragraph-shape adversary 0.85–0.92 on length-independent features (bounded power,
honestly stated). The cloud GPU pass then **refuted** the surprisal-recovery hypothesis:
surprisal-only dispersion scores 0.677 (CI spans chance) against the adversary and the
model features add nothing to the robust punctuation/rhythm core (0.921 vs 0.914), while
including gamed features dilutes it (full-14: 0.673). The shipped detector is therefore
model-free and GPU-free **by measurement**. Details: EVALUATION.md §9.

Rank 7 (dead `specificity` term) and rank 8 (`calibration_unit` confidence cap)
shipped 2026-07-13 (v0.16.0). Rank 5 (enriched surprisal) was implemented and
measured on the cloud pass: the five enriched descriptors beat the three shipped
scalars for surprisal-only separation (0.803 vs 0.757, EVALUATION.md §9.8), but
document-level surprisal is itself weaker than the model-free manifold (0.757 vs
0.881) and adds nothing to it, so the enriched features are not shipped into the
model-free detector (recorded, not added). This resolves the last L3 document-level
debt: the detector stays model-free by measurement at document scale. Ranks 2, 3, 4
and 6 were never started as scoped; their decided dispositions live in SCIPAPER_STANDARD §11,
which is the single status home.
