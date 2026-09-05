# A worked example

Two files, one manuscript. `sample-manuscript.tex` is written to carry the
habits the tools measure; `sample-manuscript-revised.tex` is the same paper
after acting on what they reported.

Everything here is synthetic. The topic — calibrating multiplicative shear bias
against image simulations — is a textbook one with a large published
literature, and every number, author and result is invented, so nothing in
these files resembles unpublished work by anyone.

## Running it

```bash
python tools/ai_ism_lint.py examples/sample-manuscript.tex --field wgl
python tools/ai_ism_lint.py examples/sample-manuscript-revised.tex --field wgl
```

A profile is required. The repository ships none — every profile asset is
gitignored — so on a fresh clone both files report `unmeasured` for the
corpus-referenced axes instead of the numbers below. Build one first with
`python tools/build_profile.py --field <field>` and the `--calibrate` commands
in `style-profile/README.md`. The figures here were produced against the `wgl`
profile on 2026-09-04 (v0.36.3) and will move with the corpus.

## What it reports

| | before | after |
|---|---:|---:|
| L0 targets | 1 | **0** |
| integrity blockers | 0 | 0 |
| total advisories | 20 | **15** |
| strong advisories | 7 | **5** |
| document-scale findings | 8 | **6** |

Per rule:

| rule | before | after | |
|---|---:|---:|---|
| `discourse-cohesion` | 3 | **1** | intro passage cleared from p1 |
| `em-dash` (L0) | 1 | **0** | |
| `ing-tail:highlighting` | 1 | **0** | |
| `document-uniformity` | 6 | **5** | |
| `document-role-decoupling` | 1 | **0** | |
| `structure-template` | 1 | 2 | announced enumeration gone, two announced counts remain |
| `salience-recital` | 4 | **3** | fell, and the two strong ones changed kind — see below |
| `collocation-novel` | 2 | **3** | rose for the same reason, and for one of its own — see below |

## Nothing was deleted to make a finding go away

Every measured value in the original survives in the revision, and the header
of `sample-manuscript-revised.tex` lists them. Two of them are also *restated*
where the argument now needs them: the headline 0.052 at a blending fraction of
0.40 appears in the abstract and again in the discussion. No value is invented
and none is dropped. The recital advisories
were answered the way their action text asks — by saying what the quantities
establish, so a passage stops being an uninterrupted run of numeral-bearing
sentences — and not by removing quantities, which is the failure mode that
action text explicitly warns against. The cohesion advisories were answered by
carrying a noun forward from the previous sentence, not by adding connectives
that fake a link.

## A coined term keeps its pair

`collocation-novel` counts, per sentence, the adjacent common-word pairs that
no passage of the field's corpus has ever written. It went from 2 findings to 3
because the revision says `blending fraction` and `blending term` — this
synthetic paper's own parameter, a pair the real literature does not use — in
more sentences, and because carrying `bias` forward for cohesion puts it next
to words it had not stood beside before (`bias runs`). That is the axis's stated exception, not a defect to fix:
a term this paper defines keeps its pair and gets its definition at first use,
and the disposition is recorded as *kept*, never answered by dissolving the pair
or changing the claim.

## The interesting result: two axes pulling against each other

`salience-recital` went from 4 findings to 3, and the two that stay strong
are no longer runs. Before, the results and method passages each carried a
run of 5 numeral-bearing sentences in 5; after, the longest run is 1 of 3
and 2 of 3, and what leads both findings is *density* — 3.3 and 4.3 numerals
per sentence, p96 and p99 of the human results and method passages.

That density is the revision's own doing. The cohesion axis asks each
sentence to reuse a content word from the sentence before it. In a results
paragraph, the word available to carry forward is usually the one the numbers
are about — here, `bias`. Repeating it pulls the subject into sentences that
also carry a numeral, and restating the headline pair where the discussion
needs it puts numerals into a passage that had none; both are exactly what
`salience-recital` counts, the fraction of sentences bearing numerals and the
longest uninterrupted run of them.

So in a number-dense passage the two axes want opposite things, and no rewrite
satisfies both. That is not a defect in either measurement. It is what an
advisory contract is for: both findings are true statements about the prose,
and which one to act on is a judgement about what the passage is *for* — and
the author makes it, not the tool. Neither axis emits a blocker, neither
produces a score, and nothing in the pipeline resolves the tension on the
author's behalf.

The count itself moved with the reference. The figures first published here
(2026-08-27) read the revision at **6** recital findings, because the bank
then held only the `[math]` projection of its passages: a human results
paragraph that writes its numbers inside math looked numeral-free, so any
density looked like recital. v0.36.3 calibrates on the numeral projection of
each passage (EVALUATION §17.5), and the same revision reads 3.

## The part that barely moved, and why

Document-scale findings go from 8 to 6, and five of the six that remain are
`document-uniformity`.

Cross-paragraph dispersion is measured over the paragraphs a document has, and
this one has eleven. An eleven-paragraph file cannot demonstrate that its paragraph
shape varies with rhetorical role, because there is little variation to measure
and no room to show a pattern is not chance. The conformal p-values behind
these axes are calibrated against complete papers of ordinary length, so a
short synthetic file sits outside that population for reasons unrelated to how
it is written.

Read that as the axis reporting the edge of its own domain rather than as
advice to pad the paper. On a real manuscript of 30-odd pages the same axis has
enough paragraphs to say something, which is where its operating point was
measured ([§9](../docs/architecture/evaluation/document-scale.md)).
`document-role-decoupling`, which did clear, is the one document-scale finding
the revision could legitimately act on: paragraph shape now tracks what each
paragraph is doing.
