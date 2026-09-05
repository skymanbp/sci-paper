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
contains 27,841 paragraph observations across seven section buckets — `method` 9,478,
`results` 3,978, `data` 3,894, `intro` 3,812, `discussion` 3,635, `conclusion` 2,611,
`abstract` 433. The file records reference fractions for announced enumeration, ordinal
runs, tricolon-like setup/list patterns, anaphora, balanced closers, and aggregate
templating.

Counts are post-2026-09-04 (v0.36.3) and reflect five rounds of corpus-layer fixes
plus the 500-paper breadth corpus (EVALUATION §2). The third round is the
heading-coverage work in limit 5 below, which added 2,946 paragraphs (25,005 -> 27,951);
the fourth is v0.32.0's citation projection fix, which removed 44 (27,951 -> 27,907)
because a paragraph made only of leaked bibliography keys is no longer a paragraph of
prose; the fifth is the v0.36.3 profile rebuild on the v0.36.0–v0.36.2 corpus-side
fixes (heading whitespace and `\texorpdfstring`, floats and citations blanked across
lines, one assembly reader), which re-cut 66 bank rows (27,907 -> 27,841): 207 rows
gone, 131 added and 478 re-paragraphed, across 48 of the 516 papers with bank
rows.
The v0.27.1 file read 593 observations with
`results` at 26, under its 30-passage floor; the v0.27.0 file read 1,942 with `method`
at 1,671, but `method` was then `DEFAULT_SECTION_BUCKET` and absorbed every unnamed
heading, and paragraphs were split from PDF line fragments rather than reconstructed.
None of the three is comparable to the others as a count of anything. **Every bucket
now clears the floor**, so no bucket is rank-only.

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

`style-profile/wgl/uid_baseline.json` records **27,851** paragraphs that met its
25-token requirement. It stores pooled and section-level means, standard deviations,
and counts for global UID, local UID, and mean surprisal under GPT-2-large. Pooled
global UID is **3.303 ± 0.420**; local UID 3.417 ± 0.445; mean surprisal 3.563 ± 0.524.

| bucket | n | global UID |
|---|---:|---|
| method | 9,485 | 3.31 ± 0.45 |
| results | 3,979 | 3.28 ± 0.26 |
| data | 3,895 | 3.36 ± 0.51 |
| intro | 3,812 | 3.26 ± 0.41 |
| discussion | 3,636 | 3.29 ± 0.37 |
| conclusion | 2,611 | 3.33 ± 0.43 |
| abstract | 433 | 3.23 ± 0.49 |

Counts are post-2026-09-05 (fifth rebuild, on the 27,851-row bank). Neither the 593-paragraph / 3.383 ± 0.680
nor the 1,942-paragraph / 3.329 ± 0.391 predecessor is comparable: the first was blind
to the breadth corpus, and the second labelled most of its paragraphs `method` by
default and split them from PDF line fragments, so both its size and its section keys
described something other than what they claimed (§14.2, EVALUATION §2).

The section means are strikingly tight — 3.23 to 3.36 across seven buckets, a spread of
0.13 against within-bucket standard deviations of 0.26–0.58. It was 0.15 before the
fourth rebuild and 0.13 after, so removing the leaked keys did not disturb the null. **Section identity barely
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
