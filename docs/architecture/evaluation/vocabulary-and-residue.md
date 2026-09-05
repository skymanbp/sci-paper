# EVALUATION §23 — vocabulary the field never wrote, sentence families from a mentor's comments, the removal map, and the residue an edit leaves

Part of the evidence record whose hub is [`../EVALUATION.md`](../EVALUATION.md);
section numbers are global. Everything here was measured on 2026-09-04 against
the rebuilt `wgl` profile (41,710 passages), the 203 held-out refereed
ApJ/ApJL/A&A papers of §17 (median 6,944 body prose words, 9,793 counting the
raw source; none in any calibration bank), the 544 in-sample refereed papers,
and the 173 `docval` machine documents of §16. Every per-1,000-word rate is per
body prose word since v0.36.2 — the register projection with placeholders
dropped — where it was per raw-source word, bibliography and preamble included.
The private Letter that motivated the work is measured too; nothing from it is
quoted beyond single words and the two-word phrases its mentor marked.

## 23.1 The zero-hit audit: every word the corpus never wrote

**The owner's rule.** `L0.register` shipped with a 15-use floor (§18.4) because
below it the axis flags a refereed paper more often than not. The owner asked for
the opposite instrument: take *every* word of the manuscript, look each one up
in the corpus, and treat a word with zero hits as a strong mark unless there is a
reason — the paper defines it, or it names a method the field has not used
before. `deai_register` now carries that audit as `register-zero:<term>` beside
the thresholded rule. The mechanical exemptions, reported ordinary, are a
formation of an attested stem (`clears` from `clear`), a term the paper defines
at first use, and a proper name (`benjamini--hochberg`); every other zero-hit
word is strong and takes one of the §5.2 step-1b dispositions.

**It is exhaustive, and it is not a detector.** Rates per 1,000 body prose
words, and the fraction of documents with at least one finding
(`eval_findings.py --field wgl`, 2026-09-04, re-taken under v0.36.2):

| population | n | `register-zero` /1k words | documents flagged | `register` (15-use rule) /1k words |
|---|---:|---:|---:|---:|
| held-out refereed | 203 | **3.374** | 100.0% | 0.037 |
| in-sample refereed (bank members) | 544 | 0.812 | 75.0% | 0.007 |
| machine, all tiers | 173 | 1.054 | 79.8% | 0.002 |
| machine `ai_adversarial` | 40 | 2.132 | 92.5% | 0.000 |
| machine `ai_long` | 29 | 1.043 | 100.0% | 0.003 |

Rank AUC of machine over held-out on the per-1k rate is **0.174**: a refereed
paper carries more words the corpus never wrote than a machine draft does,
which is the same direction §18.4 found for the thresholded rule at every floor
from 5 to 50. The audit therefore ships as advice with author dispositions and
never as a gate, and the standard says so (§2 L0). The in-sample row is what
bank membership buys — a paper whose own vocabulary is in the denominator
loses two thirds of its zero-hit words — and is not a leakage estimate, for the
era reason §17.3 gives.

**What it finds on the Letter** (re-measured on the current draft, 2026-09-04).
Thirteen zero-hit words, ten strong. Three are statistics vocabulary the
field's corpus does not use (`probit`, `deciles`, `exceedance`), three are this
plugin's own software vocabulary that had leaked into an astronomy manuscript
(`unmeasured`, `rescored`, `outranks`), one is a coinage the paper needs to
define (`resolvability`), and the ordinary hits are stem formations (`clears`,
`earns`) and a name (`benjamini--hochberg`). Every one of those is a decision
the author can make in a second, which is the point of listing them all.

**A third projection asymmetry.** Building the audit exposed the third
instance of the class recorded in §17.4 and §18.1: section headings sat in the
manuscript's body projection but never in a corpus passage (the banks hold the
prose *under* a heading), so `Validation` fused with the first sentence beneath
it and read as a zero-hit word, and the same fusion put heading words into
collocation pairs. `extract_sections.RE_HEADING_COMMAND` is now the one owner
of the heading pattern; `deai_reference.units` and `sections`,
`deai_register.body_only` and `length_gate` consume it. The thresholded rule
moved with the fix on the same 203 papers, re-run through both versions of the
code in one process: **196 findings → 81**, 0.0858 → 0.0351 per 1,000 words,
44.8% → 30.0% of documents, rank AUC 0.286 → 0.352, and the paired
own-membership test of §17.3 reads 95.1% of 81 (was 94.4% of 198). The figures
§18.4 and §21 quote stand as what they measured on that day; the operating
point they chose is unchanged. A fourth seam followed in v0.36.1 — floats,
blanked whole on the corpus side and never on the line-by-line manuscript side,
so table preambles and caption words read as zero-hit terms — and the same
papers re-measured at 81 → **57** findings, 0.0247 per 1,000 words, 22.2% of
documents, AUC 0.392, own-membership 98.2% of 57. v0.36.2 moved the
denominator, not the findings: the same 57 read **0.0371** per 1,000 body
prose words (AUC 0.391) and the audit 3.374 (AUC 0.174), because a refereed
paper's raw source carries a bibliography and a preamble that a single-file
machine draft does not, so the old rate was diluted on one side only; the
table above is the re-taken one.

## 23.2 `L2.collocation`: sentences that join words the field never joins

**What the mentor marked.** Of 25 margin comments on the Letter, eight were of
one kind — "I don't know what this means", "this is jargon" — and each sat on a
two-word phrase (`physical cells`, `controlled grid`, …) whose words are
ordinary field vocabulary and whose *pair* no passage of the corpus has
written. The register axis cannot see this: both words have healthy document
frequency. A prototype on the first 1,500 words of each document, ranking
documents by their novel-pair fraction, reached AUC 0.855 and put the Letter
at 0.557 against a human p90 of 0.300; that prototype is superseded by the
shipped axis below, which is judged per sentence and reports its document
fraction as evidence only.

**Design.** `deai_collocation.py --calibrate` builds a bank from the two human
passage banks: unigram document frequency for the 11,286 words at or above
`COMMON_RATE` (2 × 10⁻⁴), and passage frequency for 530,677 adjacent pairs of
them. A pair is two words the writer put side by side, so it breaks at
punctuation, at a `[math]`/`[CITE]` placeholder, at a dash, at a slash and at
a digit (`yields, separate` is two clauses; `50/50` and `2 sigma` are not word
pairs), and a sentence's pairs are judged distinct. The unit is the sentence;
the feature is the fraction of a sentence's judged pairs the bank does not
attest; sentences with fewer than four judged pairs abstain. The reference is
leave-one-out per bucket: at calibration a pair the bank saw in exactly one
passage is treated as that passage's own, so the reference distribution is
what a held-out sentence would see. The p90 and p95 gates read the top of a
percentile plateau, so on a feature this coarse the reference mass at or above
a gate sits below the nominal 10% and 5%. Each flagged pair carries a
co-presence weight — the passages in which both its words appear, and the
chance that a pair of words that common would never have been written — as a
ranking aid and never a filter, so a pair of two frequent words reads as a
stronger absence than a pair of two rare ones.

| bucket | n sentences | p50 | p90 (advisory) | p95 (strong) |
|---|---:|---:|---:|---:|
| abstract | 89,392 | 0.250 | 0.588 | 0.667 |
| method | 27,293 | 0.200 | 0.500 | 0.600 |
| intro | 14,382 | 0.200 | 0.444 | 0.500 |
| results | 12,419 | 0.200 | 0.500 | 0.571 |
| data | 12,054 | 0.200 | 0.500 | 0.600 |
| discussion | 12,205 | 0.200 | 0.500 | 0.571 |
| conclusion | 8,571 | 0.200 | 0.500 | 0.556 |

**Transfer and separation** (`eval_findings.py`, findings per 1,000 words and
documents with at least one):

| population | n | findings /1k words | documents flagged |
|---|---:|---:|---:|
| held-out refereed | 203 | 4.700 | 99.0% |
| in-sample refereed (bank members) | 544 | 0.203 | 43.4% |
| machine, all tiers | 173 | 4.811 | 100.0% |
| machine `ai_long` | 29 | 4.534 | 100.0% |
| machine `ai_adversarial` | 40 | 6.128 | 100.0% |

On the document novel-pair fraction the rank AUC of machine over held-out is
**0.704** — the axis separates, unlike the two vocabulary rules, and more than
salience now does (0.572 on body-word density; §17.5 records why that figure
moved). Two things the table must not be read as. The held-out row
is an upper bound on the design rate, not the rate itself: the reference is
leave-one-out over bank passages of one era, and a 2020–2021 paper's pairs drift
from a 2012–2018 bank for reasons that have nothing to do with how it is
written (the §17.3 argument). And the in-sample row is the bank-membership
effect at its largest — a paper's own pairs are attested by itself — so it is
not a leakage estimate either.

**The Letter** (re-measured on the current draft, 2026-09-04). 29 sentence
findings, 22 strong, document novel-pair fraction 0.603 over 481 judged pairs.
On the draft first measured, of the eight phrases the mentor marked two had
already been rewritten out and **five** of the six present were in flagged
sentences (`physical cells` and `controlled grid` among them). The current
draft carries neither phrase, so the mentor-phrase check is closed on the
draft it was made on rather than repeatable: the phrases it would test are
gone, which is the outcome the check exists to produce. On the shipped examples the axis rises from 2 findings to 3 across the
revision, because the synthetic paper repeats its own coined parameter and the
cohesion fix carried a noun into a new neighbourhood — the axis's stated
exception at work, recorded in [`examples/README.md`](../../../examples/README.md).

## 23.3 Three structure families from the mentor's margin

The remaining comments that named a *sentence shape* rather than a phrase fell
into three kinds: a paper-as-agent subject with a mental verb ("This Letter
asks whether …" — "is it an AI prompt?"), a wh-cleft opener ("What it can
conclude is limited by …" — "feels AI-ish"), and a modifier stack (three or
more tokens before the head noun with at least two hyphenated compounds).
`deai_structure` names them under `structure-auxiliary`, outside
`template_score`, and `--calibrate` records their human fraction per bucket:

| bucket | n paragraphs | paper-agent | wh-cleft | modifier stack |
|---|---:|---:|---:|---:|
| abstract | 433 | 0.92% | 0.00% | 15.94% |
| intro | 3,840 | 0.29% | 0.13% | 5.83% |
| method | 9,512 | 0.13% | 0.05% | 3.44% |
| data | 3,908 | 0.23% | 0.15% | 4.32% |
| results | 3,958 | 0.28% | 0.03% | 2.53% |
| discussion | 3,647 | 0.41% | 0.16% | 3.32% |
| conclusion | 2,609 | 1.00% | 0.23% | 5.83% |

A first cut of the stack rule counted any run of non-function tokens and put
15% of human method paragraphs in it; cutting the run at the head noun and
requiring two hyphenated compounds brought the fraction to what the table
shows. On the Letter the families name one paper-agent sentence, one wh-cleft
and nine stacks, and the two stacks the mentor marked are among the nine.

## 23.4 `L4.residue`: the trace an edit leaves

Five deterministic rules (`deai_residue.py`): self-referential drafting
history (a family word in a first-person sentence with no citation), a sentence
that defines the paper's own object by what it never does or has (§23.4a),
edit-meta literals, a heading or caption whose object the body never names, and
— given `--before` or `--git-ref` — a label the edit added and does not earn. A
strong finding exits 1. The strengths were set on the 203 held-out papers (70,848
body prose sentences; 85,324 under the raw-source projection the first three
passes counted), in four passes:

| pass | self-history strong | edit-meta strong | negative-label | documents with a strong finding |
|---|---:|---:|---:|---:|
| raw document, first families | 243 | 184 | 78 (strong) | 154 / 203 |
| body projection, `initially`/`originally` ordinary | 203 | 67 | 74 (ordinary) | 106 / 203 |
| `used to` dropped, `at first` ordinary | 24 in 20 papers | 67 in 15 papers | 74 in 58 papers | 34 / 203 (16.7%) |
| v0.36.2: marks read across lines, `we have added` needs a document object | **24 in 20 papers** | **69 in 8 papers** | 67 in 53 papers | **27 / 203 (13.3%)** |

The first pass was the projection asymmetry again: `\newcommand{\TODO}` in a
preamble and "Planck Collaboration XXX" in a bibliography are not prose an
edit left, so the literal and label rules now read `deai_register.body_only`,
`XXX` left the literal list, and the sentence rule drops `skip` buckets. The
second pass found that `used to` was 174 of 203 remaining strong hits — every
one the instrumental sense ("the radii used to trace …") — and that
`initially`, `originally` and `at first` open procedure steps in refereed
prose. The fourth came with v0.36.2's cross-line matching: `we have added`
wrapped at a line break had been invisible, and once seen it fired fourteen
times, every one a procedure (`we have added uniform Gaussian noise`) or
another paper's history (`in the revised version of \citet{…}`) — the `used
to` lesson again — so the phrase is a mark only with a document object (`we
have added a paragraph`). What remains strong fires in 13% of refereed
papers; 68 of the 69 edit-meta hits are `\textcolor{red}` inside tables, an
author's emphasis that the disposition `kept` answers in a word. The static
negative-label rule fires on 26% of refereed papers and is ordinary; only the
diff rule gates. The Letter carries 0 residue findings.

### 23.4a `residue-absence`: the prose form of the negative label

The author's name for the defect is a menu line reading "tomato and egg (no
braised pork)": a sentence that tells the reader what the paper's own object
never does or has, where the thing itself should stand (`the head never
participates in the decision`, `the reference carries no quoted number`, `no
support threshold is applied, because …`). The negative-label rule catches it
in headings and captions; this rule reads body sentences, and a citation in
the sentence exempts it as a baseline contrast. The families were tiered on
the held-out full texts (442 files, 1,899,092 prose words), counting sentences
without a citation token:

| family | sentences | files | per 1,000 words | tier |
|---|---:|---:|---:|---|
| `never` (not a hyphenated compound) | 15 | 13 / 442 | 0.008 | strong |
| `nothing is` / `none sees` / `none enters` | 16 | 15 / 442 | 0.008 | strong |
| `no … is applied` template | 5 | 5 / 442 | 0.003 | strong |
| `carries no` and its verb family | 98 | 67 / 442 | 0.052 | ordinary |
| `is not applied` and its verb family | 41 | 27 / 442 | 0.022 | ordinary |
| `does not participate` and its verb family | 62 | 44 / 442 | 0.033 | ordinary |
| `is not a` (measured, not adopted) | 120 | 84 / 442 | 0.063 | — |
| `with no` (measured, not adopted) | 96 | 65 / 442 | 0.051 | — |

The refereed uses of the strong forms are physics (`[math] never vanishes`),
bounds (`never exceeds 0.1%`) and procedure (`we linearly interpolate, and
never extrapolate`), one to two per paper that carries one; the ordinary
forms are procedure in the majority (`we do not use any data below z`). The
two rejected forms are hedges and definitions by contrast (`this is not the
case`, `not a surprise`), the qualifier class §6 protects. On the author's
pipeline paper before its sweep the rule found 15 strong and 17 ordinary
sentences in 11,661 prose words, `never` alone at 0.94 per 1,000 words, 118
times the refereed rate; after the sweep, 0 strong and 2 ordinary, both
physics kept under a recorded disposition. The Letter went from 2 strong to
0 strong and 1 ordinary.

## 23.5 The removal map: what a refereed paper has to remove

`condense_map.py` on the 203 held-out papers (median 7,174 prose words) and the
173 machine documents, removable words per 1,000 prose words — candidate mass
per scan, overlaps included:

| scan | held-out median | held-out p90 |
|---|---:|---:|
| `condense-restatement` | 10.01 | 35.04 |
| `condense-zero-gain` | 8.37 | 23.29 |
| `condense-dead:*` | 0.49 | 8.21 |
| `condense-verbose` | 2.65 | 5.78 |
| `condense-regloss` | 0.00 | 0.50 |
| `condense-duplicate` | 0.00 | 0.00 |

The default target (restatement plus zero-gain outside the abstract/conclusion
carve-out, each unit counted once since v0.36.2 — a sentence that was both a
restatement and zero-gain, or a sentence inside a removed paragraph, had been
counted twice) is a median **1.59%** of prose on refereed papers (p90 4.11%),
total removable 2.48%; on machine documents 0.20% and 0.29%. The map is not a
detector either (AUC of machine over human on the default target 0.097 — short
machine documents restate less) and is not meant as one: it exists because the
`condense` skill's own sweep removed 1.5% of the shipped sample manuscript by
reading, and a pass that cuts less than a refereed paper's own median has not
found what the map lists. `length_gate.py --require-shrink` turns the map's
target into an exit code.

## 23.6 What this section does not establish

Whether any individual `register-zero` or `collocation-novel` advisory is good
advice is still the labeller's question (`label_findings.py` now samples the
collocation axis too). The collocation separation is one generation process;
§20 is what happens when that is not checked. The residue strengths are set on
refereed prose only — no labelled edit history exists to measure recall on.
