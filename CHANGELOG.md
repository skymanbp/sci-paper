# Changelog

All notable changes to the `sci-paper` plugin. Versions follow the
`plugin.json` / `marketplace.json` `version` field.

## v0.39.0 — 2026-09-27

### The audit's first tier, fixed

`docs/audits/full-review-2026-09-27.md` recorded a full-repository review of
v0.38.0: nine parallel line-by-line reads of the tools, skills and documents,
every high and medium finding reproduced first-party. This release settles
every item: its first tier ("应修") and the documentation corrections that go
with it first, then the rest and a profile rebuilt on them. No
consequence class changed; the standard is v3.9 (a fourth narrow exit
contract, `verify_references.py`, and the residues and readings v0.37–v0.38 had
added without a version stamp).

**Gates no longer read missing evidence as a verdict.** An unreadable document
root raises: `length_gate --before <mistyped path>` read a zero-word baseline
and reported every section as growth (exit 1), and `ai_ism_lint dir.tex` read
an empty document and exited 0, clean. A `--git-ref` baseline now resolves its
`\input` children at the ref, so deleting a whole section file, the most
decisive condense move, is counted; before, the child vanished from the
baseline and the cut was understated. `\input{fig.tikz}` is read as written,
a nested `\input` resolves against the document root, and
`\includegraphics` is not an include.

**The projection has one more display form.** `\[ ... \]`, `$$ ... $$` and
`subequations` are display mathematics in both projections. `\[E=mc^2\]`
counted as six words of prose in the gate and the map, and `$$` fell to the
inline pattern, whose second dollar paired with the third and swallowed the
prose up to the next formula in the plain view alone. A macro definition inside
a comment is no longer harvested, and an argument-taking macro with a numeric
body is left alone (`\foo{x}` became `42{x}`).

**The condense map counts what the gate counts.** The abstract/conclusion
carve-out applies to either side of a restatement pair — the abstract precedes
the body, so with only the copy's bucket consulted every abstract claim made
the body's own statement the removable one and named the abstract as its home.
A copy whose negations or numbers differ from its home in either direction is
not a restatement (dropping `not` was still one). `removable_words` excludes
placeholders, the denominator excludes heading words, `7%` of 100 is 7 (the
float ceiling asked for 8), `--require-shrink 0` means no cut required, a
commented-out heading opens no section, any `\...ref` command keeps a float
alive, `\caption*` and nested captions are read, and `(Gaussian)` is not an
acronym.

**The linter judges paragraphs, not lines.** A paragraph-initial connector is
read on the paragraph's first prose line; in one-sentence-per-line LaTeX a
sentence-initial `Notably,` mid-paragraph was an L0 target and the same text
joined onto one line was not. Openers are read where a sentence starts.
`paved` and `showcased` join Tier A (the skill's table and grep had them; the
regex did not). Every em-dash on a line is a target with its own id;
`\label`, `\ref`, `\cite` and `\url` arguments are blanked before the lexical
scan; `not only ... but also ... Bland` is no longer a three-part parallel; an
unparseable lexicon is exit 2; Markdown front matter is metadata; several
profiles without `--field` say so.

**One field resolver.** The shared `--field` option promised auto-detection
while five tools divided the profile root by None and crashed with a
TypeError, the axis tools never auto-detected, and two tools carried private
loops. `cli_common.optional_field_dir` resolves it once; `axis_main` requires
an existing field for `--calibrate` and refuses to write an empty artifact.

**The extractor's statistics are prose statistics.** Multi-word openers can be
observed (they were counted against a single-word counter and always read
absent); placeholders are not words and do not drop a citation-led paragraph
from the bank; words are Unicode letters; bank ids carry the bucket; the
profile directory is created after the corpus check; skipped PDFs are counted
in the summary; an empty `--topic` ranks by section in the keyword fallback.

**The validator reads more.** Its shape regex accepts "N checks" and scans
`tools/README.md` (two "10 checks" survived two releases that ran eleven), and
a relative-link pass reports targets that do not exist — it found the sixteen
local-path links in the 2026-09-04 audit note on its first run.

**The bibliography checker reads what LaTeX reads.** A `\cite` inside a `%`
comment raised an integrity blocker; `\nocite`, the biblatex commands and every
group of `\cites{a}{b}` were invisible; `@string` names were compared literally;
`#` concatenation and an escaped quote dropped every later field, DOI included;
a first author agreed on any substring (`Li` for `Lin`, `Ma` for `Mandelbaum`);
a registry miss was cached forever; `http.client` errors escaped as a traceback
at exit 1. Each is fixed and pinned; a finding built from a cached record now
says so, and any other execution failure is exit 2.

**The document-level axes stop reporting `measured` where they cannot fire.**
Anchoring's conformal p cannot fall below 1/(n+1), so at the 30-document
class floor with two or more classes no finding was ever possible; the class is
now skipped and the axis `degraded`, and calibration records the floor the
Bonferroni share needs. A structure bucket the baseline lacks, and a
`sentence_stats.json` with no classified bucket, are `degraded` too. The
document-shape detector flagged by a rank rule while quoting a threshold and a
leave-one-out rate computed by a quantile rule; one rule now does both, and the
sweep drops the preamble and every `skip` unit on both sides. The partition
tool compares candidate states by conformal p instead of distances from
different manifolds, simulates a split on the original text (the joined text
let a trailing `%` comment swallow half a paragraph), and treats every heading
command as fixed. The tricolon wrap-up needs a wrap-up. A field's
`structure_baseline`, `docstructure_baseline` and `anchoring_baseline` must be
rebuilt for these to take effect; the shipped `wgl` ones were, and their
figures re-taken (below).

**The rewrite gate runs on a fresh clone.** A missing profile, a missing or
unusable `voice_model.joblib`, or a missing sentence-transformers was exit 2,
so the fidelity gate could not run where the optional model had never been
trained; each now leaves its term unmeasured at weight 0 with one stderr line,
and the run ends 0 or 1 by eligibility. Numbers and the negation, causal and
comparison markers are compared as bags, so a dropped second `not` or a
repeated value replaced by another is caught and the report names the count
mismatch; a marker moved between clauses still passes and stays with the
by-hand check. The numeral tokenizer reads the LaTeX en-dash range
`0.5--1.2`, the Unicode minus and exponent sign, and no longer starts a token
inside an identifier (`M200` yielded `00`). `--field` is optional.

**Labelling and evaluation report a thin stratum as unmeasured.** A
population with no body words, a document-scale row under the 20-document
floor, and a labelling cell short of its quota say so instead of printing a
rate, a `StatisticsError`, or a `None` formatted as a float; the floor is one
constant shared by `eval_findings` and `eval_docscale`. `label_findings --n`
is the flagged-row quota per (population, axis) cell; every finding is
collected first and each cell drawn at random with a per-document cap;
emitter failures are printed per axis instead of being read as an exhausted
corpus; pooled recall counts a passage several axes flagged once; `--field`
belongs after the subcommand. `eval_docscale` decides each flag by its
operating point's own alpha, names that point per row, and finds its tiers
under `docval/`. In voice training a failed encode never becomes the feature
cache (the language-model rows are checkpointed and the embedder retried
next run), the repeated audit splits start one seed past the primary split, a
missing numpy is one line and exit 2, and the unbound-name check is
scope-aware: it sees an import that one function bound only for itself.

**The fetcher does what its flags say.** `--journals` applies on the local
full-text shortcut (the "refereed" breadth corpus was never restricted);
`--start-at` sizes its pages from where the band began instead of requesting
a negative page; a throttled full-text run reports TRUNCATED and exits 2 like
the abstract sweep; `--updated-before` applies in full-text mode and the
abstract-only flags are refused there instead of accepted and ignored; a
version bump no longer fetches `...v2` beside `...v1`; `\documentstyle` and
comment-led files are sources and colliding tarball basenames are both kept;
omitting `--field` is a message and exit 2; the built-in query sets are
marked `[WGL]` and `--query` serves any other field.

**The per-bucket axes read the grid at nearest rank and say what they
skipped.** `quantiles` stored the ⌊qn⌋+1-th smallest value, one order
statistic high: p90 of 100 values was the 91st, and at the 30-unit floor the
tails read at P = 0.133 and 0.933. It stores the ⌈qn⌉-th now; an artifact
calibrated before this keeps the old grid until it is recalibrated, as the
shipped `wgl` profile was (below). An artifact recording
another unit than the axis measures is refused and named. A document whose
units fall in the `unknown` bucket, a bucket the baseline lacks, and a
salience reference no bucket resolves above are `degraded` with counts, where
the floor alone read `measured` with zero findings. The edit-meta residue
scan keeps the `skip` sections (an appendix TODO was invisible and the gate
exited 0), a caption's object is sought in the whole paper minus preamble and
bibliography, `\section {X}` labels are read, `truncation` and `truncated`
share one stem, `\newcommand*` is read, an unwritable `--output` is exit 2,
calibrating on no passage writes nothing and exits 2, and a bank row without
`numeral_text` is warned about instead of calibrating silently on the
`[math]` projection. `--glossary` goes through argparse, reads a definition
cue only after the pair, counts a pair joined twice in a sentence twice, and
its status depends on the bank alone; sentence findings carry the sentence's
own lines; the provenance ledger no longer lists a title block as a
paragraph; the oracle survives an empty CUDA message and a blank bank line.
The voice axis is `unmeasured` without the surprisal runtime instead of a
RuntimeError, `--scores` lists paragraphs by source line, and every one of
these tools resolves `--field` through the shared resolver.

### The rest of the audit, and the profile rebuilt on it

**Every item is settled.** Past the first tier, each finding of the audit is
fixed or closed with its reason, and §10 of the audit record names the commit
that carries it.

**The document scale reads prose, at calibrated operating points only.**
Headings and floats are blanked before paragraphs are cut: a heading had fused
into its section's first block, and a float holding a blank line split its
paragraph in two (audit B22). The length-stratum edges are fitted on the
training papers alone, as exchangeability requires (B17), and a feature whose
reference cannot resolve its own tail is `degraded` and ordinary (B18). The
in-sample percentile fallback for a manifold without split-conformal
calibration is gone (B24): no calibration writes such a baseline, so the
manifold rule goes unscored and the axis `degraded` with a rebuild instruction,
and `deai_partition` gives that reason instead of "not measurable".

**Hedging speaks for methods.** Re-measured per section on the rebuilt
profile, hedging separates machine text in `method` at 0.731–0.898 against a
0.442 human/human null and fires on 9.62% of held-out refereed method sections
at its 10% gate, so the axis runs on `intro` and `method` (EVALUATION §19.4).
The v0.33.0 measurement, taken when a manuscript section was one heading span,
had read `method` at 26.77%.

**Skills defer to the standard on strong advisories.** Standard §4 makes an
advisory strong only when a measured effect exceeds a calibrated operating
point. De-AI's structural density hits, paper-review's structural hits,
physics' naming and unit checks and mainline's narrative findings are
judgement calls with no such point; each is now an ordinary advisory ranked
first, and the standard is unchanged. A firmer central hypothesis in
proposal-polish is proposed to the author, never applied silently. Under
`--orchestrated` the parent runs the de-AI audit and figure-review itself, as it
already ran physics, mainline and logic. Mainline's cold read asks an eighth
question, the one thesis line every contribution branch serves (standard
§5.4). Brainstorm drops `--min-frameworks`, whose floor was already all twelve
framings. The paper skill's review grep finds every form the linter does
(`delving`, and `Moreover` mid-sentence).

**One copy of each fact.** The L0 word lists are the linter's patterns, and the
validator now holds the paper skill's table to them in both directions (audit
H8). The loader both evaluators read, the midrank AUC, the placeholder
vocabulary and the named section buckets each have one owner; register
findings, math density and cross-validation folds are computed once where they
were computed twice. The evidence documents keep each measurement in one place
and point to it, the validator's checks and the optional dependencies are
listed once (`tools/README.md`, `requirements.txt`), and the orphaned
`latency.json` is gone.

**Smaller corrections.** `robust` before estimator, estimation, statistic or
regression is a method name and no longer counts toward the Tier B cap (F26).
The paired leakage estimate counts a paper the way the bank holds it (E17).
`corpus_cos` without the embedder or the corpus centroid scores unmeasured
instead of 0.0 (E20). CrossRef requests carry a polite-pool address from
`SCI_PAPER_MAILTO` and retry once on 429 and 5xx (F22). The exemplar embedding
cache is rebuilt when its fingerprint disagrees with the bank (D20). The arXiv
API is queried over HTTPS, and the style dossier names the source files it
skipped. Three regressions the pull request itself introduced are fixed: a
hyphenated compound is one word again, a unit reason names only buckets the
document reaches, and a commented-out `\newcommand` no longer beats the live
one. Examples in code, tests and documents that had been taken from a
manuscript under review are replaced by invented ones; no measurement changes.

**The profile is rebuilt and the figures re-taken.** The `wgl` profile was
rebuilt on 2026-09-27 on every corpus-side fix above, and each evaluation figure
that reads an artifact was re-taken through the shipped path; a figure that was
not names the build it was taken on. The exemplar bank holds 28,444 paragraphs
from 18 of the 19 curated and 498 of the 500 reference papers. The
document-structure baseline is 504 papers, and its table moved (natural-AI
length-fair manifold AUC 0.933 → 0.893, long-form 0.740 → 0.840; human
false-flag 0.020 manifold, 0.042 role) under four changes the record does not
separate (EVALUATION §9). The learned model, retrained on 45,153 records, keeps
its grouped-split AUC at 0.9487 and the ranking its degraded mode consumes
(median Spearman ρ 1.000; 68 of 69 documents surface the same three
paragraphs). Held-out register reads 56 findings, 0.0364 per 1,000 body words,
87.5% of which would vanish had the paper been in its own bank. The worked
example reads 22 advisories before the revision and 17 after.

The suite is 802 tests in 32 files (v0.38.0: 529 in 27); the validator runs
11 checks and passes. v0.35.0–v0.35.1 moved to `CHANGELOG-ARCHIVE-v0.35.md`; this
file had reached 806 lines.

## v0.38.0 — 2026-09-16

### The recurring unattested pair is the manuscript's own term

The collocation axis judged one sentence at a time: does it join words the
field never joins? The author's mentor read the same manuscript with a
different question, "this is jargon and won't make sense to an astronomer",
and the sentences the axis had flagged were not where the jargon was. The
jargon was in the pairs the manuscript kept using, `detector settings` nine
times, `noiseless map` six, `keeps minimum` five, none of them in any of the
field's 41,644 passages and most of them undefined where they first appear.
A pair that recurs is a term; a pair that occurs once is a figure of speech
or a slip. `deai_collocation --glossary` (and `ai_ism_lint --glossary`, off by
default so no count moves) reads the same bank document-wide and lists every
unattested pair used twice or more with its uses, the sections it appears in,
the line of its first appearance in the source, and whether that sentence
carries a definition cue (`we call`, `defined as`, a parenthesis, an
appositive). It is a list to walk, not a verdict: the action is to define the
term at first use or replace it by the field's word, and to leave ordinary
phrasing the corpus happens to lack. On a manuscript under review the reading reduced the
252 distinct unattested pairs of the sentence gate to 42 candidates, 16 of
them already defined where they first appear. The sentence gate is
unchanged: on the same manuscript the default run reports the same 86
findings before and after (set difference zero). Six tests read the mode, one of them the unified linter's flag.
529 tests in 27 files.

## v0.37.1 — 2026-09-05

### An absence is deleted before it is rewritten

v0.37.0 named the absence residue and told the writer to say what the
object does instead. Applied to the author's two manuscripts, that action
had a failure mode of its own: a positive rewrite that only restates what
the neighbouring sentences already carry (one qualifying phrase reached
five occurrences in one paper; an appendix restated a coordinate convention
its method section had already given). The ruling
now in the rule's action, the `paper` skill's self-check, the `de-ai` skill's
residue bullet, and the standard's L4 bullet: judge the sentence in context
and delete the clause first; rewrite only what the page does not yet say;
keep a physical fact, a scope limit, or a conceded limitation as it stands.
The second sweep over the two manuscripts cut 17 such clauses or sentences
that the first sweep had rewritten, and the Pass-3 gate of `rewrite_reward`
then did what §6 says it does: the dropped negation marker is a `missing`
invariant, reported on 4 of 7 changed paragraphs of the shorter manuscript and
38 of 54 pipeline-paper paragraphs, every one the absence clause
itself or its companion (`\ref`, `because`, a math token inside the deleted
clause), and one tokenizer artifact (`CDM-` read as an acronym). The action
text says so, and the disposition is recorded beside the finding rather than
the negation restored (§23.4a). No detector changed; one test reads the new
action. 523 tests in 27 files.

## v0.37.0 — 2026-09-05

### A sentence that says what its object never does is a residue

The negative-label rule of v0.36.0 read headings and captions; the same
defect in body prose had no detector and no name in the standard. The
author's name for it is a menu line reading "tomato and egg (no braised
pork)": the photometric catalog `never enters the shape measurement`, the
comparison sample `carries no redshift estimate`, `no colour cut is
applied, because …`. Each tells the reader what the thing is not, in the
place where the thing should stand, and each is what a revision leaves when
an ingredient was taken out and its absence written in. `residue-absence`
(`deai_residue.py`, rule 6) reads body sentences for the families, exempts a
sentence that cites (a contrast with published work is a baseline, not a
tombstone), and skips a hyphenated compound (`never-masked tiles` is a
name). Strengths were tiered on the held-out refereed full texts, 442 files
and 1,899,092 prose words: `never` and the `nothing is` / `none sees` / `no …
is applied` forms occur 0.008 times per 1,000 words there (15 `never`
sentences in 13 files, all physics, bounds or procedure) and are strong;
`carries no`, `is not applied` and `does not participate` occur 0.02–0.05 per
1,000 words, in 6–15% of files, mostly as procedure, and are ordinary; `is
not a` and `with no` were measured and left out, being the hedges and
definitions-by-contrast §6 protects (§23.4a). On the author's pipeline paper
before its sweep the rule found 15 strong and 17 ordinary sentences, `never`
at 118 times the refereed rate; after it, 0 strong and 2 ordinary physics
statements kept under a disposition. The families live once in the tool,
mirrored between `absence-family` markers in `skills/paper/SKILL.md` beside
the history families, and `validator_check` now proves both mirrors. The
standard's L4 voice bullet says what the rule enforces: a sentence says what
an object does, not what it never does; the `paper` skill's forward-narrative
self-check gains the item, with the physics-fact and scope-limit exemptions
stated beside it. Seven tests; 523 in 27 files.

## v0.36.3 — 2026-09-05

The measurement v0.36.2 reopened is closed, and the profile every figure in
the record quotes is rebuilt on the code that quotes it. No loose ends: every
"open item", "not reproducible" and "still open" in the documents was either
closed by a measurement or restated as the decision it already was.

### The salience reference was calibrated on the wrong projection

§17.5 had the p90 gate firing at **0.4542** per held-out passage against a
0.2710 union bound, and recorded the excess as open. It was a projection seam
on the reference side: the exemplar bank stored each paragraph once, as
`latex_to_plain` text, in which `$\sigma_8 = 0.81$` is `[math]` and carries no
numeral, while the manuscript side reads `latex_to_numeral_text` and keeps
the `0.81`. First-party diagnosis before the fix: the same 150 in-sample
papers, whose own rows the bank holds, fire at 0.349 per passage under the
manuscript projection and 0.135 under the bank's. The fix is one field.
`extract_style.paired_paragraphs` projects each section both ways with the
plain placeholders kept as slot markers — split alone, a paragraph that is
only a displayed equation is `[MATH]` in one view and a swallowed blank line
in the other, and 1,326 sections misaligned — so every bank row carries
`numeral_text` beside `text` (27,831 of 27,851; the 20 rows of one paper's
`\be … \ee` display macros fall back to `text`), and `deai_salience.calibrate`
reads it through `deai_reference.calibrate(text_key=…)`. The two projections
now share one body (`extract_sections._project`), and a math span that ran
across a blank line (`$$ … $$` matched from its second dollar) no longer
carries a paragraph break. Re-measured on the same 203 papers: **2,003
findings over 9,849 scorable paragraphs = 0.2034** per passage, under the
bound as three correlated gates must land, rank AUC against machine text
0.572 → **0.663**; the mentor population 0.3984 → **0.1943** over 1,014.

### The profile is rebuilt on the code that measures it

The corpus-side fixes of v0.36.0–v0.36.2 (heading whitespace and
`\texorpdfstring`, floats and citations blanked across lines, one assembly
reader) had never been run over the corpus: every baseline still described
the 2026-08-27 bank. Rebuilt in one pass: exemplar bank 27,917 → **27,851**
rows (207 gone, 131 added, 478 re-paragraphed, across 48 of 516 papers),
register lexicon 41,644 passages · 53,367 terms, collocation bank 530,504
pairs over 11,282 partner words, salience, cohesion and hedging references,
structure (27,841 observations), document-shape (507 documents), anchoring
(517), the AI-ism classifier, the exemplar-embedding cache, and the UID
baseline (27,851 paragraphs; pooled global surprisal 3.303 ± 0.420, local
3.417 ± 0.445). That last rebuild shares the GPU with whatever else the
machine runs, and twice died of a CUDA out-of-memory raised by another
process; `deai_oracle.token_surprisals` now scores the paragraph on a CPU
instance of the same model when the GPU raises, up to three times per
process, so a rebuild finishes instead of restarting. The voice model
was retrained on the rebuilt bank (44,636 rows): grouped-split AUC
0.9518 → 0.9487, field-topic false positives 0.280 → 0.295, jargon-dense
0.393 → 0.421, each inside the audit's own split range, the fourth
retrain to place the confound in the features (§7.0a); on 1,808 paragraphs
of 63 documents the old and new bundles rank at Spearman 0.991 and surface
the same three paragraphs on 42 documents (§7.0). What moved is recorded
beside what it was: register's 57 held-out
findings are the same 57 (0.0371 per 1,000 body words, AUC 0.391), cohesion
10.81% → 10.78%, hedging in `intro` 7.80% unchanged, collocation AUC 0.704
unchanged, two hedging section gates by ±0.16.

### The UID axis had not run since v0.36.2, and its first findings were spaces

Every lint since the v0.36.2 sweep reported `L1.uid` as unmeasured with the
reason `cannot access local variable 'reference'`: `uid_findings` named its
per-bucket reference row `reference`, the same name as the `deai_reference`
module whose paragraph sweep the loop iterates, so Python bound the name
locally for the whole function and the sweep call itself raised before the
first paragraph. The row is `ref` now, and `tests/test_deai_oracle.py` runs
the sweep with a stubbed model and baseline: a flat paragraph is flagged in
each of two buckets with the reference it was scored against, a paragraph at
the reference variance yields nothing, a short one is skipped. The three
tests fail on the previous tree.

Run live, the axis's first four findings on a seven-page letter sat on its
four heading lines, each a paragraph of surprisal variance 0.5 against a
reference of 3.3. The sweep blanks a heading in place so every unit keeps
its line number, and a `\section{...}\label{...}` line keeps its label
behind forty-eight spaces, which GPT-2 tokenises into more than the UID
minimum; a `% SCOPE:` comment block never had prose. The corpus side drops
both before it splits paragraphs, so those units were measured against a
reference that holds none, and the removal map counted them as units. The
sweep now keeps a block only if it projects to something (`has_prose`): a
display-equation-only paragraph projects to `[MATH]` and stays, as it is a
row on the corpus side. On the two manuscripts 4 and 51 such units are gone
(31 and 110 remain); `tests/test_deai_reference.py` holds the shape.

### A bibliography is verified against the registries it names

Dimension F (citation existence) had only the reviewer's word for it: every
entry's author, year, title and identifier were to be "verified from the
DOI", and nothing in the tree could do the mechanical half.
`tools/verify_references.py` resolves each entry through CrossRef, DataCite
(the prefixes CrossRef does not register) or the arXiv API and compares
first author, year, title, journal, volume and first page with the record;
`--tex` cross-checks the assembled document's `\cite` keys against the
entries. An identifier that resolves nowhere, or a cited key with no entry,
is an `integrity_blocker` (exit 1); a first author, year or title that
disagrees is a strong advisory; journal, volume and page differences are
ordinary, since the record's `Astronomy &amp; Astrophysics` and a
bibliography's `\&` are one journal and a print/online year seam is not an
error. A registry outage leaves the entry unmeasured and the axis degraded.
Live on two manuscripts' bibliographies (76 entries) it found no
unresolvable identifier, one page range that differs between the CVF and
IEEE paginations of the same proceedings paper, and eleven entries with no
identifier at all. `final-review` runs it before each round's paper-review
and hands the report to the reviewer as dimension-F evidence; relevance,
whether a citation supports its sentence, is not a registry question and
stays with the reviewer. The idea is borrowed from K-Dense's
`citation-management` skill, the one part of that collection this plugin
had no counterpart for; its evidence ledgers and reporting-guideline
checklists were evaluated and not adopted.

### Closed as decisions

The human-labelling half of "half closed by provenance" is the author's act,
not a repository item (`DISPOSITIONS.md`); the mentor-phrase check on the
manuscript under review is closed on the draft it was made on, since the phrases it would test
are gone (§23.2); the five v0.14.0 "evidence still required" statuses each
name the section that states them (`DEAI_SUBSYSTEM.md` §11). The v0.33.0 and
v0.34.0 entries move to `CHANGELOG-ARCHIVE-v0.33-v0.34.md`. 516 tests in 27
files; every published figure re-rendered from its artifact by
`test_published_figures`.

## v0.36.2 — 2026-09-04

An external review of v0.36.0/v0.36.1 (Codex gpt-6-astra at maximum
reasoning), every finding verified first-party before it was acted on; the
record is [`docs/audits/codex-review-2026-09-04.md`](docs/audits/codex-review-2026-09-04.md).
Fifteen defects, six root causes, and one measurement the fixes reopened.

### The manuscript side never let a subsection inherit its section

`deai_metrics` carried a second section parser beside `extract_sections`: no
whitespace before the brace, no optional argument, and a subsection whose title
matched no bucket fell to `unknown` and was silently unmeasured — 344 of the
540 paragraphs of one held-out Planck paper — while the corpus side has
inherited since v0.28.0. `section_units` now derives from
`extract_sections.RE_SECTION` with the same inheritance; a document with no
heading is one unit, the preamble is none. Measured on the same 203 held-out
papers in one process: salience 2,753 → **4,473** findings, 0.2776 → **0.4542**
per scorable paragraph against the 0.2710 design rate (§17.5 records the
excess as open; the reference banks were bucketed the same way); cohesion
10.87% → 10.81% and hedging in `intro` 7.89% → 7.80%, unchanged; the mentor
population's salience 0.2781 → 0.3984.

### One paragraph sweep, one line-preserving blanker

Four tools projected the manuscript line by line where the corpus side
projects a passage in one pass. `extract_sections.blank_preserving` is the one
blanker (a match becomes same-length spaces, newlines kept) and
`deai_reference.paragraphs` the one paragraph sweep; structure, oracle, voice,
register, residue, metrics and the labeller read them, so a heading, a float
or a citation split across lines is blanked on both sides.

### Rates per body prose word, and no AUC from two documents

`eval_findings` divided by `text.split()` over raw source — bibliography and
preamble included, which a single-file machine draft has none of — and an
axis whose novelty was `NaN` on all but two documents still reported an AUC.
The denominator is `prose_words(body_only(text))`, placeholders dropped; fewer
than 20 scorable documents is `unmeasured`. The same findings re-read:
register 57 findings 0.0247 → **0.0371** per 1,000 (AUC 0.392 → 0.391),
zero-hit 2.212 → **3.374** (AUC 0.246 → 0.174), collocation AUC 0.691 →
0.704, salience AUC 0.774 → 0.572 (with the bucketing fix above).

### Assembly is one module, and the gate counts prose

`tex_assembly.py`: an `\input` mid-line keeps the words around it, a second
call splices again (only a child in the current include stack is a cycle), and
a `--git-ref` baseline is the document assembled *at the ref* — `length_gate`
had compared an assembled draft against a bare root. The gate counts prose
words (no `[math]`/`[FIGURE-OR-TABLE]` placeholders) and reads
`--require-shrink` as a percentage, a fraction or a word count, rejecting
`100%`, `0%`, `inf` and `30%%` and rounding a fraction up to one word.

### The removal map counts each unit once

A sentence that was both a restatement and zero-gain, or that sat inside a
removed paragraph, was budgeted twice; a canonical home may no longer drop a
negation, a comparative or a number its copy carries; an opener is a
whole-sentence removal only when at most three of its own content words would
go. Held-out default target median 3.08% → **1.59%** of prose (§23.5).

### Residue: marks across lines, and the procedural `we have added`

Edit-meta marks are scanned over the visible body as one text, so a phrase
wrapped at a line break is one mark; once visible, `we have added` fired
fourteen times on refereed prose, every one a procedure (`we have added
uniform Gaussian noise`) or another paper's history, so it is a mark only with
a document object. The diff rule compares whole negated objects and skips a
negation the old version already carried. Strong residue 34 → **27** of 203
papers (16.7% → 13.3%; §23.4).

### Register, collocation, labelling, validator

Citations are blanked across lines and macro definitions matched at line
start; a defined term's scope is its sentence. Collocation pairs break at `/`,
`.` and digits, the weights are named for what they are (`expected_copresent_passages`,
`p_copresence_absent`), scope and calibration unit are `sentence`, and the
bank is rebuilt (541,309 → 530,677 pairs). The labeller's control sample
excludes any passage a finding touches by line span. `validate_plugin` gains an
eleventh check: no tracked file past the 750-line budget. Standard and skill
text corrected where they had drifted from the code (zero-hit exemptions,
the paper-agent example, the modifier-stack definition, the restatement
rule). 491 tests in 24 files; §23, §17.5, §19.4, §21 and both README
limitation tables re-taken.

## v0.36.1 — 2026-09-04

The first run of v0.36.0 on a manuscript with AASTeX tables: three tool
defects, none of them in the manuscript.

### The fourth line seam: floats

`deai_register` projected the manuscript one line at a time, so a
`\begin{table*}…\end{table*}` spanning lines was never blanked the way the
corpus side blanks it in one pass over a passage. A `tabular*` column
specification (`@{\extracolsep{\fill}}lll`), `\tabletypesize{\scriptsize}`,
`\tablenotetext{a}{…}` and every caption's words counted on the manuscript
side only: 23 of 90 zero-hit terms on one paper were `filllll`, `tabcolsep`,
a note letter fused to its first word, and caption words. `body_only` now blanks floats and
length/table-note commands across lines beside the math spans of §23.1; the
shared float pattern names `deluxetable*`, `longtable` and a bare `tabular*`
as tables on both sides; a token with fewer than three letters (`a--c`, a
panel range) is not a word. Re-measured on the same populations: held-out
`register-zero` 2.658 → **2.212** per 1,000 words, still on 100% of refereed
papers, rank AUC 0.221 → 0.246; the thresholded rule 81 → **57** findings,
0.0351 → 0.0247 per 1,000, 30.0% → 22.2% of documents, AUC 0.352 → 0.392,
own-membership 98.2% of 57. Salience and collocation lose the passages that
were table cells (held-out 1.2025 → 1.1925 and 2.044 → 2.031 per 1,000, AUCs
0.770 → 0.774 and 0.688 → 0.691); every machine row and the manuscript figure
§23.1 quotes (14 words, 11 strong) are unchanged.

### A negated object stops at the sentence end

`residue-negative-label` captured "a mass reconstruction. The solid spheres
mark…" as one object and reported `solid` absent from the body. The capture
now ends at `.`, `!` or `?` as well as at a clause mark. Two regression tests
(465 in 23 files); manifests and headers at 0.36.1; §23.1 table and both
README limitation rows re-taken.

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

`binned kernel` is two ordinary words and a pair no corpus passage has
written. `tools/deai_collocation.py` judges each sentence by the fraction of
its distinct adjacent common-word pairs the bank does not attest, against a
leave-one-out reference per bucket at sentence unit — at calibration a pair
seen in exactly one passage is that passage's own. Only common words are
judged as partners (11,286 of them), pairs break at punctuation, placeholders
and dashes, and each flagged pair carries its expected co-occurrence and
e^−λ. On a manuscript under review it flags five of the six mentor-marked phrases
still present; on held-out papers the document novel-pair fraction separates
machine text at AUC 0.688.

### Three structure families from the mentor's margin

Paper-as-agent subjects ("This study asks whether"), wh-cleft openers ("What
matters is") and modifier stacks (a three-plus-token noun phrase, head
included, with two hyphenated compounds) join `deai_structure`'s auxiliary class: named on
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

---

Older entries: [CHANGELOG-ARCHIVE-v0.35.md](CHANGELOG-ARCHIVE-v0.35.md)
(v0.35.0-v0.35.1), [CHANGELOG-ARCHIVE-v0.33-v0.34.md](CHANGELOG-ARCHIVE-v0.33-v0.34.md)
(v0.33.0-v0.34.0), [CHANGELOG-ARCHIVE-RECENT.md](CHANGELOG-ARCHIVE-RECENT.md)
(v0.27.1-v0.32.0), [CHANGELOG-ARCHIVE.md](CHANGELOG-ARCHIVE.md)
(v0.22.0-v0.27.0) and
[CHANGELOG-ARCHIVE-EARLY.md](CHANGELOG-ARCHIVE-EARLY.md) (v0.1.0-v0.21.0).
