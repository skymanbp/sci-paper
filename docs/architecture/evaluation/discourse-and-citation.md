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
over the 27,917-paragraph `wgl` bank, the tenth percentile is exactly 0.000
markers per 1,000 words in every one of the seven section buckets: more than a
tenth of real human paragraphs contain no hedge, because a 40-word paragraph
that hedges nowhere is entirely ordinary. A gate there is one no passage can
fall below, and the axis would have reported a confident zero findings forever.
`deai_reference.resolves_gate` catches exactly this and abstains, which is how
the defect surfaced rather than shipping.

Regrouped so that one section is one unit — every paragraph sharing a source
document and a bucket joined back together — six of the seven buckets separate:

| bucket | hedging p10, section unit (markers / 1,000 words) |
|---|---:|
| discussion | 3.350 |
| results | 2.853 |
| method | 2.172 |
| intro | 1.986 |
| conclusion | 1.647 |
| data | 1.055 |
| abstract | **0.000** — abstains |

`abstract` stays flat because an abstract *is* one passage; regrouping cannot
make it coarser. Cohesion needs no such treatment: at paragraph unit its p10
runs 0.037 (`conclusion`) to 0.057 (`abstract`, `data`) and resolves everywhere.

So the two axes carry **two artifacts at two units**, and each records its own
`unit` field, because two references built from the same corpus at different
granularities are both valid and are not comparable:

| artifact | unit | bucket sizes |
|---|---|---|
| `cohesion_baseline.json` | paragraph | abstract 13,967 · method 6,903 · intro 3,252 · results 3,183 · data 2,992 · discussion 2,932 · conclusion 1,975 |
| `hedging_baseline.json` | section | abstract 10,404 · intro 502 · method 438 · conclusion 382 · discussion 327 · results 316 · data 299 |

### 19.2 Both floors were measured, not chosen

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
banks) against the six `docval` generation regimes. Rank AUC, human over
machine; 0.5 is no separation. The **null** row is the same held-out set split
in half and scored against itself — the only number that says what a given AUC
is worth.

**Cohesion (paragraph unit)**

| regime | intro | method | results | discussion | conclusion | data |
|---|---:|---:|---:|---:|---:|---:|
| ai | 0.744 | 0.648 | 0.658 | — | — | — |
| ai_adversarial | 0.830 | 0.693 | 0.767 | 0.601 | — | 0.502 |
| ai_deai | 0.738 | 0.648 | 0.683 | 0.547 | 0.751 | 0.649 |
| ai_long | 0.676 | 0.545 | 0.614 | 0.623 | 0.631 | 0.516 |
| ai_natural | 0.684 | 0.624 | 0.679 | 0.559 | 0.580 | 0.533 |
| ai_skeleton | 0.711 | 0.562 | 0.573 | 0.667 | 0.707 | 0.538 |
| **worst of six** | **0.676** | 0.545 | 0.573 | 0.547 | 0.580 | 0.502 |
| null (human/human) | 0.515 | 0.487 | 0.505 | 0.496 | 0.510 | 0.505 |
| n human units | 960 | 1,128 | 593 | 869 | 631 | 868 |

**Hedging (section unit)**

| regime | intro | method | results | discussion | conclusion | data |
|---|---:|---:|---:|---:|---:|---:|
| ai | 0.776 | 0.796 | 0.683 | — | — | — |
| ai_adversarial | 0.613 | 0.692 | 0.473 | 0.842 | 0.948 | 0.585 |
| ai_deai | 0.811 | 0.747 | 0.613 | 0.795 | 0.948 | 0.589 |
| ai_long | 0.682 | 0.603 | 0.607 | 0.568 | 0.591 | 0.459 |
| ai_natural | 0.816 | 0.761 | 0.622 | 0.850 | 0.948 | 0.544 |
| ai_skeleton | 0.750 | 0.613 | 0.490 | 0.526 | 0.376 | 0.609 |
| **worst of six** | **0.613** | 0.603 | 0.473 | 0.526 | **0.376** | 0.459 |
| null (human/human) | 0.460 | 0.574 | 0.520 | 0.475 | 0.469 | 0.508 |
| n human units | 190 | 310 | 120 | 202 | 155 | 248 |

Read the worst-of-six row against the null row, not the best cell. Hedging in
`conclusion` looks impressive at 0.948 for three regimes and is **0.376** — below
chance, pointing the wrong way — for `ai_skeleton`. Hedging in `method` looks
respectable at 0.603–0.796 until its human-vs-human null is read: at 0.574, most
of that is not separation at all. Only `intro` clears the null for every regime
on both features.

### 19.4 The transfer test agrees with the separation test, independently

Held-out flag rate at the p10 gate: the design point is 10% by construction, so
this measures whether the reference *transfers* to unseen refereed papers, not
whether those papers are defective. 203 papers:

| bucket | cohesion (paragraph) | hedging (section) |
|---|---:|---:|
| intro | 8.33% | **7.89%** |
| method | 9.93% | 26.77% |
| results | 10.62% | 24.17% |
| discussion | 12.20% | 16.34% |
| conclusion | 10.14% | 15.48% |
| data | 14.63% | 22.98% |
| abstract | 6.58% | (abstains) |
| **all** | **10.87%** | 19.67% |

Cohesion transfers across every bucket — 10.87% against a 10% design point, the
same quality of transfer `deai_salience` shows (§17.5: 0.2775 measured against a
0.2710 expectation). Hedging transfers **only in `intro`**. Everywhere else it
fires at two to three times its nominal rate on prose a referee accepted, which
means the reference does not describe the held-out population there.

Two independent measurements — one against machine text, one against unseen
human text — put the restriction in the same place. So hedging ships restricted
to `intro`, and `deai_discourse.AXES["hedging"]["buckets"]` carries the
restriction with this table beside it. A new field inherits it; widening it means
re-running this measurement, not editing the tuple.

### 19.5 What ships

| axis | unit | live buckets | held-out rate at a 10% gate | worst-of-six AUC (null) |
|---|---|---|---:|---|
| `L2.cohesion` | paragraph | all seven | 10.87% (557 of 5,125 units; 163 of 203 documents) | 0.676 in `intro` (0.515) |
| `L2.hedging` | section | `intro` only | 7.89% (15 of 190 units; 15 of 203 documents) | 0.613 in `intro` (0.460) |

On `wgl-letter`, hedging reports `degraded`: no bucket clears the 30-unit floor
after the restriction. That is the correct answer for a 36-document profile and
is reported rather than papered over.

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
