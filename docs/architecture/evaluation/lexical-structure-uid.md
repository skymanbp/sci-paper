# EVALUATION — L0 behaviour, sentence-structure and UID reference evidence · `sci-paper` v0.27.1

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
contains 593 paragraph observations across seven section buckets — `method` 163,
`discussion` 118, `data` 112, `intro` 109, `conclusion` 48, `results` 28, `abstract` 15.
The file records reference fractions for announced enumeration, ordinal runs,
tricolon-like setup/list patterns, anaphora, balanced closers, and aggregate templating.

Counts are post-2026-08-25. The pre-rebuild file read 1,942 observations with `method`
at 1,671, but `method` was then `DEFAULT_SECTION_BUCKET` and absorbed every unnamed
heading, and paragraphs were split from PDF line fragments rather than reconstructed
(§14.2 records both fixes and their measured effect). `data` is a new bucket; `results`
grew 10 → 28 and is still under the 30-passage floor.

Interpretation limits:

1. The observations are paragraph-level and cannot calibrate whole-paper shape.
2. A deterministic pattern match is evidence for inspection, not proof of poor prose
   or machine generation.
3. The current baseline does not by itself define a strong-advisory operating point.
4. Author labels for the difficult hard set are absent, so label-based calibration
   has not been performed.

## 6. UID reference evidence

`style-profile/wgl/uid_baseline.json` records
593 paragraphs that met its 25-token requirement. It stores pooled and section-level
means, standard deviations, and counts for global UID, local UID, and mean surprisal
under GPT-2-large. Pooled global UID is **3.383 ± 0.680** over all 593, across seven
buckets — `method` 163, `discussion` 118, `data` 112, `intro` 109, `conclusion` 48,
`results` 28, `abstract` 15.

Counts are post-2026-08-25 and are not comparable to the 1,942-paragraph / 3.329 ± 0.391
figure the pre-rebuild file carried: that bank labelled most of its paragraphs `method`
by default and split them from PDF line fragments, so both its size and its section
keys described something other than what they claimed (§14.2). `data` is a new bucket
and `results` has a surprisal reference for the first time.

This supports comparative evidence, but the current subsystem reports degraded status
because the profile does not document an operating point, uncertainty-to-action rule,
or leave-source-out human flag behavior. The values must not be turned into a universal
threshold.
