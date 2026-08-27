# EVALUATION — Real rewrite evaluation, perceptual panel, salience, register, narrative · `sci-paper` v0.32.0

Part of the evaluation record. The hub — evaluation contract, current
axis status, repository verification, release evidence boundary, and the
map of every section — is [`EVALUATION.md`](../EVALUATION.md); read it
first. Section numbers are global across the whole record, so a reference
like "§9.5" means the same thing in every file.

Normative policy lives in [`SCIPAPER_STANDARD.md`](../../SCIPAPER_STANDARD.md);
nothing here can redefine it. All machine-readable findings use the
`sci-paper.feedback.v1` contract.

---

## 11. Real introduction rewrite evaluation

A proposal-only run was completed on 2026-07-12 against the manuscript commit
`[removed]`,
`sec_1_intro.tex` lines 54--76 (paths as of that commit; the draft tree
was dissolved into `papers/manuscripts/the manuscript/` + git history on 2026-08-06). The manuscript was not modified. The target was the announced
"five elements / First ... Fifth" sequence.

### 11.1 Source and fidelity verification

The original paragraph, the current method description, and its current numerical and
citation sources were read in the same run. In particular:

- [removed]
  `notes/REDACTEDNOTE.md` section T2;
- [unpublished manuscript content removed 2026-08-27]

The selected candidate preserved every deterministic protected invariant from the
source paragraph: numbers, units, citations, inline mathematics/macros, uppercase
acronyms, comparison direction, negation, and causal-direction markers. Manual review
also found no change to named entities, scope, stance, stage order, or claim/evidence
relations. No new fact, number, citation, entity, mechanism, or quantitative qualifier
was added.

### 11.2 Proposed rewrite

> [unpublished manuscript content removed 2026-08-27]

### 11.3 Before/after feedback

Both reports used the same field profile and the deterministic L0, distribution,
sentence-structure, and document-structure axes.

| Measurement | Before | Proposed rewrite |
|---|---:|---:|
| L0 targets | 0 | 0 |
| integrity blockers | 0 | 0 |
| total advisories | 3 | 2 |
| target-paragraph structure finding | announced enumeration | none |
| L1 distribution | degraded | degraded |
| L2 sentence structure | degraded | degraded |
| L2 document structure | unmeasured | unmeasured |

The target finding was removed without forcing unrelated advisories to zero. The two
residual advisories occur in unchanged paragraphs at source lines 10--25 and 27--39;
their disposition remains `pending`. Whole-document shape remains unmeasured because a
single introduction does not contain the required independent section structure. L3
field similarity was not rerun locally because arbitrary-candidate featurization may
cross the project's cloud-only compute boundary; its release status remains `degraded`
for the independent calibration reasons in section 7.

The rewrite remains a proposal until the author accepts or rejects it. It must not enter
the exemplar bank or the the manuscript manuscript before that decision.

## 13. Blind A/B perceptual panel and the layer-2 tell taxonomy (v0.18.0)

Date: 2026-07-14. Subject: the full de-scaffold rewrite of a real 31-page ApJ
draft (the manuscript, weak-lensing pipeline; 71 substantial paragraphs) executed under
a mechanical fidelity gate (8 protected token multiset classes: cites, refs,
labels, byte-frozen floats, byte-frozen display math, inline math, macro
invocations, numeric literals, all multiset-identical before/after).

### 13.1 Protocol

Independent cold-read judge agents, blind to version identity and to each other,
each read the complete assembled main text and return: an `ai_feel_1to5` score
(1 = confidently human, 5 = confidently machine), a tell inventory with verbatim
quotes, and the single strongest machine-feeling passage. Four judges per
version. The panel is a perceptual validation instrument for L2: it measures
what a hostile expert reader actually notices, which the deterministic detectors
can then be tested against.

### 13.2 Case study: tell substitution under score invariance

Three versions of the same document were paneled:

| Version | Mean score | Judge scores | Top tell named |
|---|---|---|---|
| pristine v18 | 2.0 | [2,2,2,2] | announced enumeration scaffolds (4/4 judges; 3x strongest passage) |
| Phase A (de-scaffold) | 2.0 | [2,2,2,2] | antithesis density, aphoristic closers (0/4 mention enumeration) |
| Phase A2 (tell-targeted) | 2.25 | [2,3,2,2] | residual antithesis habit, intro requirement cadence |

The headline result: **the mean score is invariant while the tell inventory
turns over completely.** Removing the dominant tell family (announced
enumeration, 8 instrument findings to 0) did not move the score; judges
saturated on the next stratum (antithesis clusters, aphoristic closers) at the
same perceived intensity. Reading the mean score as "no improvement" is
therefore wrong: the correct diagnostic is which tells the judges name and
whether the previous stratum is gone. Score movement is expected only when the
tell hierarchy is exhausted.

### 13.3 Layer-2 tell taxonomy (panel-derived)

Tells the panel surfaced that the v0.17.0 detectors did not capture:

1. **Antithesis clusters**: "X rather than Y" / "not X but Y" / "X instead of
   Y" as a default sentence engine. Corpus calibration (1,957 human paragraphs,
   wgl field): at least one antithesis in 3.3% of paragraphs, two or more in
   **0.2%**. The the manuscript drafts: two or more in 5.6% of paragraphs (28x the
   human base rate). Captured in `deai_structure` as auxiliary family
   `antithesis-cluster` (threshold: 2 per paragraph).
2. **Short reversal beats**: a setup followed by a reversal sentence of five
   words or fewer ("It would not." / "It does the opposite."). Human base rate:
   **0 of 1,957 paragraphs**. Two instances in the Phase A draft, both
   rewrite-introduced. Captured as auxiliary family `short-reversal`.
3. **Aphoristic "perform rigor" closers**: sentences engineered to sound
   quotable about the method's honesty ("has to earn every claim it makes",
   "runs conservative in the null direction it could cheat in"). No reliable
   lexical pattern exists; this class is documented here as a panel-advisory
   target and handled by targeted rewrite instruction, not a detector.

Auxiliary families emit ordinary advisories under `structure-auxiliary` and are
excluded from `template_score`, so the calibrated document-dispersion manifold
(which consumes `template_score` as a dispersion feature) is unchanged.

### 13.4 Detector-vs-panel cross-validation

The upgraded detector, re-run on all three versions (field profile wgl):

| Version | `structure-template` findings | `structure-auxiliary` findings |
|---|---|---|
| pristine v18 | 8 | 4 |
| Phase A | 0 | 6 (incl. 2 reversal beats) |
| Phase A2 | 0 | 1 |

The auxiliary axis now tracks exactly what the panel reported: Phase A traded
template findings for auxiliary density (including the two rewrite-introduced
reversal beats the panel quoted verbatim), and the A2 targeted revision cut
auxiliary findings 6 to 1 while the fidelity gate stayed PASS on all 8
protected token classes and the document stayed inside the human manifold band
(distance 4.392, conformal p 0.082). Antithesis instances counted by grep fell
23 to 12.

### 13.5 Limits

One document, one field, four judges per version, and judge agents share a
model family: the panel measures a strong-reader perception proxy, not human
referee behavior. The score scale is compressed at the low end (all versions
scored near 2), so the tell-turnover reading, not the score, carries the
signal. The aphoristic-closer class has no detector and relies on
rewrite-instruction coverage; residual instances survive in A2 (the intro
requirement cadence one judge still names).

## 14. Salience hierarchy and domain register (v0.26.0)

Date: 2026-08-16. Two axes added after a reader complaint no existing axis could
express: a draft that passes L0, sits inside the document manifold, and still
reads as an undifferentiated inventory of results written in a neighbouring
discipline's vocabulary. All measurements below use the `wgl` field profile.

### 14.1 The reduction defect that preceded both

The first prototype measured `recital_frac = 0.0` on an abstract carrying
`$500$`, `$14{,}850{,}000$`, `$62\%$`, `$0.98\%$`, `$34.6\%$`, `$\AUC=0.817$`
and five more quantities. `extract_style.latex_to_plain` — the shared front end
for every axis — replaces each math span with the token `[math]`, so **every
numeral in a LaTeX manuscript is destroyed before any detector sees it**. That
reduction is correct for the lexical and sentence-shape statistics it was
written for, and it makes any numeral-bearing signal identically zero on `.tex`
input. No earlier axis could have found this class of defect.

`latex_to_numeral_text` is a second named projection. It shares the same pattern
set and differs in one decision: numerals inside *inline* math survive.
Displayed equations are dropped by both, because their digits are the constants
of a definition — counting the 3 in a volume formula as a reported quantity made
every derivation paragraph read as a recital of measurements. The LaTeX
thousands form `14{,}850{,}000` collapses to one numeral rather than three.
`latex_to_plain` is untouched, so no existing calibration asset moves.

### 14.2 Salience reference and operating points

Calibrated per section bucket at one shared unit (a passage) on the reference
and measurement sides, from the field's own banks:

| Bucket | n (current) | v0.27.1 | 2026-08-17 | Sources |
|---|---:|---:|---:|---|
| abstract | **13,981** | 13,438 | 13,438 | `human_abstracts_extra.jsonl`, `exemplar_paragraphs.jsonl` |
| method | **6,959** | 130 | 1,303 | `exemplar_paragraphs.jsonl` |
| data | **3,016** | 102 | — | `exemplar_paragraphs.jsonl` — bucket added 2026-08-25 |
| intro | **3,264** | 94 | 88 | `exemplar_paragraphs.jsonl` |
| discussion | **2,958** | 93 | 78 | `exemplar_paragraphs.jsonl` |
| results | **3,206** | 26 | 10 | `exemplar_paragraphs.jsonl` — clears the floor by 85× |
| conclusion | **1,994** | 39 | 41 | `exemplar_paragraphs.jsonl` |

Counts are post-rebuild (2026-08-25), and `method` is the headline: **it was never a
1,303-passage reference.** `method` had no pattern of its own — it was
`DEFAULT_SECTION_BUCKET`, so it absorbed every heading the classifier could not name,
and 92% of it was residue. Three sources fed it, all measured: `.tex` corpus files
carrying no `\section` markup at all (one 100-page review, split into chunks,
contributed 101 and 88 paragraphs at 100% "method"); PDF table cells accepted as
headings by the ALL-CAPS heuristic (305 of 325 headings detected across the 90 corpus
PDFs were cells such as "S", "RA", "NFW", "A85", each one switching the bucket that
following prose was filed under); and data/observation sections with no bucket of their
own. Giving `method` explicit vocabulary, giving `data` its own bucket, defaulting to
`unknown`, and requiring an ALL-CAPS heading to carry ≥ 2 words, ≥ 4 letters and ≥ 75%
letters produces the left-hand column.

A second fix landed in the same rebuild and pulls the other way. `extract_pdf_text`
took pymupdf's `get_text("blocks")` to mean paragraphs; on real journal PDFs blocks
run to a median of 5–16 words and only 21–23% end a sentence, so roughly four in five
were mid-paragraph line fragments. Rejoining them produces real paragraphs — a corpus
PDF goes from 438 fragments (median 5 words) to 105 paragraphs (median 84), and
`document_shape` on it moves from `insufficient_evidence` to `measured` — but real
paragraphs are fewer than fragments, so every bucket loses some count.

**`results` therefore does not clear the floor.** It moved 10 → 31 on the classifier
fix alone and settled at **26** once paragraphs and headings were reconstructed
correctly. Intermediate values of 31 and 24 were recorded here while the PDF fixes were
landing; 26 is the number that survived all of them.

That 26 was then read as a corpus-size limit — `gather_corpus_files` ingested 31
documents, so growing `results` was said to need more papers. **That diagnosis was
wrong**, and the second round of 2026-08-25 fixes says why: the corpus layer treated a
*file* as a paper, and could only see the three curated tiers. The 500-paper
`fulltext-arxiv/` corpus that §9 has calibrated against since v0.26 was on the same
disk, gitignored, and invisible to every paragraph-level baseline. Reading it — with
`\include` fragments folded back into their documents rather than counted separately,
and `\subsection`s inheriting their `\section` — takes `results` to **2,541** and the
bank to 25,005. EVALUATION §2 records all four defects and their measured effect.

The bank therefore reads 1,942 → 593 → 25,005 across three rebuilds, and none of the
three counts the same thing: 1,942 was inflated by mislabelling and fragment-splitting,
593 was honest but blind to 94% of the available corpus, and 25,005 is the count of
correctly-paragraphed passages whose section is identifiable across everything on disk.
The `abstract` bucket moves only 13,438 → 13,823, because abstracts come from their own
bank and only the exemplar-side contribution grew.

Human abstract percentiles:

| Feature | p50 | p75 | p90 | p95 |
|---|---:|---:|---:|---:|
| `max_recital_run_frac` | 0.20 | 0.33 | 0.50 | 0.67 |
| `recital_frac` | 0.29 | 0.50 | 0.67 | 0.78 |
| `numerals_per_sentence` | 0.57 | 1.25 | 2.00 | 2.70 |

The gate is P(X ≤ x) > 0.90 for an advisory and > 0.95 for a strong one. Two
implementation facts are load-bearing:

- **Grid resolution.** Two of the three features are ratios of small integers,
  so the reference distributions are tie-heavy. On a 0.05 grid the plateau
  around 0.5 collapses onto one stored point, and a passage landing there reads
  as exactly p90 when its true P(X ≤ x) is 0.91 — the reading that suppressed
  the very case the axis was built for. The stored grid is 0.01.
- **Tie direction.** The percentile is read at the top of the plateau a value
  lands on. Reading the lower edge reports a passage as typical whenever its
  value happens to be a common one.

**Abstain rule.** Where every reference passage above the gate shares one value,
P(X ≤ x) reaches 1.0 there and an ordinary passage reads as the 100th
percentile. `resolves_above_gate` makes the affected feature decline to rank
rather than invent a finding; a 40-identical-passage reference is the regression
test.

### 14.3 Salience on the case document

`Letter/main.tex` (804 lines, read 2026-08-16) against the wgl reference:

| Passage | `max_recital_run` | `run_frac` (pct) | `recital_frac` (pct) | `num/sent` (pct) |
|---|---|---|---|---|
| abstract | 4 of 8 | 0.50 (p91) | 0.50 (p78) | 1.38 (p79) |
| grid definition (L137) | 2 of 5 | 0.40 (p90) | 0.60 (p91) | 8.20 (p100) |
| source model (L179) | 4 of 4 | 1.00 (p100) | 1.00 (p100) | 4.00 (p99) |
| detector block (L210) | 3 of 3 | 1.00 (p100) | 1.00 (p100) | 3.33 (p99) |
| twin fit (L541) | 5 of 6 | 0.83 (p98) | 0.83 (p97) | 1.67 (p95) |

Run length is the discriminating feature for the abstract (p91) while density is
unremarkable (p78/p79). That is the intended behaviour: a quantitative abstract
is supposed to carry numbers, and what separates this one from a human abstract
is that four of its eight sentences report quantities with nothing between them.

Method-section findings are numerous (15 of 19 strong) and are **expected
accepted dispositions, not false positives**: a parameter grid is specified by
enumeration, and the reference says only that this specification is denser than
90% of human method passages. The standard's disposition machinery, not a
tuned-down threshold, is the correct handling.

**Redundancy fix.** The first implementation emitted one finding per feature per
passage — 40 findings for this document, three of them describing one defect.
One finding per passage, led by its most extreme feature with the others carried
as observed evidence, gives 19.

### 14.4 Register reference and precision

Document frequency over **41,721** passages (27,917 exemplar paragraphs + 13,804
abstracts), **53,417** terms. Firing rule: ≥ 15 manuscript uses **and** corpus df
rate < 1e-4. (The use count was 5 until v0.32.0 raised it to 15, and this
paragraph still said 5 until the 2026-08-26 sweep caught it. §17 records the
held-out rates at the old setting; §18 records them at the new one.)

The composition bias recorded in §14.6 is largely resolved. Reading the 500-paper
breadth corpus took the body contribution from 593 to 25,005 passages and it now
stands at 27,917, so abstracts fell from **96% of the reference to 33%** (13,804
of 41,721). The axis was biased toward flagging body-section vocabulary precisely
because body text was almost absent from its reference; that reference is now
two-thirds body prose. The threshold's resolution also improves by 2.9×: 41,721
passages can express a df rate of 2.4e-5, comfortably below the 1e-4 firing rule,
where 14,235 could express 7.0e-5.

Controls that must not fire:

| Term | df | Judged on | Rate | Result |
|---|---:|---|---:|---|
| `accuracy` | 774 | itself | 5.0e-2 | not flagged |
| `epoch` | 402 | itself | 2.6e-2 | not flagged |
| `same-plane` | 536 | `plane` | 3.4e-2 | not flagged |
| `aperture-mass` | 313 | `aperture` | 2.0e-2 | not flagged |
| `training` | 155 | itself | 9.9e-3 | not flagged |
| `benchmark` | 81 | itself | 5.2e-3 | not flagged |
| `classifier` | 29 | itself | 1.9e-3 | not flagged |
| `held-out` | 24 | `held` | 1.5e-3 | not flagged |

`epoch` and `accuracy` are why the rule cannot be a curated list: both are
ordinary astronomy vocabulary (an observation time; plain English), and both
appear on any hand-written "machine-learning words" list.

Positives on the case document:

| Term | Manuscript uses | Corpus df | Rate |
|---|---:|---:|---:|
| `AUC` | 12 | 1 | 6.4e-5 |
| `logit` | 6 | 0 | 0 |
| `REDACTEDTERM` | 7 | 0 | 0 |

`REDACTEDTERM` is the concept the paper introduces, so its correct disposition
is the third the action offers (confirm the first occurrence carries a
definition) rather than replacement. The axis cannot distinguish an introduced
concept from a borrowed one and does not try to, which is why it emits
advisories only.

**Precision history.** The unguarded first implementation produced 48 findings on
this document, of which roughly six were real. Three construction classes
accounted for the rest, each handled structurally rather than by raising a
threshold:

- *Subscript decorations.* `\newcommand{\Kraw}{S_\mathrm{sad}}` yielded the fake
  terms `sad`, `det`, `nat`, `crit`, `ang`, `eff`, `sep`. Macro bodies are still
  read — a term bound to a macro is by construction repeated, and the shared
  reduction erases it, so 12 uses of `\AUC` leave no "AUC" in reduced prose — but
  a `\mathrm{}` preceded by `_` or `^` is a decoration, not a word.
- *Compounds.* Hyphenation is an open construction, so almost every compound is
  corpus-rare: `aperture-mass`, this field's core observable, appears in 8
  passages as a string. Judging a compound by its rarest part fixes it while
  keeping `cross-validation` foreign via `validation`.
- *Possessives.* `sub-halo's` and `campaign's` fold onto their bare terms.

After the fix: 3 findings, all substantive.

**Recall cost, stated.** `probit` (df 0) and `pooled` (df 0) are used 3 and 4
times, below the manuscript-use floor, and are not reported. The floor buys precision at
the price of terms used a handful of times; below it the corpus's own sampling
gaps dominate the comparison.

### 14.5 Rejected: hypotaxis ratio

The most direct-seeming formalisation of "flat prose" is a deficit of
subordinate structure — propositions strung at equal weight (parataxis) rather
than ranked by subordination and causal linkage (hypotaxis). It was prototyped
as subordinators and causal-inferential markers over subordinators plus
coordinators, measured on the same human reference (n = 7,869 abstracts under
the numeral-preserving reduction).

Human abstracts: p50 = 0.167, p75 = 0.286, p90 = 0.400. The case document's
abstract: **0.286, the 77th percentile** — above the human median, not below it.

The hypothesis is refuted for this document class. Flatness of emphasis is not a
shortage of subordinate clauses, and the recital-run measurement locates it
instead. The signal is not shipped; this subsection exists so it is not
re-proposed as an obvious gap.

### 14.6 Limits

One field, one case document. Every non-abstract bucket rests on 1,994–6,959
reference passages, so **all seven clear the 30-passage floor** and none is
rank-only. `abstract` (13,981) is still the largest by a factor of 2.0, but it no
longer dwarfs the body buckets by two orders of magnitude, and `method` is
second-largest on method prose rather than on residue. The counts are the
2026-08-26 author-query sweep's; §14.2's table carries the earlier rebuilds.

The reference-size limitation recorded here from v0.26 through v0.27.1 is therefore
closed. What remains is narrower and should not be read as the same caveat: register
document frequency still inherits the corpus's composition — 35% abstracts — so a term
common in body text but absent from abstracts is still slightly over-flagged, and the
manuscript-use floor still bounds recall. Neither axis has a human-judgement
validation set. Both are calibrated distance statements against a human reference, in
the same sense as every other L1/L2 axis here, and neither is an authorship claim.

---

## 15. Narrative salience: two more refuted features, and two reference nulls (v0.26.1)

Origin: a reader complaint that AI prose inflates a one-fact paragraph into
five clauses, and separately that it recites results without ever concluding
from them. Both are now policy in SCIPAPER_STANDARD §5.4 as a **writing rule**.
This section records why none of it is a measured axis.

### 15.1 Rejected: inert-clause runs and inference-connective rate

Every sentence was labelled on three tests: GROUNDED (a number, math, a
citation, or an explicit comparison — `deai_anchoring`'s anchor definition),
INFERENTIAL (a closed set of connective, deductive, and contrastive markers),
and INERT (neither). Two hypotheses followed: AI prose runs longer INERT
streaks, and AI prose carries fewer inference markers.

Both fail.

**Inert runs, length-matched to 60–240 words:**

| bank | inert rate | max inert run |
|---|---|---|
| human arXiv abstracts (n = 11,177) | 0.500 | 0.333 |
| human RAID reference (n = 764) | 0.778 | 0.500 |
| AI RAID generations (n = 527) | 0.889 | 0.636 |
| AI Claude generations (n = 551) | 0.667 | 0.500 |

The human span is [0.500, 0.778] and the AI span [0.667, 0.889]. They overlap,
and one AI bank sits *below* one human bank. Genre separates these banks;
authorship does not.

**Inference-connective rate — the two AI banks disagree in sign:**

| bank | median | p75 | p90 |
|---|---|---|---|
| human arXiv abstracts | 0.000 | 0.125 | 0.222 |
| AI RAID generations | 0.000 | 0.000 | 0.125 |
| AI Claude generations | 0.200 | 0.400 | 0.600 |

One AI bank uses inference markers less than humans, the other two to three
times more. A feature whose direction depends on the generator is not a
feature. The corollary matters for the writing rule: **the presence of a
connective is not evidence of an inference.** Machine prose supplies the causal
frame and leaves the antecedent unbound, which is why §5.4's diagnostic is a
pointer to the antecedent rather than a search for the connective.

A first pass measured the human inference rate as identically zero. That was an
artefact: the classifier assigned one label per sentence with GROUNDED taking
priority, which erased every human sentence that both reports and concludes —
the exact move under study. The table above uses independent flags.

This is the third refutation of a surface feature for this defect, after claim
anchoring (§9.6) and the hypotaxis ratio (§14.5). Three independent surface
statistics, one outcome: the defect is a relation between a clause and the
propositions around it, and surface statistics do not see relations.

### 15.2 Spine fraction: a lead, not a result

The replacement hypothesis is **spine fraction** — bound clauses over total
clauses, where a clause is bound if it introduces a checkable fact or binds two
propositions already in play. Because the instrument is an LLM judgement, the
pilot was blinded: 20 passages (10 per class) sampled at a fixed seed, clause
split on a fixed separator set, 152 clauses annotated from a label-free file,
and the key read only afterwards. The blind file's SHA-256 was recorded before
and after a replay that added sub-bank tracking, and matched.

| contrast | human | AI | AUC | exact permutation p |
|---|---|---|---|---|
| class-level (not domain-matched) | 10 | 10 | 0.875 | 0.0008 |
| arXiv human vs Claude astro generations | 9 | 5 | 0.756 | 0.032 |
| arXiv human vs RAID cross-domain | 9 | 5 | 0.989 | 0.0010 |

The near-perfect cross-domain figure is the genre confound again. The
domain-matched effect survives but is **not established**: at n = 9 vs 5 the
Hanley–McNeil interval on AUC 0.756 is [0.441, 1.071], which covers chance.
Closing it to a half-width of 0.086 needs 60 per class.

Two further facts shape the intended use. Ten of the twenty passages scored
exactly 1.000, **two of them AI** — a well-bound machine passage is
indistinguishable, so this cannot be a detector. But every passage below 0.833
was AI (0.714, 0.667, 0.571, 0.500) and no human fell below it, so the usable
form is a one-sided low-tail quality band, which is what §5.4 asks for.

The dominant risk was annotator contamination: the annotator was blind to the
label but can often infer it from style. That risk was then measured, and it
is what killed the statistic.

### 15.2b Refuted: the adversarial pass removes the domain-matched effect entirely

Every clause the first annotator called unbound was handed to a second
annotator, blind to the class and to every other file in the study, whose task
was to *find* an antecedent. Opposite incentives make the overturn rate a
contamination measure, and the protocol pre-registered failure above 30%.

**9 of 20 challenged clauses were overturned, a rate of 0.450.**

| contrast | AUC before | AUC after | p after |
|---|---|---|---|
| class-level (not domain-matched) | 0.875 | 0.750 | 0.016 |
| arXiv human vs Claude astro (matched) | 0.756 | **0.500** | **1.000** |
| arXiv human vs RAID (cross-domain) | 0.989 | 1.000 | 0.0005 |

After correction all five Claude-generated astronomy passages score exactly
1.000, identical to all nine human arXiv passages, so the domain-matched
contrast is exactly chance. Every one of the eleven clauses whose unbound
verdict survived refutation lies in the cross-domain RAID bank; **not one
domain-matched generated passage contained a clause without an antecedent.**
The residual class-level separation is the genre confound in isolation.

The overturns are diagnostic of the contamination rather than of careless
annotation. Six of the nine fell on the Claude astronomy passages, and the
refuter's antecedents were exact: "We are convinced that polarimetric mapping
of this kind will become indispensable" and "This near-criticality is a
profound clue" were marked unbound because they *read* as machine prose, while
their demonstratives point at named earlier propositions. The first annotator's
authorship instinct, not the binding rule, produced those verdicts.

**Spine fraction is therefore refuted as a discriminator at pilot scale**, on
its own pre-registered condition, and no tool is built. The finding vindicates
the shipping decision rather than undermining it: SCIPAPER_STANDARD §5.4 ships
as a writing rule that explicitly forbids building a threshold on this signal,
and the evidence now says that restraint was correct. What survives is the
refuter's own dividing line, which is a **writing** distinction and not a
detection one: a demonstrative pointing at a single earlier proposition is a
real antecedent, whereas a generic self-reference ("our results", "this
paper") predicated on an unfalsifiable relevance claim is not.

Two limits stand. n is 20 passages and one annotator pair, so the refutation is
as small as the effect it refutes. And the second annotator is the same model
family as the first, so a shared blind spot would not show up as disagreement;
the overturn rate bounds contamination from below, not from above.

### 15.3 Corpus provenance: the pre-LLM guarantee was weaker than stated

`--date-hi` filters arXiv's `submittedDate`, which dates v1. The API's
`summary` is always the **latest** version's abstract. 6,552 of the 13,642
records in `human_abstracts_extra` (48.0%) are non-v1, and a live probe of
twelve 2021 weak-lensing submissions found eleven with `updated > published`,
two of them revised after 2022-11 — after the text could have been touched by a
public LLM. Submission date does not date the text.

`fetch_arxiv_abstracts` now records `published` and `updated` and accepts
`--updated-before`; a record with no `updated` is dropped rather than assumed
clean. The existing bank predates the field, so its text vintage is unknown
rather than clean, and re-deriving it needs a refetch.

### 15.4 Null: a subfield reference does not move the salience gate

A weak-lensing top-tier bank was built to test whether §14.2's astro-ph-wide
reference is the wrong population for a weak-lensing manuscript: 254 abstracts
(A&A 171, ApJ 75, ApJL 8), submitted 2010-01-05 to 2021-12-14, every latest
version dated on or before 2022-09-12.

| feature | broad p90 | WL p90 | broad median | WL median |
|---|---|---|---|---|
| `max_recital_run_frac` | 0.500 | 0.500 | 0.200 | 0.200 |
| `recital_frac` | 0.667 | 0.667 | 0.286 | 0.333 |
| `numerals_per_sentence` | 2.000 | 2.200 | 0.571 | 0.667 |

The case document's abstract reads p = 0.91 against either reference, and its
revision p = 0.26 versus 0.23. `salience_baseline.json` needs no rebuild and
§14.3's percentile is not an artefact of the reference population.

This does not contradict the genre effect in §15.1 and §15.2. Genre separates
at the **discipline** level — astronomy against news, reviews, and recipes —
not between astro-ph subfields.

### 15.5 The same bank cannot be the register reference

`deai_register` calls a term foreign below a document-frequency rate of 1e-4.
A 254-document corpus cannot express a non-zero rate below 1/254 = 3.94e-3,
**39.4× coarser than the threshold**; a single occurrence lands at the
threshold only at about 10,000 documents.

The consequence is not hypothetical. Under the subfield reference `saddle` —
the central concept of the case document — flips from native (16/13,642) to
foreign (0/254), as do `classifier`, `recall`, and `ablation`, all on zero
counts rather than on any property of the field's vocabulary. There are not
10,000 weak-lensing ApJ/ApJL/A&A papers in the window, so the register
reference stays on the broad bank as a hard constraint. The subfield bank is
stored and wired to nothing.

The v0.26.0 register finding is unaffected and reproduces under both
references: `AUC` is 1/13,642 in the broad bank and 0/254 in the subfield bank,
while `epoch` (0.024) and `accuracy` (0.057) are native in both.

### 15.6 Limits

The refutations in §15.1 come from a regex classifier written for the purpose,
so they are weaker evidence than a null from a tuned instrument would be — but
the disagreement in sign between two AI banks is robust to instrument quality
in a way a null is not. §15.2 rests on one annotator, 20 passages, and one
field. §15.4's WL reference is 53× smaller than the broad one, so its p90 is
the noisier of the two; the medians agree as well, which is why the null is
read as distributional agreement rather than a single-quantile coincidence.
`--updated-before` systematically excludes late-revised papers, a selection
effect on the reference that is not quantified. Only the salience and register
axes were compared across references; `docstructure` and `voice` were not.
