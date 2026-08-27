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
profile on 2026-08-27 and will move with the corpus.

## What it reports

| | before | after |
|---|---:|---:|
| L0 targets | 1 | **0** |
| integrity blockers | 0 | 0 |
| total advisories | 19 | 16 |
| strong advisories | 7 | 7 |
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
| `salience-recital` | 4 | **6** | **rose — see below** |

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

## The interesting result: two axes pulling against each other

`salience-recital` went **up**, from 4 findings to 6, as a direct consequence
of fixing cohesion.

Half of the increase is that restatement: a passage that had no numerals now
carries the headline pair, which is what makes it a recital candidate at all.
The other half is structural. The cohesion axis asks each sentence to reuse a
content word from the sentence before it. In a results paragraph, the word available to carry forward is
usually the one the numbers are about — here, `bias`. Repeating it pulls the
subject into sentences that also carry a numeral, which is exactly what
`salience-recital` counts: the fraction of sentences bearing numerals, and the
longest uninterrupted run of them.

So in a number-dense passage the two axes want opposite things, and no rewrite
satisfies both. That is not a defect in either measurement. It is what an
advisory contract is for: both findings are true statements about the prose,
and which one to act on is a judgement about what the passage is *for* — and
the author makes it, not the tool. Neither axis emits a blocker, neither
produces a score, and nothing in the pipeline resolves the tension on the
author's behalf.

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
