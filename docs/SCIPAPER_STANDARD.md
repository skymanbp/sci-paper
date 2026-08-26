# The sci-paper Standard

> **The single normative core.** Writing (`/sci-paper:paper`), checking
> (`/sci-paper:paper-review`, `figure-review`, `final-review`), de-AI
> rewriting (`/sci-paper:de-ai`) and condensation (`/sci-paper:condense`)
> implement this document. If a skill,
> tool, style profile, or workflow conflicts with this file, this file wins.
>
> Status: **v3.7 (2026-08-25)**. v3.7 moves §11's disposition register to
> [`architecture/DISPOSITIONS.md`](architecture/DISPOSITIONS.md) and this
> version history to [`../CHANGELOG.md`](../CHANGELOG.md), so the contract is
> the contract. No consequence class, exit code, ranking rule, or measurement
> state changed. The substantive change is recorded in that register:
> `L1.distribution`'s operating point is now **refuted by measurement** rather
> than merely absent, so `deai_policy.json` is withdrawn as an adoption
> candidate. §§0-10 are otherwise unchanged from v3.6.

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
configuration failure, or execution failure. Two exceptions carry their own
narrow actionable contracts, and in both the meaning of `1` is a measured
outcome the caller must act on, never a failure:

- `length_gate.py` returns 0 when the document's net unjustified prose growth
  is within tolerance, 1 when it exceeds the tolerance, and 2 for invalid input
  or execution failure (§5.3);
- `rewrite_reward.py` returns 0 when at least one candidate is eligible, 1 when
  every candidate fails scientific-fidelity or length-budget eligibility (the
  caller preserves the original and regenerates tighter, §6), and 2 for invalid
  input or missing required configuration.

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
field-specific operating points belongs in [`EVALUATION.md`](architecture/EVALUATION.md),
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

A second lexical axis, `L0.register` (`deai_register`), sits at this layer
without joining the to-zero set. It measures whether the draft speaks its own
field's vocabulary, by comparing terms the manuscript leans on against document
frequency in the field's own corpus. The evidence must be corpus frequency and
never a curated list of another discipline's words: in the astronomy reference
`AUC` appears in 1 passage of 15,599 while `epoch` appears in 402 and
`accuracy` in 774, so a hand-written "ML vocabulary" list flags all three. A
hyphenated compound is judged by its rarest part, because hyphenation is an
open construction and every compound is corpus-rare. Register findings are
always advisories: a corpus-rare term may be a borrowed method's accepted name,
or the concept the paper is introducing, and only the author can say which.

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

A third L2 axis, `L2.salience_hierarchy` (`deai_salience`), measures whether a
passage ranks the quantities it reports or recites them. Sentence structure and
document shape both stay silent here: a passage can vary its sentence lengths,
sit inside the human dispersion band, and still hand the reader an undifferentiated
inventory of results. The measured quantity is deliberately not numeric density,
because a quantitative abstract is supposed to carry numbers; it is how far the
numerals run without an interpreting sentence between them. A human writer stops
to say what a result establishes before reporting the next one. Calibration is
per section bucket on the field's own passage banks, at one unit (a passage) on
both sides, and the reading is P(X ≤ x) against a fine quantile grid, because two
of the three features are ratios of small integers whose reference distributions
are tie-heavy. Where a reference has no spread above the advisory gate the
feature abstains: with every upper-tail passage sharing one value, P(X ≤ x)
reaches 1.0 there and an ordinary passage would read as the 100th percentile.
The repair is ranking, never deletion, and a number that is the sole support of
a claim stays where it is.

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

1b. **L0 register (corpus-referenced, author-decided).** Where `deai_register`
   reports a term the field's corpus does not carry, choose one of three
   dispositions and record it: name the quantity the field already has a word
   for, keep the borrowed term but define it at first use in field terms, or
   confirm the definition is present if the paper is introducing the concept.
   This step never runs to zero and never swaps a term whose replacement would
   change the claim.

2. **L1 distribution.** Where a section is flagged for low burstiness or
   connective-opener signposting, restore field-appropriate sentence-length
   variation and delete roadmap connectives. Do not manufacture random variety;
   vary where the content varies.

3. **L2 sentence structure.** Dissolve announced enumeration, setup-list-wrap
   patterns, repeated modal or anaphoric frames, and symmetric closers into prose
   the argument carries, keeping genre-appropriate organization.

3b. **L2 salience hierarchy.** Where `deai_salience` reports a passage reciting
   its quantities, rank them instead of deleting them: keep the numbers the
   passage's own claim rests on, state what they establish, and let the section
   that argues from a supporting value carry it. A number that is the sole
   support of a claim never leaves. Because the repair moves emphasis rather
   than facts, it is subject to §6 eligibility and the §5.3 budget like any
   other rewrite, and an accepted disposition is the right outcome wherever the
   density is what the genre requires (a methods paragraph specifying a
   parameter grid).

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

### 5.4 Thesis spine: one result, everything subordinate to it (文章主旨)

A paper that reports everything its authors did, in the order they did it, has
an inventory where its thesis should be. Every entry can be true, sourced, and
non-redundant, and the reader still finishes it knowing what was *done* rather
than what was *found*. This is the failure §5.3 cannot reach: condense removes
what is **repeated**, and an inventory repeats nothing. What it lacks is rank.

The rule is one rule applied at three nested scales.

**Document.** The paper has exactly one central result, and it is statable in
one sentence. Every section earns its place by serving that sentence — setting
it up, introducing it, explaining it, deriving it, or arguing for it. A second
result is either subordinate to the first or belongs in a second paper.
The reader must finish able to answer three questions in order: what was done,
what the result is, and why it changes anything. A draft that answers only the
first is an inventory regardless of how well written it is.

**Paragraph.** One claim per paragraph, carried by its own sentence. Every
other sentence in the paragraph answers one of two questions about that claim:
on what grounds, or therefore what. A sentence that answers neither is cut, or
the paragraph has two claims and should be split.

**Clause.** Every clause either introduces a checkable new fact — a number, a
measurement, a named object, a concrete procedure — or binds two propositions
already in play. A clause that does neither is evaluation, purpose attribution,
or restatement, and it goes. The diagnostic form is a pointer: name the earlier
sentence, equation, or citation the clause depends on. A clause whose
antecedent cannot be named does not have one.

**The inventory test** makes this checkable rather than aspirational. For each
section, write two things: the one sentence that section contributes to the
central result, and the location in the section that carries it. A section with
no such sentence is inventory and is cut or folded. Two sections whose
sentences say the same thing are one section. The test is cheap, its output is
a table, and a reader can falsify any row in seconds.

**Protection outranks all of it.** Every §6 invariant survives unchanged, and
the qualifier class is the one this section most endangers: a clause that
narrows a claim — a condition, a range, an uncertainty, a scope limit, a
negation, a conceded limitation — is load-bearing **by definition** and is
never padding, however evaluative it sounds. A pass that shortens a paper by
deleting its hedges has damaged it, not improved it.

**Measurement status: this section is a writing rule, not a measured axis.**
No detector reports it and none is calibrated for it, because the underlying
signal has been measured three times and refuted three times — claim anchoring
against strong-model generations (EVALUATION §9.6), the hypotaxis ratio
(EVALUATION §14.5), and inert-clause runs plus inference-connective rate
(EVALUATION §15.1). The defect is a relation between a clause and the
propositions around it, not a surface property of the clause, so surface
statistics do not see it. Nothing in this section may be turned into a
threshold, an exit code, or an advisory count without new evidence, and a
later session proposing one of the three refuted features must read §14 first.

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

## 7-8. Skill and tool responsibilities

Every skill's required role and every tool's required behaviour are tabulated in
[`architecture/RESPONSIBILITIES.md`](architecture/RESPONSIBILITIES.md),
**incorporated by reference and normative**. It was moved out of this file on
2026-08-25 when the file passed the repository's line budget, and it has no
independent authority: where it and this document could be read to differ, this
document wins.

Every normative implementer must reference this standard (enforced by
`validate_plugin.py` `NORMATIVE_SKILLS`). `brainstorm` is the one exception: it
operates before manuscript prose exists, so its annex row binds its scope rather
than imposing a standard-reference obligation.

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

The ranked de-AI frontier is complete
([`DEAI_FRONTIER.md`](design-notes/DEAI_FRONTIER.md)). Every remaining
engineering item has a decided disposition, so the standard rests on no
undecided obstacle.

The register itself — every item, its disposition, and the measurement behind it
— is [`architecture/DISPOSITIONS.md`](architecture/DISPOSITIONS.md), moved there
on 2026-08-25 when this file passed the repository's line budget. It is a record
of decisions, not independent policy: this document stays the single normative
contract. Adoption of any item requires passing the §9 confound audit and
keeping the suite and validator green, and updates that register and
`EVALUATION.md` together.
