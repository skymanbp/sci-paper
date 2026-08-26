# EVALUATION — Held-out refereed papers as labels · `sci-paper` v0.31.0

Part of the evaluation record. The hub — evaluation contract, current
axis status, repository verification, release evidence boundary, and the
map of every section — is [`EVALUATION.md`](../EVALUATION.md); read it
first. Section numbers are global across the whole record, so a reference
like "§9.5" means the same thing in every file.

Normative policy lives in [`SCIPAPER_STANDARD.md`](../../SCIPAPER_STANDARD.md);
nothing here can redefine it. All machine-readable findings use the
`sci-paper.feedback.v1` contract.

Split out of [`narrative-salience-register.md`](narrative-salience-register.md)
on 2026-08-27 when that file passed the repository's 750-line budget. The
sections it holds are unchanged; only their home is.

---

## 17. Held-out refereed papers as labels: register and salience measured (v0.30.0, corrected v0.31.0)

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
rate. That is now a concrete open item with a number attached, replacing the
vague one it closes.

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
degraded` rather than being silenced. `wgl` (2.4e-5) is unaffected.

### 17.5 Salience: calibration transfers, essentially exactly

`ADVISORY_PERCENTILE` is 0.90 over three features, and `salience_findings`
emits one finding per over-recital passage led by its most extreme feature. If
the three gates were independent, the per-passage rate would be
1 − 0.9³ = **0.2710**. Measured on the held-out set: **2,690 findings over
9,946 eligible passages = 0.2705**.

Agreement to three decimals on papers the baseline never saw is the strongest
calibration-transfer evidence in this record, and it also implies the three
features are close to independent out of sample. The 0.966 document flag rate
carries no defect signal: at 0.27 per passage, a paper with ~49 eligible
passages flags with probability ~1 by construction. Density is the statistic;
document flag rate is not. Leakage is small here too — 1.165 vs 1.053 per
1,000 words, a factor of 1.11 against register's 3.7 — and the axis
discriminates machine text at AUC **0.770**.

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
