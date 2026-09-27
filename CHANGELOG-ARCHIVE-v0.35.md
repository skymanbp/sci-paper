# Changelog archive — v0.35.0 through v0.35.1

Entries moved out of [CHANGELOG.md](CHANGELOG.md) on 2026-09-27 (v0.39.0) when
the live changelog passed the repository's 750-line budget. Nothing here is
edited; the history is verbatim.

- Current releases: [CHANGELOG.md](CHANGELOG.md)
- **v0.33.0 through v0.34.0**: [CHANGELOG-ARCHIVE-v0.33-v0.34.md](CHANGELOG-ARCHIVE-v0.33-v0.34.md)
- **v0.27.1 through v0.32.0**: [CHANGELOG-ARCHIVE-RECENT.md](CHANGELOG-ARCHIVE-RECENT.md)
- **v0.22.0 through v0.27.0**: [CHANGELOG-ARCHIVE.md](CHANGELOG-ARCHIVE.md)
- **v0.21.0 and earlier**: [CHANGELOG-ARCHIVE-EARLY.md](CHANGELOG-ARCHIVE-EARLY.md)

---

## v0.35.1 — 2026-09-03

A post-release audit of the documentation, not of the code. An escape the
writer lost had truncated the tools table in both READMEs, the one published
figure with no artifact behind it was wrong, and several figures and dates in
the record had drifted from what they describe.

### A lost backslash ended the tools table four rows early

The `tools/tex_macros.py` row wrote `\newcommand` without its backslash, and
the consumed newline split the row, so the table stopped rendering there —
`retrieve_exemplars`, `fetch_arxiv_abstracts`, `train_ai_ism_classifier` and
`extract_md_negatives` fell out of it, in both READMEs. The same damage sat in
the v0.32.0 changelog entry at `\nocite`.

### The worked example published a count the linter does not report

`examples/README.md` said 19 total advisories where `ai_ism_lint` reports 18.
It was the only published-figure document with no artifact behind it, so
nothing read it. `tests/test_published_figures.py` now renders both of its
tables — the before/after summary and the per-rule counts — by running the
linter on the two shipped manuscripts and looking for the result, the same way
every other pinned figure is rendered from the artifact it was read from. A
cell the linter does not produce fails the case, so a document that agrees with
a stale run and a document nobody updated fail identically.

### Figures and dates the record had drifted from

- **203**, not 200, held-out refereed papers, in the two `DISPOSITIONS.md` rows
  that still carried the count from before §18 re-measured it.
- The v0.30.0–v0.33.0 changelog headings were dated 2026-08-27; their tagger
  dates are **2026-08-26**.
- The release-gate label in `EVALUATION.md` §12 stamped a version on a suite
  size measured after it. It now reads "as of 2026-09-03; last tagged release
  v0.35.1", so the version names the tag and the date names the measurement.
- Both README latency tables paired 394 tests with 81.4 s, a wall time taken on
  the 393-test suite. The suite row is re-taken: **73.0 s**, median of 3, the
  three runs spanning 70.0–86.9 s. Every other row still stands from the
  2026-08-27 take and the preamble now says which rows carry which date.
- `docs/README.md` called the evidence record five files where it is eight,
  gave three of them section maps missing the sections added since, counted
  four kinds of document where six live there, and described the validator's
  version and suite-size checks narrower than they are.
- The unit-pattern anchor in both READMEs pointed at `rewrite_reward.py:41`;
  the pattern is at `:56`.
- Both READMEs said CI runs on every push. `ci.yml` filters `branches: [main]`,
  so it runs on every push to `main` and every pull request.

### Also

- `.gitignore` covers `models/hf-cache/`, `.ce/` and `.ccm/` — relocated model
  cache and machine-local tool state, never repository content.
- Suite: 394 tests across 20 files; `validate_plugin.py` 9/9.

## v0.35.0 — 2026-08-27

The axis that counts numbers could not see numbers written as macros, a public
repository was carrying an unpublished manuscript's method summary, and the
worked example that demonstrates any of this now runs on a synthetic paper
instead of a real one.

### Numbers held in macros were invisible, in both directions

A manuscript that writes `\newcommand{\Nsamples}{12}` in its preamble and
`\Nsamples{}` in its results put a measured quantity where neither named text
projection could read it. `RE_TEX_SIMPLE_CMD` reduces a command to its
argument, so the use site contributed nothing while the definition site
contributed the digits once, in the preamble, attributed to no reported
section. Two errors running in opposite directions, which is why the net stayed
small enough to go unnoticed: on the manuscript that surfaced it, expanding the
uses adds 650 digits and dropping the definitions removes 493.

Found by running the tools on a real manuscript, not by a test. The salience
axis had been reporting recital percentiles for that paper computed on 91% of
its digits, and correcting it moved that paper from 16 recital findings to 26.

`tools/tex_macros.py` expands numeric-literal macros once, on the assembled
document root, because that is the only scope holding both a preamble
definition and a body use — the same reason `read_tex_document` folds
`\include` in the first place. Only a bare numeric literal expands, so
`\newcommand{\Msun}{M_\odot}` and every macro taking an argument are untouched.

Both salience baselines were rebuilt rather than left to score expanded
manuscripts against an unexpanded reference. They move by **zero to four
decimals** at the p90 and p95 gates, across all three features and all seven
buckets, in both `wgl` and `wgl-letter`: 88.2% of 390 corpus documents never
use the construction. That is what separates a correction from a rescaling, and
it means no published salience figure in `EVALUATION.md` changes (§22).

### An unpublished manuscript's method summary was in a public repository

This repository is public. Content from the author's unpublished manuscripts
had accumulated in the evaluation record since 2026-07-12, in increments that
each looked locally harmless — a codename in a test fixture, a macro and its
value in a docstring, one fidelity-preserving rewrite quoted in full.

The aggregate was a complete method summary: enough of the method for a competitor to reconstruct the contribution. Public for 46 days.

The quoted rewrite was the largest single exposure, and it was labelled a
proposal rather than a quotation, which is exactly why it survived review: the
rewrite gate protects numbers, citations, macros, entities and claim/evidence
relations, so a fidelity-preserving rewrite discloses what the original
discloses. Being a rewrite is not a defence.

Removed: the quoted block, the method-component list, manuscript codenames
throughout, one real measured value, and manuscript-derived test fixtures,
which now use invented macros. Kept: every measurement. Finding counts,
percentiles, rule names, before/after tables and the panel results describe how
the tools behave, not what the paper found, and they are why the record exists.

Git history was rewritten to remove the same content from every earlier commit.
That does not undo publication — the content may persist in existing clones,
forks and upstream caches.

### A worked example that is safe to ship

`examples/` now carries a synthetic manuscript and the same paper after acting
on the findings. The topic is a textbook one and every value is invented, so
the demonstration no longer depends on anyone's unpublished work.

It is also a more honest demonstration than a clean sweep would be. L0 targets
go to zero and `discourse-cohesion` from 3 findings to 1, while
`salience-recital` **rises** from 4 to 6 — because carrying a noun forward to
link two sentences pulls the subject into sentences that also carry a numeral.
In a number-dense passage cohesion and recital want opposite things and no
rewrite satisfies both. Both findings are true, and which to act on is the
author's judgement, which is why neither is a blocker and there is no score.

### Also

- The re-export contract test named its excluded module imports one at a time
  (`re`, `defaultdict`, `Path`), so it failed the moment a new import appeared.
  It now excludes module objects by type.
- Suite: 393 tests across 20 files; `validate_plugin.py` 9/9.
