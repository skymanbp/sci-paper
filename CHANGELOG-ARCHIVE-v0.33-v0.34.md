# Changelog archive — v0.33.0 through v0.34.0

Entries moved out of [CHANGELOG.md](CHANGELOG.md) on 2026-09-04 (v0.36.3) when
the live changelog passed the repository's 750-line budget and every older
archive was within 65 lines of it. Nothing here is edited; the history is
verbatim.

- Current releases: [CHANGELOG.md](CHANGELOG.md)
- **v0.27.1 through v0.32.0**: [CHANGELOG-ARCHIVE-RECENT.md](CHANGELOG-ARCHIVE-RECENT.md)
- **v0.22.0 through v0.27.0**: [CHANGELOG-ARCHIVE.md](CHANGELOG-ARCHIVE.md)
- **v0.21.0 and earlier**: [CHANGELOG-ARCHIVE-EARLY.md](CHANGELOG-ARCHIVE-EARLY.md)

---

## v0.34.0 — 2026-08-27

The review skills separate into measurement primitives and the composites that
call them, the plugin stops depending on a skill it does not ship, a recorded
count is now checked wherever it is written rather than only where someone
thought to look, the labelling harness gains the two axes it was missing, and
building a population to point it at turned up two silent corpus bugs.

### The one skill the plugin orchestrated but did not ship

`final-review` launched `modern-physics-review` as a worktree agent and
`paper-review` re-read it after its own disposition-complete state, but the file
lived in the user's global skill directory. On any other machine both skills
reached for something that was not there. Its content is now in the repository —
as `skills/physics/SKILL.md` and a paper-review mode, for the reasons in the next
section — and no skill references anything the plugin does not ship.

Its content could not be taken verbatim: that would have put a second consequence
vocabulary in the repository. The grading was 🔴/🟡/🟢 and the termination
condition read "0 个 🔴 / 0 个 🟡 … 必须收敛到 0 才算完" — a universal
zero-advisory gate, which is the thing `validate_plugin.py`'s
`STALE_REVIEW_MARKERS` exists to refuse. That table matches English strings
(`zero-issue convergence`, `0 issue across all`), so a Chinese spelling of the
same rule walked straight past it. Grading maps onto `sci-paper.feedback.v1`
instead — 🔴 to `integrity_blocker`, 🟡 to a strong advisory that must carry a
disposition, 🟢 to an ordinary advisory — and termination is a stable
disposition-complete state, not an empty report. The physics itself is unchanged.

**M9 was deleted rather than translated.** It ran a hard-coded keyword grep, and
its em-dash pattern was byte-identical to the one at `tools/ai_ism_lint.py:30`,
which already files those hits as `kind="l0_target"`. Its boilerplate word list
asks the question `tools/deai_register.py` answers from the field's own document
frequency, and `skills/paper-review/SKILL.md` already carried an override saying
corpus evidence beats an upstream word list. Keeping M9 would have given one
question two contradicting answers. `physics` delegates to those axes instead.

`calibrate` joins `NORMATIVE_SKILLS` along with the new primitives:
`docs/architecture/RESPONSIBILITIES.md` claimed every skill but `brainstorm` was
enforced there, and `calibrate` was not — it referenced the standard anyway, so
the claim was true in fact and unenforced in code.

### A count was only checked where someone thought to look

`check_registry_counts` opened `README.md` and matched `## Skills (N)`. The
repository's shape numbers are written in four other places — the headline line,
the ASCII tree, the release paragraph and the latency table — and in two
languages. Nothing read the translation at all, so `README.zh-CN.md` advertised
**9 skills, 25 product tools, 15 test files and 252 tests** to a repository of
12, 34, 19 and 381. The English latency table carried a stale figure of its own,
`360 passing` against a 381-test suite, written in a spelling
`check_recorded_test_counts` had no pattern for, inside a file it never opened.

A fifth regex would have been the fourth patch for one defect. `SHAPE_CLAIMS`
instead lists every spelling either README uses, each paired with the quantity it
claims, and both files are scanned — a shape number is checked wherever it is
written, in whichever language. `check_recorded_test_counts` reads the two
READMEs alongside the evidence record for the same reason. The check tuple moved
to module level as `CHECKS`, so the published "9 contract checks" is verified
against the tuple that actually runs instead of against a hand count. Twelve
claims across both READMEs are verified per run, and the number of checks is
still nine — which is what keeps that particular claim true.

Both stale sets are corrected. Each fix was confirmed the same way: the old value
was left in place first, to watch the validator name the file and the quantity.

### The latency table, re-taken whole

The interpreter floor moved 84 → 98 ms, so under the table's own rule no v0.33.0
row compares and every row was re-measured together on the same 5,084-word
assembled paper: L0 274 → 317 ms, all model-free axes 409 → 458 ms, the length
gate 194 → 258 ms, the validator 2.3 → 2.9 s, the suite 51.0 → 60.1 s — the last
one now covering 381 tests where the published figure covered 360, which is the
other half of why a partial update was refused.

The two model-backed rows went the other way: `--oracle` 48.7 → 33.8 s and
`--voice` 59.1 → 37.2 s, against every standard-library row rising with the
floor. The table cannot explain that and does not try. Their cost relative to a
full model-free pass falls from 120×–145× to 74×–81×, and the stamp's existing
instruction stands — read those two rows as one machine on one day, not a trend.

### The physics checklist existed three times

`paper-review` dimension K listed eight modern-physics checks; `modern-physics-review`
listed the same eight as M1-M8; and `paper-review` also launched that skill as an
isolated agent after reaching its own disposition-complete state. Dimension B carried a
fourth partial copy — conservation, symmetry, parity and asymptotics again. Dimensions
E, C and G had the same shape against the narrative-spine protocol, claim-evidence
discipline and figure inspection.

The rule that was missing is now written down beside the dimension list: **a dimension
either calls a measurement primitive or owns its content — never restates one.** Three
primitives were extracted to give the calls somewhere to land:

- `skills/physics/SKILL.md` — P1-P8, the single copy of the first-principles checklist.
- `skills/mainline/SKILL.md` — the purpose record, contribution graph and cold reader's
  seven questions, out of dimension E.
- `skills/logic/SKILL.md` — claim graph, empirical statistics and the review side of
  claim-evidence discipline, out of dimension C.

Each is measurement-only: it emits findings and never edits. Repair stays with the action
primitives, `/sci-paper:de-ai` Pass 3 and `/sci-paper:condense`, which is what dimension I
already did and what the other dimensions now do too.

`modern-physics-review` therefore never becomes a skill of its own. Its checklist is
`physics`; its fix loop and report were already paper-review §4 and §6; and the part worth
keeping — an isolated agent that cannot inherit this review's "already verified" conclusions
— is now a mode of paper-review rather than a second skill. `--no-isolated-mpr` named one
skill, and three are orchestrator-owned now, so the flag is `--orchestrated`;
`--skip-final-mpr` is `--skip-final-physics`.

`final-review` launches the three primitives at parent level instead of the single MPR
agent. That is not extra process: it is what makes their cold read independent of
paper-review's context instead of nested inside it.

**What did not change:** `paper-review` dimension D still runs `/sci-paper:de-ai
--audit-only` every round, and that is correct under this model — a composite calling a
primitive's measurement half is composition, not nesting. The defect was never the call.

### One skill table instead of two, neither of which was complete

`README.md` listed the skills twice — as "the eight functions" and again under
`## Skills` — and both lists predated `calibrate`, so the setup step every
`measured` axis depends on appeared in neither. They are now one table of ten
ordered by stage (setup, write, revise, review, explore), with the existing
per-skill descriptions carried over unchanged; the `## Skills` section points at
it. The same consolidation is in `README.zh-CN.md`.

### The labelling harness covers every axis that emits findings

`tools/label_findings.py` sampled two axes while four emit findings. It now
samples all four — `L0.register`, `L2.salience_hierarchy`, `L2.cohesion`,
`L2.hedging`. The discourse entry forced the emitter table's shape:
`discourse_findings` returns both of its axes from one call, because they are
measured over different spans, so an emitter now declares the axes it owns plus
how to tell which one a finding belongs to. `deai_discourse.axis_name()` gives
the `L2.<feature>` spelling one owner, so the sheet cannot file findings under a
name no report prints.

**Recall is now reported pooled over the axes, and only pooled.** A control row
asks whether a passage should have been flagged; a labeller who answers yes has
not said by *which* axis. Dividing every axis by the same miss count — what this
did while it carried two — charges each axis with every other axis's misses, and
does so four times over at four axes.

Populations are named rather than fixed: `--population NAME=DIR`, repeatable,
each sampled and scored separately. `--drafts DIR` remains as shorthand for
`--population draft=DIR`. Whichever population is named must sit outside the
calibration banks, and the size of that effect is now measured on this corpus:
the register axis yields **1** finding across three in-calibration papers and
**8** across fifteen of the same author's papers held out.

### Two silent bugs in the arXiv corpus builder

**All ten `AUTHOR_QUERIES` were dead.** `Surname_Initial` is the arXiv *listing*
URL's format (`/a/hoekstra_h_1`), not the search API's `au:` syntax, so every one
returned exactly 0 records — the `broad` query set was silently ten queries short
while its comment claimed those records broadened the curated-field class. A dead
query leaves no trace in the output, so `AuthorQueryFormTest` now guards the form.
Re-run with the quoted form, the ten contributed 18, 37, 6, 24, 31, 21, 4, 2, 18
and 1 new records: **13,642 → 13,804**.

**And a surname is not a person, which took two goes to get right.** The
corrected queries are scoped to `cat:astro-ph*` because unscoped,
`au:"Dell'Antonio"` returns 86 records of which 20 are a mathematical
physicist's math-ph/quant-ph work. That scoping is not enough on its own, and the
first corrected sweep proved it: `au:"Schneider, P" AND cat:astro-ph.CO` added
**274** records, mostly Donald P. Schneider's SDSS quasar surveys (58 papers on
one page against the intended Peter Schneider's 33) — a second helping of the
same bug, in the same commit that fixed the first. That sweep was rolled back
from the pre-sweep snapshot, all ten queries were checked against the names they
actually return, and the entry now reads `au:"Schneider, Peter" AND
cat:astro-ph*` (80 papers, all Peter Schneider). Nine of the ten resolve to one
person on an initial alone. The check needs the network and cannot be a test.

**Old-style arXiv ids lost their archive prefix and 404'd.** The Atom id
`http://arxiv.org/abs/astro-ph/9403003v1` was parsed with `rsplit("/", 1)`,
yielding `9403003v1`, which the e-print endpoint does not serve. Measured on a
live 1990–2021 author sweep: 7 of 19 candidates lost, reported as `failed=7` and
otherwise invisible. Everything downstream was always built for the slash —
`_bare` folds it to an underscore, `RE_ARXIV_ID` matches that form in tier
filenames, the paper directory name replaces it — only the parser never produced
one. After the fix the same sweep failed 0.

### Per-author full-text populations

`--fulltext --author "Surname" --author-is <regex> --max-authors N` builds a
population from one author's papers. The search term and the identity test are
deliberately separate flags: conflating them is what produced `Dell_Antonio_I`.

Neither is sufficient alone, and the measurement says why. `--author-is` tests a
**name**, and a name does not carry a field: 32 of 100 `au:"Kaiser, N"` papers
are nuclear theory, published under the same `N. Kaiser` spelling an identity
regex would match. Field scoping therefore has to live in the query, so
`--author` accepts a bare name (quoted for the API) *or* a whole query
(`au:"Kaiser, N" AND abs:lensing`) and passes the latter through untouched.

Team size comes from the API's author list, never from counting `\author` in the
LaTeX, which picks up template placeholder lines — a live AASTeX source in this
corpus carries `\author[xxxx-xxxx-xxxx-xxxx]{Author Name}`. A paper the API lists
no authors for is dropped and counted, not assumed small. `--author` refuses to
write into the calibration-breadth directory, for the same reason the held-out
guard does.

`--resume` no longer raises on a bank written before `year` became an int: the
carried record is normalised on the way in, so one file never mixes the two.

### The rebuild the sweep forced, and what it exposed

Three calibrators read the abstract bank and were rebuilt: salience, register,
discourse. `extract_style.py` does not read it — `exemplar_paragraphs.jsonl` is
built from the corpus tiers and `fulltext-arxiv/` only — so the UID baseline,
which reads that bank, needed no GPU rebuild. `voice_dataset` does read it, so
the learned L3 model is now behind its inputs; retraining it is GPU-hours and has
not been done.

Only the `abstract` bucket moved, because that is the bucket the abstract bank is
forced into: salience 13,823 → 13,981, cohesion 13,819 → 13,977, hedging 10,290 →
10,413, register 41,559 → 41,721 passages and 53,293 → 53,417 terms. Every other
bucket's `n` is unchanged, so **hedging's shipped operating point is untouched** —
it speaks only about `intro`, whose reference is still 502 sections.

`test_published_figures.py` then named all eight documents-versus-artifact
disagreements, which is what it was built for. Fixing them surfaced three stale
figures it does **not** cover, none of them caused by this sweep:

- §14.2's column headed `n (current)` had not matched the artifact for several
  releases — `method` was 5,957 against the artifact's 6,959, and five of seven
  buckets were wrong before this rebuild touched them.
- §14.4 described the register reference as 38,647 passages and 54,233 terms;
  the artifact said 41,559 and 53,293 even before the sweep, because the exemplar
  bank had grown 25,005 → 27,917 in an earlier rebuild.
- §14.4 also published the firing rule as **≥ 5 manuscript uses**.
  `MIN_MANUSCRIPT_USES` became 15 in v0.32.0 (`1024d0f`); the documented rule had
  disagreed with the code by 3× ever since.

Re-running `eval_findings.py` against the rebuilt profile reproduced §18 exactly
— held-out register 0.448 documents and 0.086 per 1,000 words, rank AUC 0.286,
0.944 of 198 flags suppressed by bank membership, salience gate transfer 0.2775
per passage against 0.2710 expected. §17's register figures (0.872, 0.384) are
the pre-v0.32.0 pair, which `EVALUATION.md`'s map already marked superseded —
but the section itself carried no such notice, so a reader landing on that file
met "a term is flagged at ≥ 5 manuscript uses" in the present tense. §17 now
opens with the supersession banner and names both thresholds.

### Also

- 381 tests (19 files), up from 360. The version and test-count badges in both
  READMEs were stale at 0.32.0 and 334; both now match the manifest and the
  suite.
- Pre-rebuild profile snapshots go to the gitignored `.backups/` **inside** the
  repository, per the rule v0.30.0 recorded: a snapshot placed beside the
  repository reads as a project of its own and escapes the ignore rules covering
  the same corpus-derived files.
- `eval_findings.AXES` stays at two axes on purpose, and now says why: it is not
  a generic axis loop — each axis needs a reading of its own, and the discourse
  axes have no summarizer or stated reading there yet.
- v0.27.1 through v0.29.0 moved to `CHANGELOG-ARCHIVE-RECENT.md`; this file had
  reached 830 lines against the repository's 750-line budget, which made it
  unwritable rather than merely long.

## v0.33.0 — 2026-08-26

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
