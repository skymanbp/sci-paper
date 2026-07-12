---
name: rewrite-in-voice
description: 根本性去 AI 改写器。按 SCIPAPER_STANDARD 的反馈协议处理结构性 AI 感：读取 ranked JSON，抽取 claim graph 与受保护科学不变量，从论点重新造句，以作者语料作正向锚点，生成多个候选，只在通过科学保真 eligibility 的候选中排序，复测并展示 before/after 供作者认领。Use when 用户说 "太 AI 了" / "去 AI 感" / "像人写的" / "rewrite in voice" / "重写得像我" / "机器味太重"。
disable-model-invocation: false
argument-hint: "<file_path> [--section <name>] [--n N] [--max-iter N] [--no-apply] [--distill] [--field <name>]"
---

> **Normative authority:** `docs/SCIPAPER_STANDARD.md`.
> This skill implements the standard's measure → type → rank → edit →
> re-measure → disposition loop. `docs/DEAI_SUBSYSTEM.md` explains the design;
> style profiles and learned models provide evidence, not competing policy.

# rewrite-in-voice — claim-first scientific rewrite

## 0. Non-negotiable rules

1. **Rebuild from claims, not surface substitutions.** Do not treat synonym swaps,
   connector deletion, or punctuation cleanup as a structural rewrite. Extract the
   paragraph's claim graph, evidence relations, qualifiers, and protected scientific
   content, then compose new sentences.
2. **Scientific fidelity is eligibility.** A candidate that drops a number, unit,
   citation, mathematical expression, acronym, comparison direction, negation, or
   causal direction is ineligible regardless of its style score. Named entities,
   stance, scope, and logical dependencies still require source-aware verification.
3. **Never add specificity from imagination.** Every number, entity, citation, and
   quantitative qualifier must already exist in a verified source read in the same
   turn. Specificity means retaining supported detail, not inventing it.
4. **Learned scores are advisory field-similarity signals.** They do not establish
   authorship and they are not paper gates. Missing calibration is reported as
   `degraded` or `unmeasured`, never interpreted as a clean result.
5. **Human control is explicit.** Show before/after, fidelity evidence, ranked
   findings, and residual dispositions. `--no-apply` produces proposals only.
6. **Minimum effective edit.** Rewrite only the paragraphs whose ranked findings or
   author instruction justify intervention. Do not homogenize unaffected prose.

## 1. Prepare and measure

1. Read the target file completely, then map paragraphs to sections and line ranges.
2. Resolve `--field` using the same rules as `paper-style`. A missing profile does
   not erase feedback: model-free axes still run and unavailable axes are reported.
3. Run the unified linter to a machine-readable report:

   ```bash
   python tools/ai_ism_lint.py <file> --field <field> \
     --structure --distribution --document-structure --oracle --voice \
     --format json --output <scratch>/feedback-before.json
   ```

4. Read the report as `sci-paper.feedback.v1`. Select work in ranked order:
   - any `l0_target` in the requested paragraph;
   - strong L2/L1/L3 advisories with concrete actions;
   - ordinary advisories the author explicitly asks to address;
   - document-shape findings whose location identifies a repeated section arc.
5. Do not select a paragraph solely because a compatibility score crosses an
   uncalibrated fixed threshold. Record degraded and unmeasured axes in the report.

## 2. Rewrite one paragraph

### 2.1 Build the protected claim record

Create `<scratch>/claim.txt` containing, in compact form:

- every scientific claim and its evidence relation;
- all numbers and units;
- all citations and named entities;
- all inline mathematical expressions and acronyms;
- comparison direction, negation, causal direction, scope, stance, and qualifiers.

This record may discard padding, but it must not discard protected content. Re-read
all numerical and citation sources in the same turn before writing it.

### 2.2 Retrieve positive voice anchors

When a valid exemplar bank exists:

```bash
python tools/retrieve_exemplars.py --section <section-type> \
  --topic "<claim summary>" --k 5 --field <field>
```

Read all returned exemplars. Use them only for rhythm, information distribution,
register, and transition practice. Never copy claims or distinctive wording.

### 2.3 Generate N independent candidates

Generate `N` candidates, default 5, from the protected claim record rather than by
editing the original sentence-by-sentence. Each candidate must:

- preserve every protected item and relation;
- state the claim at the same strength and scope;
- avoid new facts, citations, numbers, entities, or mechanisms;
- avoid Tier A terms and em-dashes;
- keep Tier B use within the standard's per-section/per-word cap;
- break the specific L2 pattern that motivated the rewrite, such as announced
  enumeration, setup/list/wrap-up symmetry, repeated modal frames, anaphoric runs,
  balanced closers, or repeated paragraph geometry;
- retain technically necessary lists and parallel syntax when they encode a real
  scientific distinction rather than decorative symmetry.

Write each candidate to `<scratch>/cand_<k>.txt`.

### 2.4 Enforce fidelity eligibility and rank

```bash
python tools/rewrite_reward.py --field <field> \
  --reference <scratch>/claim.txt \
  --candidates <scratch>/cand_0.txt <scratch>/cand_1.txt ...
```

Interpret the output as follows:

- `eligible=False` means the candidate cannot be selected.
- `missing_invariants` identifies the deterministic preservation failure.
- Among eligible candidates, `combined` ranks learned field similarity,
  specificity retention, and semantic similarity.
- If no candidate is eligible, preserve the original paragraph and regenerate with
  tighter constraints. Never choose the least-bad ineligible candidate.

After ranking, manually verify named entities, claim scope, stance, qualifiers, and
logical dependencies against the original paragraph and its sources. The deterministic
checker is necessary but not sufficient.

### 2.5 Re-measure the candidate

Create a temporary file with enough section context for section-level caps and run:

```bash
python tools/ai_ism_lint.py <scratch>/candidate-context.tex --field <field> \
  --structure --distribution --document-structure --oracle --voice \
  --format json --output <scratch>/feedback-after.json
```

Compare finding IDs/rules and measurement states. A successful local rewrite must:

- introduce no new integrity blocker or L0 target;
- remain fidelity-eligible;
- act on the selected strong advisory, or record why the author accepts/rejects it;
- avoid worsening a higher-priority finding elsewhere in the section;
- report all residual advisories and unavailable axes.

No advisory must be forced to zero merely to satisfy a detector. If an apparently
strong signal conflicts with clear scientific prose, retain the prose and record an
`accepted` or `rejected_as_false_positive` disposition with evidence.

### 2.6 Apply with author-visible evidence

Show:

- before and after text;
- protected invariants and eligibility result;
- relevant before/after ranked findings;
- remaining strong and ordinary advisories;
- proposed dispositions.

Unless `--no-apply` is set, apply the selected rewrite with a minimal Edit and re-read
the changed region in context.

## 3. Whole-file stopping rule

Repeat measurement after all selected paragraphs. Stop only when:

- all integrity blockers are resolved or verified false positives;
- applicable L0 targets are zero;
- every strong advisory is `acted`, `accepted`, `rejected_as_false_positive`, or
  remains `pending` with a stated reason;
- ordinary advisories and `degraded`/`unmeasured` axes are reported;
- all changed paragraphs pass scientific-fidelity verification.

This is a disposition-complete feedback state, not a universal prose PASS verdict.
If the iteration budget is exhausted, leave the original text for unresolved cases
and return the pending findings to the author.

## 4. Optional self-distillation

Only paragraphs explicitly accepted by the author may enter
`style-profile/<field>/exemplar_paragraphs.jsonl`. Record provenance and section type.
Never feed automatically generated or merely detector-favored text back as human
positive data. Retraining must include held-out and confound-aware evaluation; if it
is a multi-minute heavy run, execute it on appropriate cloud infrastructure.

## 5. Report contract

```markdown
# rewrite-in-voice — Feedback Report
Target: <file> | Field: <field> | Candidates per paragraph: N
Measurement: <axis=status list>
Paragraphs considered: K | rewritten: R | unchanged: U
L0 targets: before B -> after A
Strong advisories: acted X | accepted Y | false-positive Z | pending P

## Paragraph changes
- <line/section>: <finding ids and rules>
  - eligibility: true/false; missing invariants: ...
  - before/after: ...
  - disposition: acted/accepted/rejected_as_false_positive/pending

## Residual feedback
<ranked ordinary advisories and unavailable axes>
```

## 6. Interfaces

- `docs/SCIPAPER_STANDARD.md`: normative consequence, ranking, disposition, and
  stopping semantics.
- `/sci-paper:paper`: writing guidance and canonical L0 prose examples.
- `/sci-paper:paper-style`: descriptive corpus evidence and exemplar retrieval.
- `/sci-paper:paper-review`: scientific integrity and source verification after edits.
- `/sci-paper:mainline`: document-level narrative feedback after structural changes.
- `tools/ai_ism_lint.py`: shared structured measurement report.
- `tools/rewrite_reward.py`: hard fidelity eligibility plus eligible-candidate ranking.
