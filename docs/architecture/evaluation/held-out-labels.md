# EVALUATION — Held-out papers as labels · `sci-paper` v0.32.0 and v0.34.0

Part of the evaluation record. The hub — evaluation contract, current
axis status, repository verification, release evidence boundary, and the
map of every section — is [`EVALUATION.md`](../EVALUATION.md); read it
first. Section numbers are global across the whole record, so a reference
like "§9.5" means the same thing in every file.

Normative policy lives in [`SCIPAPER_STANDARD.md`](../../SCIPAPER_STANDARD.md);
nothing here can redefine it. All machine-readable findings use the
`sci-paper.feedback.v1` contract.

§17 was split out of
[`narrative-salience-register.md`](narrative-salience-register.md) on 2026-08-27
when that file passed the repository's 750-line budget; its content is unchanged,
only its home is. §21 was written here afterwards, because it is about the same
thing: which papers are held out, and what it costs when one quietly is not.

---

## 17. Held-out refereed papers as labels: register and salience measured (v0.30.0, corrected v0.31.0, superseded by §18)

> **Read §18 for the current register numbers.** Every register figure below was
> measured at `MIN_MANUSCRIPT_USES = 5`; v0.32.0 raised it to 15, which cut the
> held-out findings from 887 to 198 and the rate from 0.3842 to 0.0858 per 1,000
> words. §18's table carries the pairs. The section is kept because the reasoning
> — why provenance is a label, why held-out had to be enforced, what the paired
> leakage measurement controls for — is unchanged by the threshold.

Both axes had stood at "precision `unmeasured`, pending hand labels" since
v0.26.0. Half of that gap never needed a labeller. A refereed ApJ/ApJL/A&A
paper is text human authors wrote and human referees accepted, so its
provenance is already a label for the question *does this axis fire on prose
the field has accepted?* `tools/eval_findings.py` is the bound evidence path;
this section is its output, not a quotation of it.

### 17.1 The held-out set, and why "held out" had to be enforced

`register_lexicon.json` and `salience_baseline.json` are both built from
`exemplar_paragraphs.jsonl` (curated tiers plus the `fulltext-arxiv/` breadth
pull) and `human_abstracts_extra.jsonl`. Measuring on any paper reachable from
those is measuring in-sample, and at this scale that is not a technicality:
`RARE_DF_RATE` is 1e-4, so on 41,593 passages the foreign-term threshold sits
at **4.16 passages** — a single paper's own paragraphs can carry its own
vocabulary over the line.

200 papers were fetched with `fetch_arxiv_abstracts.py --fulltext
--exclude-known --fulltext-dir fulltext-heldout --journals apj,apjl,aa`, which
disqualifies every arXiv id reachable from the three banks (13,653 ids) and
keeps only records whose `journal_ref` classifies as ApJ, ApJL or A&A.
Verified independently of the fetcher's own filter: **0 overlap** with
`human_abstracts_extra.jsonl`, **0** with the 516 distinct
`exemplar_paragraphs.jsonl` sources, **0** with `fulltext-arxiv/`. A random
sample of 8 re-queried against the arXiv API returned 8 refereed
`journal_ref`s, published 2013–2017 — all pre-LLM.

> **⚠️ Correction (2026-08-27).** That verification was true when it was run and
> is not a standing property. `--exclude-known` is full-text mode only; the
> abstract sweep selects by `--query-set` and has no way to exclude, so a later
> sweep re-collected **5** of these 200 papers' abstracts — `1406.6152v2`,
> `1412.7521v2`, `1512.04555v1`, `1606.04321v1`, `1608.08629v2`. The overlap was
> 0 at build time, grew silently, and nothing was watching. All 5 were removed on
> 2026-08-27 (§21), and `test_eval_findings.AbstractBankIsNotAHeldOutLeakTest`
> now fails if any held-out paper's abstract is in the bank. **The §18.4 register
> figures are unaffected and reproduce exactly** — see §21.3.

A first sweep returned **zero** candidates: 5,618 unique results, all already
calibrated. Results come back newest-first, so an existing corpus occupies a
contiguous shallow band; on `cat:astro-ph.CO AND abs:cluster`, offsets 0–2000
were 100% known and 2000+ were ~85% new. `--start-at` exists because of that
measurement.

### 17.2 Results

| population | n | med words | reg flag | reg /1k w | sal flag | sal /1k w |
|---|---:|---:|---:|---:|---:|---:|
| published-heldout | 203 | 9,793 | **0.872** | **0.384** | 0.966 | **1.165** |
| published-insample | 544 | 10,372 | 0.717 | 0.214 | 0.914 | 1.053 |
| machine:ai | 20 | 1,266 | 0.000 | 0.000 | 1.000 | 3.227 |
| machine:ai_natural | 40 | 1,784 | 0.050 | 0.028 | 1.000 | 2.902 |
| machine:ai_deai | 20 | 1,730 | 0.050 | 0.030 | 1.000 | 3.443 |
| machine:ai_adversarial | 40 | 1,601 | 0.100 | 0.061 | 0.975 | 1.793 |
| machine:ai_skeleton | 24 | 5,641 | 0.500 | 0.102 | 0.958 | 1.508 |
| machine:ai_long | 29 | 11,114 | 0.793 | 0.118 | 1.000 | 1.520 |
| machine:ALL | 173 | 1,788 | 0.243 | 0.092 | 0.988 | 1.842 |

Rank AUC, machine over held-out published: **register 0.148**,
**salience 0.770**.

### 17.3 The two published rows are NOT a leakage estimate

They are era-disjoint. The shipped breadth pull is 2020–2021 (median 2021);
the held-out sweep reaches deeper in the newest-first order and lands on
2012–2018 (median 2016), with no overlap. Reading the 0.384 → 0.214 gap as
in-sample optimism would attribute six years of vocabulary drift to
calibration leakage.

The leakage measurement is paired instead, on one population and one era, with
membership the only thing that differs. `deai_register` calls a term foreign
below a document-frequency *rate*, so adding a paper to the bank moves both
sides of that ratio by a computable amount and no rebuild is needed. Of
**887** flags raised on held-out papers, **86.3% would be suppressed** by the
paper's own bank membership.

The paired design does not correct for the era difference; it removes it, and
that is why it is the one reported. `eval_findings.py` states
`populations_are_era_comparable: false` in its own output so the cross-population
contrast cannot be quoted as leakage by a later reader.

### 17.4 Register: a false-positive rate, now measured

On refereed papers the axis never saw, register fires on **87.2% of documents
at 0.384 findings per 1,000 words** — about four advisories on a median
9,793-word paper. Its rank AUC against machine text is **0.148**: it fires
*more* on human papers than on AI drafts, which is coherent rather than
surprising, because generated prose reuses common field vocabulary while real
papers introduce terms that are genuinely rare in any 41k-passage bank.

The mechanism is the operating point, not the implementation. A term is
flagged at ≥ 5 manuscript uses and < 4.16 corpus passages; a paper introducing
a method routinely satisfies both. This is an upper bound on the
false-positive rate *for advice purposes* — publication does not mean every
sentence is beyond improvement — but it is the rate at which a reader of a
finished paper will meet the advisory, and it is high. The axis stays
`advisory`, which is the consequence class this behaviour warrants; what it
does not yet have is an operating point derived against a held-out target
rate. That open item was closed in [§18.4](projection-and-operating-point.md)
by refuting its premise: rank AUC stays below 0.5 at every setting, so no
operating point makes this a detector.

> **⚠️ Superseded (v0.32.0).** Every register figure in §17.2–17.4 was
> re-measured in [§18.4](projection-and-operating-point.md): **0.0858** per
> 1,000 words on **44.83%** of documents, AUC **0.2856**, leakage **94.44% of
> 198**. Two changes, both in that release — the citation projection stopped
> leaking bibliography keys into prose (§18.1), and `MIN_MANUSCRIPT_USES` moved
> 5 → 15 once the sweep showed rank AUC below 0.5 at every setting. The salience
> figures below also moved slightly, because removing 7.00% of the digits the
> numeral projection carried (§18.2) shifted both the reference and the measured
> side. Read §18 for current values; this section is kept for its method and its
> history.
>
> **⚠️ Correction (2026-08-27, v0.31.0).** The figures above replace those
> v0.30.0 published — **0.991** per 1,000 words on **93.6%** of documents, AUC
> 0.080, leakage 72.7% of 2,287. Those were measured with a projection defect:
> `manuscript_terms` read the whole raw file while the corpus df was built from
> body prose only, so front matter and bibliographies were compared against a
> reference that had excluded them. **58.7%** of the findings came from outside
> body prose (27.5% preamble, 26.3% bibliography, 4.1% TeX control words, 0.9%
> `skip` sections). No threshold changed; the projection did. Salience was
> unaffected and reproduces byte-for-byte — 0 of its 1,077 findings on these
> papers fall in a bibliography.

**Guarded since v0.30.1.** §15.5 derived that a bank of n passages cannot express
a rate below 1/n, so under 10,000 passages this gate collapses to "df == 0". That
rejected a subfield bank but never became a guard, and the shipped `wgl-letter`
profile — **706** passages, **14.2× coarser** — reported `measured` with `reason:
null`. It now reports `degraded`, and its findings carry `measurement_status:
degraded` rather than being silenced. `wgl` (2.4e-5) is unaffected. Since
v0.32.0 such a profile also borrows its field's bank rather than only declaring
itself coarse ([§18.5](projection-and-operating-point.md)).

### 17.5 Salience: calibration transferred exactly — on the paragraphs it measured

`ADVISORY_PERCENTILE` is 0.90 over three features, and `salience_findings`
emits one finding per over-recital passage led by its most extreme feature. If
the three gates were independent, the per-passage rate would be
1 − 0.9³ = **0.2710**. Measured on the held-out set: **2,690 findings over
9,946 eligible passages = 0.2705**.

Agreement to three decimals on papers the baseline never saw read as the
strongest calibration-transfer evidence in this record, and as evidence that
the three features are close to independent out of sample. The 0.966 document
flag rate carries no defect signal: at 0.27 per passage, a paper with ~49
eligible passages flags with probability ~1 by construction. Density is the
statistic; document flag rate is not. Leakage is small here too — 1.165 vs
1.053 per 1,000 words, a factor of 1.11 against register's 3.7 — and the axis
discriminated machine text at AUC **0.770**.

**Re-taken under v0.36.2 (2026-09-04).** The manuscript side had bucketed
every subsection whose title matched no bucket as `unknown` and measured
nothing under it — 344 of the 540 paragraphs of one Planck parameters paper —
while the corpus side had always let a subsection inherit its parent. With
both sides inheriting, the same 203 papers give **4,473 findings over 9,849
scorable paragraphs = 0.4542** per passage (2,753 over 9,918 under the old
bucketing in the same process), and the rank AUC against machine text on
body-word density is **0.572** (the 0.770 also carried a raw-source
denominator, bibliography and preamble included, that diluted the refereed
side only). The gate transfers at the design rate on the paragraphs the old
projection kept and fires at 1.7× it on the ones it dropped; the reference
banks were bucketed the same way, so the excess is in the held-out prose or in
how the banks sample it, not in a projection seam, and it is an open item.

### 17.6 Limits

The register figure is an upper bound on advice-quality false positives, not a
precision figure; whether an individual advisory is *good advice* still needs a
human, and `label_findings.py` remains the path to it. Recall is unmeasured for
both axes and provenance labels cannot supply it. The held-out set is one field,
one journal family, 2012–2018, and the fetch stopped at the `--max-papers 200`
cap rather than at exhaustion, so 203 is not a power calculation. `machine:ai`
tiers are short (median 1,266–1,788 words) against 9,793, so every
machine-vs-human AUC inherits the length asymmetry of §9. The paired leakage
test adds only the paper's own passages, so 86.3% is a lower bound.

---

## 21. A second held-out population, and the leak that had reopened (2026-08-27)

§17's label is *the field accepted this*: 203 refereed ApJ/ApJL/A&A papers. A
second provenance label was available and says something different — papers by
one author, the user's advisor, whose prose is the imitation target rather than
a sample of the field. If register and salience behave the same way on both,
neither result is a property of how one population was sampled.

**22 papers**, `astro-ph/9608043` through `1511.02891` — 1996 to 2015, so the
whole population predates any LLM. Fetched with
`--author "au:\"Dell'Antonio\" AND cat:astro-ph*" --author-is "Dell'Antonio"
--max-authors 8 --exclude-known --date-lo 199101010000`. That clears
`MIN_DOCUMENTS = 20` with a margin of 2; below it `eval_findings.py` reports
`unmeasured` rather than a rate.

### 21.1 Building the population turned up two silent corpus bugs

LaTeX permits whitespace between a control word and its argument, so
`\section {Title}` is legal. Two regexes required the brace to follow
immediately, and both were wrong in the same way:

- `fetch_arxiv_abstracts._SECTION_RE` decides whether an e-print is structured
  enough to keep. `0707.0484` writes **7 of its 8** headers with a space and was
  being discarded as unstructured prose.
- `extract_sections.RE_SECTION` splits a paper into buckets. **9 of 790**
  downloaded papers use the spaced form — **0 of them exclusively**, which is
  why calibration was partially rather than wholly mis-split, and why nothing
  downstream ever looked broken.

Rebuilding the profile after the fix changed **5 of 27** artifacts. The exemplar
bank held at **27,917** paragraphs and **0** changed bucket, so the total says
nothing; the per-item diff is where the fix is visible. In `2105.12993v1` a
paragraph's body had begun with the literal words `Lensing amplitude anomaly` —
an unrecognised heading glued to the text under it — and now starts clean. One
paragraph boundary moved in a tier-2 paper, renumbering 24 ids in that file.
`sentence_stats.method` went n 2,205 → 2,204 and mean 23.72 → 23.73;
`lexicon.total_tokens` 228,187 → 228,180. Every LLM-typical word's raw count is
identical — only the per-1k denominators moved, in the seventh decimal.

### 21.2 Six of the 22 were not actually held out — and neither were five of §17's

`register_lexicon.json`, `salience_baseline.json` and `cohesion_baseline.json`
are each counted over `human_abstracts_extra.jsonl` as well as the exemplar
bank, and at `RARE_DF_RATE = 1e-4` the foreign-term threshold sits near four
passages, so one paper's own abstract can suppress its own flags. Sweeping every
`fulltext-*` directory except the calibration breadth pull found **11** such
records, not the 6 the mentor set was checked for:

| pull | papers | abstracts in the calibration bank |
|---|---:|---:|
| `fulltext-mentor` | 22 | **6** |
| `fulltext-heldout` | 203 | **5** |
| `fulltext-authoritative` | 75 | 0 |

The mechanism is one-directional and was never guarded. `--exclude-known` is
full-text mode only; the abstract sweep selects by `--query-set` and cannot
exclude, so any sweep run after a held-out pull re-collects what that pull held
out. §17.1's independently verified "0 overlap" was true on the day and had been
false since. All 11 records were removed (**13,804 → 13,793**) and the three
baselines recalibrated: register **41,721 → 41,710** passages and
**53,417 → 53,414** terms, salience `abstract` **13,981 → 13,971**, cohesion
`abstract` **13,977 → 13,967**, hedging `abstract` **10,413 → 10,404**.
`AbstractBankIsNotAHeldOutLeakTest` now fails on any recurrence, naming the
paper and the pull it belongs to; it was verified by reinstating one removed
record and watching it fail.

### 21.3 What the leak was worth

| | mentor, leaked | mentor, clean | §17 held-out, before | after |
|---|---:|---:|---:|---:|
| n | 22 | 22 | 203 | 203 |
| register documents flagged | 0.318 | **0.364** | 0.4483 | **0.4483** |
| register per 1,000 words | 0.047 | **0.059** | 0.0858 | **0.0858** |
| salience documents flagged | 0.955 | 0.955 | 0.966 | 0.966 |
| paired leakage suppressed | 0.875 of 8 | **0.900 of 10** | 0.944 of 198 | 0.944 of 198 |

On the mentor set the removal did exactly what the mechanism predicts: two more
papers flag once their own vocabulary leaves their own denominator. On §17's
population it changed nothing at three decimals — 11 records are 0.026% of
41,721 passages and none of the five crossed the threshold. **Every figure
published in §18.4 reproduces after the removal**, which is the useful half of a
null result: the leak was real, it was worth measuring, and it was not load-
bearing for anything already published.

### 21.4 Register is not a detector — replicated on an independent population

Rank AUC of machine text over the advisor's own papers is **0.328** for
`L0.register` and **0.635** for `L2.salience_hierarchy`. The register figure is
below 0.5 on a population §18.4 never touched, sampled by author rather than by
journal, spanning 1996–2015 rather than 2012–2018. §18.4 refuted the operating
point by showing AUC stays under 0.5 at every setting on one population; this is
that refutation reproducing on another. The axis fires *more* on real papers
than on generated prose, and a second population does not rescue it.

Salience transferred: its 0.9 gate landed at **0.2781** of passages over 996
measured, against **0.2710** expected from three independent gates — the same
agreement §17 recorded, on papers from a different two decades — and moves the
same way §17.5 does once subsections inherit their parent bucket (v0.36.2):
**0.3984** over 1,014 scorable paragraphs, 404 findings on the 22 papers.

**What this does not establish.** One field, one advisor, 22 papers. The
population is small enough that one paper is 4.5 percentage points of the
register rate, and the two populations share a corpus and a calibration, so
they are not independent evidence about the *corpus* — only about the sampling.
