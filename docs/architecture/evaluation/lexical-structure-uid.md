# EVALUATION — L0 behaviour, sentence-structure and UID reference evidence · `sci-paper` v0.32.0

Part of the evaluation record. The hub — evaluation contract, current
axis status, repository verification, release evidence boundary, and the
map of every section — is [`EVALUATION.md`](../EVALUATION.md); read it
first. Section numbers are global across the whole record, so a reference
like "§9.5" means the same thing in every file.

Normative policy lives in [`SCIPAPER_STANDARD.md`](../../SCIPAPER_STANDARD.md);
nothing here can redefine it. All machine-readable findings use the
`sci-paper.feedback.v1` contract.

---

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
[`tests/test_ai_ism_lint_cli.py`](../../../tests/test_ai_ism_lint_cli.py).

## 5. Sentence-structure reference evidence

`style-profile/wgl/structure_baseline.json`
contains 28,439 paragraph observations across seven section buckets — `method` 9,654,
`results` 4,065, `data` 3,953, `intro` 3,848, `discussion` 3,739, `conclusion` 2,747,
`abstract` 433. The file records reference fractions for announced enumeration, ordinal
runs, tricolon-like setup/list patterns, anaphora, balanced closers, and aggregate
templating.

**How the bank reached this shape.** This is the record's one account of the
corpus-layer history; every section-keyed count elsewhere is read against it.

| bucket | v0.27.1 (31 files) | v0.28.0 | v0.29.0 (heading coverage) | v0.32.0 (citation fix) | v0.36.3 (profile rebuild) | v0.39.0 (profile rebuild) |
|---|---:|---:|---:|---:|---:|---:|
| abstract | 15 | 433 | 433 | 433 | 433 | 433 |
| intro | 109 | 3,753 | 3,844 | 3,840 | 3,812 | 3,848 |
| data | 112 | 3,929 | 3,915 | 3,908 | 3,894 | 3,953 |
| method | 163 | 8,144 | 9,522 | 9,512 | 9,478 | 9,654 |
| discussion | 118 | 3,088 | 3,653 | 3,647 | 3,635 | 3,739 |
| conclusion | 48 | 2,533 | 2,610 | 2,609 | 2,611 | 2,747 |
| results | 26 | **3,118** | **3,964** | **3,958** | **3,978** | **4,065** |
| **total** | **593** | **25,005** | **27,951** | **27,907** | **27,841** | **28,439** |

- **v0.28.0 (2026-08-25), two rounds of corpus-layer defects.** Section labels:
  `classify_section` matched titles in the singular only, so
  `Results`/`Conclusions`/`Systematics` fell to `method`; `method` was the default
  bucket and absorbed every unnamed heading; PDF table cells were accepted as
  headings and PDF "paragraphs" were line fragments. An unrecognised heading is now
  `unknown` and is dropped rather than guessed. What counts as a paper: `\include`
  fragments counted as separate papers (one review entered every distribution
  twelve times); selecting the root instead lost the body it includes (72 words in
  place of 64,657); the root selector and the reader resolved `\input` targets
  differently; a `\subsection` did not inherit its `\section`, sending 54.8% of all
  section words to `unknown`; and the 500-paper `fulltext-arxiv/` breadth corpus was
  invisible to every paragraph-level baseline. Register composition moved with it:
  abstracts fell from 96% of the reference to 35%.
- **v0.29.0**, the heading-coverage work in limit 5 below: 2,946 paragraphs added.
- **v0.32.0**, the citation projection fix: 44 removed, because a paragraph made
  only of leaked bibliography keys is no longer a paragraph of prose.
- **v0.36.3**, the rebuild on the v0.36.0–v0.36.2 corpus-side fixes (heading
  whitespace and `\texorpdfstring`, floats and citations blanked across lines, one
  assembly reader): 66 fewer — 207 rows gone, 131 added and 478 re-paragraphed,
  across 48 of the 516 papers with bank rows.
- **v0.39.0 (2026-09-27)**, the rebuild on the corpus-side fixes of the 2026-09-27
  audit: a paragraph that opens on a citation or an equation enters the bank (D16),
  placeholders are no longer words (D7), non-ASCII letters are letters (D10), and
  `\[…\]` and `$$…$$` are mathematics on the corpus side as on the manuscript side
  (A5, A6). 598 more on the same 516 papers; how the 598 divide between those fixes
  was not measured.

The v0.27.1 file read 593 observations with `results` at 26, under its 30-passage
floor; the v0.27.0 file read 1,942 with `method` at 1,671, when `method` absorbed
every unnamed heading and paragraphs were split from PDF line fragments. None of the
early counts is comparable to the others as a count of anything. **Every bucket now
clears the floor** — `results`, under it in v0.27.1, holds 4,065 — so no bucket is
rank-only.

The curated tiers and the breadth corpus are distinct roles. The tiers carry every
weighted aggregate and the dossier; the breadth corpus is unweighted and feeds the
reference distributions only, so it cannot restyle the imitation target.
`retrieve_exemplars` reads the curated tiers by default. At v0.28.0 one arXiv
bundle in 500 lost 35% of its prose, because it ships chapter files with no root
that assembles them.

Interpretation limits:

1. The observations are paragraph-level and cannot calibrate whole-paper shape.
2. A deterministic pattern match is evidence for inspection, not proof of poor prose
   or machine generation.
3. The current baseline does not by itself define a strong-advisory operating point.
4. Author labels for the difficult hard set are absent, so label-based calibration
   has not been performed.
5. Section coverage is partial, measured, and partly closed. **Correction:** v0.28.1
   published this gap as "1,804 of 5,074 headings (35.6%)". Those counts are wrong.
   They came from an ad-hoc probe that used a re-typed regex including
   `\subsubsection` — which `RE_SECTION` does not split on — over every `.tex` file
   including the ones `select_document_roots` rejects, under a `timeout` that may have
   truncated the sweep. Re-derived through `corpus_documents` and the shipped
   `RE_SECTION`, the pre-v0.29.0 figures were **3,026 of 9,222 (32.8%)** in `wgl` and
   **52 of 148 (35.1%)** in `wgl-letter`. The rate was approximately right; the counts
   were not.

   v0.29.0 then ranked the actual fall-through headings and closed the unambiguous
   part, taking `wgl` to **2,334 of 9,178 (25.4%)** and `wgl-letter` to **42 of 148
   (28.4%)**. Three causes were separable. LaTeX markup inside the title: `RE_SECTION`
   captured `[^}]+` and stopped at the first inner brace, so `\section{Results\label{
   sec:res}}` classified the string `Results\label{sec:res` and
   `\section{\hspace*{+0.0mm}Foo}` classified a spacing command. Front matter:
   "Affiliations" had no `skip` rule. Vocabulary: "Covariance matrix", "Likelihood",
   "Blinding", "Cosmological constraints", "Validation" and "Forecasts" name section
   roles the rules did not carry.

   What remains `unknown` is mostly topic headings — "Matter power spectrum", "Galaxy
   clustering", "Axion stars" — and stays that way deliberately. Two frequent
   candidates were **refused**: "Measurements" (in weak lensing "Shear measurement" is
   method while "Mass measurements" is results) and "Background" (spanning intro,
   method and data). Guessing either is how `method` became the residue this
   vocabulary exists to prevent, so the remaining ~25% is a floor set by the ambiguity
   of the headings themselves, not a backlog.

## 6. UID reference evidence

`style-profile/wgl/uid_baseline.json` records **28,444** paragraphs that met its
25-token requirement. It stores pooled and section-level means, standard deviations,
and counts for global UID, local UID, and mean surprisal under GPT-2-large. Pooled
global UID is **3.301 ± 0.413**; local UID 3.412 ± 0.439; mean surprisal 3.558 ± 0.519.

| bucket | n | global UID |
|---|---:|---|
| method | 9,659 | 3.30 ± 0.44 |
| results | 4,065 | 3.28 ± 0.26 |
| data | 3,953 | 3.35 ± 0.50 |
| intro | 3,848 | 3.26 ± 0.39 |
| discussion | 3,739 | 3.29 ± 0.37 |
| conclusion | 2,747 | 3.35 ± 0.43 |
| abstract | 433 | 3.23 ± 0.49 |

Counts are from the v0.39.0 rebuild (2026-09-27), on the 28,444-row bank. Neither the 593-paragraph / 3.383 ± 0.680
nor the 1,942-paragraph / 3.329 ± 0.391 predecessor is comparable: the first was blind
to the breadth corpus, and the second labelled most of its paragraphs `method` by
default and split them from PDF line fragments, so both its size and its section keys
described something other than what they claimed (§5).

The section means are strikingly tight — 3.23 to 3.35 across seven buckets, a spread of
0.12 against within-bucket standard deviations of 0.26–0.50. It was 0.15 before the
v0.32.0 citation fix, 0.13 after it and after v0.36.3, and is 0.12 now, so neither removing
the leaked keys nor the later rebuilds disturbed the null. **Section identity barely
moves paragraph-level UID in this corpus.** That is a null worth recording rather than
a defect: it means a per-section UID operating point would be calibrating on a
difference smaller than its own noise, which is consistent with §9.8's finding that the
surprisal path adds nothing to the model-free manifold at document scale.

This supports comparative evidence, but the current subsystem reports degraded status
because the profile does not document an operating point, uncertainty-to-action rule,
or leave-source-out human flag behavior. The values must not be turned into a universal
threshold.

## 16. `L1.distribution`: the operating point is refuted, not merely absent

`deai_policy.json` would give `L1.distribution` and `L2.sentence_structure` a
calibrated operating point and move both off `degraded`. It was recorded as the
roadmap item that would do so, on the assumption that the corpus was the binding
constraint. With the corpus at 500 reference papers (2026-08-25) that assumption
is testable, and it is wrong: the two statistics the axis would threshold do not
support one.

Unit is one complete document — sections of the same class averaged, never counted
twice. Human side is the 500-paper reference corpus; AI side is the `docval` tiers.
Direction is the axis's own: burstiness flags **low** sentence-length variation,
signposting flags a **high** connective-opener rate.

| tier | burstiness ratio (median) | AUC vs human | flagged at the shipped 0.60 |
|---|---:|---:|---:|
| **human (n=499)** | **0.775** | — | **36/499 = 0.072** |
| `ai` | 0.442 | 0.987 | 19/20 |
| `ai_skeleton` | 0.435 | 0.983 | 21/24 |
| `ai_natural` | 0.646 | 0.780 | 17/40 |
| `ai_deai` | 0.721 | 0.628 | 3/20 |
| `ai_adversarial` | 1.036 | **0.181** | 1/40 |
| `ai_long` | 0.823 | **0.441** | 0/29 |

Burstiness separates naive generation almost perfectly and **reverses sign** on the
two tiers that matter: adversarial prose is *more* bursty than the human median
(1.036 against 0.775), and long-form generation sits inside the human band. An
operating point fitted here would flag 7.2% of human papers while catching 1 of 40
adversarial and 0 of 29 long-form documents. That is the pattern the standard
already used to reject the inference-connective rate — a statistic that reverses
between AI banks is not evidence — and it is the guardrail the §9 confound audit
exists to enforce.

Signposting is worse: it has no power in either direction. Every AI tier has a
median and a p90 of **0.000** connective-opened paragraphs, against a human median
of 0.005 and p90 of 0.043. Document-level AUC is **0.247** (0.267 for `ai_long`) —
below chance, because AI prose in this corpus signposts *less* than human prose.
At the shipped default of 0.20 the rule flags 1 of 498 human documents and **0 of
173 AI documents**. There is no threshold to calibrate; the statistic does not
discriminate.

**Disposition.** `deai_policy.json` is not written, and the roadmap entry that
promised it is withdrawn. `L1.distribution` stays `degraded` for a *measured*
reason rather than a missing asset, which is a stronger statement than the one it
replaces: the two axes remain useful as writing advisories — low variation and
opener-heavy paragraphs are worth an author's attention — and must not be given
consequence weight. `L2.sentence_structure` keeps its deterministic matches
`measured` and its strength `degraded` on the same evidence.

Reproduce: score `style-profile/<field>/docval/ai_*` and the `fulltext-arxiv/`
reference papers through `deai_metrics.CONNECTIVE_OPENERS` and the per-bucket
`sentence_stats.json` CV, one observation per document.
