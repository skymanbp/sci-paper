# Changelog

All notable changes to the `sci-paper` plugin. Versions follow the
`plugin.json` / `marketplace.json` `version` field.

## v0.33.0 — 2026-08-27

The roadmap's last engineering item ships and its strongest measurement is
refuted. Both outcomes came from the same discipline: measure the thing against
a population it was not built on, and believe the result.

### Two discourse axes, at two different units

`tools/deai_discourse.py` adds `L2.cohesion` (given/new linkage — how much of a
sentence's content vocabulary the sentence before it already used) and
`L2.hedging` (epistemic markers per 1,000 words). Both fire **below** the field's
tenth percentile, the opposite direction from every existing axis, because here
the defect is absence rather than excess. Roadmap rank 6, `Deferred` since
v0.26.1.

They measure at different units, and that is forced rather than chosen. Hedging
has **no paragraph-scale lower tail at all**: on the 27,917-paragraph `wgl` bank
its tenth percentile is exactly 0.000 in every one of the seven section buckets,
because a 40-word paragraph that hedges nowhere is entirely ordinary. A gate
there is one no passage can fall below, and the axis would have reported a
confident zero findings forever. Regrouped so one section is one unit, six of
seven buckets separate (p10 from 1.055 in `data` to 3.350 in `discussion`);
`abstract` stays flat and abstains, since an abstract *is* one passage. So
cohesion calibrates and detects per paragraph, hedging per section, and each
artifact records its own `unit` so the two can never be read against each other.

Hedging ships **restricted to `intro`**, and two independent measurements put the
restriction in the same place. Held-out transfer at the p10 gate on 203 refereed
papers: 7.89% in `intro` against 15.48%–26.77% everywhere else. Worst-of-six
generation regimes: 0.613 in `intro` against a 0.460 human-vs-human null, while
`conclusion` runs *below chance* at 0.376. Cohesion needs no restriction — it
transfers at 10.87% overall against a 10% design point, in every bucket, and
separates all six regimes in `intro` at worst-of-six 0.676 (null 0.515).

Both floors were measured, not picked. The cohesion sentence floor is 3 rather
than 4 because at 4 the 20-document `ai` tier offers 15 measurable introduction
paragraphs in total and at 3 it offers 62, with the separation unchanged (0.676
against 0.674). The hedging word floor is 150 because it is the first floor at
which every non-abstract bucket resolves, and 250 buys nothing while costing the
`abstract` bucket 86% of its sections.

Evidence: [EVALUATION §19](docs/architecture/evaluation/discourse-and-citation.md).

### Citation placement: refuted on its own pre-registered condition

v0.32.0 recorded citation placement as the strongest model-free discriminator in
the whole record — section-matched rank AUC **0.866** in `method`, surviving the
section, length and human-vs-human controls — and declined to ship it for one
stated reason: all 173 machine documents came from a single generation process,
so one bank could not separate "AI cites more" from "these prompts made it cite
more". The condition for shipping was a second, independently produced bank.

Two banks of 20 documents each, same 20 topics, a **different model** (Codex
`gpt-5.6-terra`), differing in one line of prompt. With no citation instruction
the same statistic scores **0.053** — not the absence of separation, but
separation of nearly equal strength *in the opposite direction*. With one it
scores **0.734**. Density swings 12.5× (1.00 to 12.55 citations per 1,000 words)
around a human median of 6.20, so the two machine extremes bracket the human
distribution instead of sitting on one side of it.

The signal is real and it is not about authorship: it is about which model,
prompted how. Refuted, and the bar it sets for anything after it — hold your sign
across independently produced banks — is stronger than the three controls
v0.32.0 applied. [EVALUATION §20](docs/architecture/evaluation/discourse-and-citation.md).

### One `(feature, unit)` reference for every per-bucket axis

`tools/deai_reference.py` (roadmap rank 2, `Deferred (elegance debt)`) now owns
the quantile grid, the plateau-top percentile reader, the 30-unit sample floor,
the paragraph and section sweeps, the artifact loader — which had **five copies**
across the suite — and the calibration loop. It holds no policy.

It stopped being elegance debt the moment a second per-bucket axis existed, and
earned its keep immediately: its one invariant is that calibration and detection
share a unit and a grid, and that check is what caught the hedging axis
calibrating where no lower tail exists. `cli_common.axis_main` absorbs the
`--calibrate`-or-read-one-file CLI that three tools carried near-byte-equivalent
copies of, and `deai_feedback.reference_block` the `reference=` payload six
detectors spelled out separately.

### Also

- `deai_discourse` is wired into `ai_ism_lint` behind `--discourse` (default on),
  and reports **one axis status per feature**, never a joint one — a field can
  support cohesion and not hedging, and does.
- Both README demos are now pinned to the axis set that produced them
  (`--no-discourse`); demo 1 arm C would otherwise draw a second advisory it was
  never scored with.
- `tests/test_published_figures.py` pins the two new references, including each
  bucket's p10 gate, and was negative-tested 4/4.
- `tests/_profilefixture.py` gives the axis tests one throwaway-profile builder;
  the two copies had already drifted on whether a record carries a `source`,
  which decides whether a section-unit reference can be built at all.
- 34 tools, 360 tests (19 files). Dead `argparse`/`json`/`deai_metrics` imports
  removed from four tools after the CLI extraction.
- The latency table is re-taken **whole**, not row by row: the interpreter floor
  alone moved 56 → 84 ms since v0.32.0, so no row from that table was comparable.
  The validator row was the worst of them, published at 359 ms against a measured
  2.3 s. A complete model-free pass is now 409 ms with the two new axes on
  (~325 ms above the floor). The first re-run was discarded — it read a 295 ms
  interpreter floor because it was competing with the session that started it.

## v0.32.0 — 2026-08-27

Asked what was still open, the audit found two more places where the calibration
side and the detection side were not reading the same text — and one of them let
the **held-out evaluation set be collected as calibration input**.

### A four-name allowlist against 46 citation commands

`RE_TEX_CITE` matched `cite|citep|citet|citealt` and required the brace to
follow the command name directly. The corpus carries **46 distinct cite-command
names over 75,566 uses**, and an unmatched one falls through to
`RE_TEX_SIMPLE_CMD`, whose job is to substitute a command's argument as text.
So the bibliography key became a word: `\citep[e.g.][]{Smith2020}` → `Smith2020`.

**8,835 leaking occurrences across 565 of 1,490 `.tex` files** — 8,100
optional-argument forms, plus `\citealp`, `\citeyear`, `\citeauthor`,
`\citenum`, `\citeyearpar`.

Matched now **by shape, not by name**, in three behaviours, because three exist:
a citation renders a mark, a declaration (`
ocite`, `\setcitestyle`) renders
nothing, and `\citetext` wraps prose the author wrote. A name allowlist is the
wrong instrument — the tail is per-paper local macros (`\citeg`, `\citejap`,
`\putcite`, one paper each). Verified exhaustively: 46 names × 5 written forms
× both projections.

### Seven per cent of the digits the salience axis read were citation years

A bibliography key ends in a year, and `latex_to_numeral_text` keeps numerals so
`deai_salience` can measure how a passage distributes its quantities. Over the
203 held-out papers, digits **396,814 → 369,056 (−27,758, −7.00%)**. This is a
correctness fix to a *shipped, `measured`* axis, larger in relative terms than
the register effect that led to it. Control re-run, not assumed: **0 of 2,759**
salience findings on those papers start on a bibliography line.

### The held-out set could be collected as calibration input

`corpus_documents` walks with `rglob` and filtered nothing, and both
`deai_anchoring --calibrate` and `deai_docstructure --calibrate` take a
`--corpus-dir` that the documentation points at the field root:

| `--corpus-dir` | before | after |
|---|---:|---:|
| `style-corpus/wgl` | **717** | 517 |
| `style-corpus/wgl/fulltext-arxiv` | 500 | 500 |
| `style-corpus/wgl/fulltext-heldout` | 200 | 200 |

The shipped baseline was 517 — built before the held-out set existed. Re-running
the documented command today would have absorbed all 200 evaluation papers, with
no error and nothing in the output but a count nobody was checking. The existing
held-out test pinned `extract_style`'s source tuple, which this path never
consults; the guard now lives in the collector, so every caller inherits it.

### The register operating point, derived rather than estimated

`MIN_MANUSCRIPT_USES = 5` was an estimate. Swept 5 → 50 against the 203 held-out
papers and 173 machine documents, **rank AUC stays below 0.5 at every setting**:
the axis fires more on refereed prose than on machine prose everywhere on the
curve, and tightening silences the machine side faster. No setting makes it a
detector, so the roadmap item is answered by refuting its premise. Cut at **15**,
the first point where a referee-grade paper is not flagged more often than not.

| | v0.31.0 | v0.32.0 |
|---|---:|---:|
| held-out register findings | 887 | **198** |
| per 1,000 words | 0.3842 | **0.0858** |
| documents flagged | 87.19% | **44.83%** |
| rank AUC vs machine text | 0.1479 | **0.2856** |
| paired leakage suppressed | 86.25% of 887 | **94.44% of 198** |
| salience gates | | *unchanged* |

`machine:ALL` register is byte-identical across the citation fix (63 findings,
0.0917, 0.2428): those documents carry no LaTeX citations, so the fix cannot
touch them. The sweep and the evaluator are separate programs and agree to four
decimals on the flag rate at the chosen point.

### A format variant is not a domain

`wgl-letter` reported `degraded` since v0.30.1. Enlarging it is impractical
(ApJL is 24 papers in 5,364 arXiv records) and wrong: register measures *domain*
vocabulary and a letter is a *format*. On 36 letter-format documents the
706-passage letter bank produced **262 findings the field bank did not** — `sne`,
`bao`, `pantheon`, `posteriors`, and `letter` itself — against **2** the other
way. A `<field>-<variant>` profile now judges against `<field>` and names the
borrowed bank in `reference.borrowed_from`. Its corpus grew 706 → 1,574 passages,
still 6.4× coarser than the gate, so the fallback stays active.

### Citation placement: unblocked, measured, not shipped

The projection fix unblocked de-AI frontier rank 6. Whole-document rank AUC is
0.906 on cited-sentence fraction, but section-matched it is 0.616–0.866
(strongest in `method`: human 0.1652 n=155 vs machine 0.3671 n=149),
length-matched within that section 0.835, and the **human-vs-human null is
0.553**. It survives every control and is the strongest model-free discriminator
in the record — and it is not shipped, because all 173 machine documents come
from one generation process and one bank cannot separate "AI cites more" from
"these prompts made it cite more".

### Also

- Broadening the citation pattern reclassified **1,028 of 79,904** held-out
  sentences (1.29%) from unanchored to anchored and **0** the other way; the
  anchoring baseline was rebuilt from the corrected 517-document population.
- `corpus_cos` ablation withdrawn rather than deferred: `confound_audit` bins on
  record metadata the feature cache does not carry, so a cache-only ablation
  computes a different statistic from the three recorded retrains, and its only
  consumer is a `degraded` audit-only classifier with no shipped operating point.
- Three register fixtures hard-coded 5 or 6 repetitions and would have gone
  silently green-to-red at the new floor; they now derive the count from
  `MIN_MANUSCRIPT_USES`.
- `REFERENCE_DIR` and the collector's held-out rule now share one literal.

328 tests across 17 files; validator 9/9.

## v0.31.0 — 2026-08-27

Asked what was left undone, the answer turned out to be inside the number
v0.30.0 had just published. **58.7% of the register false positives measured on
held-out refereed papers were not about vocabulary at all.**

### Calibration and detection were reading different documents

The corpus document frequency is built from `exemplar_paragraphs.jsonl`, which
`extract_style` produces by section-splitting and dropping the preamble and
every `skip` bucket. `manuscript_terms` read the **whole raw file**. So the two
sides of one ratio ran on different projections: `dipartimento`, `cedex`,
`helsinki` and a long list of author surnames have df 0 on the corpus side
because front matter and bibliographies were stripped there, and count ≥ 5 on
the manuscript side because they were not stripped here.

Measured on the 203 held-out papers, by region:

| region | share of findings |
|---|---:|
| body prose | 41.3% |
| preamble (title / author / affiliation) | 27.5% |
| bibliography (`thebibliography`, `\bibitem`) | 26.3% |
| TeX control words (from preamble macro bodies) | 4.1% |
| `skip` sections | 0.9% |

A bibliography is an *environment*, not a section, so the section-level `skip`
bucket never saw it — it sits inside the span of whatever section precedes it.

`deai_register.body_only` blanks those regions, preserving line numbers so
section attribution keeps working, and keeps the abstract environment that
AASTeX puts inside the dropped preamble.

### Corrected figures

| | v0.30.0 | v0.31.0 |
|---|---:|---:|
| held-out register, per 1,000 words | 0.991 | **0.384** |
| held-out register, documents flagged | 93.6% | **87.2%** |
| rank AUC vs machine text | 0.080 | **0.148** |
| paired leakage suppressed | 72.7% of 2,287 | **86.3% of 887** |
| **every salience figure** | — | **byte-identical** |

No threshold changed. Salience reproducing exactly is the control: it needed no
fix, and was checked rather than assumed — 0 of its 1,077 findings on these
papers fall in a bibliography, so the class has one member.

What remains is a long tail rather than one cause: LaTeX markup that
`latex_to_plain` does not strip (`htb` from a float specifier, `hsize`,
`vskip`), a few surnames in running prose, and genuine cross-subfield
vocabulary — the held-out sweep pulled sub-mm papers whose instrument names
(`mambo`, `aztec`, `pdbi`) a weak-lensing corpus really does not contain.

### Also

- `render` printed the whole gate-transfer dict into the sentence naming the
  0.9 percentile; a local name collision, now pinned by a test.
- §17 moved to `evaluation/held-out-labels.md`; its host had passed the
  750-line budget.

315 tests across 17 files; validator 9/9.

## v0.30.1 — 2026-08-27

An audit for anything left undone found a second field running a different
rule from the documented one, with no sign that it was.

### A count floor cannot guard a rate gate

`MIN_CORPUS_PASSAGES` is 500 passages; `RARE_DF_RATE` is 1e-4. The two are
unrelated. A bank of *n* passages cannot express a non-zero document-frequency
rate below 1/n, so under **10,000** passages the firing rule collapses from
"df rate below the gate" to "df == 0" — a single occurrence anywhere clears the
flag.

EVALUATION §15.5 derived exactly this in v0.26.1 and used it to reject a
254-document subfield bank, but the conclusion was never turned into a guard.
The shipped `wgl-letter` profile has **706** passages — **14.2× coarser** than
the gate — and `register_axis_status` returned `measured` with `reason: null`
while running the collapsed rule in production.

`deai_register.resolves_rare_rate` now decides this. A bank that cannot express
the gate reports `degraded` naming the coarseness and the rule actually in
force, and its findings carry `measurement_status: degraded` with
`reference.resolves_rare_rate: false`. They are **not** silenced: a term in
zero corpus passages is absent whatever the resolution, and converting a
degraded measurement into zero findings is the one thing this repository must
not do. The two guards keep distinct jobs — below 500 passages the axis emits
nothing; between 500 and 10,000 it emits, degraded. `wgl` is unaffected
(41,593 passages resolve to 2.4e-5, comfortably under the gate).

Also: `docs/README.md` recorded the narrative/salience/register part as holding
sections 11 and 13–15, which stopped being true when §17 landed.

308 tests across 17 files; validator 9/9.

## v0.30.0 — 2026-08-27

The last open roadmap item is closed, and closing it produced a worse result
than leaving it open would have shown. Half of it never needed a labeller: a
refereed ApJ/ApJL/A&A paper is text a human wrote and a referee accepted, so
its provenance is already a label for "does this axis fire on accepted prose".

### `tools/eval_findings.py` — provenance labels instead of hand labels

200 held-out refereed papers were fetched and verified disjoint from all three
calibration banks — **0** overlap with `human_abstracts_extra.jsonl`, **0** with
the 516 `exemplar_paragraphs.jsonl` sources, **0** with `fulltext-arxiv/`. A
random sample of 8, re-queried against the arXiv API, returned 8 refereed
`journal_ref`s published 2013–2017, all pre-LLM.

Enforcing held-out status was not a formality. `RARE_DF_RATE` is 1e-4, so on
41,593 passages the foreign-term threshold sits at **4.16 passages** — one
paper's own paragraphs can carry its own vocabulary over the line.

### `L0.register` fires on accepted prose

On papers it never saw: **0.991 findings per 1,000 words**, 93.6% of documents,
rank AUC **0.080** against machine text — it fires *more* on human papers than
on AI drafts, because generated prose reuses common field vocabulary while real
papers introduce genuinely rare terms. Recorded, not retuned: a replacement
operating point has to be derived against a held-out target rate and validated
the same way. This is now the one open roadmap item, and unlike the vague item
it replaces it has a number attached.

### `L2.salience_hierarchy` calibration transfers essentially exactly

`ADVISORY_PERCENTILE` is 0.90 over three features, so an independent-gate
expectation is 1 − 0.9³ = **0.2710** per passage. Measured on the held-out set:
2,690 findings over 9,946 eligible passages = **0.2705**. Its 0.966 document
flag rate carries no defect signal — at 0.27 per passage a paper with ~49
eligible passages flags with probability ~1 by construction. Machine text
separates at AUC **0.770**.

### The obvious leakage estimate is confounded; the paired one is not

Comparing held-out against in-sample papers looked like the leakage
measurement, and is not: the two populations are era-disjoint (2020–2021 vs
2012–2018), so the contrast charges six years of vocabulary drift to
calibration leakage. Replaced by a paired test on one population where bank
membership is the only difference — **72.7% of 2,287** held-out register flags
would be suppressed by the paper's own membership, so the in-sample view of
this axis was ~3.7× optimistic.

### Fetcher and hygiene

- `--fulltext-dir`, `--exclude-known` and `--start-at` on
  `fetch_arxiv_abstracts.py`. A first sweep returned **zero** candidates —
  5,618 results, all already calibrated — because results come back
  newest-first and an existing corpus occupies a contiguous shallow band. On
  `cat:astro-ph.CO AND abs:cluster`, offsets 0–2000 were 100% known and 2000+
  were ~85% new.
- An interlock refuses to write a held-out set into the directory
  `extract_style.py` reads as calibration breadth, and a test pins that the
  held-out directory is not a calibration source — the failure it prevents is
  silent, since the next rebuild would absorb the evaluation set with no error.
- Journal-key validation now runs in full-text mode too; `--fulltext --journals
  apjjl` previously kept nothing instead of failing.
- `.gitignore` covers `style-corpus/**/fulltext-*/` as a class rather than one
  directory name, so a new evaluation set cannot start life as a tracked copy
  of other people's papers.
- `cli_common.emit_report` shares the `--format` / `--output` tail between the
  two evidence tools.
- The changelog archives were rebalanced under the 750-line budget: v0.27.0
  moved to `CHANGELOG-ARCHIVE.md`, v0.21.0 and older to
  `CHANGELOG-ARCHIVE-EARLY.md`.

303 tests across 17 files; validator 9/9.

## v0.29.0 — 2026-08-26

Three roadmap items were closed by building the thing and measuring it, one
published number was found wrong and corrected, and the evidence behind
EVALUATION §9 became a tool instead of a memory.

### The roadmap emptied by refutation

- **The length-aware manifold is built, measured, and refuted.** Each manifold
  coordinate is a log-ratio of a sample standard deviation over *n* paragraphs,
  and `Var(log s) ≈ 1/(2(n-1))` for that statistic — so the roadmap entry had an
  exact form: subtract the fit set's mean noise from the covariance diagonal,
  add each scored document's own back. Over **12 paired seeds** the human
  out-of-fit rate is unchanged (0.030 → 0.030) and two AI tiers move the wrong
  way (`ai` 0.792 → 0.754, natural 0.170 → 0.140). The correction is
  length-*symmetric*, and the AI documents at issue are short exactly like the
  human papers they are compared against, so it cannot separate them.
- **Enlarging the conformal calibration set is refuted.** At n_cal = 78 the
  smallest achievable p is 1/79 = 0.0127, so α = 0.05 flags only a document
  beating all but two calibration points. Moving documents from training to
  calibration (0.6 → 0.3) leaves tail power flat and raises the human
  false-flag rate monotonically 0.030 → 0.038. The shipped split is at the
  better end of that trade.
- **Long-form detection holds at 0.000** across 2 metrics × 4 splits × 12 seeds.
  Rank AUC is 0.729, so the signal is present and the operating point cannot
  reach it. No longer a single-configuration result.

Only one roadmap item remains, and it is blocked on an input rather than on
effort: a human-labelled validation set for salience and register.

### The §9 point estimates are seed draws

Averaged over 12 seeds, manifold tail power is **0.170 ± 0.110** (natural),
0.261 ± 0.114 (de-AI'd), 0.237 ± 0.184 (adversarial), 0.274 ± 0.043 (skeleton).
Several differences the record read as improvements — including v0.28.0's
`0.214 → 0.250` from the bundle-ordering fix — are smaller than that spread.
The ordering fix stands on the grounds that reading a paper in its own order is
correct, and on the human-side rate it lowered; not on those deltas. §9 now
carries the spread, and **`tools/eval_docscale.py`** reproduces the whole table
from the shipped operating point so no figure has to be quoted from memory.

### Section coverage: a wrong number, then a real fix

**Correction.** v0.28.1 published the coverage gap as "1,804 of 5,074 headings
(35.6%)". Those counts were wrong — the probe used a re-typed regex including
`\subsubsection`, which `RE_SECTION` does not split on, swept files
`select_document_roots` rejects, and ran under a `timeout` that may have cut it
short. The correct pre-fix figures are **3,026 of 9,222 (32.8%)** in `wgl` and
52 of 148 (35.1%) in `wgl-letter`. The rate was about right; the counts were not.

Then the unambiguous part was closed, taking `wgl` to **2,334 of 9,178 (25.4%)**:

- `RE_SECTION` captured `[^}]+` and stopped at the first inner brace, so
  `\section{Results\label{sec:res}}` classified `Results\label{sec:res` and
  `\section{\hspace*{+0.0mm}Foo}` classified a spacing command. The title group
  now spans one level of nesting and `clean_heading` strips what survives.
- A `\section{}` whose title is empty once markup is stripped no longer resets
  the enclosing bucket — 12 such headings were turning every following
  subsection `unknown`.
- "Affiliations" is front matter (`skip`); "Covariance matrix", "Likelihood",
  "Blinding", "Cosmological constraints", "Validation" and "Forecasts" name
  section roles the vocabulary did not carry.
- **"Measurements" and "Background" were refused.** In weak lensing "Shear
  measurement" is method while "Mass measurements" is results, and "Background"
  spans intro, method and data. Guessing either is how `method` became the
  residue. The remaining ~25% is mostly topic headings and is a floor, not a
  backlog.

Every profile asset was rebuilt on both fields: the exemplar bank goes
25,005 → **27,951** paragraphs, `results` 3,118 → **3,964**, register 38,647 →
**41,593** passages, and the UID baseline re-reads at 3.321 ± 0.439 pooled with
the section-identity null intact (3.23–3.38 across seven buckets).

### Two files split, and the guard that was missing

`train_voice_model.py` (1,174 lines against a 750-line budget) split into
`voice_dataset.py` (record loading, grouping, the fingerprinted feature cache)
and `voice_audit.py` (held-out metrics, hard set, confound audits), with a
one-way dependency a test asserts. `CHANGELOG-ARCHIVE.md` (1,125) split at its
v0.19.0 seam into `CHANGELOG-ARCHIVE-EARLY.md`; the history is byte-identical
across the split.

The first split shipped four unbound names — `time`, `CHECKPOINT_EVERY`, `df`,
and the two HARDSET category sets — and **the suite stayed green**, because no
test reached `build_features`. A real retrain found it. `test_train_voice_model`
now walks the AST of every file in `tools/` for names that are neither defined
nor imported, so the next split cannot fail that way.

### The last L3 question, answered by a third replication

The roadmap carried "a field-topic-robust L3 operating point, **or a recorded
decision that one is not obtainable from this feature set**". Retraining on the
rebuilt 44,576-record bank is the third independent answer, and the three agree:

| negative control | 44,576 | 41,641 | 17,299 |
|---|---:|---:|---:|
| public-generic generated | **0.052** | 0.053 | 0.086 |
| field-topic generated | **0.280** | 0.285 | 0.318 |
| field-jargon-dense generated | **0.393** | 0.410 | 0.417 |

Every movement across a 2.6× bank increase sits inside a single retrain's own
20-split range (field-topic 0.208–0.344), while headline AUC moves the *other*
way, 0.9320 → 0.9518. More data buys the easy contrast and nothing on the one
that matters — a feature-set confound, not a sampling limit. **Decision recorded:
not obtainable from this feature set.** Reopening it needs different features.

That leaves exactly one open item, and it is blocked on labels rather than on
work: human-labelled validation for salience and register.

### Added

- **`tools/eval_docscale.py`** — reproduces the §9 table (human false-flag rate,
  per-tier tail power, rank AUC) through `manifold_operating_point`.
- **`tools/label_findings.py`** — the labelling harness for that last item, built
  to the scheme chosen on 2026-08-26: finding-level labels, one labeller plus a
  blind re-label subset for intra-rater agreement, drafts and published papers
  sampled and reported separately. It calibrates nothing. A stratum under 20
  labels reports `unmeasured` rather than a rate — the instrument that judges
  these axes must not be where 2-of-3 becomes "precision 0.667" — and the
  intra-rater kappa prints as the ceiling no axis can be held above.
- **`tests/_toolpath.py`** — the test suite's own duplicated preamble, collapsed
  the same way the CLI one was; 13 of 16 test files retrofitted, the other three
  refused because they invoke tools as subprocesses and never touch `sys.path`.
- **`tools/cli_common.py`** — the shared CLI preamble and field resolution. The
  argparse opener was duplicated across the suite and `list_fields` /
  `resolve_field` existed in five byte-equivalent copies; the duplicate-content
  guard refused a 27th. **21 of 30 tools retrofitted**, with the allowlist and
  the refusals recorded rather than left implicit: nine are library modules with
  no CLI or are the module itself, `ai_ism_lint` keeps its own resolver because
  it warns and returns `None` so the L0 pass still runs with no profile, and
  `extract_style` resolves against the corpus root — expressed as
  `exclude_prefixes=("tier-",)` rather than as a second implementation.

  The sweep was attempted twice with a regex and reverted both times. The first
  pass inserted the replacement before deleting the original, so the deletion
  consumed the replacement; the second ate four constants and a function out of
  `extract_style.py`, because a `\n\n[A-Z_]` lookahead skips every intervening
  `def` to reach the next module constant. The AST knows where a function ends.
  Both reverts were caught by the suite — the second by the unbound-name guard
  added in this same release.

## v0.28.1 — 2026-08-26

v0.28.0 fixed the corpus layer but only rebuilt the assets on the `wgl` path it
was measuring. Two derived assets were left holding the pre-fix view of the
corpus, and the audit that found them also measured how much corpus the fixed
layer still discards.

### The rebuild v0.28.0 did not finish

- **`wgl-letter` was still entirely pre-fix.** Every asset in that field dated
  from 2026-08-16 and was built by the defective code path, so `--field
  wgl-letter` served baselines nobody had re-derived. Rebuilt through
  `extract_style` plus the `deai_register` / `deai_salience` / `deai_structure`
  calibrations. The old profile read 775 `method` passages against a single
  `results` passage; it now reads `method` 232, `data` 125, `intro` 85,
  `results` 84, `discussion` 83, `conclusion` 22, `abstract` 10. The bank shrank
  from 955 passages to 641 because unattributable prose is now dropped instead of
  absorbed into `method` — the correct direction, and the reason the old numbers
  should not be compared to the new ones.
- **`ai_ism_classifier.joblib` was fit on the 593-paragraph bank.**
  `build_profile.py` runs extraction and classifier training as one chain; the
  v0.28.0 work invoked `extract_style.py` directly, so step 2 never re-ran and
  the legacy L3 advisory kept a model that disagreed with its own corpus.
  Retrained on both fields.

### Section coverage is now measured, not assumed

Sweeping every heading in both corpora through `classify_section`, **35.6% in
`wgl` (1,804 of 5,074)** and **35.8% in `wgl-letter` (63 of 176)** resolve to
`unknown` and reach no baseline. Two independent corpora agreeing to within 0.2
points points at the bucket vocabulary, not at either corpus: review-article
headings such as "Magnification bias" name no standard section. Recorded as a
limitation in both READMEs and
[`lexical-structure-uid.md`](docs/architecture/evaluation/lexical-structure-uid.md)
§5, with the explicit constraint that widening the rules must not reintroduce
the pre-v0.28.0 absorption into `method`.

### Fixed

- `train_ai_ism_classifier` printed `5-fold CV accuracy: 1.000 ± 0.000` at a
  1250:1 class ratio, where always-predict-corpus already scores 0.999. The
  ratio and that baseline now print beside it, so the headline number cannot be
  read as skill; minority-class F1 (0.796 on `wgl`, 0.905 on `wgl-letter`) is
  the signal.
- The README roadmap quoted **−0.418** for the short-stratum length correlation,
  the value superseded by the assembly-order fix. Both READMEs now read
  **−0.414**, matching
  [`document-scale.md`](docs/architecture/evaluation/document-scale.md) §9.4b.
- **Five in-page anchors pointed at headings that no longer existed.**
  `validate_plugin.py` checked relative *file* links but never `#fragments`, so
  the v0.28.0 README restructure left the Chinese README's navigation pointing
  at `#tools25-个` after the count became 26, and four demo cross-references
  pointing one demo off — "demo 3" linked to demo 4. All five fixed, and the
  validator now resolves every in-page anchor across 14 pages against the
  headings actually present, CJK included. Verified by negative control: an
  anchor broken on purpose fails the check.

## v0.28.0 — 2026-08-25

The corpus layer treated a *file* as a paper and could only see the three
curated tiers. Fixing that took the reference banks from 593 paragraphs to
25,005, cleared the `results` limitation carried since v0.27.0, and let two
roadmap items be settled by measurement rather than left open.

### The corpus layer: four defects, one shape

Each was measured before it was fixed, and the profile rebuilt against all four.

- **Every `.tex` counted as its own paper.** Bartelmann & Schneider (2001) ships
  `WeakLens.tex` plus `WeakLens_1..10` and `WeakLens_D`, so that one review
  entered every downstream distribution twelve times at tier-1 weight — the
  pseudoreplication this project refuses everywhere else. `tier-1-top` held 20
  `.tex` files and 8 papers. `select_document_roots` now drops `\include` /
  `\input` fragments and unmarked siblings (`bib.tex`), while keeping plain-TeX
  papers that predate LaTeX2e and carry no document marker at all.
- **Selecting the root is only half the fix.** `WeakLens.tex` is 72 words; its
  ~40,000-word body is in the eleven chapters it includes. `read_tex_document`
  splices them, once — 64,657 words — skipping commented-out `% \includeonly`
  builds and breaking cycles.
- **The selector and the reader disagreed on `\input` targets.** arXiv flattens
  submissions, so `\input{sections/intro}` names a sibling; the selector matched
  by stem and dropped it as a fragment while the reader resolved by literal path
  and never spliced it back. Four bundles lost most of their prose, one keeping
  2 of 9,743 words.
- **A `\subsection` did not inherit its `\section`.** "Covariance matrix",
  "Likelihood" and "Blinding" are method prose; classified alone they are
  `unknown` and discarded — **54.8% of all section words** in the 561-document
  corpus. The PDF path got this fix earlier the same day; the LaTeX path had
  not. An inherited `skip` now also stays skipped, so appendix subsections no
  longer escape into the distributions.

### The breadth corpus was on disk and invisible

500 arXiv full-text papers — fetched for §9, gitignored, present since v0.26 —
were unreachable by every paragraph-level baseline, because the curated tiers
and the reference distributions shared one file list. They are now distinct
roles: `REFERENCE_DIR` is gathered, **unweighted**, and excluded from every
aggregate, so breadth cannot restyle the dossier's imitation target.
`retrieve_exemplars` reads the curated tiers by default (`--include-reference`
widens) and learns about the `data` bucket, which reached the bank on
2026-08-25 but never reached `VALID_SECTIONS`.

| bucket | v0.27.1 | v0.28.0 |
|---|---:|---:|
| method | 163 | 8,144 |
| data | 112 | 3,929 |
| intro | 109 | 3,753 |
| **results** | **26** | **3,118** |
| discussion | 118 | 3,088 |
| conclusion | 48 | 2,533 |
| abstract | 15 | 433 |
| **total** | **593** | **25,005** |

**Every bucket now clears the 30-passage floor**, `results` by 104×, so no
bucket is rank-only. Register goes 14,235 → 38,647 passages and 41,154 → 54,233
terms, with abstracts falling from 96% of the reference to 35%. The `results`
limitation and the "corpus growth for thin buckets" roadmap item are closed —
and the diagnosis they rested on was wrong: the constraint was never corpus
availability.

### Two roadmap items settled by measurement

- **`deai_policy.json` is withdrawn, not deferred** (EVALUATION §16). It would
  have moved `L1.distribution` and `L2.sentence_structure` off `degraded`.
  Measured on 500 human papers against 173 `docval` AI documents, one
  observation per document: burstiness **reverses sign** — adversarial prose is
  more bursty than the human median (1.036 vs 0.775, AUC 0.181) and long-form
  sits inside the human band (AUC 0.441) — while flagging 7.2% of humans; and
  signposting has AUC **0.247**, below chance, flagging **0 of 173** AI
  documents at the shipped default. That is the pattern the standard already
  used to reject the inference-connective rate. Both axes stay `degraded` for a
  measured reason rather than a missing asset.
- **The length-aware manifold has its mechanism measured** (§9.4b) and both
  cheap routes refuted. Inside the short stratum, human manifold distance still
  correlates **−0.414** with paragraph count, unchanged by the assembly-order
  fix above — an estimator-noise effect, not a corpus defect. Normalizing the
  distance stays
  rejected (guardrail 9). Finer Mondrian stratification, tested at 3/4/5/6
  strata, reduces the residual to about −0.27 and buys **no power at all** — the
  conformal test simply becomes more conservative, and skeleton power drops
  0.208 → 0.125. What remains is an explicit estimator-noise model, not shipped.

### Fidelity gate: a hyphen between numerals is a range

Third occurrence of one root cause in `rewrite_reward`'s tokenizer, after the
Oxford comma and the spaced unit: a separator absorbed into the token. `[-+]?`
accepted a sign directly after a digit, so `0.5-1.2 arcsec` tokenized as
`{0.5, -1.2}` and a faithful rewrite saying "from 0.5 to 1.2" was reported as
MISSING `-1.2` while INVENTING `1.2`, then hard-rejected at `-inf`. Every
hyphenated range did this, which is most of them. Measured on the README's own
demo: 12 phantom missing numbers across three candidates, all three rejected;
after the fix the two faithful candidates pass and the one that genuinely drops
seven numbers is the only rejection.

### Re-measured, not carried forward

- **§9 document scale reproduces, then improves.** Every tier re-scored through
  the shipped path with the length-fair protocol restored: all eight published
  AUCs within **0.012** (manifold 0.933 / 0.943 / 0.927 / 0.914; role 0.690 /
  0.742 / 0.810 / 0.507). The 42× *paragraph-bank* growth did not move
  document-scale discrimination, which is expected — §9 always calibrated
  against `fulltext-arxiv`. What did move it is below. A fifth tier is
  recorded: long-form AI, manifold AUC 0.740 with **0.000** tail power.
- **The keystone axis was reading its own corpus out of order.**
  `_paper_documents` assembled each bundle by sorted FILENAME, so
  `Conclusion.tex` preceded `Introduction.tex` — and this axis measures section
  arc and paragraph sequence. 122 of the 500 bundles hold more than one `.tex`,
  12 provably out of order, and all 122 also folded appendices,
  acknowledgements, author lists and the journal's own class documentation in
  as body prose. Rebuilt in include order, manifold tail power rises on natural
  AI **0.214 → 0.250** and on adversarial **0.158 → 0.184** while the human
  false-flag rate *falls* 0.0346 → 0.0325. The role axis trades the other way
  (natural 0.107 → 0.036), so the union is 0.286 / 0.600 / 0.447 / 0.333.
  Fixing this required splitting `deai_docstructure.py` (1,092 lines against a
  750-line budget) into a measurement layer, `deai_docshape.py`, which it
  re-exports in full under a contract test.
- **L3 retrained** on 41,641 records (2.6× the previous bank): grouped-split AUC
  0.9320 → **0.9502**, balanced accuracy 0.8509 → **0.8736**, matched-stratum
  0.9236 → **0.9303**. The confound did not move — field-jargon-dense false
  positives 0.417 → 0.410, inside the split range — so two retrains on very
  differently sized banks now agree it belongs to the feature set, and L3 stays
  `degraded`.
- **Retraining is not behaviour-preserving, and is not claimed to be** (§7.0).
  Checked at the production unit: 1,845 paragraphs scored by both bundles, same
  feature pipeline. Rank correlation holds at Spearman **ρ = 0.846**; the three
  paragraphs surfaced for review overlap **0.654**; 11 of 54 documents get an
  identical set. Same schema, same features, same `degraded` posture, no
  invented threshold — but an old triage list will not reproduce exactly.
- **UID** now spans 25,005 paragraphs, pooled global UID 3.322 ± 0.446. Section
  means span only 3.23–3.38 against within-bucket σ of 0.26–0.57, recorded as a
  null: a per-section UID operating point would calibrate on less than its own
  noise.
- **Latency** re-measured on a real 5,084-word corpus paper: all model-free axes
  390 ms, `--oracle` 23.1 s, `--voice` 26.6 s, validator 359 ms, suite 43.1 s.

### Three files split, because they could no longer be edited

The repository enforces a 750-line budget per file. Three files had passed it,
and the hook refuses *any* write to an over-budget file — including a one-line
factual correction. Each split follows an existing seam rather than inventing
one, and each is verified by a re-export or incorporation contract.

- **`deai_docstructure.py`** (1,092 → 443) splits at measurement versus
  feedback. `deai_docshape.py` (708) holds the per-paragraph feature vector,
  cross-paragraph dispersion, the joint manifold, role coupling, the conformal
  operating points and the baseline builder; `deai_docstructure` turns them
  into findings and a CLI, and re-exports every public name under a contract
  test modelled on the one `extract_style` already has.
- **`SCIPAPER_STANDARD.md`** (823 → 736) at contract versus register. §§7-8
  become [`architecture/RESPONSIBILITIES.md`](docs/architecture/RESPONSIBILITIES.md),
  **incorporated by reference and still normative** with no independent
  authority; §11 becomes
  [`architecture/DISPOSITIONS.md`](docs/architecture/DISPOSITIONS.md), a record
  of decisions rather than policy; and a 49-line embedded version history moves
  to this changelog, where it belonged. §§0-10 of the contract are unchanged.
  The standard is now v3.7.
- **`CHANGELOG.md`** (1,463 → 484) at v0.26.2, with the remainder verbatim in
  [`CHANGELOG-ARCHIVE.md`](CHANGELOG-ARCHIVE.md).

### Documentation

Both READMEs restructured around a **three-way comparison** — as-generated
versus a word-list humanizer versus this pipeline, on one paragraph — which is
the demo that shows the difference: the humanizer clears the L0 target and the
corpus-zero advisory while the `ing-tail` advisory simply follows the
substitution, and across 20 documents it moves strong advisories by exactly
zero. A full-review section documents the A–R dimensions and the merge rule.
EVALUATION gains §16 and §9.4b, and both tool tables collapse from eight
subsections into one table with a `layer` column.

33 new tests (222 → 255); 25 → 26 tools. No consequence class, exit code,
schema, ranking rule, or normative policy changed.

## v0.27.1 — 2026-08-17

v0.27.0 fixed the section classifier and measured what it would change. This
release carries out the rebuild that fix required and writes the resulting
numbers back into the evaluation record. No code, consequence class, exit code,
or normative policy changed; every edit here is a measurement or a document.

### The rebuild, and what it moved

The full `wgl` profile was rebuilt with the fixed classifier — extraction, then
each `--calibrate` stage, then a complete `train_voice_model.py` retrain
(18,647 rows, 20/20 audit splits completed). `wgl-letter` was rebuilt alongside
it. Every figure below is read from the rebuilt artifact, not from the v0.27.0
projection.

- **Reference banks.** `structure_baseline` and `uid_baseline` now hold 1,942
  paragraph observations across six buckets rather than 1,957 across five;
  `results` gains a surprisal reference for the first time. Salience buckets
  move `method` 1,377 → 1,303, `discussion` 35 → 78, `conclusion` 26 → 41, and
  gain `results` at n=10. `conclusion` crosses the 30-passage floor, so it is
  `measured` rather than rank-only for the first time. The register reference
  goes 15,599 → 15,584 passages and 41,933 → 41,714 terms.
- **The learned model barely moved, and that is the result.** Comparing the new
  audit against the pre-rebuild record key by key, every headline figure changed
  by at most 0.002 in AUC (primary split 0.9414 → 0.9399; 20-split mean 0.9324 →
  0.9320) and the negative-control false-positive rates by at most 0.005. L3
  stays `degraded` with no operating point, for the same measured reasons.
- **What did move is the per-section audit strata, which were degenerate.** The
  `discussion` stratum held a median of 5 positive rows and some splits held
  none, so its minimum F1 and recall were both 0.000; post-rebuild the median is
  19 and those minima are 0.857 and 0.850. The `conclusion` stratum's smallest
  split rose from 3 rows to 9. Before the fix that breakdown was not measuring
  section behaviour — it was measuring an empty cell.
- **§15 was checked and left alone.** Its figures come from the abstract and
  generated banks, which are not section-bucketed; the rebuilt abstract
  percentile grids are byte-identical to the pre-rebuild ones. The v0.27.0
  notice that named §15 as affected was over-broad and is corrected.

### A stale artifact the rebuild exposed

The local `voice_model_evaluation.json` predated the hard-set restructure: it
carried only the retired `auc_low_score_predicts_strong_ai_feel` key, while
`EVALUATION.md` §7.3 already documented `primary_provenance` and
`perception_baseline`. The document was ahead of the artifact on disk, which no
gate checked because nothing compared documented figures against the file they
describe. The retrain regenerates the record in the current schema, and §7.3's
0.937 / 0.444 now reproduce from it.

### Resolved limitation

`EVALUATION.md` §7.5 recorded that the cloud bundle was built with scikit-learn
1.4.2 and emitted an unpickle-version warning under a newer local install, and
predicted a local rebuild would clear it. Verified: the retrained bundle loads
under local scikit-learn 1.8.0 with no warnings. The limitation is removed
rather than restated.

### Corrections

- `style-profile/README.md` quoted the pre-ligature-fix projection (`method`
  1672, `conclusion` 51, total 1944) where `CHANGELOG.md` and `EVALUATION.md`
  carried the re-measured 1671 / 50 / 1942. It was missed in the v0.27.0
  re-measurement sweep and now agrees with the artifact it describes.
- Profile snapshots taken before a rebuild now live in the gitignored
  `.backups/` inside the repository. A snapshot placed beside the repository
  reads as a project of its own in the parent directory and escapes the ignore
  rules that cover the same corpus-derived files.
