# The sci-paper Standard

> **The single normative core.** Writing (`/sci-paper:paper`), checking
> (`/sci-paper:paper-review`, `figure-review`, `final-review`), de-AI
> rewriting (`/sci-paper:de-ai`) and condensation (`/sci-paper:condense`)
> implement this document. If a skill,
> tool, style profile, or workflow conflicts with this file, this file wins.
>
> Status: **v3.4 (2026-07-18)**. v3.4 records the skill consolidation
> (11 → 8 orthogonal skills): the former paper-style, rewrite-in-voice and
> academic-humanizer fold into the single `de-ai` skill; mainline and
> paper-attack-tree fold into paper-review dimensions E and M; the new
> `condense` skill becomes the §5.3 action surface. §7 responsibilities are
> rebuilt accordingly; no policy in §§0-6 or §§8-11 changes.
> v3.3 makes §5.3 mechanically enforced: a
> length-budget hard gate in `rewrite_reward.py` (candidate time) and the new
> `length_gate.py` delta gate (loop close), with recorded justifications as the
> only path for growth.
> v3.2 (2026-07-16) adds §5.3 (condense, do not accumulate:
> the default direction of every edit is shorter; explanatory patches are the
> canonical violation), the corpus-verified lexicon extensions with the
> claim–evidence and preserve-list guidance in `skills/paper/SKILL.md`, and the
> `proposal-polish` skill row (§7).
> v3.1 (2026-07-14) adds the auxiliary L2 template families
> (antithesis clusters, short reversal beats — panel-derived, corpus-calibrated,
> excluded from `template_score` so the document manifold is unchanged) and
> recognizes the blind perceptual panel as an L2 validation instrument whose
> diagnostic reading is tell-inventory turnover, not the mean score. v3
> (2026-07-13) folds the complete de-AI subsystem into this
> single authority (there is no separate de-AI standard): it specifies the
> document-scale detection core (per-stratum dispersion manifold, role coupling,
> split-conformal), the cooperative L4 layer (partition, anchoring, provenance,
> personal baseline), the `calibration_unit` confidence cap, the ordered
> de-AI-ization procedure (§5.2, 去AI化步骤), and a disposition for every open
> item (§11). v2 made the feedback contract operational, separated scientific
> integrity from author-disposable prose feedback, and preserved the established
> lexical de-AI standard as L0.

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
configuration failure, or execution failure. One exception carries its own
narrow actionable contract: `length_gate.py` returns 0 when the document's
net unjustified prose growth is within tolerance, 1 when it exceeds the
tolerance, and 2 for invalid input or execution failure (§5.3).

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
field-specific operating points belongs in [`EVALUATION.md`](EVALUATION.md),
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

A second, **auxiliary family class** covers rhetorical figures that are
legitimate in isolation but machine-typical at density: **antithesis clusters**
(two or more contrastive frames such as "X rather than Y" / "not X but Y" in
one paragraph) and **short reversal beats** (a punchy reversal sentence of five
words or fewer, such as "It would not."). Auxiliary families emit ordinary
advisories under their own rule (`structure-auxiliary`) and are excluded from
`template_score`, so the calibrated document-dispersion manifold is unchanged by
their addition. The repair rule is asymmetric: keep a contrastive frame only
where the contrast is load-bearing technical content, and state posture
contrasts as plain positive claims. Perceptually confirmed tells that resist
pattern capture — aphoristic "perform rigor" closers — are documented as a
panel-advisory class in `EVALUATION.md` rather than forced into a detector.

A **blind perceptual panel** — independent cold-read judges who score AI-feel
and must name concrete tells with quotes, compared across document versions —
is a recognized L2 validation instrument. Its diagnostic reading is the *tell
inventory turnover*, not the mean score: judges saturate on the most visible
tell family, so removing it exposes the next stratum at a similar score. The
protocol and its case study live in `EVALUATION.md`.

Document-level evidence concerns shape rather than repeated subject matter, and
is the de-AI center of gravity: field register shifts the *level* of
per-paragraph features (which fools any per-paragraph score), while
machine-uniformity compresses their *spread across a document*. The document
detector (`deai_docstructure`, axis `L2.document_structure`) measures:

- **cross-paragraph dispersion** as a joint Mahalanobis distance in log
  dispersion-ratio space, fit **per length stratum** with a pooled fallback;
  `manifold_operating_point` is the single scoring entry shared by findings, the
  partition tool, and evaluations, so no two consumers see a different geometry;
- **role-coupled dispersion** (axis-level within the same detector): a
  permutation-normalized one-way η² of paragraph shape by rhetorical role, so the
  detector rewards variation *where the argument demands it* and both machine
  failure modes (uniform and forced-ragged) sit in the low-coupling tail;
- **split-conformal (Mondrian) operating points**: the human false-flag rate is a
  finite-sample, distribution-free type-I guarantee from human data alone,
  stratified by document-length tercile and separated from the wide-CI question
  of detection power.

A separate L2 writing-quality axis, `L2.claim_anchoring` (`deai_anchoring`),
measures section-class conditional anchored-sentence rates. It is a
writing-quality band, **not an AI-discrimination axis**: the "under-anchoring is
the AI tell" hypothesis is refuted for strong-model generations (EVALUATION §9.6).

A detector needs enough sections and substantial paragraphs to support the
measurement. Otherwise it reports `insufficient_evidence` and leaves the axis
unmeasured. Calibration uses complete human source documents, not paragraphs
misrepresented as independent papers.

L2 actions must preserve clarity and logic. The goal is not random irregularity.
A rewrite should remove needless scaffolding and repetitive symmetry while
keeping genre-appropriate organization and readable argument flow. Document-scale
findings are repaired with the fidelity-free partition operators (§2 L4), never by
manufacturing raggedness.

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

The per-paragraph learned classifier (`deai_voice`, axis `L3.voice`) is an
**offline audit instrument, not a product detector one calibration away from an
operating point.** This is a decided status fixed by three measured facts: the
single-paragraph unit is near-unjudgeable (perceptual AUC at chance, EVALUATION
§10); on field-topic text the classifier mis-flags at a high rate while overall
separation stays high (a level confound the paragraph unit cannot escape,
EVALUATION §7); and document-level surprisal dispersion is weaker than the
model-free manifold and adds nothing to it (EVALUATION §9.8). L3 therefore stays
`degraded` with no operating point, emits rank-only triage, and its per-paragraph
findings are confidence-capped (§3, `calibration_unit`).

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

L4 also holds the **cooperative repair tools**, none an AI detector, each turning
the subsystem from a verdict machine into a writing partner. The partition
operator is corpus-referenced and `measured` wherever the human dispersion
manifold is calibrated; the provenance and personal-baseline tools are honestly
`unmeasured` until the author supplies their own draft history or prior papers:

- **`deai_partition`** — fidelity-free merge/split suggestions that move a
  document toward the human dispersion band. Operations touch zero tokens, so the
  protected-invariant sets are byte-identical and the `-inf` fidelity gate cannot
  fire. Suggest-only; reordering deliberately excluded.
- **`deai_provenance`** (axis `L4.editing_provenance`) — matches each current
  paragraph to a designated AI-draft ancestor (an earlier file or a git ref from
  the author's own history) and labels the span by a deterministic token edit
  ratio (`ai_untouched` → `author_original`). It reads only the author's own
  history and never asserts authorship of anyone else's text.
- **`deai_personal`** (axis `L4.personal_baseline`) — uses the author's own prior
  papers as a same-author, same-field, same-jargon dispersion reference,
  sidestepping the field-topic confound entirely, and flags a draft that varies
  paragraph shape far less than the author usually does.

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
calibration_unit         paragraph | section | document | null; the granularity at which the evidence was calibrated
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

`calibration_unit` records the granularity at which a finding's evidence was
calibrated. Because a single paragraph is near-unjudgeable for AI-ness,
**paragraph-unit findings are structurally capped at 0.5 confidence** in the
finding contract itself, not left to each detector. Section- and document-unit
findings are not capped; deterministic evidence (an edit ratio) is exempt. A
`null` unit makes no granularity claim and is uncapped, preserving every legacy
caller.

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

### 5.2 De-AI-ization procedure (去AI化步骤)

Removing machine-writing regularity is layered and ordered. Each step names the
concrete move and the tool; every step is subordinate to invariant protection and
re-measurement (§5 steps 6–7). The order runs cheap-and-deterministic first, then
local structure, then the document-scale keystone, then positive voice, then the
confound-free self-checks.

0. **Measure and record.** Run every applicable axis; list unavailable axes with a
   reason (§0.2). Nothing below acts on an unmeasured axis as if it were clean.

1. **L0 to zero (deterministic).** Remove every Tier A hit and em-dash; bring each
   Tier B word within its section cap. `ai_ism_lint` gates this; L0 is the only
   axis rewritten *to zero*.

2. **L1 distribution.** Where a section is flagged for low burstiness or
   connective-opener signposting, restore field-appropriate sentence-length
   variation and delete roadmap connectives. Do not manufacture random variety;
   vary where the content varies.

3. **L2 sentence structure.** Dissolve announced enumeration, setup-list-wrap
   patterns, repeated modal or anaphoric frames, and symmetric closers into prose
   the argument carries, keeping genre-appropriate organization.

4. **L2 document structure (the keystone).** If the dispersion manifold or
   role-coupling flags over-uniformity, apply `deai_partition` merge/split
   suggestions — fidelity-free, so the `-inf` gate cannot fire — to move the
   document toward the human dispersion band, and let paragraphs differ *where the
   argument demands it* (role coupling), never at random. Length is handled by the
   per-stratum plus conformal calibration, never by normalizing a distance.

5. **L4 anchoring and voice.** Anchor unanchored Results and Methods claims to
   numbers, citations, references, or comparisons (a writing-quality gain, not an
   AI verdict); strengthen the specific claim, the stance, and faithful
   compression using author exemplars. Every added fact is source-traceable.

6. **Confound-free self-checks.** If an AI-draft ancestor exists, run
   `deai_provenance` and rewrite any span still labelled `ai_untouched`. If the
   author's own prior papers exist, run `deai_personal` and match the draft's
   shape variation to the author's own baseline.

7. **Protect invariants and re-measure.** Every move above preserves claims,
   numbers, units, citations, causal direction, stance, and qualifiers (the
   eligibility gate, §6). Re-run every affected axis; a rewrite may not clear one
   signal by adding another defect or dropping evidence.

8. **Disposition and report.** Record each residual advisory's disposition; report
   all four measurement states and before/after counts; never collapse the result
   into a universal verdict.

The procedure improves writing, not detector scores: a clearer, faithful,
better-sourced paragraph is the target, and lowering detector visibility is never
an end in itself.

### 5.3 Condense, do not accumulate (改写、删减、精简，而不是堆叠)

The default direction of every edit is **shorter**. Preference order: delete,
then condense in place, then a same-length rewrite; growth comes last. An edit
that leaves the passage longer than it started is presumed wrong until
justified. The only legitimate reasons to grow are author-requested new content
and a source-verified scientific necessity (a missing assumption, definition,
unit, or caveat whose absence is an integrity defect).

The canonical violation is the **explanatory patch**: answering a finding by
appending a clarifying clause, sentence, or footnote to the flagged text
instead of rewriting the flagged text itself. This rule pairs with the L4
forward-narrative rule (§2 L4): forward narrative bans stacking *states*;
this rule bans stacking *words*.

Fix loops report a length delta (words or characters) for every edited passage
alongside the §5 step-9 counts, and re-measurement (§5 step 7) includes length.
Clearing a detector signal by inflating prose is a defect, not a fix.

Enforcement is mechanical, not aspirational, at two points:

- **Candidate time (preventive).** `rewrite_reward.py --original <paragraph>`
  makes the budget a second hard eligibility gate: a candidate longer than the
  original paragraph scores `-inf` regardless of its style evidence, and a
  condensation bonus prefers the shorter of otherwise-equal candidates.
  `--allow-growth <reason>` lifts the gate for one run and prints the recorded
  reason into the ranking output.
- **Loop close (detective).** `length_gate.py <file> --before <snapshot>` (or
  `--git-ref <ref>`) compares rendered-prose word counts per section between
  the pre-edit and post-edit versions. Each unjustified growing section emits
  a strong advisory (`length-growth:<section>`); `--allow
  "<section>=<reason>"` converts it to an ordinary advisory carrying the
  recorded justification. The exit code gates the NET document budget
  (§0.1): 0 when total growth minus justified growth is within tolerance,
  1 when it exceeds it, 2 for execution failure. A pure section rename
  appears as a paired shrink/growth that nets to zero, so it does not trip
  the exit gate; the paired findings document it for the report.

A fix or rewrite loop may not close (§5.1) while a `length-growth` finding
lacks a disposition: condense back within budget, record the author's
justification, or note the rename that pairs the growth with a shrink.
Comments and mathematics do not count toward the budget; the gate measures
rendered prose. Snapshot the pre-edit version (a scratch copy or the git ref)
before the first edit of every loop, so the gate always has an honest
baseline.

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
| `de-ai` | The single de-AI surface: Pass 1 subsystem measurement (L0–L4), Pass 2 vendored humanizer structural-tell audit, Pass 3 claim-first faithful rewrite under §6 eligibility and the §5.3 length budget; provide the descriptive field-calibration assets; never redefine consequence classes. |
| `condense` | The redundancy/length action surface: execute §5.3 (delete > condense-in-place > same-length; growth only with recorded justification) with one-canonical-home-per-fact deduplication, proven by the length gate; never delete a fact's sole support. |
| `paper-review` | Produce typed findings across dimensions A–R, including the narrative-spine protocol (dimension E) and adversarial escalation (dimension M); verify integrity evidence; allow multiple explicitly related contributions; treat an escalation `CONFIRMED` as a critique that survived verification, then classify its consequence separately; avoid a universal paper verdict. |
| `figure-review` | Separate objective scientific/rendering blockers from aesthetic advisories; measure canvas balance at the pixel level. |
| `brainstorm` | Radial pre-draft ideation: produce candidate directions with evidence, derivation skeletons and reader payoff; never fabricate scientific content or write manuscript prose. |
| `final-review` | Preserve independent isolated reviews (paper-review, figure-review, de-ai audit, MPR); merge typed findings; resolve blockers and L0 targets; record advisory dispositions and unmeasured axes. |
| `proposal-polish` | Funding-proposal register (vision plus feasibility): keep backed ambition, enforce claim-feasibility matching, apply the L0 policy and §6 rewrite invariants unchanged; never fabricate support. |

`docs/DEAI_SUBSYSTEM.md` documents architecture. `EVALUATION.md` records
empirical evidence. Neither overrides this standard.

All of the above except `brainstorm` are normative implementers and must
reference this standard (enforced by `validate_plugin.py` `NORMATIVE_SKILLS`).
`brainstorm` operates before manuscript prose exists; its role row binds its
scope, not a standard-reference obligation.

---

## 8. Tool responsibilities

| Tool | Layer | Required behavior |
|---|---|---|
| `ai_ism_lint.py` | L0 hub plus optional L1-L3 aggregation | Emit text or structured JSON from the same findings; use L0-only exit semantics. |
| `deai_metrics.py` | L1 | Emit calibrated distribution findings and explicit missing-baseline status. |
| `deai_oracle.py` | L1 | Emit surprisal/UID findings with observed and reference values; advisory-success exit 0. |
| `deai_structure.py` | L2 sentence | Emit template evidence with calibration metadata; advisory-success exit 0. |
| `deai_docstructure.py` | L2 document | Measure document shape (per-stratum dispersion manifold, role coupling, split-conformal) with sample-sufficiency checks; one shared `manifold_operating_point` scoring entry. |
| `deai_anchoring.py` | L2 | Emit the section-class claim-anchoring band as a writing-quality axis, never an AI-discrimination axis. |
| `deai_voice.py` | L3 | Emit calibrated similarity evidence, model metadata, and confound status without authorship claims; degraded, offline audit instrument. |
| `deai_feedback.py` | shared | Validate schema (incl. `calibration_unit` cap), attach actions, rank findings, summarize statuses, and serialize output. |
| `rewrite_reward.py` | L3-L4 | Exclude unfaithful candidates before ranking eligible rewrites; rank by L0 advisory reduction and fidelity. |
| `retrieve_exemplars.py` | L4 | Supply author-voice evidence without copying unsupported scientific content. |
| `length_gate.py` | QD (§5.3) | Compare per-section rendered-prose word counts between two document versions; strong advisory and exit 1 on unjustified growth; record `--allow` justifications in the report. |
| `deai_partition.py` | L4 | Suggest fidelity-free merge/split operations toward the human dispersion band; zero-token, suggest-only. |
| `deai_provenance.py` | L4 | Label author edit depth vs a designated AI-draft ancestor from the author's own history; `unmeasured` without one. |
| `deai_personal.py` | L4 | Compare a draft to the author's own prior papers (confound-free reference); `unmeasured` below three papers. |

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
9. **Stratify length; never normalize it away.** Document length is a measured
   confound handled by per-stratum manifolds and length-Mondrian conformal
   operating points. Dividing a document-scale distance by a function of paragraph
   count is prohibited: it exploits systematic length differences between classes
   rather than correcting estimator noise (measured in `EVALUATION.md` §9.8).

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

---

## 11. De-AI subsystem status and open-item dispositions

The ranked de-AI frontier is complete ([`DEAI_FRONTIER.md`](DEAI_FRONTIER.md)).
Every remaining engineering item has a decided disposition, so the standard rests
on no undecided obstacle. Adoption of any item requires passing the §9 confound
audit and keeping the suite and validator green, and updates this table and
`EVALUATION.md` together.

| Item | Disposition | Reason |
|---|---|---|
| Document-scale detection core (dispersion manifold, role coupling, split-conformal, per-stratum) | **Shipped, `measured`** | Calibrated on the complete human corpus; falsification and length-fair AUCs in EVALUATION §9.2–9.5. |
| Cooperative layer (`deai_partition`, `deai_anchoring`, `deai_provenance`, `deai_personal`) | **Shipped** | Partition/anchoring `measured`; provenance/personal `unmeasured` by design until the author supplies own history/papers. |
| `L3.voice` operating point | **Decided degraded** | Offline audit instrument; per-paragraph unit near-unjudgeable and document-level surprisal refuted (§2 L3, EVALUATION §7, §9.8). |
| `L1.distribution` operating point | **Decided degraded** | No `deai_policy.json` field-calibrated operating point; burstiness/signposting summaries exist but carry no policy threshold (EVALUATION §2). |
| `L1.uid` operating point | **Decided degraded** | No field-policy-calibrated compatibility operating point; the surprisal path is measured not to add document-level power. |
| Enriched surprisal features (roadmap rank 5) | **Done, not shipped** | Better than the three scalars but inert for the model-free detector, so recorded not shipped (EVALUATION §9.8). |
| Length normalization of manifold distance | **Rejected** | A length-confound exploit, not a noise correction (guardrail 9, EVALUATION §9.8). |
| Baseline unification into one `(feature, unit)` object (rank 2) | **Deferred (elegance debt)** | Explicitly a staged consolidation, never a rewrite; the current architecture is correct and green. |
| Jargon-conditional per-paragraph operating point (rank 3) | **Won't pursue as scoped** | The jargon confound is handled at document scale by per-stratum + conformal; a per-paragraph operating point is inconsistent with the L3-degraded decision. |
| `corpus_cos` ablation (rank 4) | **Deferred (audit-only)** | Documented as a field-register confound feature in the degraded, audit-only classifier; marginal value while L3 has no shipped operating point. |
| Topic-orthogonal axes: cohesion, hedging, citation placement (rank 6) | **Deferred, blocked** | Citation placement is blocked on the `extract_style` `\cite`-flattening root-cause fix; each is a future calibrated axis, not a gap in this spec. |
| Long-form generation (`ai_long`) | **Standing falsification target** | A recorded measured limit (EVALUATION §9.7); future detector work is benchmarked against it. |
