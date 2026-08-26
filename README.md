# sci-paper

[![CI](https://github.com/skymanbp/sci-paper/actions/workflows/ci.yml/badge.svg)](https://github.com/skymanbp/sci-paper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.31.0-informational.svg)](CHANGELOG.md)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A5CF6.svg)](https://docs.claude.com/en/docs/claude-code/plugins)
[![Python](https://img.shields.io/badge/python-%E2%89%A5%203.11-3776AB.svg)](requirements.txt)
[![Tests](https://img.shields.io/badge/tests-315%20passing-success.svg)](tests/)

**A Claude Code plugin that writes, reviews, de-AIs, and condenses scientific
manuscripts for top-tier journals — under one typed standard, with every claim
traced to a source and every unavailable measurement labelled as unavailable.**

Built for ApJ / MNRAS / PRD / JCAP-class papers and NSF / NIH proposals.
**8 skills · 32 tools · 315 tests · one normative contract · zero authorship verdicts.**

[中文文档](README.zh-CN.md) — [What it does](#what-it-does) ·
[How it works](#how-it-works) · [See it work](#see-it-work) ·
[Benchmarks](#benchmark-dashboard) · [Install](#install) ·
[Skills](#skills-8) · [Tools](#tools-32) ·
[Limitations](#status-known-limitations-and-roadmap) ·
[The standard](docs/SCIPAPER_STANDARD.md) · [Docs](docs/README.md)

---

## What it is

sci-paper turns a Claude Code session into a manuscript workbench governed by a
single written contract, [`docs/SCIPAPER_STANDARD.md`](docs/SCIPAPER_STANDARD.md).

You point it at a `.tex` draft. It measures the draft against **your own field's
corpus** — not a generic model prior — and returns **typed, ranked,
source-traced findings**: what is wrong, how badly, why it thinks so, what to
do, and which axes it could not measure at all. Then it rewrites, and every
rewrite is gated on hard scientific fidelity before style is even considered.

It never tells you a paper is 87% AI-generated. That number does not exist
anywhere in this system, by design.

---

## What it does

### The problem it targets

Three failure modes ruin technical manuscripts, and none of them is a vocabulary
problem:

1. **Prose still reads as machine-written after keyword cleanup.** Swapping
   "delve" for "examine" leaves the deeper regularities untouched — smoothed
   sentence-length variation, templated construction, over-regular document
   shape, claims with no evidence behind them. *Measured here directly: a
   synthetic document with **zero** banned words is still caught at the document
   level ([demo 4](#4-a-document-with-zero-banned-words-still-caught)).*
2. **A single AI-detector score cannot tell an editor what to change** — and it
   is confounded by field, source, section genre, length, jargon, and
   mathematical density. It answers a question ("who wrote this?") that an
   author does not need answered.
3. **Review silently converts missing evidence into good news.** An
   uncalibrated axis reports zero findings, and zero findings read as clean.

### The eight functions

| # | Function | Skill | What you get |
|---|---|---|---|
| **1** | **Write to standard** | [`paper`](skills/paper/SKILL.md) | The writing framework in context: accuracy rules, formula and citation conventions, forward narrative, the L0 lexical policy with canonical examples, positive-voice guidance, measurement states, stopping semantics. |
| **2** | **De-AI a draft** | [`de-ai`](skills/de-ai/SKILL.md) | Three chained passes — subsystem measurement (L0–L4), a structural-tell audit, then **claim-first rewriting** that rebuilds prose from the protected claim graph instead of polishing in place. `--audit-only` stops after measurement. |
| **3** | **Condense without losing science** | [`condense`](skills/condense/SKILL.md) | Whole-document redundancy elimination under one-canonical-home-per-fact, loop-until-dry convergence, and a **mechanical length gate** as the closing proof that the document actually shrank. |
| **4** | **Review the manuscript** | [`paper-review`](skills/paper-review/SKILL.md) | Source-traced **A–R review**: mathematics, physics, logic and statistics, language, structure and narrative spine, citations, data and figures, interfaces, redundancy, reproducibility, modern-physics checks, consistency, adversarial verification (three passes + twelve-framing escalation), staleness, process artifacts, citation precision, glossary alignment. |
| **5** | **Review the figures** | [`figure-review`](skills/figure-review/SKILL.md) | Reviews **compiled pages at 150 DPI**, not source. Traces figure/caption/data provenance, measures canvas balance at the pixel level, separates scientific and build contradictions from readability advisories. |
| **6** | **Run the full review board** | [`final-review`](skills/final-review/SKILL.md) | Parent orchestrator: runs paper-review, figure-review, de-ai `--audit-only`, and modern-physics-review as **isolated worktree agents**, merges their typed findings, and verifies a stable disposition-complete state across consecutive rounds. |
| **7** | **Polish a funding proposal** | [`proposal-polish`](skills/proposal-polish/SKILL.md) | NSF Project Summary/Description, NIH Specific Aims, fellowships. Keeps the vision-and-feasibility register a paper would trim, enforces claim–feasibility matching, edits the score-forming first pages hardest. |
| **8** | **Explore research directions** | [`brainstorm`](skills/brainstorm/SKILL.md) | Radial research-direction explorer: twelve framing passes per node, glossary-anchored terminology, complete derivation per branch, recursive divergence to convergence. Deferred or incomplete leaves are hard-banned. |

All eight run over the same evidence layer — 32 tools emitting one schema,
`sci-paper.feedback.v1` — so a finding from the linter, the review skill, and
the orchestrator are the same object with the same ID.

### Scope boundary — what it deliberately will not do

| It will not | Because |
|---|---|
| Output an authorship verdict or an "% AI" score | The learned axis is **field-similarity triage**, capped at 0.5 confidence at paragraph scale. Its false-positive rate on field-topic AI prose is 28–39% ([why](#why-there-is-no-single-score-the-l3-confound)). |
| Emit a universal paper-level PASS/FAIL | Terminal state is *disposition-complete*, not "zero advisories". |
| Convert a missing baseline into zero findings | Unavailable axes report `unmeasured` / `degraded` with the reason. |
| Optimise prose to evade detectors | Rewrite ranking optimises faithful scientific prose. Fidelity is a hard gate, not a weight. |
| Invent preliminary data, partners, funding history, or letters | Proposal mode is an editor, not a fabricator. |
| Publish your corpus | Corpus files are read-only, copyright-sensitive, gitignored. |

---

## How it works

```
             ┌──────────────────────────────────────────────┐
  your field │  style-corpus/<field>/tier-{1,2,3}-*/         │  papers you supply
  corpus  ──▶│  → extract_style.py → style-profile/<field>/  │  (read-only, gitignored)
             └──────────────────────────────────────────────┘
                                  │ descriptive statistics, exemplars, calibrated references
                                  ▼
  draft.tex ──▶ measure ──▶ typed findings ──▶ rank ──▶ edit ──▶ re-measure ──▶ disposition
                   │                                                    │
                   │ L0  lexicon + punctuation + domain register        │ every strong
                   │ L1  information distribution, surprisal / UID      │ advisory ends
                   │ L2  sentence templates, salience, document shape   │ as acted /
                   │ L3  learned field similarity (capped, degraded)    │ accepted /
                   │ L4  positive voice + cooperative repair            │ false-positive
                   └────────────────────────────────────────────────────┘
```

The loop is the whole product: **measure → type → rank → edit → re-measure →
disposition.**

### The six hard parts

Anyone can ship a banned-word list. These are the parts that took evidence.

**1 · Fidelity is a gate, not a score.** `rewrite_reward.py` ranks candidates
**only after** deterministic scientific-fidelity eligibility. The check is
**bidirectional**: dropping *or inventing* a number, unit, citation, inline
equation, uppercase acronym, semantic LaTeX macro, comparison direction,
negation, or causal-direction marker scores `-inf`, whatever the style score.
The tokenizer boundaries are themselves regression-tested, because the naive
versions rejected faithful rewrites — a greedy numeral pattern made dropping an
Oxford comma read as simultaneously *missing* `2400,` and *inventing* `2400`
([`rewrite_reward.py:33`](tools/rewrite_reward.py#L33)); a permissive unit
pattern made `"in 2020 we found"` yield the unit `we`
([`rewrite_reward.py:41`](tools/rewrite_reward.py#L41)).
See [demo 3](#3-the-fidelity-gate-rejects-the-best-scoring-candidate).

**2 · Document-scale detection, because paragraph-scale de-AI does not fix it.**
The load-bearing measurement: applying a paragraph-level de-AI rewrite to AI
documents changed **22% of the text and removed all 14 em-dashes**, yet
document-level dispersion barely moved — 0.47 → 0.49, against human 1.08
([§9.1](docs/architecture/evaluation/document-scale.md)). Rewriting each paragraph
toward a "more human" target still leaves them uniform *relative to each other*.
So the primary detector is a **joint manifold statistic**: the per-document vector
of log dispersion ratios scored by Mahalanobis distance against the human centre
and covariance — pure-stdlib, 11-D, ridge-stabilised. The joint geometry catches
what independent marginals cannot: a shape adversary can land plausible
per-feature spreads with the wrong covariance. An orthogonal axis measures **role
coupling** — humans vary paragraph shape *where the argument demands it*. On the
493-paper human corpus the two axes' 5% tails are **exactly disjoint** (0 flagged
by both; independence predicts ~1.3).

**3 · Operating points are split-conformal and length-stratified.** Percentile
thresholds fit on the papers that set them are in-sample. The shipped operating
points calibrate nonconformity on held-out human papers, with
`p = (1 + #{calibration ≥ score}) / (n_cal + 1)` flagged at `p ≤ α = 0.05` —
**finite-sample, distribution-free `P(false flag) ≤ α`**. Calibration is
**Mondrian-stratified by document-length tercile**, because length is a measured
confound: short human papers score systematically higher manifold distances
(stratum-0 95th percentile 5.23 versus 4.16/4.36), and every AI validation
document is short. The unstratified thresholds compared short AI documents
against a mostly-long human reference, and the flag rates they produced
(0.607/0.600/0.447/0.292) **overstated tail power**. The honest numbers replaced
them and are [in the dashboard](#document-scale-discrimination-and-its-false-positive-control).

**4 · Register comes from your corpus, not from a word list.**
`deai_register.py` flags terms the manuscript leans on (≥ 5 uses) whose document
frequency **in your field's own corpus** is below 1e-4. No curated
cross-discipline blocklist. That is what lets `AUC` (df 1) separate from `epoch`
(df 402) and `accuracy` (df 774) with no hand-maintained astronomy exception
list. Compounds are judged by their rarest part; `\mathrm{}` after `_` or `^` is
a subscript, not a term; possessives fold.

**5 · Silence is never read as clean.** Every axis reports one of `measured`,
`degraded`, `unmeasured`, `not_applicable`, and every report lists all four — in
the demos below, `L1.distribution` stays `degraded` rather than reporting zero
findings. A missing dependency keeps its axis `unmeasured`. Intended behaviour,
not a degraded mode to be fixed by installing something.

**6 · Refuted signals stay in the record.** Three surface formalisations of the
"thesis spine" were built, measured, and **refuted**; it ships as a *writing rule
with no detector*, and the standard forbids building a threshold on it. The
claim-anchoring tell was refuted for strong-model generations, so
`deai_anchoring.py` ships labelled a **writing-quality axis, not an
AI-discrimination axis**. Hypotaxis ratio: rejected. Inert-clause runs and
inference-connective rate: rejected. `L1.distribution`'s operating point:
**refuted 2026-08-25** — burstiness reverses sign on adversarial prose (AUC
0.181) and signposting runs below chance (0.247), so the `deai_policy.json`
roadmap item was withdrawn rather than shipped
([§16](docs/architecture/evaluation/lexical-structure-uid.md)). A zero-width
confidence interval from a broken resampler: found, fixed, regenerated. All of it
is in [EVALUATION.md](docs/architecture/EVALUATION.md) with the numbers that
killed each one. **A refuted detector is evidence, and it stays in the record.**

---

## See it work

Every command and number below was produced on **2026-08-25** against this
working tree at v0.28.0, on the `wgl` reference profile. Nothing is illustrative.
A fresh clone ships **no** profile ([why](#field-aware-evidence)), so `measured`
axes require you to build one from your own papers first.

### 1. Three treatments of the same paragraph

Not before/after — **what a word-list humanizer changes versus what this
changes**, on one paragraph, measured by one tool. The source is the
worst-scoring Results paragraph in the repository's 20-document AI set.

**A — as generated.** `L0=1, advisories=4`

> …by a factor of 1.4, driven primarily by the removal of selection bias **rather
> than** a reduction in shape-noise itself. The dominant remaining systematic is
> PSF model **error:** a 2 per cent fractional error … **underscoring** that PSF
> characterization **rather than** the shear estimator will set the floor…

```
[l0_target L0 tier-a:underscoring]         Tier A lexical target present.
[advisory  L0 corpus-zero:underscoring]    The field lexicon records ZERO occurrences.
[advisory  L2 structure-auxiliary:results] antithesis-cluster; reference results fraction 0.2% (n=3964).
[advisory  L2 colon-elaboration]           A prose colon introduces an appositive elaboration.
[advisory  L2 ing-tail:underscoring]       A participial tail appends interpretation.
```

**B — an ordinary de-AI pass.** Swap the flagged words for synonyms, delete the
em-dashes. That is the whole mechanical recipe. `L0=0, advisories=3`

```
[advisory  L2 structure-auxiliary:results] antithesis-cluster    <- unchanged
[advisory  L2 colon-elaboration]           prose colon           <- unchanged
[advisory  L2 ing-tail:highlighting]       participial tail      <- FOLLOWED the substitution
```

Read the third line. `underscoring` became `highlighting`, clearing the Tier A
target and the corpus-zero advisory — and the **ing-tail advisory simply renamed
itself**. The sentence still appends its interpretation as a participial tail;
only the word did. **The paragraph now passes a keyword check while reading
exactly as it did.**

**C — the sci-paper pass.** Claim-first rewrite under the fidelity invariants:
every number, unit and citation preserved, length budget respected.
`L0=0, advisories=1`

> …by a factor of 1.4. Most of that gain comes from removing the selection bias;
> the shape-noise contribution is essentially unchanged. The dominant remaining
> systematic is PSF model error. A 2 per cent fractional error propagates to
> Δm ≈ 4×10⁻³… PSF characterization will therefore set the systematic floor.

```
[advisory L2 salience-recital:results] results passage recites its quantities:
  max_recital_run_frac 0.20 (p73), recital_frac 0.40 (p87), numerals_per_sentence 1.20 (p95).
  Longest run of numeral-bearing sentences is 1 of 5, against an n=2541 human results reference.
```

The survivor is a **different kind of note**: the mechanical tells are gone, so
the tool has moved to editorial judgement — how many numbers a passage carries
before the argument has to do the work — against 2,541 human Results passages.

| | A: as generated | B: word-list humanizer | C: sci-paper |
|---|---:|---:|---:|
| L0 targets · advisories | 1 · 4 | **0** · 3 | **0** · **1** |
| structural findings resolved | — | **0 of 3** | **3 of 3** |

Across the **whole 20-document set**, same three treatments, same tool: documents
with an L0 target **4 → 0 → 0**; em-dashes **2 → 0 → 0**; advisories
**346 → 344 → 302**; strong advisories **127 → 127 → 102**. The word-list pass
moves strong advisories by **exactly zero** — it removes what a detector greps
for and nothing a reader would notice. (Arm C there is the repository's
independently written de-AI set, not a rewrite of arm A, so read it as three
populations on the same topics; the paragraph above is the like-for-like.)

### 2. Before / after on a draft

A 189-word two-section draft: six Tier A words, two em-dashes, an ordinal run,
and a six-sentence recital of a parameter grid.

```console
$ python tools/ai_ism_lint.py before.tex --field wgl \
    --structure --distribution --register --salience --document-structure

findings: blockers=0 L0=8 advisories=10 (strong=1)
axis L0.lexical: measured   axis L0.register: measured   axis L2.salience_hierarchy: measured
axis L1.distribution: degraded: using documented compatibility heuristics; deai_policy.json is unavailable
axis L2.sentence_structure: degraded: template evidence measured, but no calibrated strong-feedback operating point is available

  L  3 [l0_target L0 tier-a:pivotal]  Tier A lexical target 'pivotal' is present.
  L  8 [l0_target L0 em-dash]         Em-dash punctuation is an L0 rewrite target.
  ...
  L 14 [advisory L2 salience-recital:method strong] method passage recites its quantities:
       max_recital_run_frac 0.60 (p98), recital_frac 0.60 (p96), numerals_per_sentence 1.80 (p98).
       Longest run of numeral-bearing sentences is 6 of 10, against an n=5957 human method reference.
  L 14 [advisory L2 structure-template:method] repeated sentence-construction template(s):
       ordinal-run; reference method fraction 5.3% (n=8144).
$ echo $?   # -> 1
```

Read the last finding closely. Not "you used a list" — *this construction appears
in 5.3% of the 8,144 human method passages in your own corpus, and yours is one
of them*, with the sample size stated so you can judge what that 5.3% is worth.

After a claim-first rewrite keeping all 24 grid values, `L0=0 advisories=0`
(exit 0), and the length gate confirms it actually shrank:

```console
$ python tools/length_gate.py after.tex --before before.tex
section                       before   after   delta  status
Introduction                      84      58     -26  ok
Method                           105      88     -17  ok
TOTAL                            189     146     -43
net unjustified growth: -43 words (tolerance 0)            # exit 0
```

### 3. The fidelity gate rejects the best-scoring candidate

Three candidate rewrites of one method paragraph, ranked against a reference
holding the claim and the protected content:

```console
$ python tools/rewrite_reward.py --field wgl --reference ref.txt --original orig.txt \
    --candidates cand1.txt cand2.txt cand3.txt

rank cand  combined   voice  fidelity   Δadv eligible  L0(r/c)  words(o/c)
   1    0     0.205   0.491     0.549   0.00     True  0/0  105/88  cand1.txt
   2    2     0.201   0.599     0.517   0.00     True  0/0  105/88  cand3.txt
   3    1      -inf   0.729     0.554   0.00    False  0/0  105/65  cand2.txt
     missing: {'numbers': ['0.01', '0.06', '12', '3', '4', '6', '8'], 'acronyms': ['PSF']}

[best] candidate 0: cand1.txt                               # exit 0
```

Read `voice` against `eligible`. `cand2` scores **0.729** — the **highest of the
three**, and the tightest at 65 words — and loses to nothing at all, because it
dropped seven numbers and an acronym while condensing. The style score never gets
to vote. Had all three been ineligible the tool exits `1`: *preserve the original
and regenerate tighter*, not a crash.

### 4. A document with zero banned words, still caught

A 5-section manuscript with no Tier A vocabulary, no em-dashes and no register
outliers — **`L0=0`** — written to read cleanly sentence by sentence:

```console
$ python tools/ai_ism_lint.py big.tex --field wgl --document-structure ...
findings: blockers=0 L0=0 advisories=10 (strong=1)
axis L2.document_structure: measured

  L 1 [advisory L2 document-dispersion-manifold strong] The document's joint cross-paragraph
      dispersion sits 18.43 Mahalanobis units from the human center (conformal p = 0.0122
      <= alpha 0.05 against 81 held-out human papers (stratum 0 manifold)): its paragraph-shape
      variation pattern departs from the human band as a whole. This is a measured deviation,
      not an AI verdict.

  L 1 [advisory L2 document-uniformity:word_count]     4.859 vs human low-tail 39.260
  L 1 [advisory L2 document-uniformity:n_sentences]    0.484 vs human low-tail  1.631
  L 1 [advisory L2 document-uniformity:mean_sent_len]  2.973 vs human low-tail  5.268
  L 1 [advisory L2 document-uniformity:paren_rate]     0.000 vs human low-tail  0.749
  L 1 [advisory L2 document-uniformity:equivocal_rate] 0.000 vs human low-tail  0.350
```

Failure mode 1, reproduced on demand. A keyword-cleaning tool reports this
document clean. The document-scale axis places it at `p = 0.0122` against
held-out human papers, then names the five dimensions that put it there: its
paragraphs are all the same length, all the same sentence count, and it never
once uses a parenthesis or a hedge. It still refuses to call the document
AI-written — the honest statement is *this document's paragraph-shape variation
departs from the human band*, which is what the finding says.

### 5. What a full review looks like

The linter is one input. `/sci-paper:final-review` orchestrates the rest in
isolated worktrees and merges typed findings from four independent passes:

| Pass | Covers |
|---|---|
| `paper-review` | 18 dimensions **A–R**: mathematics, physics, logic and statistics, language and de-AI, structure and narrative spine, citation existence and relevance, data/results/figures, interfaces, redundancy, reproducibility, modern-physics checks, systemic consistency, adversarial verification, staleness, process artifacts, draft language, reference precision, glossary alignment |
| `figure-review` | every figure re-rendered from the compiled PDF at 150 DPI — caption/data consistency, units, readability at print size, colour accessibility, float placement, cross-figure coherence |
| `de-ai --audit-only` | the L0–L4 measurement stack plus the vendored humanizer structural-tell catalogue |
| modern-physics review | parent-level domain check |

The merge rule is the point: **integrity blockers must be resolved, L0 targets
must reach zero, every strong advisory needs a recorded disposition, and ordinary
advisories plus unavailable axes stay visible**. Rounds repeat until that
disposition-complete state is *stable across two consecutive rounds* — not until
the feedback count reaches zero, and never as a universal PASS/FAIL. Dimension
**M** re-derives the paper's own mathematics in three passes and escalates
disagreements through twelve framings to `CONFIRMED` / `REFUTED` / `MARGINAL`.

---

## Benchmark dashboard

Two kinds of number, not interchangeable: **discrimination and calibration**,
read from the evaluation record; and **latency**, measured first-party for this
README. All discrimination figures below were **re-scored on 2026-08-25** against
the rebuilt profile, through the shipped path — not carried forward.

### Document-scale discrimination and its false-positive control

AUC is length-fair: each document is compared only against human papers in its
own length stratum (170 in the short stratum). Flag rates are split-conformal,
Mondrian-stratified by length tercile, giving **finite-sample,
distribution-free `P(false flag) ≤ α`** for exchangeable human papers. Source:
[§9.5](docs/architecture/evaluation/document-scale.md).

| Contrast | Manifold AUC | Role AUC | Manifold tail power | Role | union |
|---|---:|---:|---:|---:|---:|
| human vs **natural** AI | **0.933** | 0.690 | 0.250 | 0.036 | 0.286 |
| human vs **de-AI'd** AI (paragraph de-AI as an attack) | **0.943** | 0.742 | 0.400 | 0.268 | **0.600** |
| human vs **shape-adversarial** AI (deliberate raggedness) | 0.927 | **0.810** | 0.184 | 0.316 | 0.447 |
| human vs **skeleton-matched** structural clone | 0.914 | 0.507 | 0.292 | 0.042 | 0.333 |
| human vs **long-form** AI *(standing falsification target)* | 0.740 | 0.634 | **0.000** | 0.069 | 0.069 |
| **human false-flag**, scored over 492 papers, α = 0.05 | — | — | **0.033** | **0.043** | 0.075 |

The axes are complementary by construction: the manifold carries discrimination
against every tier including structure clones, while the role axis concentrates
on the tier that narrows the manifold's margin. Every published AUC reproduced
within **0.012** across the 42× rebuild — all eight, not a matching total.

Tail power is reported plainly, including where it is weak and where it is zero,
and **the tail-power column above is a single seed draw**: the per-seed spread on
those tiers is 0.04–0.18, so over 12 seeds natural reads 0.170 ± 0.110. Long-form
is not caught at the strict operating point at all, in any configuration tried.
The estimator-noise model that was supposed to fix short documents has now been
built and refuted — it moves the human rate not at all
([§9.4c](docs/architecture/evaluation/document-scale.md)). Re-run the whole table
with `python tools/eval_docscale.py --field wgl`.

### Why there is no single score: the L3 confound

The learned paragraph-scale model is good — and ships `degraded` **anyway**, for
a measured reason. Retrained 2026-08-26 on 44,576 records. Source:
[§7](docs/architecture/evaluation/learned-model.md).

| Metric | Value | 95% split range | 17,299-record bank |
|---|---:|---|---:|
| Grouped-split AUC (20 splits, complete papers held out) | **0.9518** | 0.9448 – 0.9604 | 0.9320 |
| Matched-stratum AUC (section × length × math × field-term) | **0.9306** | 0.9161 – 0.9507 | 0.9236 |
| Balanced accuracy | **0.8761** | 0.8647 – 0.8912 | 0.8445 |
| Author hard-set, **true provenance** | 0.936 | 0.840 – 0.999 | 0.937 |
| False-positive rate — public-generic AI text | 0.052 | 0.031 – 0.066 | 0.086 |
| False-positive rate — **field-topic AI text** | **0.280** | 0.208 – 0.344 | 0.318 |
| False-positive rate — **field-jargon-dense AI text** | **0.393** | 0.278 – 0.485 | 0.417 |

A 0.95 AUC headline and a 28–39% false-positive rate on field-topic AI prose are
the same model: the learned score partly measures *field register*, so it is
unreliable on the exact distribution a de-AI pass must catch. **Three retrains
across a 2.6× bank range agree** — field-topic went 0.318 → 0.285 → 0.280, every
step inside one retrain's own split range, while headline AUC moved the other way
(0.9320 → 0.9518). More data buys the easy contrast and nothing on the one that
matters, so the roadmap item closes by decision: **not obtainable from this
feature set**; reopening needs different features, not a bigger bank. The
document-level surprisal path measured 0.757, weaker than the model-free manifold
(0.881), and adds nothing to it.

Retraining is not behaviour-preserving and is not claimed to be: on 1,845
paragraphs scored by both bundles the degraded mode's ranking holds at Spearman
**ρ = 0.846** and the three surfaced paragraphs overlap **0.654**. Same schema,
features and posture — but an old triage list will not reproduce exactly.

### Latency and repository health

Measured 2026-08-25 on Windows 11, Python 3.13.3, RTX 4060 Ti, median of 7
subprocess runs (3 for the model-backed rows) including interpreter startup. The
document is a real 5,084-word corpus paper, assembled from its LaTeX includes.

| Pass | Median wall | Dependencies |
|---|---:|---|
| Python interpreter floor | 56 ms | — |
| L0 lexicon + register | **208 ms** | stdlib |
| **All model-free axes** (L0 + L1 + L2 incl. document structure) | **390 ms** | stdlib |
| `length_gate.py` | 180 ms | stdlib |
| `+ --oracle` (GPT-2-large token surprisal) | 23.1 s | `transformers` + `torch` |
| `+ --voice` (learned L3 triage) | 26.6 s | `scikit-learn` + `sentence-transformers` |
| `validate_plugin.py` — **9/9 checks pass** | 359 ms | stdlib |
| Full test suite — **315 passing**, 17 files | 35.5 s | stdlib |

The headline: **a complete model-free pass over a 5,084-word manuscript costs
~334 ms of analysis above the interpreter floor**, with no optional dependency
installed. The two model-backed axes cost 60×–80× more and are opt-in flags —
you should not need a GPU to lint a paper. CI runs the validator and the suite on
every push and PR, Python 3.11, Ubuntu.

---

## Install

```bash
git clone https://github.com/skymanbp/sci-paper.git
claude --plugin-dir /path/to/sci-paper          # development
```

Skills are then namespaced `/sci-paper:<name>`.

**Python ≥ 3.11.** The shared schema, the deterministic L0 linter, the model-free
L1/L2 axes, the document-structure analysis, and the validator are **standard
library only**. Optional capabilities add dependencies:

```bash
pip install -r requirements.txt      # all optional extras
```

| Package | Enables |
|---|---|
| `pymupdf` | PDF corpus extraction, compiled-page inspection |
| `sentence-transformers` | semantic exemplar retrieval, embedding features |
| `scikit-learn` + `joblib` | legacy and learned field-similarity models |
| `transformers` + `torch` | token-surprisal / UID measurement |
| `numpy` | learned feature, cache, and rewrite-score utilities |

> Never install an optional dependency merely to turn an unavailable axis into a
> nominal score. A missing package keeps its axis `unmeasured`, by design.

## Quick start

```bash
# 1. Verify the checkout.
python tools/validate_plugin.py
python -m unittest discover -s tests -v

# 2. Put your field's papers under style-corpus/<field>/tier-*/ and build the profile.
python tools/build_profile.py --field wgl

# 3. Produce one unified, machine-readable feedback report.
python tools/ai_ism_lint.py draft.tex --field wgl \
  --structure --distribution --document-structure --register --salience \
  --oracle --voice --format json --output feedback.json
```

---

## Skills (8)

Four jobs; what each one does is in [the eight functions](#the-eight-functions).
Drive them from Claude Code as `/sci-paper:<name> draft.tex --field wgl`.

- **Write** — [`paper`](skills/paper/SKILL.md) (load the standard) · [`proposal-polish`](skills/proposal-polish/SKILL.md) (NSF / NIH register)
- **Revise** — [`de-ai`](skills/de-ai/SKILL.md) (measure → audit → faithful rewrite) · [`condense`](skills/condense/SKILL.md) (remove redundancy, prove the shrink)
- **Review** — [`paper-review`](skills/paper-review/SKILL.md) (A–R, source-traced) · [`figure-review`](skills/figure-review/SKILL.md) (compiled pages) · [`final-review`](skills/final-review/SKILL.md) (isolated orchestration)
- **Explore** — [`brainstorm`](skills/brainstorm/SKILL.md) (radial research exploration)

## Tools (32)

One `sci-paper.feedback.v1` contract for every finding; corpus, training, and
evaluation entries produce artifacts instead. `layer` is the axis the tool serves
— `core` contract and gates, `build` corpus and profile construction, `eval`
reproducible evidence. Per-tool detail: [tools/README.md](tools/README.md).

| Tool | Layer | Purpose |
|---|---|---|
| `tools/deai_feedback.py` | core | Implements `sci-paper.feedback.v1`: stable IDs, consequence classes, measurement states, dispositions, ranking, summaries, rendering. Standard library only. |
| `tools/ai_ism_lint.py` | core | The unified CLI. Aggregates L0 and every advisory axis into one ranked text/JSON report. Exit `0` = no L0 target, `1` = L0 target present, `2` = invalid input or execution failure. |
| `tools/length_gate.py` | core | Per-section prose length-budget delta gate (standard §5.3). Exit 1 on net unjustified growth between two document versions; `--allow` records justifications. |
| `tools/rewrite_reward.py` | core | Ranks rewrite candidates **after** hard scientific-fidelity eligibility. Dropping *or inventing* a protected invariant scores `-inf`. |
| `tools/deai_register.py` | L0 | Domain register: terms the manuscript leans on that the field's own corpus does not carry, judged by corpus document frequency rather than a curated cross-discipline list. Compounds are judged by their rarest part. Advisories only. |
| `tools/ai_ism_negatives_handcrafted.txt` | L0 | Seed negative examples for the legacy classifier (data asset). |
| `tools/deai_metrics.py` | L1 | Model-free information-distribution findings — sentence-length variation, connective openers — with explicit calibration state. |
| `tools/deai_oracle.py` | L1 | Optional token-surprisal and Uniform Information Density evidence. Unavailable assets and compatibility thresholds stay explicit. |
| `tools/deai_structure.py` | L2 | Sentence and paragraph construction: enumeration, repeated frames, parallel runs, symmetry, and related template families. |
| `tools/deai_salience.py` | L2 | Salience hierarchy: how far a passage's measured quantities run without an interpreting sentence between them, against a per-section human reference. Sole consumer of the numeral-preserving LaTeX projection. |
| `tools/deai_docshape.py` | L2 | Document-shape measurement and complete-document calibration: the per-paragraph feature vector, cross-paragraph dispersion, the joint Mahalanobis manifold, role coupling, split-conformal operating points, and the baseline builder. Split from `deai_docstructure.py` on 2026-08-25; that module re-exports every public name here. |
| `tools/deai_docstructure.py` | L2 | Whole-document rhetorical shape and complete-document calibration: dispersion band, per-length-stratum joint manifold, role coupling, split-conformal operating points. |
| `tools/deai_anchoring.py` | L2 | Section-class conditional claim-anchoring band — a writing-quality axis, explicitly **not** an AI-discrimination axis. |
| `tools/deai_features.py` | L3 | Reusable distributional, UID, punctuation, embedding, and structural features. |
| `tools/deai_voice.py` | L3 | Optional learned field-similarity triage. A bundle without an operating point is degraded and never an authorship verdict. |
| `tools/train_voice_model.py` | L3 | Trains the optional field-similarity model with source-paper grouping. Confound audits are mandatory. Re-exports every public name from `voice_dataset.py` and `voice_audit.py`. |
| `tools/voice_dataset.py` | L3 | Record loading, source-family grouping, the train-only field lexicon, and the fingerprinted feature-matrix cache. Split from `train_voice_model.py` on 2026-08-26. |
| `tools/voice_audit.py` | L3 | Held-out metrics, bootstrap AUC intervals, the author hard set, and the repeated grouped confound audits. Fits nothing; produces the evidence a bundle needs to leave `degraded`. |
| `tools/deai_partition.py` | L4 | Fidelity-free merge/split suggestions that move a document toward the human dispersion band. Suggest-only, zero-token operations. |
| `tools/deai_provenance.py` | L4 | Editing-provenance ledger over the author's **own** draft history; labels each span AI-untouched → author-original by token edit ratio. Not a detector; `unmeasured` without an AI-draft ancestor. |
| `tools/deai_personal.py` | L4 | Personal dispersion baseline against the author's own prior papers — a confound-free same-author reference. `unmeasured` below three papers. |
| `tools/eval_docscale.py` | eval | Reproduces the §9 document-scale table — human false-flag rate and per-tier tail power — by scoring the corpus and every `docval` tier through the same operating point findings use. |
| `tools/eval_findings.py` | eval | Scores register and salience against **provenance** labels instead of hand labels: their firing rate on held-out refereed ApJ/ApJL/A&A papers, on the in-sample papers, and on the `docval` machine tiers, plus a paired test that isolates calibration leakage from publication era. |
| `tools/label_findings.py` | eval | Samples register and salience findings into a human-labelling sheet, re-serves a blind subset for intra-rater agreement, and scores precision/recall stratified by drafts vs published papers. Reports `unmeasured` for any stratum under 20 labels. |
| `tools/build_profile.py` | build | Builds the basic field profile: extraction, optional legacy classifier, exemplar-cache warm-up. |
| `tools/cli_common.py` | build | Shared command-line preamble and field resolution, used by 22 of 32 tools. Holds no policy: no default beyond the two roots, reads no profile, emits no findings. |
| `tools/extract_style.py` | build | Extracts lexicon, sentence statistics, transitions, a descriptive dossier, and a section-typed exemplar bank. Re-exports every public name from `extract_sections.py`. |
| `tools/extract_sections.py` | build | Source-text projection and section splitting: the section vocabulary and its classifier, both named LaTeX projections, and the PDF heading heuristic. Section buckets key every per-section reference, so changing this requires a profile rebuild. |
| `tools/retrieve_exemplars.py` | build | Retrieves section- and topic-matched exemplar paragraphs, with embedding or explicit fallback retrieval. |
| `tools/fetch_arxiv_abstracts.py` | build | Fetches dated abstract corpora for controlled evaluation and training, optionally restricted to a subfield query set and named refereed journals. Rate limiting **stops the sweep and exits 2** rather than writing a truncated corpus as if it were complete. |
| `tools/train_ai_ism_classifier.py` | legacy | Trains the legacy word-ngram classifier, used only as degraded advisory evidence. |
| `tools/extract_md_negatives.py` | legacy | Harvests candidate generated paragraphs for controlled evaluation and training. |

> `tools/validate_plugin.py` is a release tool, not a product tool, and is excluded above.

---

## The feedback contract

Every finding carries exactly one **consequence class**:

| Class | Meaning | Required consequence |
|---|---|---|
| `integrity_blocker` | The scientific record may be wrong, unsupported, inconsistent, unreproducible, or unusable | **Must** be resolved from sources. Cannot be waived as a style preference. |
| `l0_target` | A Tier A word, an em-dash, or a Tier B word beyond one occurrence per section | Rewrite to zero. Not a claim that the paper is scientifically invalid. |
| `advisory` | Structural, distributional, learned, rhetorical, clarity, or aesthetic evidence | Rank, act on the strongest, then record a disposition for the rest. |

Every axis reports one **measurement state** — `measured`, `degraded`,
`unmeasured`, or `not_applicable` — and a final report lists all four.
**Silence is never read as clean.**

Every strong advisory ends at one **disposition**: `acted`, `accepted`,
`rejected_as_false_positive`, or `pending` with a stated reason. Ordinary
advisories stay visible and need not disappear — which is why
[demo 1](#1-three-treatments-of-the-same-paragraph) ends at one, not zero.

## Field-aware evidence

A *field* is one subdirectory under `style-corpus/` with a matching directory
under `style-profile/`. With exactly one field present, tools auto-detect it;
with several, pass `--field <name>` explicitly. **Nothing assumes a particular
field exists** — including the `wgl` field used throughout this README.

```
style-corpus/<field>/tier-1-top/        top-journal exemplars
                     tier-2-mentor/     mentor or target-author exemplars
                     tier-3-reference/  other relevant field papers
        |  python tools/extract_style.py --field <field>
        v
style-profile/<field>/                  generated evidence (gitignored)
```

For scale, the reference profile behind every measured number here carries:

| Asset | Scale |
|---|---|
| `exemplar_paragraphs.jsonl` | **27,951** section-typed paragraphs from 19 curated + 500 reference papers |
| `register_lexicon.json` | 41,593 passages · 55,133 terms |
| `uid_baseline.json` | 27,951 paragraphs under GPT-2-large · pooled global UID 3.321 ± 0.439 |
| `structure_baseline.json` | method 9,522 · results 3,964 · data 3,915 · intro 3,844 · discussion 3,653 · conclusion 2,610 · abstract 433 |
| `salience_baseline.json` | abstract 13,823 · method 6,964 · intro 3,267 · results 3,210 · data 3,023 · discussion 2,963 · conclusion 1,995 |
| `docstructure_baseline.json` | 507 complete documents · conformal α 0.05 · length strata [46, 75] |
| `anchoring_baseline.json` | 517 documents · all six section classes above the 30-document minimum |
| `voice_model.joblib` | 44,576 records · 14 features · **no operating point**, `degraded` |

Every bucket clears the 30-passage floor — untrue before 2026-08-25, when
`results` held 26 and that was misread as a corpus-size limit.
Corpus contents are **read-only, copyright-sensitive inputs**, never committed. A
dossier is evidence, not a standard and not proof of authorship.

## Design philosophy and tech stack

1. **One normative contract.** [`docs/SCIPAPER_STANDARD.md`](docs/SCIPAPER_STANDARD.md)
   decides. Skills, tools, profiles, and models implement or measure it; none may
   create a competing consequence vocabulary, a universal prose PASS/FAIL, or an
   authorship claim.
2. **Evidence cannot promote itself to policy.** Corpus statistics, thresholds,
   learned models, and evaluation results inform findings. They never redefine
   the standard.
3. **Honest measurement states over convenient defaults.** Missing calibration,
   absent dependencies, or insufficient sample size stay `unmeasured` or
   `degraded`. Converting unavailable evidence into zero findings is the failure
   this project was built to eliminate.
4. **Fidelity dominates style, unconditionally.** Not a large weight — a gate.
   The scientific content of a sentence is not tradeable against how it reads.
5. **Negative results ship**, with the numbers that killed them.

| Layer | Choice | Why |
|---|---|---|
| Core analysis | **Python ≥ 3.11 standard library** | Linter, schema, model-free L1/L2 axes, the 11-D Mahalanobis document manifold (no numpy), and validator run on a bare interpreter. Adoption should not require a wheel build. |
| Calibration | **Split-conformal, Mondrian-stratified** | Finite-sample, distribution-free false-flag control without assuming a score distribution. |
| Corpus reference | **User-supplied, tiered, gitignored** | Style is field-relative. A generic prior is the thing being replaced. |
| Optional models | `transformers`+`torch`, `scikit-learn`, `sentence-transformers` | Strictly opt-in flags. Absence degrades an axis, never the run. |
| Distribution | **Claude Code plugin** (`.claude-plugin/plugin.json`) | Skills at `skills/<name>/SKILL.md`, namespaced `/sci-paper:<name>`. |
| Contract enforcement | `tools/validate_plugin.py` + GitHub Actions | 9 checks over manifests, registries, doc authority, recorded counts, imports, CLI entry points, exit semantics, tests, CI wiring. Drift fails CI instead of accumulating. |

---

## Repository layout and development

```text
sci-paper/
├── .claude-plugin/          plugin.json · marketplace.json
├── .github/workflows/       ci.yml — validator + test suite on push and PR
├── docs/                    ← index + authority order at docs/README.md
│   ├── SCIPAPER_STANDARD.md      the single normative contract (v3.7)
│   ├── architecture/             DEAI_SUBSYSTEM.md · EVALUATION.md (hub) + evaluation/
│   └── design-notes/             frozen, dated reasoning records (not status)
├── skills/<name>/SKILL.md   8 skills          ├── tests/     17 files, 315 tests
├── tools/                   31 product tools  ├── CHANGELOG.md · ACKNOWLEDGMENTS.md
├── style-corpus/<field>/    user-supplied read-only corpus (gitignored)
└── style-profile/<field>/   generated and calibrated evidence (gitignored)
```

`python tools/validate_plugin.py` runs 9 contract checks and
`python -m unittest discover -s tests -v` runs the 315-test suite; both must pass
before a release. The validator covers release metadata, skill frontmatter,
standard references, documentation boundaries and index completeness, in-page
anchors, recorded suite sizes against real discovery, product registries, syntax,
runtime imports, CLI entry points, schema fields, and linter exit semantics —
`tools/validate_plugin.py` itself is the authoritative list. A release also
requires independent review, clean-checkout verification, and green hosted CI.

---

## Status, known limitations, and roadmap

Current: **v0.31.0**. Full per-version history in [CHANGELOG.md](CHANGELOG.md).

**Normative core:** `docs/SCIPAPER_STANDARD.md` v3.7 — the complete de-AI
standard in one file (layered model, document-scale detection core, cooperative
layer, the `calibration_unit` confidence cap, the §5.2 de-AI-ization procedure,
the §5.3 condense-not-accumulate rule with mechanical enforcement, and the §5.4
thesis spine shipped deliberately **without** a detector). There is no separate
de-AI standard.

### Known limitations, stated plainly

| Limitation | Current state |
|---|---|
| **No learned-model operating point** | L3 ships `degraded`. The document-level surprisal path was *measured* not to provide one (0.757 vs the model-free manifold's 0.881). |
| **Field-topic false positives** | 28–39% on field-topic and jargon-dense AI prose. **Closed by decision:** three retrains across a 2.6× bank range agree the confound is in the feature set, so no field-topic-robust operating point is obtainable from it. |
| **Short-document tail power, and it is a seed draw** | Manifold 5%-tail power on short natural-AI documents averages **0.170 ± 0.110** over 12 seeds against a 0.933 length-fair ranking; per-tier spread reaches 0.18, wider than several differences the record once read as improvements. Three fixes were built and all three fail: distance normalisation (rejected), finer stratification, and an explicit estimator-noise covariance. `tools/eval_docscale.py` re-runs the table instead of quoting it. |
| **Long-form generation is not caught** | At α = 0.05, manifold tail power on long-form AI is **0.000** — stable across 2 metrics × 4 calibration splits × 12 seeds. Rank AUC is 0.729, so the signal exists and the operating point cannot reach it. |
| **Cooperative-layer tools** | `deai_provenance` and `deai_personal` are honestly `unmeasured` until the author supplies their own draft history or ≥ 3 prior papers. |
| **`L1.distribution` / `L2.sentence_structure`** | `degraded` — and now for a *measured* reason. Burstiness reverses sign on adversarial prose (AUC 0.181) and signposting runs below chance (0.247), so no operating point is available to write. |
| **Retrains are not behaviour-preserving** | Rebuilding the profile refits L3. Ranking holds at ρ 0.846 and triage overlap 0.654, but an old triage list will not reproduce exactly. |
| **A quarter of the corpus is never used** | Headings matching no section bucket are dropped rather than guessed: **2,334 of 9,178 (25.4%)** in `wgl`, 42 of 148 in `wgl-letter`. The remainder is mostly topic headings ("Matter power spectrum"); "Measurements" and "Background" were refused as genuinely ambiguous. |
| **Register fires on accepted prose** | Measured on 203 held-out refereed ApJ/ApJL/A&A papers it never saw: **0.384 findings per 1,000 words**, 87.2% of documents, rank AUC **0.148** against machine text — it fires *more* on human papers than on AI drafts. 86.3% of those flags would vanish if the paper sat in its own bank. v0.30.0 published 0.991/93.6%/0.080; **58.7% of that was a projection defect**, not vocabulary — detection read whole files while the corpus df excluded front matter and bibliographies. |
| **Advice quality is still unlabelled** | Provenance answers "does it fire on accepted prose", not "is this advisory right". Salience's gate transfers almost exactly (0.2705 per passage against a 0.2710 expectation); precision and recall for the advice itself need `tools/label_findings.py`. |
| **A fresh clone measures nothing** | All profile assets are gitignored. Until you build a profile from your own papers, every corpus-referenced axis is `unmeasured`. |

### Roadmap

Open, and it now carries a number: `L0.register`'s operating point must be re-derived
against a held-out target rate. What it replaces — "needs a human-labelled validation
set" — is closed by measurement: refereed ApJ/ApJL/A&A papers *are* human labels, and
200 held-out ones scored both axes
([§17](docs/architecture/evaluation/narrative-salience-register.md)). A labeller still
judges whether an advisory is good *advice*; `label_findings.py` is that path.

**Closed by refutation, not by shipping.** The length-aware manifold, a larger conformal
calibration set, long-form tail power, three L3 retrains, and the held-out-vs-in-sample
leakage contrast were built or tested and refuted; each is a row above. `deai_policy.json`
stays withdrawn; anchors stay `[WGL]`. Detail: [§9.4c](docs/architecture/evaluation/document-scale.md),
[§7.0a](docs/architecture/evaluation/learned-model.md), §17.3.

## Acknowledgments and license

`sci-paper` adapts material from two MIT-licensed projects —
[academic-humanizer](https://github.com/AIScientists-Dev/academic-humanizer) and
[blader/humanizer](https://github.com/blader/humanizer) — with what was adopted
and what was deliberately declined recorded in
[ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).

[MIT](LICENSE) covers code, skills, documentation, and tooling authored in this
repository. User-supplied corpus contents and generated excerpts retain their
source rights and are **not** covered by this repository license.

---

<sub>**Keywords:** Claude Code plugin · Claude Code skills · agent skills ·
scientific writing · academic writing · paper review · peer review · manuscript
preparation · AI text detection · AI-generated text detector · humanizer · de-AI ·
AI detector for research papers · LaTeX · arXiv · astrophysics · weak gravitational
lensing · cosmology · ApJ · MNRAS · PRD · JCAP · NSF proposal · NIH Specific Aims ·
research writing assistant · corpus-driven style · conformal prediction · split
conformal · uniform information density · reproducibility · scientific integrity · LLM tooling · research automation.</sub>
