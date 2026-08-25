# EVALUATION — Whole-document cross-paragraph dispersion (the keystone axis) · `sci-paper` v0.27.1

Part of the evaluation record. The hub — evaluation contract, current
axis status, repository verification, release evidence boundary, and the
map of every section — is [`EVALUATION.md`](../EVALUATION.md); read it
first. Section numbers are global across the whole record, so a reference
like "§9.5" means the same thing in every file.

Normative policy lives in [`SCIPAPER_STANDARD.md`](../../SCIPAPER_STANDARD.md);
nothing here can redefine it. All machine-readable findings use the
`sci-paper.feedback.v1` contract.

---

## 9. Whole-document cross-paragraph dispersion (the keystone axis)

> ### ⚠️ Re-measured against the rebuilt baseline — 2026-08-25
>
> The 2026-08-17 rebuild regenerated `docstructure_baseline.json`, but §9 was
> **not** on the v0.27.1 re-measurement list (that release re-measured §5, §6,
> §7 and §14, and checked §15). Its figures therefore still described the
> **507**-paper reference while the shipped artifact carried **493**. This
> notice records the re-measurement that closes the gap.
>
> **The control that makes the rest credible.** The role-coupling axis needs no
> fit, so a refit cannot move it — and it reproduces the pre-rebuild record
> exactly: conformal flag rates 0.107 / 0.333 / 0.316 / 0.042 across the four
> tiers, identical to the published table, and length-fair AUC within 0.001 of
> every published value. Same scoring code, same tier documents, same strata.
> Whatever *did* move is the refit, not the pipeline.
>
> **What moved: the manifold improved, and not by trading away false-flag
> control.** Re-measured on the 493-paper baseline against the same AI tiers:
>
> | quantity | 507-paper record | 493-paper rebuild |
> |---|---:|---:|
> | conformal flag rate, natural | 0.071 | **0.214** |
> | conformal flag rate, de-AI'd | 0.133 | **0.400** |
> | conformal flag rate, adversarial | 0.026 | **0.158** |
> | conformal flag rate, skeleton | 0.125 | **0.292** |
> | length-fair AUC, natural | 0.873 | **0.928** |
> | length-fair AUC, de-AI'd | 0.901 | **0.939** |
> | length-fair AUC, adversarial | 0.836 | **0.919** |
> | length-fair AUC, skeleton | 0.822 | **0.916** |
>
> Human false-flag control held. Scoring all 493 reference papers through the
> shipped operating point directly: **manifold 16/493 = 0.0325**, **role
> 21/493 = 0.0426**, both under the nominal α = 0.05 (union 37/493 = 0.0751).
> Leave-one-out over the conformal calibration set alone agrees — manifold
> 0.0404, role 0.0487. The extra tail power is not borrowed from the human side.
>
> **The rest of §9, re-measured against the same corpus.** The human corpus is
> user-supplied and gitignored — CI and a fresh clone cannot see it — but it is
> present on any machine that holds the profile, at
> `style-corpus/<field>/fulltext-arxiv/`, keyed by the same arXiv IDs the
> baseline's `documents` list carries. Every remaining human-side figure was
> therefore re-measured rather than left at its 507-paper vintage:
>
> | quantity | 507-paper record | 493-paper rebuild |
> |---|---:|---:|
> | §9.1 disjointness, pre-conformal 5% tails | 0 of 507 (independence ~1.3) | **0 of 493** (independence ~1.27) |
> | §9.1 disjointness, at the conformal operating point | — | **0** (independence ~0.68) |
> | §9.3 paired skeleton-vs-its-own-twin AUC | 0.934 (twins held out of the fit) | **0.958** (shipped scorer, twins in reference — *not* the same protocol) |
> | §9.4 r(manifold distance, paragraph count) | 0.353 | **−0.080** |
>
> Two of those deserve a sentence. The **disjointness result survives the
> rebuild**: no human paper is flagged by both axes, on either the pre-conformal
> tails or the shipped operating point, so the axes remain complementary rather
> than redundant. And the **length confound has essentially gone** on the
> shipped path — 0.353 was measured against the *pooled* manifold, whereas the
> shipped scorer now sends each document to its own length-stratum manifold, and
> against that the correlation is −0.080 with median distances of 2.481 / 2.099 /
> 2.186 across the three strata. The Mondrian stratification of §9.5 is doing
> the job it was introduced to do.
>
> **Still not re-measured:** the document-level surprisal sweep of §9.8, which
> needs GPT-2 over all 493 papers (hours of compute, and its conclusion — the
> surprisal path is weaker than the model-free manifold and adds nothing to it —
> is only reinforced by a rebuild that raised the model-free numbers and left
> the surprisal path untouched). Bootstrap CIs were not recomputed for any
> post-rebuild point estimate; the pre-rebuild intervals belong to the
> pre-rebuild points and are not transferred.
>
> Reproduce: score `style-profile/<field>/docval/ai_*` and the corpus papers
> through `manifold_operating_point` and `document_role_coupling`, using the
> baseline's own per-stratum calibration as the human reference.

The architecture reflection ([`DEAI_ARCHITECTURE_ROADMAP.md`](../../design-notes/DEAI_ARCHITECTURE_ROADMAP.md))
identified the document scale as the confound-orthogonal signal: field register shifts the
*level* of per-paragraph features, while AI-uniformity compresses their *spread* across a
document, which no per-paragraph score can see (the 32–41% field-topic FPR of §7.2).

[`tools/deai_docstructure.py`](../../../tools/deai_docstructure.py) measures, per model-free
per-paragraph feature, the cross-paragraph dispersion of a complete document
(`deai_features.cross_paragraph_dispersion`), and flags a document that varies a feature
below the human low tail. The axis was first calibrated one-observation-per-paper over 14
complete human `wgl` papers (multi-file papers concatenated to avoid pseudoreplication);
the current reference is **493** complete papers, and `L2.document_structure` is
`measured`. Per-stratum leave-one-paper-out false-flag rates on the percentile-threshold
path are 0.091 / 0.077 / 0.087, above the nominal 0.05 — which is why the shipped
operating points are the split-conformal ones of §9.5, whose leave-one-out human rate is
0.040. The `docstructure_baseline.json` artifact is gitignored and rebuilt per field.

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

The shipped detector implements the band view at three levels, calibrated over **493
complete human papers** (the bulk full-text fetch grew the reference 14 → 507 within two
days; the 2026-08-17 rebuild re-ingested it at 493 — see the notice at the top of §9,
which also carries the post-rebuild operating characteristics):

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
tabulated in 9.5. On the 507-paper human corpus the two flag sets at the pre-conformal
5% tails were exactly disjoint (0 of 507 papers flagged by both; independence would
predict ~1.3), so the axes are complementary rather than redundant. **The result
survives the rebuild**: re-measured over the 493 reference papers, the pre-conformal 5%
tails still overlap in 0 papers (independence ~1.27), and so do the flag sets at the
shipped conformal operating point (0 of 493, independence ~0.68). The AI side agrees —
of the four tiers in §9.5, `natural` and `skeleton` show zero documents flagged by both
axes, and `de-AI'd` and `adversarial` show one and two respectively, against union rates
of 0.667 and 0.421. Below `MIN_MANIFOLD_DOCUMENTS` reference papers the manifold is
honestly omitted and the per-feature flags remain the primary (strong) findings.

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

> **Post-rebuild note.** Re-running the pairing through the *shipped* scorer on the
> 493-paper baseline gives paired AUC **0.958** (24/24 pairs measurable, clone median
> distance 4.104 versus human twin 2.381, one pair where the clone does not beat its
> twin). That is **not** this section's protocol: the 0.934 below holds the 24 skeleton
> sources out of the manifold fit, whereas the shipped baseline contains them, so 0.958
> is the optimistic in-reference variant and 0.934 remains the honest held-out number.
> Both agree on the conclusion — a structural clone does not escape the manifold.

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

> **Vintage:** the figures below are measured on the **507**-paper reference against the
> **pooled** manifold. The headline length confound was re-measured post-rebuild against
> the **shipped** scorer, which routes each document to its own length-stratum manifold:
> `r(distance, paragraph count)` falls from **0.353** to **−0.080** over 493 papers, with
> median distances 2.481 / 2.099 / 2.186 across the three strata. In other words the
> confound this section identifies is real, and the Mondrian stratification introduced in
> §9.5 in response to it has largely removed it from the shipped path. The role axis's
> operating characteristics were re-measured and are unchanged to the digit (see the §9
> notice), so the mechanism described here stands.

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

The percentile thresholds above were in-sample: the same papers fit the manifold and
set its threshold (LOO 0.063 vs nominal 0.05 on the 507-paper reference; 0.091 / 0.077 /
0.087 per stratum post-rebuild), and the confidence constants were ungrounded. The
shipped operating points are now split-conformal: the manifold is fit on a
proper-training split (**295** papers) and its nonconformity scores calibrated on
**198** held-out human papers; the role z needs no fit, so all **493** are calibration.
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
| manifold | **0.214** | **0.400** | **0.158** | **0.292** |
| role-decoupling | 0.107 | 0.333 | 0.316 | 0.042 |
| union | **0.321** | **0.667** | **0.421** | **0.333** |

Post-rebuild (2026-08-25, n = 28 / 15 / 38 / 24 measurable tier documents). The
pre-rebuild record on the 507-paper reference read manifold 0.071 / 0.133 / 0.026 /
0.125 and union 0.179 / 0.467 / 0.342 / 0.167; the role row is unchanged to the digit,
which is the control — the role z needs no fit, so a refit cannot move it, and its exact
reproduction is what licenses attributing the manifold change to the refit rather than to
the measurement pipeline.

A three-way replication on an independent split of the 507-paper reference (train 253 /
calibration 152 / test 102 humans, seed distinct from the shipped one) gave human test
rates manifold 0.029 and role 0.069 — both within binomial noise of α; per-stratum rates
on ~33 test papers wobble (one stratum hit 7/33 on the role axis), the expected
conditional-coverage fluctuation at ~50 calibration papers per stratum plus residual
within-bin length correlation. That replication was not repeated post-rebuild (it needs
a fresh seeded three-way split). Two post-rebuild human checks stand in its place, and
agree. Scoring all **493** reference papers through the shipped operating point directly:
**manifold 16/493 = 0.0325**, **role 21/493 = 0.0426**, union 37/493 = 0.0751 — partly
in-sample, since the 295 training papers are among them, so read it as the rule's
behaviour on its own reference rather than as a held-out estimate. Leave-one-out over the
conformal calibration set only, which *is* out-of-fit, gives **manifold 0.0404 pooled**
(0.0494 / 0.0345 / 0.0339 by stratum, n = 81 / 58 / 59) and **role 0.0487 pooled**
(0.0473 / 0.0494 / 0.0494, n = 169 / 162 / 162). Both sit at or under nominal α, so the
manifold's higher tail power is not paid for on the human side.

The discrimination signal itself survives length matching. Length-fair AUC against the
**169** same-stratum (short) humans, post-rebuild:

| length-fair AUC | natural | de-AI'd | adversarial | skeleton |
|---|---|---|---|---|
| manifold | **0.928** | **0.939** | **0.919** | **0.916** |
| manifold, pre-rebuild (171 humans) | 0.873 | 0.901 | 0.836 | 0.822 |
| role-decoupling | **0.702** | **0.751** | **0.818** | **0.515** |
| role, pre-rebuild | 0.703 | 0.752 | 0.819 | 0.516 |

The role row again reproduces to within 0.001, and the manifold gains 0.04–0.09 on every
tier. Bootstrap CIs were **not** recomputed for the post-rebuild point estimates; the
pre-rebuild intervals (manifold natural 0.81–0.93, de-AI'd 0.83–0.96, adversarial
0.78–0.89, skeleton 0.75–0.89) describe the 507-paper measurement and must not be
attached to the new points. Restricting the human reference to the 81 out-of-fit
calibration papers only — a stricter comparison than the protocol above — gives manifold
0.908 / 0.923 / 0.896 / 0.894, so the gain is not an artifact of including training
papers in the reference.

The corrected picture: the manifold carries robust length-fair discrimination against
every tier including structure clones, and after the rebuild it also carries usable
5%-tail power on short documents (natural 0.071 → 0.214, skeleton 0.125 → 0.292); the
role axis's genuine power concentrates on the shape adversary (0.818), and the skeleton
tier's earlier role signal (0.658) was length, not coupling. A length-aware manifold
(normalizing estimator noise by paragraph count) remains the recorded next refinement:
the short-human distance distribution is still heavy-tailed, and 0.214 is better than
0.071 but well short of what the 0.928 ranking implies is available.

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

> **Vintage:** measured on the **507**-paper reference and **not** re-measured on the
> 2026-08-17 rebuild — the sweep needs GPT-2 surprisal over the raw human corpus. The
> conclusion it supports (the surprisal path is weaker than the model-free manifold and
> adds nothing to it) is only reinforced by the rebuild, which raised the model-free
> manifold's numbers while leaving the surprisal path untouched.

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
