---
name: calibrate
description: Make the plugin yours. Walks the whole calibration chain for one field — corpus intake, profile extraction, per-axis calibration, optional model training, a held-out provenance measurement, and finding-level labelling against your own standard, style and target journal — then verifies the result. Every axis reports `measured`, `degraded` or `unmeasured` from its own floor; a stratum that cannot support a rate stays `unmeasured` rather than being given one. Produces evidence only: no threshold here creates a verdict, an authorship claim, or a paper PASS/FAIL. Use when: "calibrate" / "set up my corpus" / "train on my papers" / "adapt to my journal" / "why is this axis degraded" / 校准 / 建语料库 / 用我自己的论文训练 / 适配目标期刊 / 标注 / 这个轴为什么是 degraded.
disable-model-invocation: false
argument-hint: "<field-name> [--variant <journal-format>] [--from <step>] [--labels-only]"
---

> **Not a normative skill.** `docs/SCIPAPER_STANDARD.md` decides what good
> scientific prose is; nothing produced here can change that. Calibration
> supplies the *reference distributions* the advisory axes compare against, and
> `docs/architecture/EVALUATION.md` records what each one is worth. A corpus
> statistic cannot redefine a consequence class, create an authorship verdict,
> or turn an advisory into a blocker.

# calibrate — 校准：make the axes speak your field

## 0. What this skill does, and what it refuses

A fresh clone ships **no** corpus and **no** profile. Every `measured` axis in
this plugin is measured *against a reference distribution built from papers you
supply*, so out of the box the field-referenced axes are honestly `unmeasured`.
This skill is the path from that state to a calibrated one, for one field.

It refuses three things, and will say so rather than do them:

1. **It will not lower a floor to make a number appear.** If a section bucket
   holds fewer than 30 reference passages, or a labelling cell fewer than 20
   labels, the result is `unmeasured`. A rate computed from four observations is
   worse than no rate, because it reads like the others.
2. **It will not fold your held-out papers into calibration.** The evaluation
   set is the only thing that can tell you your own false-positive rate; the
   collector refuses any `fulltext-*` directory other than `fulltext-arxiv`
   (EVALUATION §18.3).
3. **It will not turn a calibrated distribution into a detector.** The register
   axis fires *more* on refereed prose than on machine prose at every setting of
   its knob (rank AUC below 0.5 everywhere, §18.4). Calibration buys advisory
   relevance, not discrimination.

## 1. Name the field, and decide whether you need a format variant

The field name is a directory name and nothing more; everything is scoped by it.
Pick the name of the literature you write into (`wgl`, `condmat`, `epi`, …).

A **target journal is usually not a new field.** Register measures *domain
vocabulary*; a letter is a *format*. A letter and a full paper in one field
share their words and differ in length and structure — which `deai_salience`
and `deai_docstructure` already measure per format (EVALUATION §18.5).

Create `<field>-<variant>` only when you have enough letters to resolve the
register gate: below 500 passages the axis is silent, and below the 1e-4 rate it
cannot express "rare" at all. A `<field>-<variant>` profile whose own bank
cannot resolve the gate automatically judges against `<field>` and names the
borrowed bank in every finding — so a thin variant profile is safe, not broken.

## 2. Build the corpus

```
style-corpus/<field>/tier-1-top/        top-journal exemplars (weighted highest)
                     tier-2-mentor/     your advisor's or target author's papers
                     tier-3-reference/  other relevant field papers
                     fulltext-arxiv/    optional breadth corpus (unweighted)
                     fulltext-heldout/  optional evaluation set (NEVER calibration)
```

The three `tier-*` directories carry every weighted aggregate and the style
dossier. `fulltext-arxiv/` is gathered **unweighted** and feeds the reference
distributions only, so breadth cannot restyle the imitation target.

Corpus content is copyright-sensitive and is gitignored by a blanket rule; it
never leaves the machine. To pull a breadth corpus or a held-out set:

```bash
python tools/fetch_arxiv_abstracts.py --field <field> --fulltext \
    --fulltext-dir fulltext-arxiv --journals apj,apjl,aa \
    --max-papers 500 --sleep 3
python tools/fetch_arxiv_abstracts.py --field <field> --fulltext \
    --fulltext-dir fulltext-heldout --journals apj,apjl,aa \
    --max-papers 200 --sleep 3 --exclude-known
```

`--exclude-known` is what makes the second pull disjoint from the first. Verify
the disjointness before trusting any rate computed from it.

## 3. Extract the profile

```bash
python tools/extract_style.py --field <field>
```

This writes the descriptive lexicon, sentence statistics, transition inventory,
style dossier, exemplar bank and register lexicon into `style-profile/<field>/`.

**Keep the `source` field in your bank.** Section-unit references are assembled
from the paragraph bank by grouping on it, so a record that cannot be attributed
to a document is dropped rather than pooled — pooling would join paragraphs from
unrelated papers into a section no author ever wrote.
Everything under that directory is generated and gitignored: it is rebuilt from
the corpus, never edited by hand.

**A paper is a document, not a file.** `\include`/`\input` fragments are folded
back into their root and a bundle contributes one paper. If your counts look
like "one paper per file", the assembly did not run.

## 4. Calibrate the axes

Run these after every corpus change. Each prints its own floors; read them.

```bash
python tools/deai_salience.py      --calibrate --field <field>
python tools/deai_structure.py     --calibrate --field <field>
python tools/deai_register.py      --calibrate --field <field>
python tools/deai_anchoring.py     --calibrate --field <field>
python tools/deai_docstructure.py  --calibrate --field <field>
python tools/deai_discourse.py     --calibrate --field <field>
```

| axis | what it needs | what happens below it |
|---|---|---|
| `L2.salience_hierarchy` | ≥ 30 reference passages per section bucket; passages ≥ 30 words and ≥ 3 sentences | that bucket is `degraded`; a reference with no spread above the p90 gate abstains rather than flagging |
| `L2.sentence_structure` | per-section reference fractions | `measured` for deterministic matches, `degraded` for strength — there is no calibrated strong-advisory operating point |
| `L0.register` | ≥ 500 corpus passages, and enough of them to resolve a 1e-4 document-frequency rate | under 500 the axis is silent; unable to resolve the rate it is `degraded`, or borrows `<field>`'s bank and says so |
| `L2.claim_anchoring` | ≥ 30 documents per section class | classes below the floor are omitted from the band, honestly, rather than estimated |
| `L2.document_structure` | ≥ 3 complete documents, each ≥ 3 sections with ≥ 2 substantial paragraphs | `unmeasured`; legacy baselines without a conformal block fall back to percentile thresholds |
| `L2.cohesion` | ≥ 30 reference paragraphs per bucket, each ≥ 3 sentences and ≥ 40 words | that bucket abstains; a reference with no spread *below* the p10 gate reports nothing rather than everything |
| `L2.hedging` | ≥ 30 reference **sections** per bucket, each ≥ 150 words — and the bucket must be one the axis is calibrated for | `degraded`. It ships restricted to `intro` because that is the only bucket where its gate was shown to transfer (EVALUATION §19.4); a thin profile is `degraded` there too |

If you point `--corpus-dir` anywhere, point it at the field root or at
`fulltext-arxiv/`. Aimed at the field root it collects the calibration corpus
and **refuses** every other `fulltext-*` directory, which is what keeps a
held-out set held out.

## 5. Optional models

These need optional dependencies (`requirements.txt`) and are never required for
the model-free axes:

```bash
python tools/deai_oracle.py --calibrate --field <field>      # UID baseline, GPU-hours
python tools/train_voice_model.py --field <field>            # learned L3 triage
```

The UID baseline reads paragraphs of ≥ 25 tokens under a causal LM (GPT-2-large
by default; `--model` changes it) and is expensive — hours on a consumer GPU for
a 500-paper corpus. It supports comparative evidence only: the surprisal path is
*measured* to add nothing to the model-free manifold at document scale
(EVALUATION §9.8), so skipping it costs you no shipped capability.

The learned model ships `degraded` by design and has no operating point. Do not
read its score as a probability of anything.

## 6. Measure your own false-positive rate

With a held-out set in place, provenance is a label already: a refereed paper is
text a human wrote and a referee accepted.

```bash
python tools/eval_findings.py --field <field>
```

Read the two axes differently. Register is an absolute rarity test, so its
held-out rate **is** a false-positive rate. Salience is a percentile gate, so a
non-zero rate is the design point and the number tests calibration *transfer*,
not defectiveness. Neither is precision for the *advice*: publication does not
mean every sentence is beyond improvement, so the register figure is an upper
bound. That is what §7 is for.

## 7. Labelling calibration — your standard, your journal

This is the only step that needs a person, and it is the only one that can say
whether an advisory is **good advice for you**. It is entirely local: no
network, no API, no external service. Your labels are written to a JSONL file
you own, are read back only by `score`, and never enter `style-profile/` or any
calibration input.

```bash
python tools/label_findings.py sample --field <field> \
    --population mentor=style-corpus/<field>/fulltext-mentor \
    --n 240 --out labels.jsonl
# fill in "label": true | false, guided by each row's own "question"
python tools/label_findings.py relabel --sheet labels.jsonl --frac 0.2 \
    --out recheck.jsonl
python tools/label_findings.py score --sheet labels.jsonl --recheck recheck.jsonl
```

Four things about the sheet decide whether the effort is worth anything:

- **Named populations, reported separately.** "Does it misfire on the prose I am
  modelling myself on" and "does it misfire on published work" are different
  questions with different answers, so each `--population NAME=DIR` is sampled
  and scored on its own. Whichever population you name, it must sit **outside**
  the calibration banks: on an in-sample paper ~94% of register flags are
  suppressed by that paper's own bank membership (§17.3). Measured here — the
  same axis yields 1 finding across three in-calibration papers and 8 across
  fifteen held out. `published` is added for you from the held-out set unless
  you name your own.
- **Stratified by axis, not only by population.** Salience fires roughly twenty
  times as often as register. A shared quota is spent on salience before
  register reaches the floor, and the register cell then reads `unmeasured`
  however large the sheet is.
- **A flag and a control ask opposite questions.** A flagged row asks whether the
  advisory is right. A control row asks whether it *should* have been flagged —
  that miss is the numerator of recall. Each row carries its own `question`;
  read it rather than assuming.
- **The re-label pass is the ceiling, not a formality.** One labeller cannot
  give an inter-rater bound, so 20% comes back blind and shuffled. The resulting
  intra-rater kappa is the precision no axis can be held above, because the task
  itself does not support one.

**Your standard and target journal enter here, and only here.** Judge each
advisory against the prose *you* would submit to *your* journal. If your field
writes methods sections that recite parameter grids, label those salience
advisories false, and the measured precision will say so. That is the intended
use: the numbers describe your judgement, not a universal one.

`--population NAME=DIR` accepts a directory of `.tex` files or a directory of
per-paper subdirectories — the shape every `style-corpus/<field>/fulltext-*`
pull has; a manuscript whose `main.tex` `\input`s its sections is one paper, not
fifteen fragments. `--drafts DIR` is shorthand for `--population draft=DIR`.

To build a population from one author's papers, `tools/fetch_arxiv_abstracts.py
--fulltext --author "Surname" --author-is <regex> --max-authors N
--fulltext-dir fulltext-<name>` fetches into a directory calibration never
reads. `--author-is` is not optional in practice: `au:` matches a **surname**,
and a surname is not a person.

**Sample size.** Any cell under 20 labels reports `unmeasured`. The sampler
prints, before you start, every cell its populations cannot fill — and some
cannot be filled by any sheet size, only by more papers. Measured on the `wgl`
corpus: fifteen held-out single-author-group papers yield 8 register findings
and 2 hedging findings, and the entire 203-paper held-out set yields 15 hedging
findings, because hedging speaks only about introductions and fires below a
tenth percentile. Salience and cohesion fill from a handful of papers.

## 8. Verify, then record what stayed unmeasured

```bash
python tools/validate_plugin.py
python -m unittest discover -s tests
```

`tests/test_published_figures.py` renders every figure your documentation quotes
*from* the artifact it came from and fails if the document no longer carries it.
With no profile built it skips rather than passes: absence is reported as
absence.

Then write down, in your own evaluation record, every axis that is still
`degraded` or `unmeasured` **and why**. An axis that is silent because your
corpus is thin is a different fact from one that is silent because its premise
was refuted, and a record that blurs them is worth less than no record.

## 9. What this skill will not do for you

- It will not choose your corpus. Which papers represent the writing you want to
  be measured against is a judgement about your field, not a computation.
- It will not tell you an axis is trustworthy because it calibrated cleanly.
  Clean calibration means the reference distribution exists; whether the axis
  discriminates is a separate measurement (§6, §7).
- It will not produce a number for a stratum that cannot support one, under any
  argument about how useful the number would be.
