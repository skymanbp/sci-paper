# Changelog

All notable changes to the `sci-paper` plugin. Versions follow the
`plugin.json` / `marketplace.json` `version` field.

## v0.37.0 — 2026-09-05

### A sentence that says what its object never does is a residue

The negative-label rule of v0.36.0 read headings and captions; the same
defect in body prose had no detector and no name in the standard. The
author's name for it is a menu line reading "tomato and egg (no braised
pork)": the head `never participates in the detection decision`, the
reference stratum `carries no quoted number`, `no support threshold is
applied, because …`. Each tells the reader what the thing is not, in the
place where the thing should stand, and each is what a revision leaves when
an ingredient was taken out and its absence written in. `residue-absence`
(`deai_residue.py`, rule 6) reads body sentences for the families, exempts a
sentence that cites (a contrast with published work is a baseline, not a
tombstone), and skips a hyphenated compound (`never-touched controls` is a
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
Letter is closed on the draft it was made on, since the phrases it would test
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
`\tablenotetext{a}{Tied…}` and every caption's words counted on the manuscript
side only: 23 of 90 zero-hit terms on one paper were `filllll`, `tabcolsep`,
`aTied`, `crimson`, `isosurfaces`. `body_only` now blanks floats and
length/table-note commands across lines beside the math spans of §23.1; the
shared float pattern names `deluxetable*`, `longtable` and a bare `tabular*`
as tables on both sides; a token with fewer than three letters (`a--c`, a
panel range) is not a word. Re-measured on the same populations: held-out
`register-zero` 2.658 → **2.212** per 1,000 words, still on 100% of refereed
papers, rank AUC 0.221 → 0.246; the thresholded rule 81 → **57** findings,
0.0351 → 0.0247 per 1,000, 30.0% → 22.2% of documents, AUC 0.352 → 0.392,
own-membership 98.2% of 57. Salience and collocation lose the passages that
were table cells (held-out 1.2025 → 1.1925 and 2.044 → 2.031 per 1,000, AUCs
0.770 → 0.774 and 0.688 → 0.691); every machine row and the Letter figure
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

Paper-as-agent subjects ("This Letter asks whether"), wh-cleft openers ("What
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

---

Older entries: [CHANGELOG-ARCHIVE-v0.33-v0.34.md](CHANGELOG-ARCHIVE-v0.33-v0.34.md)
(v0.33.0-v0.34.0), [CHANGELOG-ARCHIVE-RECENT.md](CHANGELOG-ARCHIVE-RECENT.md)
(v0.27.1-v0.32.0), [CHANGELOG-ARCHIVE.md](CHANGELOG-ARCHIVE.md)
(v0.22.0-v0.27.0) and
[CHANGELOG-ARCHIVE-EARLY.md](CHANGELOG-ARCHIVE-EARLY.md) (v0.1.0-v0.21.0).
