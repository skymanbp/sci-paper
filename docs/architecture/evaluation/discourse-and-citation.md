# 19–20. Discourse texture, and citation placement refuted (v0.33.0)

Part of [`EVALUATION.md`](../EVALUATION.md); section numbers are global.

Two roadmap items close here, in opposite directions. The cohesion and hedging
axes (roadmap rank 6, `Deferred` since v0.26.1) ship, one of them narrower than
it was proposed. Citation placement (recorded in v0.32.0 as "unblocked and
measured; not shipped") is refuted on its own pre-registered condition.

---

## 19. Discourse texture: cohesion and hedging (`deai_discourse`)

Two properties of scientific prose that a reader feels before naming them:

- **Cohesion** — given/new linkage. The mean fraction of each sentence's content
  words that already appeared in the sentence before it. A paragraph whose
  sentences share no vocabulary reads as a list of assertions, not an argument.
- **Hedging** — epistemic markers per 1,000 words against a fixed marker list.
  Prose with no hedge anywhere has stopped distinguishing what the data show
  from what the authors infer.

Both flag the **low** tail (advisory p10, strong p05) — the opposite direction
from `deai_salience`, because here the defect is absence rather than excess.
Both are advisories against the field's own distribution. Neither is an
authorship claim, and §19.4 is why that wording is load-bearing rather than
boilerplate.

### 19.1 The two axes measure at different units, because one of them has to

Hedging has **no paragraph-scale lower tail at all**. Calibrated per paragraph
over the 28,444-paragraph `wgl` bank, the tenth percentile is exactly 0.000
markers per 1,000 words in every one of the seven section buckets: more than a
tenth of real human paragraphs contain no hedge, because a 40-word paragraph
that hedges nowhere is entirely ordinary. A gate there is one no passage can
fall below, and the axis would have reported a confident zero findings forever.
`deai_reference.resolves_gate` catches exactly this and abstains, which is how
the defect surfaced rather than shipping.

Regrouped so that one section is one unit — every paragraph sharing a source
document and a bucket joined back together, on the reference side and, since
v0.39.0, on the manuscript side as well, however many headings split the
bucket there — six of the seven buckets separate:

| bucket | hedging p10, section unit (markers / 1,000 words) |
|---|---:|
| discussion | 3.378 |
| results | 3.128 |
| method | 2.273 |
| intro | 2.066 |
| conclusion | 1.600 |
| data | 0.824 |
| abstract | **0.000** — abstains |

`abstract` stays flat because an abstract *is* one passage; regrouping cannot
make it coarser. Cohesion needs no such treatment: at paragraph unit its p10
runs 0.037 (`conclusion`) to 0.057 (`abstract`) and resolves everywhere.

So the two axes carry **two artifacts at two units**, and each records its own
`unit` field, because two references built from the same corpus at different
granularities are both valid and are not comparable:

| artifact | unit | bucket sizes |
|---|---|---|
| `cohesion_baseline.json` | paragraph | abstract 13,966 · method 7,138 · results 3,309 · intro 3,269 · data 3,069 · discussion 3,022 · conclusion 1,988 |
| `hedging_baseline.json` | section | abstract 10,400 · intro 503 · method 438 · conclusion 384 · discussion 329 · results 317 · data 303 |

Sizes and gates are the 2026-09-27 profile rebuild, read on the nearest-rank
quantile grid (audit C12); the CHANGELOG records the earlier builds.

### 19.2 Both floors were measured, not chosen

Both sweeps below were run on the v0.33.0 bank, when the floors were set, and
not again since; on the rebuilt bank every non-abstract bucket still resolves
at the 150-word floor (§19.1).

**Hedging, section word floor.** A rate per 1,000 words computed over too few
words turns on the presence of one or two of them. Sweeping the floor against
the bank:

| floor (words) | `data` p10 | `abstract` sections retained |
|---:|---:|---:|
| 40 | 0.00 | 388 |
| 120 | 0.58 | 368 |
| **150** | **1.05** | **335** |
| 250 | 1.30 | 46 |

150 is the first floor at which every non-abstract bucket resolves. 250 buys
nothing further and costs the `abstract` bucket 86% of its sections.

**Cohesion, sentence floor.** Three sentences yields only two overlap
measurements, which is thin. It is nonetheless the right floor, because the
alternative is an axis that rarely looks at anything: at four sentences the
20-document `ai` tier offers **15** measurable introduction paragraphs in total,
and at three it offers **62** — while the worst-of-six-regimes separation is
unchanged (0.676 at three sentences against 0.674 at four).

### 19.3 What separates, and what does not

203 held-out refereed papers (`fulltext-heldout`, disjoint from all calibration
banks) against the six `docval` generation regimes, on the 2026-09-27 profile.
Rank AUC, human over machine; 0.5 is no separation. The **null** row is the
same held-out set split in half and scored against itself — the only number
that says what a given AUC is worth. A regime with fewer than five units in a
bucket is `—`, and the worst is taken over the rest.

**Cohesion (paragraph unit)**

| regime | intro | method | results | discussion | conclusion | data |
|---|---:|---:|---:|---:|---:|---:|
| ai | 0.746 | 0.645 | 0.668 | — | — | — |
| ai_adversarial | 0.832 | 0.698 | 0.772 | — | — | 0.508 |
| ai_deai | 0.739 | 0.624 | 0.678 | 0.558 | — | 0.650 |
| ai_long | 0.677 | 0.552 | 0.546 | 0.609 | 0.627 | 0.519 |
| ai_natural | 0.686 | 0.599 | 0.671 | 0.573 | — | 0.538 |
| ai_skeleton | 0.713 | 0.569 | 0.585 | 0.744 | 0.716 | 0.544 |
| **worst of six** | **0.677** | 0.552 | 0.546 | 0.558 | 0.627 | 0.508 |
| null (human/human) | 0.489 | 0.520 | 0.485 | 0.465 | 0.443 | 0.531 |
| n human units | 1,040 | 2,038 | 1,326 | 1,412 | 631 | 1,391 |

**Hedging (section unit)**

| regime | intro | method | results | discussion | conclusion | data |
|---|---:|---:|---:|---:|---:|---:|
| ai | 0.770 | 0.898 | 0.769 | — | — | — |
| ai_adversarial | 0.605 | 0.832 | 0.510 | — | — | 0.649 |
| ai_deai | 0.806 | 0.858 | 0.670 | — | — | — |
| ai_long | 0.671 | 0.731 | 0.551 | 0.593 | 0.601 | 0.464 |
| ai_natural | 0.811 | 0.866 | 0.675 | — | — | 0.609 |
| ai_skeleton | 0.744 | 0.788 | 0.578 | 0.421 | 0.358 | 0.641 |
| **worst of six** | **0.605** | **0.731** | 0.510 | 0.421 | 0.358 | 0.464 |
| null (human/human) | 0.487 | 0.442 | 0.440 | 0.472 | 0.520 | 0.489 |
| n human units | 198 | 156 | 120 | 158 | 154 | 139 |

Read the worst-of-six row against the null row, not the best cell. Hedging in
`conclusion` reads 0.601 for `ai_long` and **0.358** — below chance, pointing
the wrong way — for `ai_skeleton`, the only two regimes that reach it. Hedging
clears its null for every regime in `intro` and in `method` (0.731–0.898
against 0.442); cohesion does so in `intro`, and in `data` its worst regime sits
below its null. The v0.33.0 table, taken when a manuscript section was one
heading span, read hedging in `method` at 0.603–0.796 against a 0.574 null.

### 19.4 The transfer test agrees with the separation test, independently

Held-out flag rate at the p10 gate: the design point is 10% by construction, so
this measures whether the reference *transfers* to unseen refereed papers, not
whether those papers are defective. 203 papers, 2026-09-27 profile:

| bucket | cohesion (paragraph) | hedging (section) |
|---|---:|---:|
| intro | 8.17% | **9.09%** |
| method | 10.50% | **9.62%** |
| results | 10.33% | 14.17% |
| discussion | 11.97% | 8.23% |
| conclusion | 10.30% | 13.64% |
| data | 14.88% | 12.23% |
| abstract | 6.76% | (abstains) |
| **all** | **11.15%** (882 of 7,912) | 10.92% (101 of 925) |

Cohesion transfers across every bucket, `data` highest. Hedging transfers in
`intro`, `method` and `discussion` and over-fires in the other three.

Two independent measurements — one against machine text, one against unseen
human text — agree on `intro` and `method`; `discussion` transfers, but a
regime lands below chance there (§19.3). So hedging ships restricted to `intro`
and `method`, and `deai_discourse.AXES["hedging"]["buckets"]` carries the
restriction with this table beside it. A new field inherits it; widening it
means re-running this measurement, not editing the tuple — which is how
`method` joined on 2026-09-27, after the v0.33.0 measurement had put it at
26.77% and restricted the axis to `intro` alone.

### 19.5 What ships

| axis | unit | live buckets | held-out rate at a 10% gate | worst-of-six AUC (null) |
|---|---|---|---:|---|
| `L2.cohesion` | paragraph | all seven | 11.15% (882 of 7,912 units; 170 of 203 documents) | 0.677 in `intro` (0.489) |
| `L2.hedging` | section | `intro`, `method` | 9.32% (33 of 354 units; 31 of 203 documents) | 0.605 in `intro` (0.487); 0.731 in `method` (0.442) |

On `wgl-letter` both hedging buckets reach the 30-unit floor on the rebuilt
profile (`intro` 37 sections, `method` exactly 30), so the axis reports
`measured` there under the restriction measured on `wgl`.

**What this evidence does not license.** It says the reference distributions are
real and section-bound. It does not say a low value means a machine wrote the
passage. The advisory an author receives says the passage is unusual for the
field and what to do about it; nothing in `deai_discourse` emits a provenance
claim, and no threshold in it may be read as one.

---

## 20. Citation placement: refuted by the second bank

v0.32.0 recorded this as the strongest model-free discriminator in the whole
record — section-matched rank AUC 0.866 in `method` on cited-sentence fraction,
surviving the section, length, and human-vs-human controls — and declined to
ship it, for one stated reason: all 173 machine documents came from a single
generation process, so one bank cannot separate *AI cites more* from *these
prompts made it cite more*. The pre-registered condition for shipping was a
second, independently produced AI bank.

### 20.1 The second bank

Two banks of 20 documents each, on the same 20 topics as the existing `docval`
tiers, generated by a **different model** (Codex, `gpt-5.6-terra`) and differing
from each other in **one line of the prompt**:

- **F** — says nothing about citations.
- **G** — asks explicitly for dense citation in author-year form.

### 20.2 Citation density, per 1,000 words

| population | citations / 1,000 words |
|---|---:|
| **codex_F** (no citation instruction) | **1.00** |
| human held-out (203 papers) | 6.20 (per-document p10 2.64, median 5.94, p90 11.24) |
| ai_long | 7.06 |
| ai_skeleton | 7.72 |
| ai | 10.77 |
| ai_adversarial | 11.95 |
| ai_natural | 12.26 |
| **codex_G** (dense citation ask) | **12.55** |
| ai_deai | 13.15 |

One model, one prompt line, a **12.5× swing** — from a sixth of the human median
to twice it. The two machine extremes bracket the human distribution rather than
sitting on one side of it.

### 20.3 The statistic the disposition actually named

Cited-sentence fraction, section-matched, which is where the 0.866 came from.
Rank AUC, machine over human held-out:

| population | median in `method` | method | results | discussion |
|---|---:|---:|---:|---:|
| human held-out | 0.1652 (n=155) | — | — | — |
| Claude, all six tiers | 0.3671 (n=149) | **0.866** | 0.666 | 0.616 |
| codex_G (dense ask) | 0.2716 (n=20) | 0.734 | 0.864 | 0.677 |
| **codex_F (no ask)** | **0.0000 (n=20)** | **0.053** | 0.062 | 0.051 |

`codex_F` at 0.053 is not the absence of separation. It is separation of nearly
the same strength **in the opposite direction**: a gate that reads a high
cited-sentence fraction as machine-like would flag about 87% of human `method`
sections before it flagged one `codex_F` document.

### 20.4 Verdict

Refuted, on the condition the record set for it in advance. The signal is real
and it is not a property of machine authorship: it is a property of *which model,
prompted how*. The same model moves from 0.053 to 0.734 on one prompt line, and
`codex_G` — a machine bank — lands closer to the human median than three of the
six Claude tiers do.

This is the same failure mode the record has now rejected four times: the
inference-connective rate reversing sign between two AI banks (§15.1), burstiness
reversing sign on adversarial prose (§16), the register axis firing more on
refereed prose than machine prose at every knob setting (§18.4), and now this. A
statistic whose sign depends on which machine population you happened to sample
is not a discriminator, however large its AUC on the sample you have.

No citation-placement axis, threshold, or advisory may be built on this evidence.
Reopening requires a statistic that holds its sign across independently produced
banks — which is a stronger bar than the three controls v0.32.0 applied, and is
the bar this section establishes for anything that follows it.
