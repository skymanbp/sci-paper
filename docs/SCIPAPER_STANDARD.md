# The sci-paper Standard

> **The single normative core.** Writing (`/sci-paper:paper`), checking
> (`/sci-paper:paper-review`, `mainline`, `figure-review`, `final-review`) and
> rewriting (`/sci-paper:rewrite-in-voice`) implement this document. If a skill,
> tool, style profile, or workflow conflicts with this file, this file wins.
>
> Status: **v2 (2026-07-12)**. v2 makes the feedback contract operational,
> separates scientific integrity from author-disposable prose feedback, and
> preserves the established lexical de-AI standard as L0.

---

## 0. Governing model: feedback, not a paper verdict

sci-paper does not produce a universal `PASS` or `FAIL` judgement for a paper.
It measures evidence, classifies findings, ranks the next useful actions, and
reports what remains.

```
measure -> typed findings -> ranked actions -> edit -> re-measure -> disposition
```

This is not the same as making every finding optional. The system uses three
classes with different consequences:

| Class | Meaning | Required consequence |
|---|---|---|
| `integrity_blocker` | The scientific record may be wrong, unsupported, internally inconsistent, unreproducible, or unusable | Must be resolved from sources. The author cannot waive it as a style preference. |
| `l0_target` | A preserved lexical de-AI target: Tier A, Tier B excess above its calibrated cap, or em-dash | Rewrite to zero applicable targets. This is a prose target, not a judgement that the paper is scientifically invalid. |
| `advisory` | Calibrated L1-L4 or editorial evidence that a passage may be templated, distant from the field reference, unclear, or weaker than an available alternative | Rank, act on the strongest items, then record an author disposition for any residual. |

Examples of `integrity_blocker` include incorrect mathematics or physics,
fabricated or unsourced numbers, citation-source mismatch, data leakage,
invalid statistics, claim-evidence contradiction, a broken required build, and
missing required artifacts. A reviewer may later refute a suspected blocker;
until then it remains unresolved. It cannot be converted into an advisory just
because fixing it is inconvenient.

An `advisory` is evidence for an editorial action, not evidence of authorship.
Tools must say that text is structurally templated or distant from a calibrated
reference. They must not claim that a machine wrote it.

### 0.1 Exit semantics

`ai_ism_lint.py` uses exit status only for its actionable L0 contract:

- `0`: input and requested measurements completed, with no L0 targets. Advisory
  findings may still be present.
- `1`: one or more L0 targets are present.
- `2`: invalid input, unavailable required configuration, or execution failure.

Standalone advisory tools return `0` when measurement completes, whether or
not advisories are found. They return nonzero only for invalid input,
configuration failure, or execution failure.

Scientific-integrity review is broader than the linter and is reported through
typed findings. It is never compressed into the linter's L0 exit status.

### 0.2 Measurement availability

A missing model, baseline, detector, source, or calibration is not zero
findings. The corresponding axis is `unmeasured` or `degraded`, with a reason
and the action needed to restore measurement. Reports must distinguish:

- `measured`: the requested detector completed against its declared reference;
- `degraded`: a documented fallback or partial reference was used;
- `unmeasured`: no valid measurement was possible;
- `not_applicable`: the axis does not apply to this artifact.

A final report lists all four states. Silence is never interpreted as clean.

---

## 1. Why prose retains AI-feel after keyword cleanup

AI-feel is not a vocabulary. Keyword replacement leaves deeper regularities:

1. **Information is smoothed.** Sentence length, information density, and
   surprisal vary less than in the field reference.
2. **Sentence construction is templated.** Announced enumeration, setup-list-
   wrap patterns, repeated modal or anaphoric runs, and symmetric closers recur.
3. **Document shape is over-regular.** Paragraphs and sections repeat the same
   rhetorical geometry even when their subject matter differs.
4. **Voice lacks scientific commitment.** Claims remain generic, unsupported by
   specific evidence, excessively balanced, or detached from the author's
   actual reasoning.
5. **A learned score can be confounded.** Mathematical density, jargon, section
   genre, or corpus imbalance can dominate a classifier without measuring the
   quality the system intends to improve.

The evidence for the current detectors, measured effects, known confounds, and
field-specific operating points belongs in [`../EVALUATION.md`](../EVALUATION.md),
not in this normative document.

---

## 2. Layered signal model

L0 preserves the earlier sci-paper lexical standard. L1-L3 diagnose negative
signals. L4 states positive qualities to add. QD covers scientific and editorial
quality dimensions.

| Layer | Scope | Typical evidence | Consequence |
|---|---|---|---|
| **L0** | Lexical and punctuation | Tier A occurrence, Tier B excess, em-dash | `l0_target`; rewrite to zero |
| **L1** | Information distribution | burstiness, signposting, surprisal, UID | ranked `advisory` |
| **L2** | Sentence and document structure | template families, repeated paragraph shape, repeated section arc | ranked `advisory` |
| **L3** | Learned similarity | calibrated model distance with model and confound metadata | ranked `advisory` |
| **L4** | Positive scientific voice | specificity, defended claim, author exemplars, faithful compression | rewrite objective and review evidence |
| **QD** | Scientific and editorial quality | mathematics, physics, sources, statistics, logic, figures, narrative, language | `integrity_blocker` or `advisory`, according to consequence |

### L0: preserved lexical de-AI standard

The canonical Tier A and Tier B lists, em-dash rule, grep patterns, and writing
examples remain in [`../skills/paper/SKILL.md`](../skills/paper/SKILL.md). The
field dossier and generated lexicon are calibration data, not a competing
policy authority.

L0 contains exactly:

- every Tier A hit;
- every em-dash hit;
- only the portion of Tier B usage above the applicable section cap.

A Tier B occurrence within its cap is measured and may be shown for context,
but it is not an L0 target. Classifier signals, sentence templates,
three-part structures, corpus-distance signals, and ordinary style preferences
are not L0 targets.

### L1: information distribution

L1 measures distributional properties against a field and section reference,
including sentence-length variation, connective-openers, surprisal, and
uniform-information-density features. Feedback names the observed value, the
reference, the distance, uncertainty where available, and a concrete action.
Hardcoded universal prose thresholds are forbidden.

### L2: sentence and document structure

Sentence-level template families include:

- announced enumeration;
- ordinal runs;
- setup-list-wrap patterns;
- repeated lexical or modal/anaphoric sentence frames;
- balanced or symmetric closers.

Document-level evidence concerns shape rather than repeated subject matter:

- within-section paragraph-shape regularity;
- cross-section shape similarity;
- repeated first-to-last paragraph arcs.

A detector needs enough sections and substantial paragraphs to support the
measurement. Otherwise it reports `insufficient_evidence` and leaves the axis
unmeasured. Calibration uses complete human source documents, not paragraphs
misrepresented as independent papers.

L2 actions must preserve clarity and logic. The goal is not random irregularity.
A rewrite should remove needless scaffolding and repetitive symmetry while
keeping genre-appropriate organization and readable argument flow.

### L3: learned similarity

A learned model is a calibrated similarity instrument, not an authorship
oracle. Its output must be accompanied by:

- model identifier and version;
- training and calibration reference;
- field and section applicability;
- operating-point provenance, if an operating point is used;
- known confounds and current audit status;
- measurement availability.

The normative report uses distance and uncertainty language. Labels such as
`P(human)` may be retained internally for model compatibility, but user-facing
text must not say that a low score proves machine authorship. A universal
`0.5` cutoff is not part of this standard.

### L4: positive scientific voice

Removing tells is insufficient. A faithful rewrite should add or strengthen:

- a precise claim with an identifiable scientific subject;
- concrete evidence, numbers, entities, or conditions when the source supports
  them;
- an explicit stance or interpretation and its reason;
- economical transitions carried by the argument rather than roadmap prose;
- section-appropriate variation in sentence and paragraph shape;
- forward narrative that describes the current scientific state rather than
  the history of drafting or failed internal approaches.

Every added number, citation, entity, unit, causal claim, and qualifier must be
traceable to a source. Specificity never licenses invention.

### QD: scientific and editorial quality

The detailed QD review dimensions remain in the writing and review skills. Each
finding is typed by consequence:

- correctness, provenance, reproducibility, required build, and
  claim-evidence defects are `integrity_blocker`;
- language, organization, aesthetics, and other preferences are `advisory`
  unless they make the scientific content ambiguous or unusable;
- objective figure failures, such as illegible labels, missing units, or a
  caption that contradicts the rendered figure, are blockers; aesthetic
  preferences are advisories.

The same critique can change class after verification. A suspected citation
mismatch begins as a blocker under scrutiny; if source inspection refutes it,
the finding is closed as a false positive rather than silently deleted.

---

## 3. Shared finding contract

Every tool and skill projects its results from the same conceptual object.
The machine-readable schema identifier is:

```text
sci-paper.feedback.v1
```

Required fields for each finding:

```text
finding_id
kind                    integrity_blocker | l0_target | advisory
layer                    L0 | L1 | L2 | L3 | L4 | QD
rule
scope                    document | section | paragraph | sentence | figure | table | equation | citation
location                 path, start_line, optional end_line and section
message
observed                 value, unit, optional raw evidence
reference                field, genre/section, statistic, value/range, provenance
normalized_distance      nullable when unavailable or categorical
confidence               value and basis
measurement_status       measured | degraded | unmeasured | not_applicable
priority                  components and final sortable key
recommended_action
detector                  name, version, configuration, calibration asset
source_trace              required for integrity-bearing claims; otherwise nullable
disposition               pending | acted | accepted | rejected_as_false_positive
before_after              optional linkage to the finding or measurement after action
```

`finding_id` is stable for the same detector, rule, location, and evidence
identity. Human-readable text and JSON must be generated from the same finding
objects. A tool must never reconstruct JSON by parsing its printed prose.

For unavailable measurements, the report includes an axis-level status object
even when there is no location-specific finding.

---

## 4. Ranking and strong advisories

Ranking is transparent and lexicographic. It is not an opaque aggregate
probability. Every component appears in JSON.

1. **Consequence class**: integrity blockers first, then L0 targets, then
   advisories.
2. **Finding strength within class**: verified contradictions before suspected
   contradictions; Tier A/em-dash and Tier B excess by applicable policy;
   calibrated advisory strength.
3. **Layer priority**: within prose advisories, direct structural evidence and
   strong source-backed clarity defects normally precede coarse learned scores.
4. **Reader exposure**: abstract and introduction receive a boost, followed by
   conclusions, then other sections, unless the finding is local to a required
   technical artifact.
5. **Calibrated distance**: larger empirical distance from the applicable human
   reference ranks first.
6. **Confidence**: stronger measurement and calibration evidence ranks first.
7. **Stable tie-break**: path, line, rule, and detector.

A **strong advisory** is operationally an advisory that satisfies all of:

- measurement status is `measured`;
- an applicable field/genre reference exists;
- the effect lies beyond the detector's calibrated strong-feedback operating
  point or in an empirically rare categorical family;
- confidence and sample sufficiency meet the detector's declared requirement;
- the action is specific enough to attempt without guessing scientific content.

The operating point and its provenance are detector metadata, not universal
constants in this standard. If any condition is absent, the finding remains an
ordinary advisory or unmeasured evidence.

`--top N` may limit displayed detail, but it must not change total counts,
ranking, axis status, or the summary.

---

## 5. Feedback to action protocol

All writing, checking, rewriting, and final-review workflows use this loop:

1. **Measure.** Run every applicable requested axis. Record unavailable axes.
2. **Classify.** Type each finding as blocker, L0 target, or advisory.
3. **Verify integrity findings.** Read the cited source, data, code, rendered
   artifact, or derivation before editing. Do not fix a scientific claim from a
   detector message alone.
4. **Rank.** Use the visible ordering in Section 4.
5. **Act.** Resolve blockers first, then L0 targets, then the strongest
   advisories. Make the minimum effective change.
6. **Protect invariants.** Rewrites must preserve claims, numbers, units,
   entities, citations, causal direction, stance, and qualifiers unless a
   source-verified scientific correction intentionally changes them.
7. **Re-measure.** Re-run every affected available axis. A rewrite may not clear
   one signal by introducing another defect or dropping evidence.
8. **Disposition residuals.** Record each remaining advisory as pending, acted,
   author-accepted, or rejected as a verified false positive. A tool cannot
   accept an advisory on the author's behalf.
9. **Report state.** Give before/after counts, unresolved blockers, remaining L0
   targets, strong and ordinary advisories, dispositions, and unmeasured axes.
   Never reduce the result to a universal paper verdict.

### 5.1 Stopping semantics

A review or rewrite cycle may stop when:

- all integrity blockers are resolved or verified false positives;
- applicable L0 targets are zero;
- every strong advisory is acted on, accepted by the author, rejected as a
  verified false positive, or explicitly left pending for a stated reason;
- ordinary residual advisories and all unmeasured axes are reported.

This is a feedback state, not proof that the paper is correct or publication
ready. Independent review may create new findings.

---

## 6. Rewrite eligibility and reward

Meaning preservation is an eligibility condition, not a soft score that can be
outweighed by smoother prose. A candidate is ineligible if it changes or drops
an unsupported subset of the following:

- scientific claim or conclusion;
- numerical value, uncertainty, unit, or comparison direction;
- named entity, dataset, method, population, or condition;
- citation and the claim it supports;
- causal direction;
- stance, modality, limitation, or qualifier;
- logical dependency between sentences.

Only eligible candidates are ranked by positive voice, calibrated feedback
improvement, clarity, and economy. If no candidate is eligible, preserve the
source text and report that no faithful rewrite was found.

A fixed cosine margin is not sufficient as the sole fidelity test. Fidelity
checks combine deterministic preservation tests with semantic comparison and,
for scientific changes, source verification.

---

## 7. Skill responsibilities

| Skill | Required role |
|---|---|
| `paper` | Load this standard; provide canonical L0 lists and detailed writing/QD guidance. |
| `paper-style` | Provide descriptive field evidence and calibration assets; never redefine consequence classes. |
| `rewrite-in-voice` | Consume ranked findings, generate only faithful candidates, re-measure, and report residual dispositions. |
| `paper-review` | Produce typed findings across its dimensions; verify integrity evidence; avoid a universal paper verdict. |
| `mainline` | Produce evidence-based narrative findings; allow multiple explicitly related contributions rather than imposing one universal spine doctrine. |
| `figure-review` | Separate objective scientific/rendering blockers from aesthetic advisories. |
| `paper-attack-tree` | Treat `CONFIRMED` as a critique that survived verification, then classify its consequence. It does not mean that the paper failed. |
| `final-review` | Preserve independent isolated reviews; merge typed findings; resolve blockers and L0 targets; record advisory dispositions and unmeasured axes. |

`docs/DEAI_SUBSYSTEM.md` documents architecture. `EVALUATION.md` records
empirical evidence. Neither overrides this standard.

---

## 8. Tool responsibilities

| Tool | Layer | Required behavior |
|---|---|---|
| `ai_ism_lint.py` | L0 hub plus optional L1-L3 aggregation | Emit text or structured JSON from the same findings; use L0-only exit semantics. |
| `deai_metrics.py` | L1 | Emit calibrated distribution findings and explicit missing-baseline status. |
| `deai_oracle.py` | L1 | Emit surprisal/UID findings with observed and reference values; advisory-success exit 0. |
| `deai_structure.py` | L2 sentence | Emit template evidence with calibration metadata; advisory-success exit 0. |
| `deai_docstructure.py` | L2 document | Measure document shape with sample-sufficiency checks and document-level calibration. |
| `deai_voice.py` | L3 | Emit calibrated similarity evidence, model metadata, and confound status without authorship claims. |
| `deai_feedback.py` | shared | Validate schema, attach actions, rank findings, summarize statuses, and serialize output. |
| `rewrite_reward.py` | L3-L4 | Exclude unfaithful candidates before ranking eligible rewrites. |
| `retrieve_exemplars.py` | L4 | Supply author-voice evidence without copying unsupported scientific content. |

Compatibility tuple APIs may remain temporarily, but new orchestration consumes
structured finding APIs. Adapters project from structured findings, not the
reverse.

---

## 9. Calibration and evaluation guardrails

1. **Calibrate by field and genre.** Do not transplant an operating point without
   evidence that the target distribution matches.
2. **Keep complete documents intact during document-level calibration.** Do not
   create false sample size by treating paragraphs from one paper as independent
   papers.
3. **Report uncertainty and leave-one-paper-out behavior.** A detector's apparent
   separation is insufficient without human false-positive evidence.
4. **Audit confounds.** Evaluate score relationships with mathematical density,
   jargon, section type, length, source paper, and any other plausible shortcut.
5. **Reward writing quality, not detector evasion.** A clearer, faithful,
   scientifically sourced paragraph is the target. Lower detector visibility is
   not independently valuable.
6. **Preserve clarity and logic.** Structural variation must not make prose
   random, obscure dependencies, or damage genre-appropriate organization.
7. **Keep the lexicon re-derivable.** Field data may update the lists and caps,
   while this standard continues to define their consequence.
8. **Record evidence outside the norm.** Sample counts, effect sizes, model
   metrics, and current operating points live in `EVALUATION.md` and calibration
   assets so they can change without silently changing policy.

---

## 10. User decisions and author control

The author controls editorial acceptance, not scientific truth. The system must
surface decisions that genuinely require the author:

- accept or reject a residual advisory after seeing its evidence and proposed
  action;
- choose between multiple faithful rewrites;
- provide or label gold voice examples;
- decide scope when two scientifically valid narratives serve different goals;
- approve publication or release actions.

The author cannot waive an unresolved integrity blocker merely by marking it
accepted. The correct paths are to fix it, verify it as a false positive, or
leave it explicitly unresolved.
