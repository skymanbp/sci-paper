# sci-paper

[![CI](https://github.com/skymanbp/sci-paper/actions/workflows/ci.yml/badge.svg)](https://github.com/skymanbp/sci-paper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.27.1-informational.svg)](CHANGELOG.md)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A5CF6.svg)](https://docs.claude.com/en/docs/claude-code/plugins)
[![Python](https://img.shields.io/badge/python-%E2%89%A5%203.11-3776AB.svg)](requirements.txt)
[![Tests](https://img.shields.io/badge/tests-214%20passing-success.svg)](tests/)

**A Claude Code plugin that writes, reviews, de-AIs, and condenses scientific
manuscripts for top-tier journals — under one typed standard, with every claim
traced to a source and every unavailable measurement labelled as unavailable.**

Built for ApJ / MNRAS / PRD / JCAP-class papers and NSF / NIH proposals.
**8 skills · 25 tools · 214 tests · one normative contract · zero authorship verdicts.**

[中文文档](README.zh-CN.md) — [What it does](#what-it-does) ·
[How it works](#how-it-works) · [See it work](#see-it-work) ·
[Benchmarks](#benchmark-dashboard) · [Install](#install) ·
[Skills](#skills-8) · [Tools](#tools-25) ·
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
   level ([demo 3](#3-a-document-with-zero-banned-words-still-caught)).*
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

All eight run over the same evidence layer — 25 tools emitting one schema,
`sci-paper.feedback.v1` — so a finding from the linter, the review skill, and
the orchestrator are the same object with the same ID.

### Scope boundary — what it deliberately will not do

| It will not | Because |
|---|---|
| Output an authorship verdict or an "% AI" score | The learned axis is **field-similarity triage**, capped at 0.5 confidence at paragraph scale. Its false-positive rate on field-topic AI prose is 32–42% ([why](#why-there-is-no-single-score-the-l3-confound)). |
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
See [demo 2](#2-the-fidelity-gate-rejects-the-best-scoring-candidate).

**2 · Document-scale detection, because paragraph-scale de-AI does not fix it.**
The load-bearing measurement here: applying a paragraph-level de-AI rewrite to AI
documents changed **22% of the text and removed all 14 em-dashes**, yet
document-level dispersion barely moved — 0.47 → 0.49, against human 1.08
([§9.1](docs/architecture/evaluation/document-scale.md)). Rewriting each toward a
"more human" target still leaves the paragraphs uniform *relative to each other*.
So the primary detector is a **joint manifold statistic**: the per-document
vector of log dispersion ratios scored by Mahalanobis distance against the human
centre and covariance — a pure-stdlib 11-D implementation, ridge-stabilised. The
joint geometry catches what independent marginals cannot: a shape adversary can
land plausible per-feature spreads with the wrong covariance. An orthogonal axis
measures **role coupling** — humans vary paragraph shape *where the argument
demands it*. On the 507-paper human corpus the two axes' 5% tails were **exactly
disjoint** (0 flagged by both; independence predicts ~1.3).

**3 · Operating points are split-conformal and length-stratified.** Percentile
thresholds fit on the same papers that set them are in-sample. The shipped
operating points calibrate nonconformity scores on held-out human papers, with
`p = (1 + #{calibration ≥ score}) / (n_cal + 1)` flagged at `p ≤ α = 0.05` —
**finite-sample, distribution-free `P(false flag) ≤ α`** for exchangeable human
papers. Calibration is **Mondrian-stratified by document-length tercile**,
because length is a measured confound: short human papers score systematically
higher manifold distances (stratum-0 95th percentile 5.23 versus 4.16/4.36), and
every AI validation document was short. The unstratified thresholds had been
comparing short AI documents against a mostly-long human reference, and the
previously reported flag rates (0.607/0.600/0.447/0.292) **overstated tail
power**. The honest numbers replaced them and are
[in the dashboard](#document-scale-length-fair-discrimination).

**4 · Register comes from your corpus, not from a word list.**
`deai_register.py` flags terms the manuscript leans on (≥ 5 uses) whose document
frequency **in your field's own corpus** is below 1e-4. No curated
cross-discipline blocklist. That is what lets `AUC` (df 1) separate from `epoch`
(df 402) and `accuracy` (df 774) without anyone hand-maintaining an astronomy
exception list. Compounds are judged by their rarest part; `\mathrm{}` after `_`
or `^` is a subscript, not a term; possessives fold.

**5 · Silence is never read as clean.** Every axis reports one of `measured`,
`degraded`, `unmeasured`, `not_applicable`, and every report lists all four —
visible in every demo below, where `L1.distribution` stays `degraded` because
`deai_policy.json` does not exist rather than reporting zero findings. A missing
dependency keeps its axis `unmeasured`. That is intended behaviour, not a
degraded mode to be fixed by installing something.

**6 · Refuted signals stay in the record.** Three surface formalisations of the
"thesis spine" signal were built, measured, and **refuted**; the rule ships as a
*writing rule with no detector*, and the standard forbids building a threshold on
it. The claim-anchoring tell was likewise refuted for strong-model generations,
so `deai_anchoring.py` ships labelled a **writing-quality axis, not an
AI-discrimination axis**. Hypotaxis ratio: rejected. Inert-clause runs and
inference-connective rate: rejected. A zero-width confidence interval from a
broken resampler: found, fixed, baseline regenerated. All of it is in
[EVALUATION.md](docs/architecture/EVALUATION.md), with the numbers that killed
each one. **A refuted detector is evidence, and it stays in the record.**

---

## See it work

Every command and number below was produced on **2026-08-25** against this
working tree at v0.27.1, on the `wgl` reference profile. Nothing here is
illustrative.

> The demo document is synthetic prose written for this README, not corpus
> material. A fresh clone ships **no** profile ([why](#field-aware-evidence)), so
> `measured` axes require you to build one from your own papers first.

### 1. Before / after on a draft

A 200-word two-section draft with the usual tells: Tier A vocabulary, an
em-dash, an announced enumeration, and a six-sentence run of recited parameters.

```console
$ python tools/ai_ism_lint.py before.tex --field wgl \
    --structure --distribution --register --salience --document-structure

findings: blockers=0 L0=10 advisories=10 (strong=0)
axis L0.lexical: measured
axis L0.register: measured
axis L2.salience_hierarchy: measured
axis L1.distribution: degraded: using documented compatibility heuristics; deai_policy.json is unavailable
axis L2.sentence_structure: degraded: template evidence measured, but no calibrated strong-feedback operating point is available
axis L2.document_structure: unmeasured: need at least 3 sections with at least 2 substantial paragraphs each

  L  3 [l0_target L0 tier-a:pivotal] Tier A lexical target 'pivotal' is present.
  L  9 [l0_target L0 em-dash] Em-dash punctuation is an L0 rewrite target.
  ...
  L  3 [advisory L0 corpus-zero:pivotal] The field lexicon records zero occurrences of 'pivotal'.
  L 14 [advisory L2 structure-template:method] Paragraph contains repeated sentence-construction
       template(s): announced-enumeration; reference method fraction 4.4% (n=135).
$ echo $?
1
```

Read the last finding closely. It is not "you used a list" — it is *this
construction appears in 4.4% of the human method passages in your own corpus,
and yours is one of them*, with the reference sample size stated so you can
judge how much that 4.4% is worth.

After a claim-first rewrite:

```console
$ python tools/ai_ism_lint.py after.tex --field wgl \
    --structure --distribution --register --salience --document-structure
findings: blockers=0 L0=0 advisories=2 (strong=0)          # exit 0

$ python tools/length_gate.py after.tex --before before.tex
section                       before   after   delta  status
Introduction                      79      46     -33  ok
Method                           119     117      -2  ok
TOTAL                            198     163     -35
net unjustified growth: -35 words (tolerance 0)
findings: blockers=0 L0=0 advisories=0 (strong=0)          # exit 0
```

| Measurement | Before | After |
|---|---:|---:|
| L0 targets | 10 | **0** |
| integrity blockers | 0 | 0 |
| advisories (of which strong) | 10 (0) | **2 (0)** |
| linter exit code | `1` | **`0`** |
| document length | 198 w | **163 w** (−35) |
| length-gate advisories | — | **0** |
| protected numbers preserved | — | **7 / 7** |

**It did not converge to zero, and that is correct.** The two residual advisories
are a salience reading on the rewritten method paragraph (p89 against an n=109
human method reference) and a low-burstiness note on the same section. Neither is
strong, and the answer is a recorded disposition rather than a tuned-down
threshold: a parameter grid is *supposed* to carry numbers.

**The gate caught the author, twice.** The first rewrite attempt grew the Method
section by 60 words and the gate flagged it (`+60 GROWTH`). The second fixed that
but silently dropped two numbers while condensing — caught by demo 2.

### 2. The fidelity gate rejects the best-scoring candidate

Three candidate rewrites of one method paragraph, ranked against the original:

```console
$ python tools/rewrite_reward.py --field wgl --reference ref.txt --original ref.txt \
    --candidates cand_lossy.txt cand_faithful.txt cand_tight.txt

rank cand  combined   voice  fidelity   Δadv eligible  L0(r/c)  words(o/c)
   1    2     0.327   0.990     0.861   0.00     True  0/0  72/58  cand_tight.txt
   2    1      -inf   0.873     0.843   0.00    False  0/0  72/78  cand_faithful.txt
     over length budget: +6 words (SCIPAPER_STANDARD section 5.3; use --allow-growth
     REASON only with an author-approved justification)
   3    0      -inf   0.936     0.818   0.00    False  0/0  72/66  cand_lossy.txt
     missing: {'numbers': ['1.2', '12']}

[best] candidate 2: cand_tight.txt                          # exit 0
```

Read the `voice` column against `eligible`. `cand_lossy` scores **0.936** on
learned field similarity — better than the faithful `cand_faithful` at 0.873 —
and loses to nothing at all, because it dropped `12` radial bins and `1.2`
million sources. The style score never gets to vote. `cand_faithful` preserves
every number and is *still* ineligible, for exceeding the §5.3 length budget by
six words. Had all three been ineligible the tool exits `1` — a measured outcome
meaning *preserve the original and regenerate tighter*, not a crash.

### 3. A document with zero banned words, still caught

A 5,225-word, 10-section manuscript generated from sentence templates. No Tier A
vocabulary, no em-dashes, no register outliers — **`L0=0`**:

```console
$ python tools/ai_ism_lint.py big.tex --field wgl --document-structure

findings: blockers=0 L0=0 advisories=25 (strong=4)
axis L2.document_structure: measured

  L 1 [advisory L2 document-dispersion-manifold strong] The document's joint cross-paragraph
      dispersion sits 13.99 Mahalanobis units from the human center (conformal p = 0.0169
      <= alpha 0.05 against 58 held-out human papers (stratum 1 manifold)): its paragraph-shape
      variation pattern departs from the human band as a whole. This is a measured deviation,
      not an AI verdict.

  L 1 [advisory L2 document-role-decoupling strong] Paragraph-shape variation is decoupled from
      rhetorical role: coupling z is -0.15 (conformal p = 0.0307 <= alpha 0.05 against 162 human
      papers (stratum 1)). Human papers vary paragraph shape where the argument demands it;
      here the variation is unrelated to role.

  L 1 [advisory L2 document-shape:cross_section_similarity strong] Document-level cross section
      similarity is 0.991, at empirical percentile 1.000 of the complete-document reference.
```

This is failure mode 1, reproduced on demand. A keyword-cleaning tool reports
this document clean. The document-scale axes place it at `p = 0.0169` and
`p = 0.0307` against held-out human papers — and still refuse to call it
AI-written, because the honest statement is *this document's paragraph-shape
variation departs from the human band*, which is exactly what the finding says.

---

## Benchmark dashboard

Two kinds of number, not interchangeable: **discrimination and calibration**,
read from the evaluation record; and **latency**, measured first-party for this
README.

### Document-scale, length-fair discrimination

AUC against 169 same-length-stratum held-out human papers — the honest protocol
after the length confound was found and corrected. Source:
[§9.5](docs/architecture/evaluation/document-scale.md), re-measured 2026-08-25.

| Contrast | Manifold AUC | Role-coupling AUC |
|---|---:|---:|
| human vs **natural** AI | **0.928** | 0.702 |
| human vs **de-AI'd** AI (paragraph-level de-AI as an attack) | **0.939** | 0.751 |
| human vs **shape-adversarial** AI (deliberate raggedness) | 0.919 | **0.818** |
| human vs **skeleton-matched** structural clone | 0.916 | 0.515 |

The axes are complementary by construction: the manifold carries robust
discrimination against every tier including structure clones, while the role
axis's power concentrates on exactly the tier that narrows the manifold's margin.

### False-positive control at α = 0.05

Split-conformal, Mondrian-stratified by length tercile. Guarantee:
finite-sample, distribution-free `P(false flag) ≤ α` for exchangeable human
papers. Source: [§9.5](docs/architecture/evaluation/document-scale.md).

| Quantity | Manifold | Role | Target |
|---|---:|---:|---:|
| Human false-flag rate, leave-one-out over the calibration set | **0.040** | **0.049** | ≤ 0.05 |
| Leave-one-out per-feature band flag rate | 0.051 | 0.051 | 0.05 |

Tail power at the same operating point — reported plainly, including where it is
weak:

| Flag | natural | de-AI'd | adversarial | skeleton |
|---|---:|---:|---:|---:|
| manifold | 0.214 | 0.400 | 0.158 | 0.292 |
| role-decoupling | 0.107 | 0.333 | 0.316 | 0.042 |
| **union** | 0.321 | 0.667 | 0.421 | 0.333 |

Short documents still have the weakest tail power on the manifold axis, because
the short-human distance distribution is heavy-tailed. A length-aware manifold is
queued rather than improvised.

### Why there is no single score: the L3 confound

The learned paragraph-scale model is good — and ships `degraded` **anyway**, for
a measured reason. Source:
[§7.1–7.3](docs/architecture/evaluation/learned-model.md).

| Metric | Value | 95% interval |
|---|---:|---|
| Grouped-split AUC (20 splits, complete papers held out) | 0.9320 | 0.9218 – 0.9416 |
| Matched-stratum AUC (section × length × math × field-term) | 0.9236 | 0.9044 – 0.9414 |
| Balanced accuracy | 0.8509 | 0.8382 – 0.8642 |
| Author hard-set, **true provenance** | 0.937 | — |
| False-positive rate — public-generic AI text | 0.086 | — |
| False-positive rate — **field-topic AI text** | **0.318** | — |
| False-positive rate — **field-jargon-dense AI text** | **0.417** | — |

A 0.93 AUC headline and a 32–42% false-positive rate on field-topic AI prose are
the same model. The learned score partly measures *field register*, so it is
unreliable on the exact distribution a de-AI pass must catch. That is why L3 is
triage, capped at 0.5 confidence at paragraph scale, and never an authorship
verdict. The document-level surprisal path was also measured (0.757), is weaker
than the model-free manifold (0.881), and adds nothing to it — so it does not
rescue L3 either.

### Latency

Measured 2026-08-25 on Windows 11, Python 3.13.3, median of 7 subprocess runs per
row, including interpreter startup.

| Pass | Document | Median wall | Dependencies |
|---|---|---:|---|
| Python interpreter floor | — | 59 ms | — |
| L0 lexicon + register | 5,225 w | **328 ms** | stdlib |
| **All model-free axes** (L0 + L1 + L2 incl. document structure) | 5,225 w | **329 ms** | stdlib |
| All model-free axes | 200 w | 193 ms | stdlib |
| `length_gate.py` | 5,225 w | 341 ms | stdlib |
| `+ --oracle` (GPT-2-large token surprisal) | 5,225 w | 25.3 s | `transformers` + `torch` |
| `+ --voice` (learned L3 triage) | 5,225 w | 47.2 s | `scikit-learn` + `sentence-transformers` |
| `validate_plugin.py` (9 contract checks) | repository | 2.0 s | stdlib |
| Full test suite (214 tests) | repository | 82.9 s | stdlib |

The headline: **a complete model-free pass over a 5,225-word manuscript costs
~270 ms of analysis above the interpreter floor**, with no optional dependency
installed. The two model-backed axes cost 75×–140× more and are opt-in flags,
which is the intended shape — you should not need a GPU to lint a paper.

### Repository health

| Check | Result |
|---|---|
| Contract validator | **9/9 checks pass** |
| Unit / CLI tests | **214 passing** (15 files) |
| CI | validator + suite on every push and PR, Python 3.11, Ubuntu |

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

Then drive it from Claude Code:

```text
/sci-paper:paper                                  # load the writing standard
/sci-paper:de-ai         draft.tex --field wgl    # measure → audit → faithful rewrite
/sci-paper:condense      draft.tex                # remove redundancy, prove the shrink
/sci-paper:paper-review  draft.tex --field wgl    # A–R source-traced review
/sci-paper:figure-review draft.pdf                # compiled-page figure evidence
/sci-paper:final-review  draft.tex --field wgl    # isolated multi-reviewer orchestration
/sci-paper:brainstorm    "topic"                  # radial research exploration
/sci-paper:proposal-polish grant.tex --agency nsf # proposal register
```

---

## Skills (8)

Four jobs; what each one does is in [the eight functions](#the-eight-functions).

- **Write** — [`paper`](skills/paper/SKILL.md) · [`proposal-polish`](skills/proposal-polish/SKILL.md)
- **Revise** — [`de-ai`](skills/de-ai/SKILL.md) · [`condense`](skills/condense/SKILL.md)
- **Review** — [`paper-review`](skills/paper-review/SKILL.md) · [`figure-review`](skills/figure-review/SKILL.md) · [`final-review`](skills/final-review/SKILL.md)
- **Explore** — [`brainstorm`](skills/brainstorm/SKILL.md)

## Tools (25)

One `sci-paper.feedback.v1` contract for every finding; corpus/training entries
produce artifacts instead. Per-tool detail: [tools/README.md](tools/README.md).

#### Contract, gates, and CLI

| Tool | Purpose |
|---|---|
| `tools/deai_feedback.py` | Implements `sci-paper.feedback.v1`: stable IDs, consequence classes, measurement states, dispositions, ranking, summaries, rendering. Standard library only. |
| `tools/ai_ism_lint.py` | The unified CLI. Aggregates L0 and every advisory axis into one ranked text/JSON report. Exit `0` = no L0 target, `1` = L0 target present, `2` = invalid input or execution failure. |
| `tools/length_gate.py` | Per-section prose length-budget delta gate (standard §5.3). Exit 1 on net unjustified growth between two document versions; `--allow` records justifications. |
| `tools/rewrite_reward.py` | Ranks rewrite candidates **after** hard scientific-fidelity eligibility. Dropping *or inventing* a protected invariant scores `-inf`. |

#### L0 — lexicon and register

| Tool | Purpose |
|---|---|
| `tools/deai_register.py` | Domain register: terms the manuscript leans on that the field's own corpus does not carry, judged by corpus document frequency rather than a curated cross-discipline list. Compounds are judged by their rarest part. Advisories only. |
| `tools/ai_ism_negatives_handcrafted.txt` | Seed negative examples for the legacy classifier (data asset). |

#### L1 — information distribution

| Tool | Purpose |
|---|---|
| `tools/deai_metrics.py` | Model-free information-distribution findings — sentence-length variation, connective openers — with explicit calibration state. |
| `tools/deai_oracle.py` | Optional token-surprisal and Uniform Information Density evidence. Unavailable assets and compatibility thresholds stay explicit. |

#### L2 — sentence and document structure

| Tool | Purpose |
|---|---|
| `tools/deai_structure.py` | Sentence and paragraph construction: enumeration, repeated frames, parallel runs, symmetry, and related template families. |
| `tools/deai_salience.py` | Salience hierarchy: how far a passage's measured quantities run without an interpreting sentence between them, against a per-section human reference. Sole consumer of the numeral-preserving LaTeX projection. |
| `tools/deai_docstructure.py` | Whole-document rhetorical shape and complete-document calibration: dispersion band, per-length-stratum joint manifold, role coupling, split-conformal operating points. |
| `tools/deai_anchoring.py` | Section-class conditional claim-anchoring band — a writing-quality axis, explicitly **not** an AI-discrimination axis. |

#### L3 — learned field similarity

| Tool | Purpose |
|---|---|
| `tools/deai_features.py` | Reusable distributional, UID, punctuation, embedding, and structural features. |
| `tools/deai_voice.py` | Optional learned field-similarity triage. A bundle without an operating point is degraded and never an authorship verdict. |
| `tools/train_voice_model.py` | Trains the optional field-similarity model with source-paper grouping. Confound audits are mandatory. |

#### L4 — cooperative repair

| Tool | Purpose |
|---|---|
| `tools/deai_partition.py` | Fidelity-free merge/split suggestions that move a document toward the human dispersion band. Suggest-only, zero-token operations. |
| `tools/deai_provenance.py` | Editing-provenance ledger over the author's **own** draft history; labels each span AI-untouched → author-original by token edit ratio. Not a detector; `unmeasured` without an AI-draft ancestor. |
| `tools/deai_personal.py` | Personal dispersion baseline against the author's own prior papers — a confound-free same-author reference. `unmeasured` below three papers. |

#### Corpus and profile building

| Tool | Purpose |
|---|---|
| `tools/build_profile.py` | Builds the basic field profile: extraction, optional legacy classifier, exemplar-cache warm-up. |
| `tools/extract_style.py` | Extracts lexicon, sentence statistics, transitions, a descriptive dossier, and a section-typed exemplar bank. Re-exports every public name from `extract_sections.py`. |
| `tools/extract_sections.py` | Source-text projection and section splitting: the section vocabulary and its classifier, both named LaTeX projections, and the PDF heading heuristic. Section buckets key every per-section reference, so changing this requires a profile rebuild. |
| `tools/retrieve_exemplars.py` | Retrieves section- and topic-matched exemplar paragraphs, with embedding or explicit fallback retrieval. |
| `tools/fetch_arxiv_abstracts.py` | Fetches dated abstract corpora for controlled evaluation and training, optionally restricted to a subfield query set and named refereed journals. Rate limiting **stops the sweep and exits 2** rather than writing a truncated corpus as if it were complete. |

#### Legacy and training data

| Tool | Purpose |
|---|---|
| `tools/train_ai_ism_classifier.py` | Trains the legacy word-ngram classifier, used only as degraded advisory evidence. |
| `tools/extract_md_negatives.py` | Harvests candidate generated paragraphs for controlled evaluation and training. |

> `tools/validate_plugin.py` is a development and release tool, not a shipped
> product tool, and is excluded from the count above.

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
advisories stay visible and do not have to disappear — which is why
[demo 1](#1-before--after-on-a-draft) ends at three advisories rather than zero.

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

For scale, the reference profile behind every measured number on this page
carries (read directly from the artifacts):

| Asset | Scale |
|---|---|
| `exemplar_paragraphs.jsonl` | 578 section-typed paragraphs |
| `register_lexicon.json` | 14,220 passages · 41,126 terms |
| `docstructure_baseline.json` | 493 complete documents · conformal α 0.05 · length strata [46, 76] |
| `anchoring_baseline.json` | 500 documents |
| `salience_baseline.json` | abstract 13,438 · intro 110 · method 109 · data 106 · discussion 78 · conclusion 41 · results 31 — all six body buckets clear the 30-passage floor |

Corpus contents are **read-only, copyright-sensitive inputs** and are never
committed. Generated dossiers and exemplars may quote source prose and must not be
published unless their rights permit it. A corpus dossier is descriptive evidence —
not a normative standard, and not proof of authorship. Whole-document calibration
requires complete papers as independent observations; paragraph exemplars cannot
be relabelled as independent documents.

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

## Repository layout

```text
sci-paper/
├── .claude-plugin/          plugin.json · marketplace.json
├── .github/workflows/       ci.yml — validator + test suite on push and PR
├── docs/                    ← index + authority order at docs/README.md
│   ├── SCIPAPER_STANDARD.md      the single normative contract (v3.6)
│   ├── architecture/             DEAI_SUBSYSTEM.md · EVALUATION.md (hub) + evaluation/
│   └── design-notes/             frozen, dated reasoning records (not status)
├── skills/<name>/SKILL.md   8 skills
├── tools/                   25 product tools + the repository validator
├── tests/                   15 test files, 214 tests
├── style-corpus/<field>/    user-supplied read-only corpus (gitignored)
├── style-profile/<field>/   generated and calibrated evidence (gitignored)
├── ACKNOWLEDGMENTS.md       adapted-material attribution and adoption boundaries
├── CHANGELOG.md             per-version history
└── CLAUDE.md                working rules for this repository
```

## Development

`python tools/validate_plugin.py` runs 9 contract checks and
`python -m unittest discover -s tests -v` runs the 214-test suite; both must pass
before a release. The validator covers release metadata, skill frontmatter,
standard references, documentation authority boundaries and index completeness,
recorded suite sizes against real discovery, stale contract markers, product
registries, Python syntax, runtime imports, CLI entry points, schema fields,
linter exit semantics, Tier B behavior, tests, and CI wiring —
`tools/validate_plugin.py` itself is the authoritative list. A release also
requires independent code review, clean-checkout verification, and a green
hosted CI run on the release commit.

---

## Status, known limitations, and roadmap

Current: **v0.27.1**. Full per-version history in [CHANGELOG.md](CHANGELOG.md).

**Normative core:** `docs/SCIPAPER_STANDARD.md` v3.6 — the complete de-AI
standard in one file (layered model, document-scale detection core, cooperative
layer, the `calibration_unit` confidence cap, the §5.2 de-AI-ization procedure,
the §5.3 condense-not-accumulate rule with mechanical enforcement, and the §5.4
thesis spine shipped deliberately **without** a detector). There is no separate
de-AI standard.

### Known limitations, stated plainly

| Limitation | Current state |
|---|---|
| **No learned-model operating point** | L3 ships `degraded`. The document-level surprisal path was *measured* not to provide one (0.757 vs the model-free manifold's 0.881). |
| **Field-topic false positives** | 32–42% on field-topic and jargon-dense AI prose. This is why there is no score. |
| **Short-document tail power** | Manifold 5%-tail power on short documents is 0.214 for natural AI — tripled by the 2026-08-17 rebuild, still well short of what the 0.928 length-fair ranking implies is available. |
| **Small body-section reference** | The 2026-08-25 section rebuild cleared `results` (10 → 31, now measured) by removing the mislabelled bulk of `method` (1,303 → 109). The body buckets are honestly small now; `results` clears the floor by one passage. |
| **Cooperative-layer tools** | `deai_provenance` and `deai_personal` are honestly `unmeasured` until the author supplies their own draft history or ≥ 3 prior papers. |
| **`L1.distribution` / `L2.sentence_structure`** | `degraded` by design — no `deai_policy.json` operating point exists. Visible in every demo above. |
| **No human-judgement validation set** | Salience and register operating points are corpus-referenced, not human-labelled. |
| **A fresh clone measures nothing** | All profile assets are gitignored. Until you build a profile from your own papers, every corpus-referenced axis is `unmeasured`. |

### Roadmap

- **Length-aware manifold** — normalise dispersion-estimator noise by paragraph
  count, to recover 5%-tail power on short documents without inflating the human
  false-flag rate.
- **`deai_policy.json`** — a documented operating point for L1 distribution and
  sentence-structure strength (corpus unit, uncertainty, applicability,
  validation behavior). This is what would move two axes off `degraded`.
- **Human-labelled validation set** for salience and register precision/recall.
- **Field-topic-robust L3 operating point** with provenance and uncertainty — or
  a recorded decision that one is not obtainable from this feature set.
- **Corpus growth for thin buckets** (`results`, and sub-floor section strata).

**Field-specific guidance:** weak-lensing scientific anchors stay marked `[WGL]`
where they apply. Shared writing and review policy is field-agnostic.

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
research writing assistant · corpus-driven style · conformal prediction ·
split conformal · uniform information density · reproducibility ·
scientific integrity · LLM tooling · research automation.</sub>
