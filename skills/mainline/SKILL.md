---
name: mainline
description: 论文主线与叙事结构审查器。完整 cold-read 论文，建立 contribution graph、claim dependencies、section functions 和读者困惑点；用 SCIPAPER_STANDARD 的 typed feedback 区分科学/论证 blocker、strong narrative advisory 与 ordinary editorial advisory。支持多个明确相关的贡献，不预设所有论文只能有一条线；保留隔离上下文可读性验证和发散方向收敛。Use when 用户说主线不清、叙事乱、章节衔接有问题、mainline、整合 brainstorm 输出或做 spine-level review。
disable-model-invocation: false
argument-hint: "<file_path> [--max-iter N] [--no-fix] [--skip-isolated-readability] [--orchestrator-isolated] [--from-brainstorm <shortlist>] [--field <name>]"
---

# mainline — contribution-graph and cold-read feedback

> **Normative authority:** `docs/SCIPAPER_STANDARD.md`.
> `paper-review` verifies per-claim scientific correctness; this skill examines how
> those claims are organized and understood. It does not define a separate paper
> PASS/FAIL or require every editorial preference to disappear.

Workflow:

read → map contribution graph → collect cold-read evidence → type/rank findings →
edit → re-read → disposition

## 0. Hard rules

1. **Read the complete current manuscript.** Mainline is a global property; grep and
   abstract-only sampling cannot establish it.
2. **Do not rely on memory.** Reconstruct claims, dependencies and section functions
   from the current file and cited evidence each round.
3. **Do not guess the intended spine.** If a contribution or dependency cannot be
   inferred, record the ambiguity and its location.
4. **Do not bridge logical gaps with connectors.** `Furthermore`, `Moreover`,
   `Additionally` and similar transitions cannot replace a missing premise, broken
   dependency or wrong section order.
5. **Multiple contributions are legitimate.** A paper may contain several contributions
   when their relationship, shared question and evidence dependencies are explicit.
   Disconnected components are evidence to investigate, not an automatic fatal verdict.
6. **Cold-reader confusion is evidence.** It must be classified by consequence and
   addressed or dispositioned; it is not automatically an integrity blocker.
7. **Scientific fidelity is eligibility for edits.** Narrative changes may not alter
   numbers, units, citations, mathematics, entities, comparison direction, negation,
   causal direction, scope or stance.
8. **Use unified findings.** Missing required argument or claim/evidence contradiction
   may be `integrity_blocker`; L0 rules remain `l0_target`; narrative and structure
   findings are generally advisories.
9. **No universal zero-advisory convergence.** Strong advisories require a disposition;
   ordinary advisories remain visible without blocking workflow completion.

## 1. Preparation and maps

1. Read `docs/SCIPAPER_STANDARD.md`, `/sci-paper:paper`, and the target manuscript.
2. Resolve optional field evidence. Missing dossier/baseline is `unmeasured`, not clean.
3. If `--from-brainstorm` is supplied, read the shortlist as provenance for candidate
   directions, not as an obligation to include all of them.
4. Build a **paper-level purpose record** with source locations:
   - `root_question`;
   - `contributions[]`;
   - `method_or_argument` for each contribution;
   - `key_evidence[]`;
   - `take_home` and scope.
5. Build a three-level outline:
   - section title and function;
   - paragraph claim/topic;
   - claim → evidence/derivation/dependency pointers.
6. Build a contribution graph:
   - nodes: claims, definitions, methods, evidence and conclusions;
   - directed edges: prerequisite, supports, qualifies, contrasts, derives-from;
   - named contribution subgraphs;
   - explicit relations among subgraphs and the shared root question.
7. Record disconnected nodes/components, but do not classify them until their scientific
   or rhetorical role is read in context.
8. Run the shared de-AI report when available:

```bash
python tools/ai_ism_lint.py <file> --field <field> \
  --structure --distribution --document-structure --oracle --voice \
  --format json --output <scratch>/mainline-feedback.json
```

Structural and learned signals are advisory evidence and retain their measurement state.

## 2. Positive review lenses

### A1. Purpose and contribution clarity

- Can a cold reader state the root question without importing project context?
- Is each contribution stated at the strength and scope supported by its evidence?
- Are the contributions related explicitly rather than merely placed in one list?
- Do abstract, introduction and conclusion describe the same contribution set?

A missing or contradictory central scientific claim can be an `integrity_blocker`.
A contribution that is real but hard to infer is normally a strong advisory.

### A2. Information economy

- Does each paragraph add a claim, definition, evidence, qualification or necessary link?
- Are repeated explanations, nominalizations and low-information modifiers removable?
- Can a passage be compressed without losing scientific content?

Compression is advisory unless duplication creates conflicting versions or stale science.
Do not impose a fixed percentage reduction on every paragraph.

### A3. Narrative architecture

- Does section order follow scientific and logical dependencies?
- Does each section have a recognizable function?
- Are result, interpretation and limitation located where readers can connect them?
- Does the architecture fit the paper genre rather than a mandatory three-act template?

### A4. Reader orientation

- Are definitions introduced before use?
- Do transitions name the actual dependency, object, equation or result?
- Are cross-references specific and correct?
- Can a reader resume after a section break without reconstructing hidden context?

### A5. Derivation completeness

- Are assumptions and symbols available before each derivation?
- Is every important inferential jump explained or delegated to a valid appendix/reference?
- Does the prose distinguish algebraic consequence, physical interpretation and empirical
  observation?

Correctness belongs to `paper-review`; missing steps that make a core conclusion unsupported
may still be an `integrity_blocker` here.

### A6. Logical sufficiency

- Do conclusions follow from the stated premises and evidence?
- Are causal, necessary/sufficient and generalization claims justified?
- Are limitations propagated to the take-home message?

### A7. Contribution chaining

- For each contribution, is the chain question → method/argument → evidence → conclusion
  complete?
- If there are several contributions, is their relation explicit: shared method, staged
  dependency, common dataset, theorem-to-application, or coordinated answer to the root
  question?
- Are orphan claims genuine supporting material, misplaced content, or a separate paper?

A graph with multiple components is not automatically wrong. It becomes a blocker only if
required logical support is absent or the manuscript asserts a unity that the evidence
contradicts. Otherwise it is a ranked narrative advisory.

## 3. Negative review lenses

### B1. Undefined or circular concepts

Locate undefined terms, circular definitions, overloaded symbols and vague operational
language. Semantic conflict is a blocker; clear-but-improvable wording is advisory.

### B2. Unexplained contribution fragmentation

Look for contributions that share no stated question, dependency, method or implication.
Recommend one of:

- explain the true relation;
- subordinate a supporting result;
- move a tangential result to a justified location;
- remove it;
- propose a separate paper, but do not delete scientific content without author approval.

Do not force a single thread merely because the graph has more than one component.

### B3. Breadth without development

Find method variants not used, related-work catalogues without synthesis, repeated claims,
and sections that open directions without evidence or closure. Type by consequence rather
than calling every instance fatal.

### B4. Broken section dependencies

Find sections whose inputs were not introduced, results with no method, discussion claims
with no result, and conclusions with no supporting chain. A missing required dependency is a
blocker; a weak transition is advisory.

### B5. Ambiguous architecture

Check excessive nesting, headings that hide section function, mixed method/result/discussion
responsibilities and sequences that violate dependency order. Genre and journal conventions
matter; there is no fixed maximum valid subsection count.

### B6. Missing scientific narrative

Find activity logs (`we did X, then Y`) without question or interpretation, result lists with
no implication, and motivation that does not connect to the contribution. Add only
source-supported interpretation; never invent significance.

### B7. Context drift

Check terminology, symbols, assumptions, sample definitions, scope and contribution labels
across sections. Scientific conflict is a blocker; alias inconsistency is advisory.

### B8. Low-information language

Use search only to locate candidates such as vague quantifiers, unsupported evaluative
adjectives and empty nouns. Read each in context:

- retain measured or technically defined language;
- replace unsupported evaluation with verified quantities when sources exist;
- delete padding;
- keep necessary uncertainty rather than fabricating precision.

A word match alone is not a finding. Tier A/Tier B/em-dash consequences come from the shared
L0 policy, while ordinary vagueness is advisory unless it changes claim validity.

## 4. Brainstorm convergence

Run whether or not a shortlist was supplied:

1. Enumerate candidate directions actually present in the manuscript.
2. Distinguish:
   - separate contributions coordinated by the paper's root question;
   - supporting analyses;
   - speculative discussion;
   - process artifacts or abandoned directions.
3. For each direction, record evidence, dependency and reader payoff.
4. Recommend concentration only where a direction is unsupported, distracts from the stated
   scope, duplicates another claim or belongs in another work.
5. Do not hide discarded directions under generic `future work`; retain an open question only
   when it is scientifically motivated by current evidence.
6. After restructuring, re-check abstract/introduction/conclusion and scientific fidelity.

## 5. Isolated cold-read verification

Use exactly one of these execution paths:

- standalone invocation: unless `--skip-isolated-readability` is explicitly supplied, launch a
  fresh isolated worktree reader after the in-process graph is stable;
- parent-orchestrated invocation: with `--orchestrator-isolated`, the current process is already
  the fresh isolated worktree reader, so it performs the questionnaire itself and must not spawn
  a nested agent;
- explicit user skip: `--skip-isolated-readability` leaves this axis `unmeasured`.

The selected reader must read the current manuscript from start to finish without prior
summaries and answer with file:line evidence:

1. What is the root question?
2. What contributions does the paper make?
3. How are those contributions related?
4. What method or argument supports each contribution?
5. What is the key evidence for each?
6. What is the take-home message and scope?
7. Where did the reader need to backtrack, infer missing context, or choose between competing
   interpretations?

The isolated reader does **not** need to answer “single thread”. Multiple contributions are
acceptable if the reader can state their relation. Each confusion is converted to a typed
finding:

- contradiction or missing required support → `integrity_blocker`;
- high-exposure, reproducible confusion with a concrete repair → strong advisory;
- local wording preference → ordinary advisory;
- false inference unsupported by the text → `rejected_as_false_positive` with explanation.

Agent failure or an explicit skip is reported as `unmeasured`, never as a clean result.

## 6. Fix and re-measure

Default behavior fixes authorized manuscript content; `--no-fix` reports only.

1. Rank findings by the unified standard.
2. Resolve integrity blockers before narrative polish.
3. Remove L0 targets without introducing semantic drift.
4. Apply the minimum structural edit that repairs a strong advisory.
5. Preserve numbers, units, citations, math, acronyms, entities, comparison/causal direction,
   negation, scope, stance and logical dependencies.
6. Re-read the modified section and all dependent abstract/conclusion passages.
7. Rebuild the affected contribution graph and rerun the shared feedback report.
8. Re-run `paper-review` after any substantive claim or derivation change.

Do not fix broken logic with a transition phrase, decorate weak structure with adjectives, or
turn every multi-contribution paper into one artificial list.

## 7. Stopping rule

Stop as `DISPOSITION_COMPLETE` when:

- all narrative-related integrity blockers are resolved or verified false positives;
- applicable L0 targets are zero;
- every strong narrative advisory is acted, accepted, rejected as false positive, or pending
  with a stated reason;
- ordinary advisories and unavailable axes are reported;
- isolated cold-read evidence is incorporated or explicitly unavailable;
- all edits preserve scientific fidelity.

If `--max-iter` is reached, return `BREAK_WITH_USER_DECISION` with unresolved findings. Do not
increase the budget silently and do not issue a universal paper-quality verdict.

## 8. Report contract

```markdown
# Mainline — Typed Feedback Report
Target: <file> | Field: <field or none> | Workflow state: <state>

## Purpose and contribution record
- root question: ... (file:line)
- contributions: ... (file:line)
- contribution relations: ...
- key evidence: ...
- take-home and scope: ...

## Contribution graph
- nodes/edges/components
- component roles and explicit relations
- orphan or ambiguous nodes

## Measurement state
| axis | status | provenance / limitation |

## Ranked findings
| id | kind | layer | rule | location | evidence | action | disposition |

## Cold-read evidence
<answers 1–7 and typed confusion findings>

## Residual feedback
- pending strong advisories
- ordinary advisories
- degraded/unmeasured axes
- author decisions required
```

Do not emit PASS/FAIL rows or claim that zero L0 targets proves a coherent manuscript.

## 9. Interfaces

- `/sci-paper:paper`: writing and L0 guidance.
- `/sci-paper:paper-review`: scientific integrity and source tracing.
- `/sci-paper:paper-style`: descriptive corpus evidence.
- `/sci-paper:rewrite-in-voice`: claim-first paragraph reconstruction.
- `/sci-paper:brainstorm`: candidate direction provenance.
- `/sci-paper:final-review`: isolated multi-review orchestration.

## 10. Anti-patterns

- Inferring the spine from keywords or the abstract alone.
- Treating component count greater than one as automatic failure.
- Forcing every paper into problem → gap → method → result → implication.
- Dismissing cold-reader confusion because the subject is technical.
- Requiring every editorial advisory to disappear.
- Using learned field-similarity as authorship evidence.
- Replacing necessary uncertainty with invented numbers.
- Deleting a valid secondary contribution without author review.
- Calling an advisory-only report a failed paper.
