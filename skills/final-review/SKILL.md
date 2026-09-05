---
name: final-review
description: Pre-submission final-review orchestrator. Each round loads /sci-paper:paper and SCIPAPER_STANDARD as the framework, then runs paper-review (all A-R dimensions, including the narrative spine and adversarial escalation), figure-review, de-ai (--audit-only structural-tell audit) and the physics, mainline and logic measurement primitives in isolated worktrees. Merges sci-paper.feedback.v1 typed findings: scientific-integrity blockers must be resolved, L0 targets must reach zero, strong advisories must carry a disposition, and ordinary advisories plus unavailable axes stay visible in the report. Verifies that this disposition-complete state is stable across consecutive rounds rather than forcing all editorial feedback to zero, and never emits a universal paper PASS/FAIL. Use for: final review, submission-readiness evidence gathering, isolated orchestration of every review skill, 投稿前总审.
disable-model-invocation: false
argument-hint: "<file_path> [--max-rounds N] [--skip <skill>[,<skill>...]] [--field <name>] [--out <dir>] [--require-consecutive N]"
---

# final-review — isolated typed-review orchestrator

> **Normative authority:** `docs/SCIPAPER_STANDARD.md`.
> This skill verifies a stable, disposition-complete review state. It does not certify
> journal acceptance, authorship, aesthetic perfection or a universal paper PASS.

The required review components are:

1. `/sci-paper:paper` as the writing and L0 framework;
2. `/sci-paper:paper-review` for A–R source-traced scientific review, including
   the narrative-spine protocol (dimension E) and adversarial escalation (dimension M);
3. `/sci-paper:figure-review` for compiled-page figure evidence;
4. `/sci-paper:de-ai` in `--audit-only` mode for the structural-tell and de-AI
   measurement audit;
5. `/sci-paper:physics` for the first-principles checklist (P1-P8);
6. `/sci-paper:mainline` for the narrative-spine cold read;
7. `/sci-paper:logic` for reasoning, statistics and claim-evidence discipline.

Components 5-7 are measurement primitives that paper-review also composes. The parent
launches them at its own level so their cold read is independent of paper-review's
context rather than nested inside it.

`/sci-paper:condense` is an action skill, not a reviewer: redundancy findings
surface through paper-review dimension I, and the parent routes their fixes to
condense during §3.7. Keeping detection in one lane avoids duplicate review surfaces.

## 0. Hard orchestration rules

1. **Run, do not remember.** Every round launches fresh isolated reviewers for all non-skipped
   components. Prior reports are comparison artifacts, not substitutes for current review.
2. **Isolation is mandatory.** paper-review, figure-review, de-ai, physics, mainline and logic run
   in separate `isolation: worktree` agents. The parent loads `paper` and the standard, merges
   reports and applies authorized fixes.
3. **No nested agents.** paper-review receives `--orchestrated`; the parent launches physics,
   mainline and logic at the same level as the other reviewers. paper-review's M.2 escalation is in-process by design.
   Any child attempt to spawn an agent is a prompt error.
4. **Preserve evidence, not verdict authority.** The parent may not discard a child finding,
   but must verify/deduplicate it and type its consequence. A CONFIRMED critique is not
   automatically an integrity blocker.
5. **Merge by structured contract.** Each child returns or is normalized to
   `sci-paper.feedback.v1`; text and JSON derive from the same findings.
6. **Scientific blockers are non-waivable.** Incorrect math/physics/statistics, source or
   citation mismatch, leakage, contradiction, broken required build and missing required
   artifacts must be resolved or verified false positives.
7. **L0 target is zero.** Tier A, em-dash and Tier B excess must be removed.
8. **Advisories use dispositions.** Strong advisories must be acted, accepted, rejected as
   false positives, or pending with a stated reason. Ordinary advisories remain visible and
   do not have to disappear.
9. **Measurement states remain explicit.** A skipped, failed or unavailable axis is
   `unmeasured`/`degraded`, not clean.
10. **Minimum effective fixes only.** Every edit maps to a finding ID; no opportunistic
    rewriting or unrelated refactor.
11. **Stable rounds verify state, not zero suggestions.** `--require-consecutive` rounds must
    reproduce a disposition-complete state with no new blockers/L0 and no unexplained change
    in strong advisories.
12. **Do not expand budget silently.** `--max-rounds` exhaustion returns
    `BREAK_WITH_USER_DECISION` with the exact unresolved state.

## 1. Invocation and states

```text
/sci-paper:final-review <file_path> [flags]
```

Defaults:

- `--max-rounds 10`
- `--require-consecutive 2`
- no skipped reviewers
- output under `final-review-out/<date>__<slug>/`

Valid skips: `paper-review`, `figure-review`, `de-ai`, `physics`, `mainline`, `logic`.
A skip must be user-explicit, remains visible as `unmeasured`, and cannot be described as
reviewed. A figure-less document normally yields `not_applicable`, not PASS.

Workflow states:

- `IN_PROGRESS`
- `DISPOSITION_COMPLETE`
- `BREAK_WITH_USER_DECISION`
- `SUBAGENT_FAILURE`
- `PROMPT_VIOLATION`
- `USER_INTERRUPTED`

## 2. Preparation

1. Read the current target manuscript completely.
2. Read `docs/SCIPAPER_STANDARD.md` and the current SKILL.md files for paper, paper-review,
   figure-review, de-ai, physics, mainline and logic.
3. Resolve field evidence; missing assets remain explicit.
4. Create the output root and round directory.
5. Initialize a finding registry keyed by stable finding ID plus semantic deduplication key
   `(rule, location, evidence)`.
6. Record target path, current revision/hash, build system and selected field.

## 3. Each review round

### 3.1 Load the framework

In the parent context, invoke `/sci-paper:paper` and read the normative standard. Record their
current versions/paths in `paper-baseline.md`. This provides policy, not a child verdict.

### 3.2 Isolated paper-review

Launch a worktree agent with a self-contained prompt:

- cold-read the current target and all sources;
- read the reference report the parent produced for this round with
  `python tools/verify_references.py <bib> --tex <target> --format json --output
  <round>/references.json` (an unresolvable identifier or a cited key with no entry is an
  integrity blocker; unmeasured entries stay visible) and judge relevance, which no
  registry measures, for every entry;
- invoke `/sci-paper:paper-review <target> --orchestrated --field <field>`;
- do not spawn any child agent (M.2 escalation runs in-process);
- return the complete typed report, including A–R coverage (dimension E narrative-spine
  answers and dimension M record included), measurement states, blockers, L0 targets,
  strong/ordinary advisories, dispositions and build evidence;
- set physics, mainline and logic to `SKIPPED_FOR_ORCHESTRATOR`.

If it attempts nesting, return `NESTED_AGENT_REJECTED`; the round becomes
`PROMPT_VIOLATION` and must be reissued with the corrected prompt.

### 3.3 Isolated figure-review

Launch a separate worktree agent to invoke `/sci-paper:figure-review` on the current compiled
paper. It must return:

- render/build measurement state;
- figure inventory and source provenance;
- typed blockers and advisories (including canvas-balance measurements);
- explicit `not_applicable` if no figures exist.

It must not return literal PASS/WARN as the merge interface.

### 3.4 Isolated de-ai audit

Launch a separate worktree agent to invoke `/sci-paper:de-ai <target> --audit-only
--field <field>`. Audit-only runs Pass 1 (subsystem measurement) and Pass 2
(humanizer structural-tell audit) with no rewrite. It must return:

- the full `sci-paper.feedback.v1` measurement report with every axis state;
- L0 targets (Tier A / em-dash / Tier B excess) as `l0_target` findings;
- structural-tell and distribution findings as ranked advisories;
- document-shape findings with their fidelity-free partition suggestions,
  clearly marked apply-by-hand.

The parent applies L0 fixes and selected strong-advisory rewrites itself in §3.7
(or runs de-ai Pass 3 in the parent context); the auditor never edits.

### 3.5 Parent-level isolated measurement primitives

Launch one sibling worktree agent per primitive -- `/sci-paper:physics`,
`/sci-paper:mainline`, `/sci-paper:logic` -- never from inside paper-review. Each prompt
must instruct the agent to:

- cold-read all current sources;
- load and execute that primitive's protocol, and only that one;
- avoid spawning sub-agents;
- return each issue with evidence and a proposed consequence class;
- report disagreements with other reviewers without assuming the other reviewers are wrong;
- state unavailable checks explicitly.

Their scopes do not overlap by construction: physics owns first principles, logic owns
reasoning and statistics, mainline owns whether a cold reader can follow. A primitive that
restates another's checklist is a prompt error, not extra coverage.

Normalize each output to the shared finding schema. A disagreement is a finding candidate, not
an automatic blocker; verify the evidence and assign consequence.

### 3.6 Merge and verify

Combine all child reports into one registry:

```text
registry = merge_by_stable_id_and_semantic_key(
    paper_review,
    figure_review,
    de_ai_audit,
    physics,
    mainline,
    logic,
)
```

For overlaps:

- retain every source trace and detector;
- keep the most severe consequence only when evidence supports it;
- record reviewer disagreement rather than silently choosing one;
- do not parse JSON from human-readable prose;
- totals come from the merged structured findings.

The parent verifies any finding before editing its target. A child's REFUTED result remains a
positive evidence record; a CONFIRMED editorial critique remains an advisory.

### 3.7 Apply fixes and dispositions

Order work by the unified priority key:

1. integrity blockers;
2. L0 targets;
3. strong advisories;
4. ordinary advisories only when authorized or clearly part of a blocker/L0 repair.

For each action:

- map it to finding IDs;
- read the target and source evidence;
- apply the minimum effective edit (dimension-I redundancy findings route to
  `/sci-paper:condense`; structural-tell rewrites follow de-ai Pass 3 discipline);
- re-read affected context;
- rerun the relevant build, scientific check, figure render, linter or claim-fidelity check;
- record `acted`, `accepted`, `rejected_as_false_positive` or `pending`.

Subjective strong advisories that require author preference may remain pending with a precise
question. Do not erase them merely to make counts zero.

## 4. Stable-round criterion

A round is **disposition-complete** when:

- pending integrity blockers = 0;
- pending L0 targets = 0;
- critical derivations under scrutiny = 0;
- required build/artifacts are valid;
- every strong advisory has a disposition or stated pending reason;
- ordinary advisories and unmeasured/degraded axes are reported;
- skipped reviewers are labeled unmeasured;
- no child report or merge failed.

A stable round additionally requires:

- no new blocker or L0 target relative to the previous complete round;
- no previously resolved blocker/L0 reappears;
- strong-advisory set and dispositions are unchanged or the change is explained by new evidence;
- scientific anchors and build outputs remain current.

Increment `consecutive_stable_rounds` only for stable disposition-complete rounds. Reset it when
new blockers/L0 targets appear, a required measurement fails, or a disposition changes without
new evidence. When it reaches `--require-consecutive`, return `DISPOSITION_COMPLETE`.

The de-ai audit may continue to report ordinary distribution advisories; those do not reset
stability unless they expose a new blocker/L0 or a new strong advisory requiring disposition.

## 5. Failure and budget handling

- Child failure/timeout: retry only after diagnosing the cause; repeated failure returns
  `SUBAGENT_FAILURE` with that axis unmeasured.
- Nested-agent attempt or wrong primitive ownership: `PROMPT_VIOLATION`.
- User skip: record `unmeasured` and continue under explicit limitation.
- `--max-rounds` exhausted: `BREAK_WITH_USER_DECISION`; list pending blockers, L0 targets,
  strong advisories, failed/unmeasured axes and options. Do not increase the budget or claim
  completion.
- User interruption: preserve all current reports and registry.

## 6. Final report contract

```markdown
# Final Review — Disposition-Complete Report
Target: <file> | Revision: <hash> | Field: <field or none>
Workflow state: DISPOSITION_COMPLETE | BREAK_WITH_USER_DECISION | SUBAGENT_FAILURE
Rounds: K | Consecutive stable rounds: N

## Measurement coverage
| reviewer/axis | status | provenance / limitation |

## Merged summary
- integrity blockers: resolved / pending
- L0 targets: resolved / pending
- strong advisories: acted / accepted / false-positive / pending
- ordinary advisories: total / reported
- M derivations: verified / under scrutiny
- build and figure render status

## Ranked merged findings
| id | source reviewers | kind | layer | rule | location | evidence | action | disposition |

## Scientific anchors
| claim/quantity | manuscript | source | verification |

## Reviewer disagreements
<evidence from each side and final consequence/disposition>

## Residual feedback
- pending strong advisories and author questions
- ordinary advisories
- degraded/unmeasured/not_applicable axes
- explicit skips

## Fix trace by round
<finding IDs, before/after, verification>

## Per-reviewer reports
<links or verbatim reports; preserve structured JSON beside them>
```

Do not show a per-skill PASS table. "No findings under measured axes" is not proof about
unmeasured axes.

## 7. Completion meaning

`DISPOSITION_COMPLETE` means the mandated review workflow reached a stable state in which:

- scientific blockers were resolved or disproved;
- L0 targets are zero;
- strong advisories have explicit author/process dispositions;
- ordinary residuals and limitations are visible;
- independent reviewers reproduced that state for the required consecutive rounds.

It does not mean the paper is guaranteed correct, accepted, human-authored, aesthetically
unique or free of every possible reviewer objection.

## 8. Anti-patterns

- Reusing last round's report without rerunning isolated reviewers.
- Allowing paper-review to spawn a nested primitive under `--orchestrated`.
- Treating every child CONFIRMED critique as a blocker.
- Treating every advisory or reviewer disagreement as mandatory prose change.
- Requiring figure-review to return PASS.
- Requiring the narrative-spine protocol (paper-review dimension E) to find exactly one
  contribution thread.
- Letting the de-ai auditor edit the manuscript instead of returning findings.
- Adding condense as a fifth review lane (its detection surface is paper-review dimension I).
- Calling missing calibration a clean result.
- Resetting or dropping inconvenient findings during deduplication.
- Declaring completion because all numeric issue counts are zero while axes were skipped.
- Forcing subjective advisories to disappear instead of recording author disposition.
- Increasing iteration budget silently.
