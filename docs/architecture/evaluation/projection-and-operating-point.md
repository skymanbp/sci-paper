# EVALUATION — Projection symmetry, the register operating point, citation placement · `sci-paper` v0.32.0

Part of the evaluation record. The hub — evaluation contract, current
axis status, repository verification, release evidence boundary, and the
map of every section — is [`EVALUATION.md`](../EVALUATION.md); read it
first. Section numbers are global across the whole record, so a reference
like "§9.5" means the same thing in every file.

Normative policy lives in [`SCIPAPER_STANDARD.md`](../../SCIPAPER_STANDARD.md);
nothing here can redefine it. All machine-readable findings use the
`sci-paper.feedback.v1` contract.

Section 17 ([`held-out-labels.md`](held-out-labels.md)) measured two axes
against 203 held-out refereed papers. This section is what auditing that
measurement found: two more places where the calibration side and the
detection side were not reading the same text, an operating point that could
finally be derived rather than estimated, and one deferred axis that the fixes
unblocked. Auditing the release that shipped those fixes then found a fourth
thing, one layer up: nothing had ever been able to check whether a *published*
figure still matched the artifact it was read from (§18.8).

---

## 18. Projection symmetry, the register operating point, and citation placement (v0.32.0)

### 18.1 A four-name allowlist against 46 citation commands

`RE_TEX_CITE` matched `cite|citep|citet|citealt` and required the brace group
to follow the command name directly. A survey of every `\…cite…{` shape in the
corpus found **46 distinct command names over 75,566 uses**. Four were covered,
and none of those four when carrying natbib's optional argument.

An unmatched citation command reaches `RE_TEX_SIMPLE_CMD`, whose job is to
replace `\cmd{arg}` with `arg`. So the bibliography key became a word:

| form | before | after |
|---|---|---|
| `\citep{Smith2020}` | `[CITE]` | `[CITE]` |
| `\citep[e.g.][]{Smith2020}` | `[]Smith2020` | `[CITE]` |
| `\citealp{Smith2020}` | `Smith2020` | `[CITE]` |
| `\citeauthor` / `\citeyear` / `\citeyearpar` / `\citenum` | `Smith2020` | `[CITE]` |
| `\nocite{…}`, `\defcitealias{…}{…}`, `\setcitestyle{…}` | key or option text | *(nothing)* |
| `\citetext{DES Collaboration \citeyear{x}}` | key | `DES Collaboration [CITE]` |

Leaking occurrences in the corpus: **8,835 across 565 of 1,490 `.tex` files** —
8,100 optional-argument forms, 357 `\citealp`, 173 `\citeyear`, 135
`\citeauthor`, 60 `\citenum`, 10 `\citeyearpar`.

The replacement matches **by shape, not by name**: any command whose name
carries `cite`, with any number of optional arguments, followed by a brace
group. A name allowlist is the wrong instrument here — the tail is per-paper
local macros (`\citeg`, `\citejap`, `\citeiac`, `\putcite`, one paper each),
and the next paper's macro is in no list writable today. Three behaviours are
separated because three exist: a citation renders a mark, a declaration renders
nothing, and `\citetext` wraps prose the author wrote.

Verification is exhaustive rather than sampled: 46 command names × 5 written
forms × both projections. Every combination reduces without exposing the key,
except `\citetext`, whose argument is prose by definition.

### 18.2 Seven per cent of the digits the salience axis read were citation years

`latex_to_numeral_text` is the projection that keeps numerals so
`deai_salience` can measure how a passage distributes its reported quantities.
It shares its pattern set with `latex_to_plain` by design, so it inherited the
same defect — and a bibliography key ends in a **year**.

Old and new projection, run over the same 203 held-out papers:

| | before | after | change |
|---|---:|---:|---:|
| digits in the numeral projection | 396,814 | 369,056 | **−27,758 (−7.00%)** |
| bibkey-shaped tokens | 4,264 | 1,357 | −2,907 |

So one in every fourteen "quantities" the salience axis was reading on real
LaTeX was the year in `\citealp{Bethermin2012}`. This is a correctness fix to a
**shipped, `measured`** axis, and it is larger in relative terms than the
register effect that led to it.

The 1,357 that remain sit in bibliography entries, which this projection does
not strip. They produce no findings: **0 of 2,759** salience findings on these
papers start on a bibliography line — the same control §17.4 ran, re-run rather
than assumed.

### 18.3 The held-out set could be collected as calibration input

`corpus_documents` walks a directory with `rglob` and filters nothing.
`deai_anchoring --calibrate` and `deai_docstructure --calibrate` both take a
`--corpus-dir`, and the documented invocation points at the field root.

| `--corpus-dir` | documents collected |
|---|---:|
| `style-corpus/wgl` (before) | **717** |
| `style-corpus/wgl` (after) | 517 |
| `style-corpus/wgl/fulltext-arxiv` | 500 |
| `style-corpus/wgl/fulltext-heldout` | 200 |

The shipped anchoring baseline was built from 517 documents, before the
held-out set existed. Re-running the same documented command today would have
absorbed all 200 evaluation papers into the baseline being calibrated — no
error, no warning, and nothing in the output but a document count nobody was
checking.

`tests/test_eval_findings.py` already pinned the held-out contract, but it
pinned `extract_style`'s source tuple. This path never consults that tuple; it
walks whatever it is handed. The guard therefore belongs in `corpus_documents`,
where every caller inherits it, and not in the two CLIs that happen to be the
callers today. Asking for the held-out directory *by name* still works, because
that is deliberate and is how the evaluator reaches its own population.

### 18.4 The register operating point, derived rather than estimated

`MIN_MANUSCRIPT_USES = 5` was an estimate: "five uses is where a term is
load-bearing". With 203 refereed papers the calibration never saw, the
false-positive rate at any candidate setting is measurable. Swept against those
papers and 173 machine documents:

| uses | human /1k words | human docs flagged | machine /1k words | machine docs | **rank AUC** |
|---:|---:|---:|---:|---:|---:|
| 5 | 0.4265 | 85.2% | 0.0632 | 24.3% | 0.154 |
| 8 | 0.2329 | 67.5% | 0.0163 | 10.4% | 0.195 |
| 10 | 0.1769 | 60.1% | 0.0146 | 9.8% | 0.235 |
| **15** | **0.0848** | **44.8%** | **0.0024** | **2.3%** | **0.285** |
| 20 | 0.0539 | 32.5% | 0.0013 | 1.7% | 0.344 |
| 30 | 0.0322 | 26.6% | 0.0004 | 0.6% | 0.369 |
| 50 | 0.0117 | 12.3% | 0.0000 | 0.0% | 0.438 |

(Rates here use `body_only` word counts, so they sit above the headline figure
below, which uses the evaluator's own denominator. Columns are internally
comparable; the level is not comparable across the two.)

**The AUC column is the result.** It is below 0.5 at every setting: the axis
fires more on refereed prose than on machine prose *everywhere on the curve*,
and tightening the knob silences the machine side faster than the human one —
at 50 uses machine text is flagged exactly never. There is no operating point
at which this becomes a detector, so the roadmap item "re-derive the operating
point" is answered by refuting its premise. What the knob buys is advisory
volume.

The point was cut at **15**, the first setting where a paper already good
enough to referee is *not* flagged more often than not. Published effect,
combined with §18.1 (both changes are in this release):

| | v0.31.0 | v0.32.0 |
|---|---:|---:|
| held-out register findings | 887 | **198** |
| held-out register per 1,000 words | 0.3842 | **0.0858** |
| held-out documents flagged | 87.19% | **44.83%** |
| in-sample register per 1,000 words | 0.2141 | 0.0289 |
| rank AUC vs machine text | 0.1479 | **0.2856** |
| paired leakage suppressed (§17.3) | 86.25% of 887 | **94.44% of 198** |
| every salience figure | | *gates unchanged* |

The sweep and the evaluator are separate programs; they agree to four decimal
places on the flag rate at the chosen point (0.4483). Of the 198 flags that
remain, 11 survive the paper's own bank membership.

### 18.5 A format variant is not a domain

`wgl-letter` reported `degraded` since v0.30.1: 706 passages cannot express the
1e-4 gate, so the rule in force was `df == 0`. The obvious repair — enlarge the
bank — is impractical and, more importantly, wrong.

Impractical: ApJL is **24 papers in 5,364 arXiv records** on these queries
(0.45%), so 10,000 passages needs roughly 90,000 records fetched at the 3-second
rate guidance.

Wrong: the register axis measures *domain* vocabulary, and a letter is a
**format**. A letter and a full paper in one field share their words; they
differ in length and structure, which `deai_salience` and `deai_docstructure`
measure against the letter profile's own baselines. Running the same 36
letter-format documents against both banks:

| | findings |
|---|---:|
| agreed by both banks | 53 |
| **only the 706-passage letter bank** | **262** |
| only the 41,559-passage field bank | 2 |

The 262 are core cosmology: `sne`, `bao`, `pantheon`, `quasars`, `posteriors`,
`likelihoods`, `desy` — and `letter`, which appears in a letter because it is
one. That is §15.5's prediction reproduced exactly: below the gate's
resolution, "rare" means "absent from this small bank".

So a `<field>-<variant>` profile whose own bank cannot resolve the gate now
judges against `<field>`, and the borrowed bank is named in the axis status and
in every finding's `reference.borrowed_from` rather than applied silently. The
two the field bank alone flags are `dell'antonio` (a surname reaching prose
from a curated tier) and `cirsi` (an instrument).

The letter corpus did grow — 706 → **1,574 passages** from the 24 ApJL sources
— which still resolves 6.4× coarser than the gate, so the fallback stays
active. It improves the salience and structure baselines, which are per-format
and correctly its own.

### 18.6 Citation placement: unblocked, measured, not shipped

Rank 6 of the de-AI frontier listed citation placement as blocked on this
projection fix. It is now measurable, and it separates — but most of the naive
separation is genre.

| comparison | human | machine | AUC |
|---|---:|---:|---:|
| whole documents, cited-sentence fraction | 0.1643 | 0.3132 | **0.9061** |
| section-matched: `method` | 0.1652 (n=155) | 0.3671 (n=149) | 0.8656 |
| section-matched: `unknown` | 0.2955 (n=337) | 0.4091 (n=204) | 0.7132 |
| section-matched: `data` | 0.2069 | 0.3333 | 0.6896 |
| section-matched: `results` | 0.1143 | 0.1875 | 0.6658 |
| section-matched: `discussion` | 0.1644 | 0.2069 | 0.6163 |
| **length-matched** `method` (< 1,200 words) | 0.1905 (n=62) | 0.4000 (n=124) | **0.8349** |
| **human-vs-human null**, `method` | in-sample 0.1832 (n=428) vs held-out 0.1652 | | **0.5528** |

The machine documents are ~1.5k words against ~9.8k for the papers, so the
whole-document figure compares introduction-shaped prose against papers that
also contain citation-sparse methods and results. Section matching costs it
0.04–0.29 depending on the section; length matching within the strongest
section costs almost nothing more. The human-vs-human null at 0.553 says the
statistic is stable across two independent human banks and six years of drift.

Surviving all three controls makes this the strongest model-free discriminator
in the record — compare `L0.register` at 0.286 and `L2.salience_hierarchy` at
0.772. **It is not shipped.** All 173 machine documents come from one
generation process, and one bank cannot separate "AI cites more" from "these
prompts made it cite more". That is a §9 confound audit question, and the axis
stays unbuilt until a second, independently produced AI bank answers it.

### 18.7 What this section does not close

- **Recall.** Every register figure here is a false-positive rate. How many
  genuinely foreign terms the axis misses is still `unmeasured`, and provenance
  cannot supply it — see §17.6 and `tools/label_findings.py`.
- **Advice quality.** Whether an individual advisory is worth acting on needs
  a labeller, unchanged by anything in this section.
- **`corpus_cos` ablation.** Not run, and now withdrawn as an item rather than
  deferred: `confound_audit` bins on record metadata the feature cache does not
  carry, so an ablation runnable from the cache would compute a different
  statistic from the three recorded retrains (§7.0a) and could not be compared
  with them. Its only consumer is a `degraded`, audit-only classifier with no
  shipped operating point, whose status rests on independently refuted grounds,
  so no ablation result could change shipped behaviour.
- **The anchoring baseline moved.** Broadening the citation pattern reclassified
  1,028 of 79,904 held-out sentences (1.29%) from unanchored to anchored and
  **0** in the other direction, and the baseline was rebuilt from the corrected
  517-document population. The axis is more accurate; its operating point was
  not re-derived here.
- **README demo 2 stays a dated record.** Its 189-word draft was never retained,
  so its two reference denominators — `n=5957` (`method` salience) and `n=8144`
  (`method` structure), both v0.28.0 — and the percentiles computed against them
  cannot be recomputed. Reconstructing a draft that satisfies the stated
  constraints would be authoring a new demo, not re-running the old one, so the
  section stamp now says which demo is current and which is dated instead of
  claiming both. Demo 1 *was* re-run (§18.8).

### 18.8 Published figures had no check at all

Every figure in the tables above is read from `style-profile/<field>/`, which is
gitignored. No validator check has ever been able to open those files, so the
only thing holding a document and its artifact together was the working rule
"re-read the artifact in the same turn you paste it". Audited, that rule failed
three times in three releases:

| release | what drifted |
|---|---|
| v0.29.0 | The README demo's numbers were re-run against the rebuilt profile; the section's provenance stamp naming the *previous* one was not. |
| v0.32.0 | The post-release sweep corrected `EVALUATION.md`'s axis table and missed both READMEs' artifact tables — six of seven structure counts and six of seven salience counts, in each language. |
| after the v0.32.0 tag | The UID baseline finished rebuilding on the corrected corpus (27,951 → 27,917 paragraphs, pooled global UID 3.321 ± 0.439 → **3.303 ± 0.437**) with nothing pointing at the four documents that quote it. |

`tests/test_published_figures.py` closes it by inverting the direction of the
check: instead of reading a number out of a document and asking whether it looks
right, it renders the expected substring **from the artifact** and asks whether
the document still contains it. A document that agrees with a stale artifact and
a document nobody updated then fail identically, which is the property the
working rule never had. It pins 39 figures across the two READMEs, this record,
and the hub's axis and bucket tables, and it was verified by putting each
corrected figure back to its stale value — 11 mutations, 11 caught.

The field is read from this record's own path literal rather than hard-coded, so
a second field needs no edit. On a clean clone there is no profile, so the cases
**skip**: absence is reported as absence, never as agreement.

One published block the check cannot reach is README §"See it work". Its figures
come from running the linter over 20-document corpora rather than from reading a
JSON, so pinning them would add roughly 40 s to a 40 s suite. Demo 1 was
therefore re-run by hand and its stamp now carries the date. Arm B — the
word-list humanizer — had never been retained, but the whole 20-document set
carries exactly **four** L0 targets (one em-dash pair, two `underscoring`, one
Tier B excess), so that arm is four edits over arm A and was re-derived rather
than quoted. It reproduced the section's central claim independently:

| | A: as generated | B: word-list | C: sci-paper |
|---|---:|---:|---:|
| documents with an L0 target | 4 | 0 | 0 |
| em-dashes | 2 | 0 | 0 |
| advisories | 331 | 329 | 315 |
| **strong advisories** | **131** | **131** | 126 |

The word-list pass moves strong advisories by exactly zero, which is what the
2026-08-25 pass found at 127 → 127 → 102 on the previous profile. The
single-paragraph blocks reproduce finding-for-finding in all three arms; only
the reference denominators moved (`n=3964` → 3,958, `n=2541` → 3,206) and one
percentile with them (p73 → p71). Demo 2's draft was not retained, so it stays
dated (§18.7).
