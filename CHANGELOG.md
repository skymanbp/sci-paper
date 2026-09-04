# Changelog

All notable changes to the `sci-paper` plugin. Versions follow the
`plugin.json` / `marketplace.json` `version` field.

## v0.36.0 — 2026-09-04

Five tracks from one plan, each answering a specific complaint about what the
plugin could not see: words the field never wrote, sentences a mentor marked
as "jargon, what does this mean", a condense pass that scraped a few percent
by hand, and the trace an edit leaves behind. Three new tools, three new
structure families, one new exit contract, and the standard at v3.8 inside its
750-line budget. Evidence: [§23](docs/architecture/evaluation/vocabulary-and-residue.md).

### The zero-hit audit, and a third projection asymmetry

`deai_register` kept a 15-use floor so that it would not flag a refereed
paper more often than not. The owner's rule replaces the knob with an
exhaustive question: which body words does the manuscript use that **no
passage of the field's corpus carries?** Every one is listed under
`register-zero:<term>`, strong unless it is a mechanical formation of an
attested stem, and the only other exemptions are the author's — the paper
defines the word, or cites the method it names. Measured on 203 held-out
refereed papers against 173 machine documents it is not a detector (2.66 words
per 1,000 on every refereed paper, rank AUC 0.221) and ships as advice.

Building it exposed the third instance of the projection asymmetry recorded
in §17.4 and §18.1: section headings sat in the manuscript's body projection
but never in a corpus passage, so `Validation` fused with the sentence under
it and read as a word the field never wrote. `extract_sections.RE_HEADING_COMMAND`
is now the one owner of the heading pattern and `deai_reference.units`,
`deai_register.body_only` and `length_gate` consume it. The thresholded rule
moved with it on the same 203 papers: 196 findings → 81, 0.0858 → 0.0351 per
1,000 words.

### `L2.collocation`: words the field never joins

`physical cells` is two ordinary words and a pair no passage of 41,710 has
written. `tools/deai_collocation.py` judges each sentence by the fraction of
its distinct adjacent common-word pairs the bank does not attest, against a
leave-one-out reference per bucket at sentence unit — at calibration a pair
seen in exactly one passage is that passage's own. Only common words are
judged as partners (11,286 of them), pairs break at punctuation, placeholders
and dashes, and each flagged pair carries its expected co-occurrence and
e^−λ. On the private Letter it flags five of the six mentor-marked phrases
still present; on held-out papers the document novel-pair fraction separates
machine text at AUC 0.688.

### Three structure families from the mentor's margin

Paper-as-agent subjects ("This paper presents"), wh-cleft openers ("What
matters is") and modifier stacks (three-plus tokens before a head noun with
two hyphenated compounds) join `deai_structure`'s auxiliary class: named on
the sentence, never in `template_score`, with per-bucket human fractions in
the recalibrated baseline (stacks 2.5–15.9%, paper-agent 0.13–1.00%, wh-cleft
0.00–0.23%).

### Condensation that is measured against a map, not a feeling

`tools/condense_map.py` enumerates every removable entry — restatements with
their canonical home, zero-gain sentences, dead figures/tables/labels/macros/
acronyms, verbose constructions, repeated glosses, duplicated paragraphs —
with the words each frees, and totals a default target. `length_gate.py
--require-shrink` turns that target into an exit code (`length-shrink-short`,
strong, exit 1). Held-out refereed papers carry a median default target of
3.1% of prose; the old `condense` skill removed less than that by reading. The
skill is rewritten around the map: one disposition per entry, closed by the
gate.

### `L4.residue`: the trace an edit leaves

`tools/deai_residue.py`: first-person drafting history (`we initially`, `no
longer`), edit-meta text (`TODO`, `see previous version`), a heading or
caption whose object the body never names, and with `--before`/`--git-ref`
the label an edit added and does not earn. Exit 1 on a strong finding is the
third narrow exit contract, so its strengths were set on 203 held-out refereed
papers rather than assumed: the first families put a strong finding in 154 of
them; reading body prose only (a `\newcommand{\TODO}` in a preamble and
"Planck Collaboration XXX" in a bibliography are not residue), dropping `used
to` (174 instrumental hits) and demoting `initially`/`originally`/`at first`
bring that to 34, and the static negative-label rule is ordinary while the diff
rule gates. The history families live once in the tool,
mirrored between markers in `skills/paper/SKILL.md`, and `validate_plugin`'s
tenth check calls the tool's own `validator_check` to prove the mirror and to
scan shipped documentation for the edit-meta literals.

### Everything that had to move with it

`ai_ism_lint` runs both new axes by default (`--no-collocation`,
`--no-residue`); `eval_findings` and `label_findings` cover collocation; the
`examples/` table gains a `collocation-novel` row (3 → 6, and why); the
standard is v3.8 at 749 lines. 38 tools, 463 tests in 23 files, 10 validator
checks. The README latency table is re-taken whole: the model-free row rose
from 458 ms to 1.07 s, most of it the 541,309-pair bank load, which
`--no-collocation` drops. v0.30.0–v0.31.0 moved to `CHANGELOG-ARCHIVE-RECENT.md`;
this file had reached 790 lines.

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

A manuscript that writes `\newcommand{\Nfields}{63}` in its preamble and
`\Nfields{}` in its results put a measured quantity where neither named text
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

## v0.32.0 — 2026-08-26

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
a citation renders a mark, a declaration (`\nocite`, `\setcitestyle`) renders
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

---

Older entries: [CHANGELOG-ARCHIVE-RECENT.md](CHANGELOG-ARCHIVE-RECENT.md)
(v0.27.1-v0.31.0), [CHANGELOG-ARCHIVE.md](CHANGELOG-ARCHIVE.md)
(v0.22.0-v0.27.0) and
[CHANGELOG-ARCHIVE-EARLY.md](CHANGELOG-ARCHIVE-EARLY.md) (v0.1.0-v0.21.0).
